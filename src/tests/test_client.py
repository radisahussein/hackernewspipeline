"""Tests for HNClient — all HTTP mocked, never hits real API."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ingestion.client import fetch_stories, _parse_story


def _make_response(hits: list, nb_pages: int = 1, status: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.json.return_value = {"hits": hits, "nbPages": nb_pages}
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


def _make_hit(
    object_id: str = "1",
    title: str = "Test story",
    created_at: str = "2024-01-15T10:00:00.000Z",
    points: int = 10,
    num_comments: int = 5,
    url: str = "https://example.com",
) -> dict:
    return {
        "objectID": object_id,
        "title": title,
        "created_at": created_at,
        "points": points,
        "num_comments": num_comments,
        "url": url,
    }


# --- _parse_story unit tests ---

def test_parse_story_valid_hit_returns_dict():
    hit = _make_hit(object_id="42", title="Rust 2.0 released")
    result = _parse_story(hit)
    assert result is not None
    assert result["story_id"] == 42
    assert result["title"] == "Rust 2.0 released"
    assert result["score"] == 10
    assert result["num_comments"] == 5


def test_parse_story_missing_title_returns_none():
    hit = _make_hit()
    hit["title"] = None
    assert _parse_story(hit) is None


def test_parse_story_missing_id_returns_none():
    hit = _make_hit()
    hit["objectID"] = None
    assert _parse_story(hit) is None


def test_parse_story_non_integer_id_returns_none():
    hit = _make_hit()
    hit["objectID"] = "not-a-number"
    assert _parse_story(hit) is None


def test_parse_story_null_score_defaults_to_zero():
    hit = _make_hit()
    hit["points"] = None
    result = _parse_story(hit)
    assert result is not None
    assert result["score"] == 0


# --- fetch_stories integration tests (mocked HTTP) ---

@pytest.mark.asyncio
async def test_fetch_stories_single_page_returns_stories():
    hits = [_make_hit(object_id=str(i), title=f"Story {i}") for i in range(3)]
    mock_resp = _make_response(hits, nb_pages=1)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_resp

        result = await fetch_stories(since_ts=0)

    assert len(result) == 3
    assert result[0]["story_id"] == 0
    assert result[2]["story_id"] == 2


@pytest.mark.asyncio
async def test_fetch_stories_paginates_until_nb_pages_exhausted():
    page1_hits = [_make_hit(object_id="1", title="P1")]
    page2_hits = [_make_hit(object_id="2", title="P2")]

    resp1 = _make_response(page1_hits, nb_pages=2)
    resp2 = _make_response(page2_hits, nb_pages=2)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.side_effect = [resp1, resp2]

        result = await fetch_stories(since_ts=0)

    assert len(result) == 2
    assert mock_client.get.call_count == 2


@pytest.mark.asyncio
async def test_fetch_stories_retries_on_429():
    hits = [_make_hit()]
    throttled = _make_response([], status=429)
    ok_resp = _make_response(hits, nb_pages=1)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.side_effect = [throttled, ok_resp]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await fetch_stories(since_ts=0)

    assert len(result) == 1
    assert mock_client.get.call_count == 2


@pytest.mark.asyncio
async def test_fetch_stories_stops_on_empty_hits():
    resp = _make_response([], nb_pages=5)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = resp

        result = await fetch_stories(since_ts=0)

    assert result == []
    assert mock_client.get.call_count == 1


@pytest.mark.asyncio
async def test_fetch_stories_skips_hits_with_missing_title():
    hits = [
        _make_hit(object_id="1", title="Valid story"),
        {**_make_hit(object_id="2"), "title": None},
    ]
    mock_resp = _make_response(hits, nb_pages=1)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_resp

        result = await fetch_stories(since_ts=0)

    assert len(result) == 1
    assert result[0]["story_id"] == 1


@pytest.mark.asyncio
async def test_fetch_stories_until_ts_included_in_request():
    hits = [_make_hit()]
    mock_resp = _make_response(hits, nb_pages=1)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_resp

        await fetch_stories(since_ts=1000, until_ts=2000)

    call_kwargs = mock_client.get.call_args
    params = call_kwargs[1]["params"]
    assert "2000" in params["numericFilters"]
    assert "1000" in params["numericFilters"]
