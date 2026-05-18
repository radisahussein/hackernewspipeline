"""Tests for DuckDBStore — all use in-memory DB."""
import datetime

import pytest

from storage.db import DuckDBStore


@pytest.fixture
def db():
    store = DuckDBStore(db_path=":memory:")
    yield store
    store.close()


def _story(story_id: int, title: str = "Test", score: int = 10, num_comments: int = 5) -> dict:
    return {
        "story_id": story_id,
        "title": title,
        "url": f"https://example.com/{story_id}",
        "score": score,
        "num_comments": num_comments,
        "created_at": "2024-01-15T10:00:00.000Z",
    }


def test_init_schema_creates_tables(db):
    tables = db._conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
    ).fetchall()
    table_names = {row[0] for row in tables}
    assert "raw_stories" in table_names
    assert "keyword_events" in table_names
    assert "weekly_mentions" in table_names
    assert "keyword_velocity" in table_names


def test_insert_stories_returns_inserted_count(db):
    stories = [_story(1), _story(2), _story(3)]
    inserted = db.insert_stories(stories)
    assert inserted == 3


def test_insert_stories_dedup_on_story_id(db):
    stories = [_story(1), _story(2)]
    db.insert_stories(stories)
    inserted = db.insert_stories([_story(1), _story(3)])
    assert inserted == 1  # only story 3 is new


def test_insert_stories_empty_list_returns_zero(db):
    assert db.insert_stories([]) == 0


def test_get_last_fetched_at_empty_db_returns_zero(db):
    assert db.get_last_fetched_at() == 0


def test_get_last_fetched_at_returns_max_created_at(db):
    db._conn.execute(
        "INSERT INTO raw_stories (story_id, title, created_at, score, num_comments) VALUES (1, 'A', '2024-06-15 10:00:00', 0, 0)"
    )
    db._conn.execute(
        "INSERT INTO raw_stories (story_id, title, created_at, score, num_comments) VALUES (2, 'B', '2024-06-20 10:00:00', 0, 0)"
    )
    ts = db.get_last_fetched_at()
    expected = int(datetime.datetime(2024, 6, 20, 10, 0, 0).timestamp())
    assert ts == expected


def test_row_count_returns_correct_count(db):
    db.insert_stories([_story(1), _story(2)])
    assert db.row_count("raw_stories") == 2


def test_insert_stories_sets_fetched_at(db):
    db.insert_stories([_story(1)])
    row = db._conn.execute("SELECT fetched_at FROM raw_stories WHERE story_id=1").fetchone()
    assert row[0] is not None


def test_insert_stories_null_score_defaults_to_zero(db):
    story = _story(1)
    story["score"] = None
    db.insert_stories([story])
    row = db._conn.execute("SELECT score FROM raw_stories WHERE story_id=1").fetchone()
    assert row[0] == 0
