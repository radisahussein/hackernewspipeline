"""One-time backfill: fetch 2 years of HN stories into DuckDB."""
import asyncio
import datetime
import logging

from ingestion.client import fetch_stories
from storage.db import DuckDBStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

WINDOW_DAYS = 7
YEARS_BACK = 2


async def backfill() -> None:
    now = datetime.datetime.now(datetime.UTC)
    start = now - datetime.timedelta(days=YEARS_BACK * 365)

    with DuckDBStore() as db:
        cursor = start
        total = 0
        while cursor < now:
            window_end = min(cursor + datetime.timedelta(days=WINDOW_DAYS), now)
            since_ts = int(cursor.timestamp())
            until_ts = int(window_end.timestamp())

            stories = await fetch_stories(since_ts=since_ts, until_ts=until_ts)
            inserted = db.insert_stories(stories)
            total += inserted
            iso_week = cursor.strftime("%Y-W%W")
            log.info(
                "Fetched %s → %s (%s): %d fetched, %d new",
                cursor.date(), window_end.date(), iso_week, len(stories), inserted,
            )

            cursor = window_end

        log.info("Backfill complete. Total inserted: %d", total)


if __name__ == "__main__":
    asyncio.run(backfill())
