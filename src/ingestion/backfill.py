"""One-time backfill: fetch 2 years of HN stories into DuckDB."""
import asyncio
import datetime
import logging

from ingestion.client import fetch_stories, fetch_stories_with_count
from storage.db import DuckDBStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

# 1-day windows keep each query under Algolia's 1000-hit retrieval cap
# (~300-500 HN stories/day on average)
WINDOW_HOURS = 24
YEARS_BACK = 2


async def backfill() -> None:
    now = datetime.datetime.now(datetime.UTC)
    start = now - datetime.timedelta(days=YEARS_BACK * 365)

    with DuckDBStore() as db:
        cursor = start
        total = 0
        windows = 0
        while cursor < now:
            window_end = min(cursor + datetime.timedelta(hours=WINDOW_HOURS), now)
            since_ts = int(cursor.timestamp())
            until_ts = int(window_end.timestamp())

            stories, nb_hits = await fetch_stories_with_count(since_ts=since_ts, until_ts=until_ts)
            if nb_hits >= 1000:
                log.warning(
                    "Window %s → %s hit Algolia cap (nbHits=%d) — some stories may be missing. "
                    "Consider reducing WINDOW_HOURS.",
                    cursor.date(), window_end.date(), nb_hits,
                )
            inserted = db.insert_stories(stories)
            total += inserted
            windows += 1
            if windows % 30 == 0:
                log.info(
                    "Progress: %s → %s | fetched=%d new=%d total=%d",
                    cursor.date(), window_end.date(), len(stories), inserted, total,
                )

            cursor = window_end

        log.info("Backfill complete. Windows=%d total inserted=%d", windows, total)


if __name__ == "__main__":
    asyncio.run(backfill())
