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

## cd40436 — 2026-05-18
**Done:** Added `taxonomy.py` — 150+ terms across 6 categories, `AMBIGUOUS` patterns with `re.IGNORECASE`, precompiled `_SIMPLE_PATTERNS` and `_AMBIGUOUS_PATTERNS`.
**Next:** Implement `detect_keywords` function.

## 66273c2 — 2026-05-18
**Done:** Added `detector.py` — `detect_keywords(title, url)` with word-boundary regex, URL path extraction converting hyphens/slashes to spaces for matching.
**Next:** Tests for detector.

## a4cd647 — 2026-05-18
**Done:** 22 detector tests covering Rust false positives ("rusty"), Go false positives ("going", "go to", "go ahead", "go back"), URL path matching, multi-keyword, dedup, edge cases.
**Next:** Batch keyword pipeline and TF-IDF discovery.

## 9f7d2bc — 2026-05-18
**Done:** Added `keyword_pipeline.py` (batch 10k-story processor writing to `keyword_events`) and `tfidf_discovery.py` (sklearn TF-IDF on weekly corpus, top-20 non-taxonomy terms).
**Next:** Phase 2 complete. Phase 3 — aggregation, hype scoring, anomaly detection.

---

## Phase 2 complete — 2026-05-18
**Done:**
- `taxonomy.py`: 150+ terms, 6 categories, precompiled regex patterns with IGNORECASE; AMBIGUOUS dict for Go/Rust/R/C/RAG/MCP
- `detector.py`: `detect_keywords(title, url)` — word-boundary regex + URL path extraction
- `keyword_pipeline.py`: batch processor, 10k-story chunks, skips already-processed stories
- `tfidf_discovery.py`: TF-IDF on weekly title corpus, surfaces top-20 unlisted emerging terms
- 22 detector tests — explicit false positives for Go/Rust; all 41 suite tests pass twice

**Next:**
- Create `phase/3-scoring` branch from `stage` (after merge)
- Implement `weekly_agg.py` — SQL rollup into `weekly_mentions`
- Implement `hype_score.py` — 0–100 composite (0.5×mentions + 0.3×weighted_score + 0.2×avg_comments)
- Implement `velocity.py` — z-score on 12-week rolling avg, `is_trending`/`is_crashing` flags
- Write `test_aggregation.py` and `test_anomaly.py`

## 07324ba — 2026-05-18
**Done:** Added `weekly_agg.py` — SQL rollup of `keyword_events + raw_stories` into `weekly_mentions` (mention_count, weighted_score, avg_comments) per keyword per ISO week.
**Next:** Hype score normalization.

## d2114fb — 2026-05-18
**Done:** Added `hype_score.py` — min-max normalizes mention_count/weighted_score/avg_comments across all keywords per week, writes composite hype_score (0.5×mentions + 0.3×weighted + 0.2×comments).
**Next:** Velocity and z-score anomaly.

## 09d26bc — 2026-05-18
**Done:** Added `velocity.py` — WoW % velocity, 12-week rolling z-score, `is_trending`/`is_crashing` flags. Handles flat-baseline std=0 via proportional synthetic z-score (50% change → |z|=2).
**Next:** Tests.

## f481397 — 2026-05-18
**Done:** 14 tests across `test_aggregation.py` and `test_anomaly.py` — mention count, weighted score, avg comments, hype range 0–100, spike/crash z-score flags, stable week not flagged, velocity sign.
**Next:** Phase 3 complete. Phase 4 — Prefect orchestration.

---

## Phase 3 complete — 2026-05-18
**Done:**
- `weekly_agg.py`: SQL rollup → `weekly_mentions` with mention_count, weighted_score, avg_comments
- `hype_score.py`: min-max normalization per week, composite score with 0.5/0.3/0.2 weights
- `velocity.py`: WoW velocity %, 12-week rolling z-score, is_trending/is_crashing; flat-baseline handled via proportional synthetic z
- 14 tests (7 agg, 7 anomaly) — 55 total suite tests pass twice

**Next:**
- Create `phase/4-orchestration` branch from `stage` (after merge)
- Implement Prefect `@flow` + `@task` in `src/pipeline/flow.py`
- Tasks: fetch, keyword detection, weekly agg (last 2 weeks), hype scores, velocity, quality checks
- Quality checks: assert new_stories > 0, keyword_events grew, max(created_at) < 26h ago
- Deploy notes to README (Prefect Cloud free tier setup)

## c140dbf — 2026-05-18
**Done:** Added `pipeline/flow.py` — Prefect `@flow` + 6 `@task` (fetch, detect, aggregate, hype, velocity, quality checks). Quality checks assert: new stories >0, keyword_events not empty, max(created_at) <26h.
**Next:** Phase 4 complete. Phase 5 — Streamlit dashboard.

---

## Phase 4 complete — 2026-05-18
**Done:**
- `pipeline/flow.py`: `daily_pipeline()` Prefect flow orchestrating full ETL + quality gates
- 6 tasks with retries (fetch 3×, transforms 2×, quality check 1×)
- Quality assertions: HN API liveness, detector health, data freshness (26h SLA)
- `_current_and_prev_iso_weeks()` ensures last 2 weeks always recomputed
- All 55 tests still pass

**Next:**
- Create `phase/5-dashboard` branch from `stage` (after merge)
- Implement `src/dashboard/app.py` — Streamlit 3-tab layout (Trending Now, Hype Cycles, Emerging Terms)
- Sidebar: category filter, time window, last pipeline run metadata
- Tab 1: top 5 risers/fallers by velocity, anomaly feed with HN story links
- Tab 2: multi-keyword hype cycle line chart, anomaly markers, compare mode
- Tab 3: TF-IDF emerging terms table
- Add `@st.cache_data(ttl=3600)` on all query functions
- Write `test_dashboard.py` (query layer only)

