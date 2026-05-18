"""Batch keyword detection over raw_stories not yet in keyword_events."""
import logging

from storage.db import DuckDBStore
from transforms.detector import detect_keywords
from transforms.taxonomy import KEYWORD_TO_CATEGORY

log = logging.getLogger(__name__)

BATCH_SIZE = 10_000


def run_keyword_pipeline(db: DuckDBStore) -> int:
    """Detect keywords for all unprocessed stories. Returns total hits written."""
    unprocessed = db._conn.execute("""
        SELECT rs.story_id, rs.title, rs.url, rs.score, rs.created_at
        FROM raw_stories rs
        WHERE rs.story_id NOT IN (SELECT DISTINCT story_id FROM keyword_events)
        ORDER BY rs.story_id
    """).fetchall()

    total_hits = 0
    batch: list[tuple] = []

    for story_id, title, url, score, created_at in unprocessed:
        keywords = detect_keywords(title, url)
        for kw in keywords:
            category = KEYWORD_TO_CATEGORY.get(kw, "Unknown")
            batch.append((story_id, kw, category, score, created_at))

        if len(batch) >= BATCH_SIZE:
            db._conn.executemany(
                "INSERT INTO keyword_events (story_id, keyword, category, score, created_at) VALUES (?, ?, ?, ?, ?)",
                batch,
            )
            total_hits += len(batch)
            batch = []

    if batch:
        db._conn.executemany(
            "INSERT INTO keyword_events (story_id, keyword, category, score, created_at) VALUES (?, ?, ?, ?, ?)",
            batch,
        )
        total_hits += len(batch)

    log.info("keyword_pipeline: %d stories processed, %d keyword hits written", len(unprocessed), total_hits)
    return total_hits
