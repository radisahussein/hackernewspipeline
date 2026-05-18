import asyncio
import time
from typing import Any

import httpx

BASE_URL = "https://hn.algolia.com/api/v1/search_by_date"
MAX_RETRIES = 3


async def _fetch_page(
    client: httpx.AsyncClient,
    since_ts: int,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    params = {
        "tags": "story",
        "numericFilters": f"created_at_i>{since_ts}",
        "hitsPerPage": page_size,
        "page": page,
    }
    delay = 1.0
    for attempt in range(MAX_RETRIES):
        resp = await client.get(BASE_URL, params=params, timeout=30.0)
        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt == MAX_RETRIES - 1:
                resp.raise_for_status()
            await asyncio.sleep(delay)
            delay *= 2
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError("unreachable")


def _parse_story(hit: dict[str, Any]) -> dict[str, Any] | None:
    story_id = hit.get("objectID")
    title = hit.get("title")
    if not story_id or not title:
        return None
    try:
        story_id = int(story_id)
    except (TypeError, ValueError):
        return None
    return {
        "story_id": story_id,
        "title": title,
        "url": hit.get("url"),
        "score": hit.get("points") or 0,
        "num_comments": hit.get("num_comments") or 0,
        "created_at": hit.get("created_at"),
        "fetched_at": None,
    }


async def fetch_stories(since_ts: int, page_size: int = 1000) -> list[dict[str, Any]]:
    """Fetch all stories created after since_ts (Unix timestamp)."""
    now = int(time.time())
    stories: list[dict[str, Any]] = []

    async with httpx.AsyncClient() as client:
        page = 0
        while True:
            data = await _fetch_page(client, since_ts, page, page_size)
            hits = data.get("hits", [])
            nb_pages = data.get("nbPages", 1)

            for hit in hits:
                story = _parse_story(hit)
                if story is None:
                    continue
                # stop if we've gone past "now" (shouldn't happen, but guard)
                import datetime
                if story["created_at"]:
                    try:
                        ts = int(datetime.datetime.fromisoformat(
                            story["created_at"].replace("Z", "+00:00")
                        ).timestamp())
                        if ts > now:
                            continue
                    except (ValueError, AttributeError):
                        pass
                stories.append(story)

            page += 1
            if page >= nb_pages or not hits:
                break

    return stories
