"""Daily incremental fetch: pull only stories newer than last_fetched_at."""
import asyncio
import datetime
import logging

from ingestion.client import fetch_stories
from storage.db import DuckDBStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)


async def incremental_fetch() -> int:
    with DuckDBStore() as db:
        since_ts = db.get_last_fetched_at()
        until_ts = int(datetime.datetime.now(datetime.UTC).timestamp())
        since_dt = datetime.datetime.fromtimestamp(since_ts, tz=datetime.UTC) if since_ts else "beginning"
        log.info("Fetching stories since %s", since_dt)

        stories = await fetch_stories(since_ts=since_ts, until_ts=until_ts)
        inserted = db.insert_stories(stories)
        log.info("Fetched %d new stories since %s", inserted, since_dt)
        return inserted


if __name__ == "__main__":
    asyncio.run(incremental_fetch())
