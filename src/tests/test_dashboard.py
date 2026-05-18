"""Tests for dashboard query layer — no Streamlit UI, just the data functions."""
import sys
from pathlib import Path

import pytest

from storage.db import DuckDBStore

# Patch DEFAULT_DB_PATH before importing dashboard so it doesn't open hn.duckdb
import storage.db as _db_mod

_ORIG_DEFAULT = _db_mod.DEFAULT_DB_PATH


@pytest.fixture(autouse=True)
def patch_db_path(tmp_path, monkeypatch):
    """Redirect dashboard queries to a fresh in-memory store for each test."""
    _store = DuckDBStore(db_path=":memory:")
    _populate_test_data(_store)
    # dashboard functions use _connect() which opens DB_PATH — patch module-level constant
    import dashboard.app as app_mod
    monkeypatch.setattr(app_mod, "DB_PATH", ":memory:")
    # Monkey-patch _connect to return the in-memory connection
    monkeypatch.setattr(app_mod, "_connect", lambda: _store._conn)
    yield _store
    _store.close()


def _populate_test_data(db: DuckDBStore) -> None:
    ISO_WEEK = "2024-W03"
    # Insert 5 stories
    for i in range(1, 6):
        db._conn.execute(
            "INSERT INTO raw_stories (story_id, title, score, num_comments, created_at) VALUES (?, ?, ?, ?, ?)",
            [i, f"Story about Rust {i}", 100 * i, 10 * i, "2024-01-15 10:00:00"],
        )
        db._conn.execute(
            "INSERT INTO keyword_events (story_id, keyword, category, score, created_at) VALUES (?, ?, ?, ?, ?)",
            [i, "Rust", "Languages", 100 * i, "2024-01-15 10:00:00"],
        )

    db._conn.execute(
        "INSERT OR REPLACE INTO weekly_mentions (keyword, iso_week, mention_count, weighted_score, avg_comments, hype_score) VALUES (?, ?, ?, ?, ?, ?)",
        ["Rust", ISO_WEEK, 5, 300.0, 30.0, 75.0],
    )
    db._conn.execute(
        "INSERT OR REPLACE INTO weekly_mentions (keyword, iso_week, mention_count, weighted_score, avg_comments, hype_score) VALUES (?, ?, ?, ?, ?, ?)",
        ["Python", ISO_WEEK, 3, 150.0, 15.0, 45.0],
    )
    db._conn.execute(
        "INSERT OR REPLACE INTO keyword_velocity (keyword, iso_week, velocity, rolling_avg, z_score, is_trending, is_crashing) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ["Rust", ISO_WEEK, 25.0, 60.0, 2.5, True, False],
    )
    db._conn.execute(
        "INSERT OR REPLACE INTO keyword_velocity (keyword, iso_week, velocity, rolling_avg, z_score, is_trending, is_crashing) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ["Python", ISO_WEEK, -5.0, 50.0, -0.3, False, False],
    )


ISO_WEEK = "2024-W03"


def test_get_trending_keywords_returns_list_of_dicts(patch_db_path):
    import dashboard.app as app
    result = app.get_trending_keywords.__wrapped__(ISO_WEEK)
    assert isinstance(result, list)
    assert len(result) > 0
    assert "keyword" in result[0]
    assert "velocity" in result[0]
    assert "hype_score" in result[0]


def test_get_trending_keywords_ordered_by_velocity_desc(patch_db_path):
    import dashboard.app as app
    result = app.get_trending_keywords.__wrapped__(ISO_WEEK)
    velocities = [r["velocity"] for r in result]
    assert velocities == sorted(velocities, reverse=True)


def test_get_hype_cycle_returns_dataframe_with_expected_keys(patch_db_path):
    import dashboard.app as app
    df = app.get_hype_cycle.__wrapped__("Rust", n_weeks=12)
    assert not df.empty
    assert "iso_week" in df.columns
    assert "hype_score" in df.columns
    assert df["hype_score"].notna().all()


def test_get_hype_cycle_respects_n_weeks_limit(patch_db_path):
    import dashboard.app as app
    df = app.get_hype_cycle.__wrapped__("Rust", n_weeks=12)
    assert len(df) <= 12


def test_get_available_keywords_returns_sorted_list(patch_db_path):
    import dashboard.app as app
    keywords = app.get_available_keywords.__wrapped__()
    assert isinstance(keywords, list)
    assert len(keywords) >= 2
    assert keywords == sorted(keywords)


def test_get_latest_week_returns_string(patch_db_path):
    import dashboard.app as app
    week = app.get_latest_week.__wrapped__()
    assert isinstance(week, str)
    assert "W" in week


def test_get_pipeline_metadata_returns_count(patch_db_path):
    import dashboard.app as app
    meta = app.get_pipeline_metadata.__wrapped__()
    assert meta["total_stories"] == 5


def test_get_hype_cycle_unknown_keyword_returns_empty(patch_db_path):
    import dashboard.app as app
    df = app.get_hype_cycle.__wrapped__("Nonexistent_Tech_9999", n_weeks=12)
    assert df.empty
