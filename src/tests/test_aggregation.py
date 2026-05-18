"""Tests for weekly aggregation and hype score computation."""
import pytest

from storage.db import DuckDBStore
from transforms.weekly_agg import run_weekly_aggregation
from transforms.hype_score import compute_hype_scores


@pytest.fixture
def db():
    store = DuckDBStore(db_path=":memory:")
    yield store
    store.close()


def _insert_story(db, story_id, score, num_comments, iso_week_date="2024-01-15"):
    db._conn.execute(
        "INSERT INTO raw_stories (story_id, title, score, num_comments, created_at) VALUES (?, ?, ?, ?, ?)",
        [story_id, f"Story {story_id}", score, num_comments, f"{iso_week_date} 10:00:00"],
    )


def _insert_keyword_event(db, story_id, keyword, score, iso_week_date="2024-01-15"):
    db._conn.execute(
        "INSERT INTO keyword_events (story_id, keyword, category, score, created_at) VALUES (?, ?, ?, ?, ?)",
        [story_id, keyword, "Languages", score, f"{iso_week_date} 10:00:00"],
    )


ISO_WEEK = "2024-W03"


def test_weekly_agg_correct_mention_count(db):
    _insert_story(db, 1, score=100, num_comments=10)
    _insert_story(db, 2, score=200, num_comments=20)
    _insert_keyword_event(db, 1, "Rust", score=100)
    _insert_keyword_event(db, 2, "Rust", score=200)

    run_weekly_aggregation(db, ISO_WEEK)

    row = db._conn.execute(
        "SELECT mention_count FROM weekly_mentions WHERE keyword='Rust' AND iso_week=?",
        [ISO_WEEK],
    ).fetchone()
    assert row is not None
    assert row[0] == 2


def test_weekly_agg_correct_weighted_score(db):
    _insert_story(db, 1, score=100, num_comments=10)
    _insert_story(db, 2, score=200, num_comments=20)
    _insert_keyword_event(db, 1, "Rust", score=100)
    _insert_keyword_event(db, 2, "Rust", score=200)

    run_weekly_aggregation(db, ISO_WEEK)

    row = db._conn.execute(
        "SELECT weighted_score FROM weekly_mentions WHERE keyword='Rust' AND iso_week=?",
        [ISO_WEEK],
    ).fetchone()
    assert row is not None
    assert abs(row[0] - 150.0) < 0.01  # (100+200)/2


def test_weekly_agg_correct_avg_comments(db):
    _insert_story(db, 1, score=100, num_comments=10)
    _insert_story(db, 2, score=200, num_comments=30)
    _insert_keyword_event(db, 1, "Python", score=100)
    _insert_keyword_event(db, 2, "Python", score=200)

    run_weekly_aggregation(db, ISO_WEEK)

    row = db._conn.execute(
        "SELECT avg_comments FROM weekly_mentions WHERE keyword='Python' AND iso_week=?",
        [ISO_WEEK],
    ).fetchone()
    assert row is not None
    assert abs(row[0] - 20.0) < 0.01


def test_weekly_agg_multiple_keywords(db):
    _insert_story(db, 1, score=50, num_comments=5)
    _insert_keyword_event(db, 1, "Go", score=50)
    _insert_keyword_event(db, 1, "Docker", score=50)

    run_weekly_aggregation(db, ISO_WEEK)

    rows = db._conn.execute(
        "SELECT keyword FROM weekly_mentions WHERE iso_week=? ORDER BY keyword",
        [ISO_WEEK],
    ).fetchall()
    keywords = [r[0] for r in rows]
    assert "Go" in keywords
    assert "Docker" in keywords


def test_hype_score_within_0_100_range(db):
    # Insert 3 keywords with varied counts so normalization has range
    for i, (kw, mentions, score, comments) in enumerate([
        ("Python", 100, 500, 50),
        ("Rust",   50,  200, 20),
        ("Go",     10,  100, 5),
    ]):
        for j in range(mentions if i == 0 else (50 if i == 1 else 10)):
            sid = i * 1000 + j
            _insert_story(db, sid, score=score // max(mentions, 1), num_comments=comments // max(mentions, 1))
            _insert_keyword_event(db, sid, kw, score=score // max(mentions, 1))

    run_weekly_aggregation(db, ISO_WEEK)
    compute_hype_scores(db, ISO_WEEK)

    rows = db._conn.execute(
        "SELECT keyword, hype_score FROM weekly_mentions WHERE iso_week=?", [ISO_WEEK]
    ).fetchall()
    assert len(rows) >= 3
    for kw, hs in rows:
        assert hs is not None, f"{kw} has NULL hype_score"
        assert 0.0 <= hs <= 100.0, f"{kw} hype_score {hs} out of range"


def test_hype_score_highest_for_most_mentioned(db):
    # Python: 50 mentions, Go: 5 mentions — Python should score higher
    for j in range(50):
        _insert_story(db, j, score=100, num_comments=10)
        _insert_keyword_event(db, j, "Python", score=100)
    for j in range(50, 55):
        _insert_story(db, j, score=100, num_comments=10)
        _insert_keyword_event(db, j, "Go", score=100)

    run_weekly_aggregation(db, ISO_WEEK)
    compute_hype_scores(db, ISO_WEEK)

    python_score = db._conn.execute(
        "SELECT hype_score FROM weekly_mentions WHERE keyword='Python' AND iso_week=?", [ISO_WEEK]
    ).fetchone()[0]
    go_score = db._conn.execute(
        "SELECT hype_score FROM weekly_mentions WHERE keyword='Go' AND iso_week=?", [ISO_WEEK]
    ).fetchone()[0]
    assert python_score > go_score


def test_weekly_agg_no_data_returns_zero(db):
    count = run_weekly_aggregation(db, "2024-W99")
    assert count == 0
