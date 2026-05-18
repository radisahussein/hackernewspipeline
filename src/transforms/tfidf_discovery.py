"""TF-IDF based discovery of emerging tech terms not yet in taxonomy."""
import logging
import re

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from storage.db import DuckDBStore
from transforms.taxonomy import ALL_KEYWORDS

log = logging.getLogger(__name__)

MIN_DOC_FREQ = 5
TOP_N = 20
STOP_WORDS = "english"


def discover_emerging_terms(db: DuckDBStore, iso_week: str) -> list[dict]:
    """
    Run TF-IDF on story titles for the given ISO week.
    Returns top-N terms not already in TAXONOMY.
    """
    rows = db._conn.execute("""
        SELECT title
        FROM raw_stories
        WHERE strftime(created_at, '%Y-W%W') = ?
          AND title IS NOT NULL
    """, [iso_week]).fetchall()

    if not rows:
        log.warning("No stories found for week %s", iso_week)
        return []

    titles = [row[0] for row in rows]

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=MIN_DOC_FREQ,
        stop_words=STOP_WORDS,
        token_pattern=r"(?u)\b[A-Za-z][A-Za-z0-9.+#\-]{1,}\b",
    )
    try:
        matrix = vectorizer.fit_transform(titles)
    except ValueError:
        log.warning("TF-IDF failed for week %s (too few docs?)", iso_week)
        return []

    feature_names = vectorizer.get_feature_names_out()
    scores = matrix.sum(axis=0).A1

    known_lower = {kw.lower() for kw in ALL_KEYWORDS}

    results = []
    for term, score in sorted(zip(feature_names, scores), key=lambda x: -x[1]):
        if term.lower() in known_lower:
            continue
        results.append({"term": term, "iso_week": iso_week, "tfidf_score": float(score)})
        if len(results) >= TOP_N:
            break

    _write_emerging_terms(db, results)
    return results


def _write_emerging_terms(db: DuckDBStore, terms: list[dict]) -> None:
    db._conn.execute("""
        CREATE TABLE IF NOT EXISTS emerging_terms (
            term        TEXT,
            iso_week    TEXT,
            tfidf_score DOUBLE,
            PRIMARY KEY (term, iso_week)
        )
    """)
    rows = [(t["term"], t["iso_week"], t["tfidf_score"]) for t in terms]
    if rows:
        db._conn.executemany(
            "INSERT OR IGNORE INTO emerging_terms (term, iso_week, tfidf_score) VALUES (?, ?, ?)",
            rows,
        )
