import duckdb
import pytest

from storage.db import DuckDBStore


@pytest.fixture
def in_memory_db():
    """DuckDB in-memory store for tests."""
    store = DuckDBStore(db_path=":memory:")
    yield store
    store.close()
