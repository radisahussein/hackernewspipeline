"""Compute normalized hype scores for all keywords in a given ISO week."""
import logging

import pandas as pd

from storage.db import DuckDBStore

log = logging.getLogger(__name__)


def _normalize_0_100(series: pd.Series) -> pd.Series:
    """Min-max normalize to 0–100. Returns 50 if all values are equal."""
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series([50.0] * len(series), index=series.index)
    return (series - mn) / (mx - mn) * 100


def compute_hype_scores(db: DuckDBStore, iso_week: str) -> int:
    """
    Normalize mention_count, weighted_score, avg_comments across all keywords
    for the given week and write composite hype_score (0–100).
    Returns number of rows updated.
    """
    rows = db._conn.execute("""
        SELECT keyword, mention_count, weighted_score, avg_comments
        FROM weekly_mentions
        WHERE iso_week = ?
    """, [iso_week]).fetchall()

    if not rows:
        return 0

    df = pd.DataFrame(rows, columns=["keyword", "mention_count", "weighted_score", "avg_comments"])

    df["norm_mentions"] = _normalize_0_100(df["mention_count"].astype(float))
    df["norm_weighted"] = _normalize_0_100(df["weighted_score"].astype(float))
    df["norm_comments"] = _normalize_0_100(df["avg_comments"].astype(float))

    df["hype_score"] = (
        0.5 * df["norm_mentions"]
        + 0.3 * df["norm_weighted"]
        + 0.2 * df["norm_comments"]
    )

    for _, row in df.iterrows():
        db._conn.execute(
            "UPDATE weekly_mentions SET hype_score = ? WHERE keyword = ? AND iso_week = ?",
            [round(float(row["hype_score"]), 4), row["keyword"], iso_week],
        )

    log.info("hype_score: week=%s updated=%d rows", iso_week, len(df))
    return len(df)
