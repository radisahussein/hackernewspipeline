# TechPulse — Progress Log

## 053b905 — 2026-05-18
**Done:** Initialized project layout with `pyproject.toml`, all deps (httpx, duckdb, pandas, prefect, scipy, scikit-learn, streamlit), and `src/` directory scaffold.
**Next:** Implement `HNClient` with pagination and retry logic.

## 9a06f2e — 2026-05-18
**Done:** Added `HNClient` (`src/ingestion/client.py`) with full pagination loop, exponential backoff on 429/5xx (3 retries), and story parsing with null guards.
**Next:** Tests for HNClient.

## 4497f1b — 2026-05-18
**Done:** 10 tests for `HNClient` covering pagination, 429 retry, empty-hits stop, and parse edge cases (null title, null ID, non-integer ID).
**Next:** Implement `DuckDBStore`.

## ab236f1 — 2026-05-18
**Done:** Added `DuckDBStore` (`src/storage/db.py`) — creates all 4 tables, idempotent upsert via `INSERT OR IGNORE`, `get_last_fetched_at()`, `row_count()`.
**Next:** Tests for DuckDBStore.

## 3829514 — 2026-05-18
**Done:** 9 DuckDB in-memory tests covering schema creation, insert count, dedup, empty insert, `last_fetched_at` on empty/populated DB, `fetched_at` write, and null score default.
**Next:** Backfill and incremental fetch scripts.

## 377e1f9 — 2026-05-18
**Done:** Added `backfill.py` (7-day window loop, 2-year range) and `incremental.py` (delta fetch using `last_fetched_at`).
**Next:** Phase 1 complete. Phase 2 — keyword detection system.

---

## Phase 1 complete — 2026-05-18
**Done:**
- Project scaffold: `pyproject.toml`, `uv` deps, `src/` layout with all module packages
- `HNClient` (`src/ingestion/client.py`): async pagination, exponential backoff on 429/5xx, story parsing with null guards
- `DuckDBStore` (`src/storage/db.py`): 4-table schema, idempotent upsert, `last_fetched_at`, `row_count`
- `backfill.py`: 7-day window loop over 2 years, idempotent
- `incremental.py`: delta fetch using `last_fetched_at`
- 19 tests (10 client, 9 storage) — all pass twice, no warnings

**Next:**
- Create `phase/2-keyword-detection` branch from `stage`
- Implement `TAXONOMY` dict (150+ terms, 6 categories) in `src/transforms/taxonomy.py`
- Implement `detect_keywords(title, url)` with word-boundary regex and ambiguous-term guards
- Implement `keyword_pipeline.py` batch processor
- Implement `tfidf_discovery.py` for emerging term detection
- Write `test_detector.py` with explicit false-positive cases for "Go"/"Rust"

