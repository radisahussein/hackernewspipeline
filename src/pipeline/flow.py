"""Prefect daily pipeline: fetch → detect → aggregate → score → anomaly → quality check."""
import asyncio
import datetime
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from prefect import flow, task, get_run_logger
from prefect.cache_policies import NO_CACHE

from ingestion.client import fetch_stories
from storage.db import DuckDBStore
from transforms.keyword_pipeline import run_keyword_pipeline
from transforms.weekly_agg import run_weekly_aggregation
from transforms.hype_score import compute_hype_scores
from transforms.velocity import compute_velocity


def _current_and_prev_iso_weeks() -> list[str]:
    today = datetime.date.today()
    weeks = []
    for delta in (0, 7):
        d = today - datetime.timedelta(days=delta)
        weeks.append(d.strftime("%Y-W%W"))
    return list(dict.fromkeys(weeks))  # deduplicate if same week


@task(retries=3, retry_delay_seconds=60, cache_policy=NO_CACHE)
async def fetch_new_stories(db: DuckDBStore) -> int:
    logger = get_run_logger()
    since_ts = db.get_last_fetched_at()
    stories = await fetch_stories(since_ts=since_ts)
    inserted = db.insert_stories(stories)
    logger.info("Fetched %d new stories", inserted)
    return inserted


@task(retries=3, retry_delay_seconds=60, cache_policy=NO_CACHE)
def run_keyword_detection(db: DuckDBStore) -> int:
    logger = get_run_logger()
    hits = run_keyword_pipeline(db)
    logger.info("Keyword detection: %d hits", hits)
    return hits


@task(retries=2, retry_delay_seconds=30, cache_policy=NO_CACHE)
def recompute_weekly_aggregates(db: DuckDBStore) -> None:
    logger = get_run_logger()
    for week in _current_and_prev_iso_weeks():
        count = run_weekly_aggregation(db, week)
        logger.info("Aggregated week=%s rows=%d", week, count)


@task(retries=2, retry_delay_seconds=30, cache_policy=NO_CACHE)
def update_hype_scores(db: DuckDBStore) -> None:
    logger = get_run_logger()
    for week in _current_and_prev_iso_weeks():
        count = compute_hype_scores(db, week)
        logger.info("Hype scores week=%s rows=%d", week, count)


@task(retries=2, retry_delay_seconds=30, cache_policy=NO_CACHE)
def update_velocity(db: DuckDBStore) -> None:
    logger = get_run_logger()
    for week in _current_and_prev_iso_weeks():
        count = compute_velocity(db, week)
        logger.info("Velocity week=%s rows=%d", week, count)


@task(cache_policy=NO_CACHE)
def run_quality_checks(db: DuckDBStore, new_stories_count: int) -> None:
    logger = get_run_logger()

    if new_stories_count == 0:
        raise ValueError("Quality check FAILED: no new stories fetched — HN API may be down")

    keyword_events_count = db.row_count("keyword_events")
    if keyword_events_count == 0:
        raise ValueError("Quality check FAILED: keyword_events is empty — detector produced zero hits")

    max_created_at = db._conn.execute(
        "SELECT MAX(created_at) FROM raw_stories"
    ).fetchone()[0]
    if max_created_at is not None:
        if isinstance(max_created_at, datetime.datetime):
            age_hours = (datetime.datetime.now(datetime.UTC) - max_created_at.replace(tzinfo=datetime.UTC)).total_seconds() / 3600
            if age_hours > 26:
                raise ValueError(
                    f"Quality check FAILED: most recent story is {age_hours:.1f}h old (threshold: 26h)"
                )

    logger.info(
        "Quality checks PASSED: new_stories=%d keyword_events=%d",
        new_stories_count,
        keyword_events_count,
    )


@flow(name="hn-tech-radar-daily", log_prints=True)
async def daily_pipeline() -> None:
    db = DuckDBStore()

    new_count = await fetch_new_stories(db)
    run_keyword_detection(db)
    recompute_weekly_aggregates(db)
    update_hype_scores(db)
    update_velocity(db)
    run_quality_checks(db, new_count)

    db.close()


if __name__ == "__main__":
    asyncio.run(daily_pipeline())
