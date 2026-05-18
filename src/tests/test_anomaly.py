"""Tests for z-score anomaly detection and velocity computation."""
import pytest

from storage.db import DuckDBStore
from transforms.velocity import compute_velocity


@pytest.fixture
def db():
    store = DuckDBStore(db_path=":memory:")
    yield store
    store.close()


def _seed_weekly_mention(db, keyword: str, iso_week: str, hype_score: float) -> None:
    db._conn.execute(
        """INSERT OR REPLACE INTO weekly_mentions
           (keyword, iso_week, mention_count, weighted_score, avg_comments, hype_score)
           VALUES (?, ?, 10, 50.0, 5.0, ?)""",
        [keyword, iso_week, hype_score],
    )


def _weeks(start_year: int, start_week: int, count: int) -> list[str]:
    weeks = []
    year, week = start_year, start_week
    for _ in range(count):
        weeks.append(f"{year}-W{week:02d}")
        week += 1
        if week > 52:
            week = 1
            year += 1
    return weeks


def test_spike_triggers_is_trending(db):
    # 12 weeks of baseline ~20, then week 13 spikes to 80
    weeks = _weeks(2024, 1, 13)
    for w in weeks[:12]:
        _seed_weekly_mention(db, "Rust", w, 20.0)
    _seed_weekly_mention(db, "Rust", weeks[12], 80.0)

    compute_velocity(db, weeks[12])

    row = db._conn.execute(
        "SELECT z_score, is_trending FROM keyword_velocity WHERE keyword='Rust' AND iso_week=?",
        [weeks[12]],
    ).fetchone()
    assert row is not None
    assert row[0] > 2.0
    assert row[1] is True


def test_crash_triggers_is_crashing(db):
    # 12 weeks of baseline ~60, then week 13 crashes to 5
    weeks = _weeks(2024, 1, 13)
    for w in weeks[:12]:
        _seed_weekly_mention(db, "Python", w, 60.0)
    _seed_weekly_mention(db, "Python", weeks[12], 5.0)

    compute_velocity(db, weeks[12])

    row = db._conn.execute(
        "SELECT z_score, is_crashing FROM keyword_velocity WHERE keyword='Python' AND iso_week=?",
        [weeks[12]],
    ).fetchone()
    assert row is not None
    assert row[0] < -2.0
    assert row[1] is True


def test_stable_week_not_flagged(db):
    weeks = _weeks(2024, 1, 13)
    for w in weeks[:12]:
        _seed_weekly_mention(db, "Docker", w, 40.0)
    _seed_weekly_mention(db, "Docker", weeks[12], 42.0)  # tiny change

    compute_velocity(db, weeks[12])

    row = db._conn.execute(
        "SELECT is_trending, is_crashing FROM keyword_velocity WHERE keyword='Docker' AND iso_week=?",
        [weeks[12]],
    ).fetchone()
    assert row is not None
    assert row[0] is False
    assert row[1] is False


def test_velocity_positive_on_increase(db):
    weeks = _weeks(2024, 1, 3)
    _seed_weekly_mention(db, "Go", weeks[0], 20.0)
    _seed_weekly_mention(db, "Go", weeks[1], 40.0)
    _seed_weekly_mention(db, "Go", weeks[2], 50.0)

    compute_velocity(db, weeks[2])

    row = db._conn.execute(
        "SELECT velocity FROM keyword_velocity WHERE keyword='Go' AND iso_week=?",
        [weeks[2]],
    ).fetchone()
    assert row is not None
    assert row[0] > 0  # 50 > 40


def test_velocity_negative_on_decrease(db):
    weeks = _weeks(2024, 1, 3)
    _seed_weekly_mention(db, "TypeScript", weeks[0], 80.0)
    _seed_weekly_mention(db, "TypeScript", weeks[1], 60.0)
    _seed_weekly_mention(db, "TypeScript", weeks[2], 40.0)

    compute_velocity(db, weeks[2])

    row = db._conn.execute(
        "SELECT velocity FROM keyword_velocity WHERE keyword='TypeScript' AND iso_week=?",
        [weeks[2]],
    ).fetchone()
    assert row is not None
    assert row[0] < 0  # 40 < 60


def test_first_week_velocity_is_zero(db):
    _seed_weekly_mention(db, "Zig", "2024-W01", 30.0)
    compute_velocity(db, "2024-W01")

    row = db._conn.execute(
        "SELECT velocity FROM keyword_velocity WHERE keyword='Zig' AND iso_week='2024-W01'"
    ).fetchone()
    assert row is not None
    assert row[0] == 0.0


def test_is_trending_false_for_non_spiked_keywords(db):
    weeks = _weeks(2024, 1, 13)
    for w in weeks[:12]:
        _seed_weekly_mention(db, "Rust", w, 20.0)
        _seed_weekly_mention(db, "Python", w, 20.0)
    # Rust spikes, Python stays flat
    _seed_weekly_mention(db, "Rust", weeks[12], 80.0)
    _seed_weekly_mention(db, "Python", weeks[12], 21.0)

    compute_velocity(db, weeks[12])

    rust_row = db._conn.execute(
        "SELECT is_trending FROM keyword_velocity WHERE keyword='Rust' AND iso_week=?",
        [weeks[12]],
    ).fetchone()
    python_row = db._conn.execute(
        "SELECT is_trending FROM keyword_velocity WHERE keyword='Python' AND iso_week=?",
        [weeks[12]],
    ).fetchone()
    assert rust_row[0] is True
    assert python_row[0] is False
