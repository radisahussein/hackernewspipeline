"""Weekly rollup: keyword_events + raw_stories → weekly_mentions."""
import logging

from storage.db import DuckDBStore

log = logging.getLogger(__name__)


def run_weekly_aggregation(db: DuckDBStore, iso_week: str) -> int:
    """
    Compute weekly aggregates for the given ISO week and upsert into weekly_mentions.
    Returns number of rows written.
    """
    db._conn.execute("""
        INSERT OR REPLACE INTO weekly_mentions
            (keyword, iso_week, mention_count, weighted_score, avg_comments)
        SELECT
            ke.keyword,
            strftime(rs.created_at, '%Y-W%W')           AS iso_week,
            COUNT(*)                                     AS mention_count,
            CAST(SUM(rs.score) AS DOUBLE) / COUNT(*)    AS weighted_score,
            AVG(rs.num_comments)                         AS avg_comments
        FROM keyword_events ke
        JOIN raw_stories rs USING (story_id)
        WHERE strftime(rs.created_at, '%Y-W%W') = ?
        GROUP BY ke.keyword, iso_week
    """, [iso_week])

    count = db._conn.execute(
        "SELECT COUNT(*) FROM weekly_mentions WHERE iso_week = ?", [iso_week]
    ).fetchone()[0]
    log.info("weekly_agg: week=%s rows=%d", iso_week, count)
    return count


def run_weekly_aggregation_all(db: DuckDBStore) -> int:
    """Recompute aggregates for all weeks present in keyword_events."""
    weeks = db._conn.execute("""
        SELECT DISTINCT strftime(rs.created_at, '%Y-W%W')
        FROM keyword_events ke
        JOIN raw_stories rs USING (story_id)
        ORDER BY 1
    """).fetchall()

    total = 0
    for (week,) in weeks:
        total += run_weekly_aggregation(db, week)
    return total
