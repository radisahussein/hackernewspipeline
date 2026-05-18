import datetime
from pathlib import Path
from typing import Any

import duckdb

DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "hn.duckdb"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS raw_stories (
    story_id     INTEGER PRIMARY KEY,
    title        TEXT    NOT NULL,
    url          TEXT,
    score        INTEGER DEFAULT 0,
    num_comments INTEGER DEFAULT 0,
    created_at   TIMESTAMP,
    fetched_at   TIMESTAMP
);

CREATE TABLE IF NOT EXISTS keyword_events (
    story_id   INTEGER,
    keyword    TEXT,
    category   TEXT,
    score      INTEGER,
    created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS weekly_mentions (
    keyword        TEXT,
    iso_week       TEXT,
    mention_count  INTEGER,
    weighted_score DOUBLE,
    avg_comments   DOUBLE,
    hype_score     DOUBLE,
    PRIMARY KEY (keyword, iso_week)
);

CREATE TABLE IF NOT EXISTS keyword_velocity (
    keyword     TEXT,
    iso_week    TEXT,
    velocity    DOUBLE,
    rolling_avg DOUBLE,
    z_score     DOUBLE,
    is_trending BOOLEAN,
    is_crashing BOOLEAN,
    PRIMARY KEY (keyword, iso_week)
);
"""


class DuckDBStore:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self._path = str(db_path)
        self._conn = duckdb.connect(self._path)
        self.init_schema()

    def init_schema(self) -> None:
        self._conn.execute(SCHEMA_SQL)

    def get_last_fetched_at(self) -> int:
        """Return max created_at as Unix timestamp, or 0 if table is empty."""
        result = self._conn.execute(
            "SELECT MAX(created_at) FROM raw_stories"
        ).fetchone()
        if result is None or result[0] is None:
            return 0
        ts = result[0]
        if isinstance(ts, datetime.datetime):
            return int(ts.timestamp())
        return 0

    def insert_stories(self, stories: list[dict[str, Any]]) -> int:
        """Bulk-insert stories, ignore duplicates. Returns inserted row count."""
        if not stories:
            return 0

        now = datetime.datetime.now(datetime.UTC)
        rows = [
            (
                s["story_id"],
                s["title"],
                s.get("url"),
                s.get("score") or 0,
                s.get("num_comments") or 0,
                s.get("created_at"),
                now,
            )
            for s in stories
        ]

        before = self._conn.execute("SELECT COUNT(*) FROM raw_stories").fetchone()[0]
        self._conn.executemany(
            """
            INSERT OR IGNORE INTO raw_stories
                (story_id, title, url, score, num_comments, created_at, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        after = self._conn.execute("SELECT COUNT(*) FROM raw_stories").fetchone()[0]
        return after - before

    def row_count(self, table: str) -> int:
        return self._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def close(self) -> None:
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
