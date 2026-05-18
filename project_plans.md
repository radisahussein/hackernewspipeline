# Portfolio Project Plans

Four production-quality portfolio projects. Each scoped for solo build, free tiers only, deployable, and signal-rich for HR/hiring managers.

---

## Project 1: TechPulse — HN Tech Trend Radar

### The Problem

Most "data pipeline" portfolio projects are either toy ETL scripts with no UI, or dashboards with no real pipeline behind them. Hiring managers cannot tell if you understand the full lifecycle: ingestion, transformation, storage, and serving. The gap is **end-to-end ownership** — plus analytical depth that proves you can extract signal from noise.

### The Solution

A tech trend intelligence platform that ingests Hacker News stories and comments daily via the Algolia HN API (free, no key required), runs keyword detection across a curated taxonomy of 150+ tech terms, computes weekly "hype scores" per technology, and serves a live dashboard showing which technologies are rising, peaking, or dying — with anomaly detection that flags overnight viral spikes.

**Why this beats WeatherFlow:** weather data is passive — the insight is obvious (temperature anomaly). TechPulse requires *building* the signal: defining what "trending" means, extracting keywords from unstructured text, combining frequency + engagement + recency into a composite score. That's analytical maturity, not just SQL.

**Why this beats a generic dashboard:** it has a defined data contract (raw stories → keyword events → weekly aggregates → trend scores), a daily scheduler proving unattended operation, an NLP layer proving text processing skills, and a feature (hype cycle visualization) that hiring managers at tech companies will actually use and share.

**Gaps to address:**
- HN Algolia API rate limit: 10,000 req/hr (generous). Solution: batch daily fetches by timestamp window, store `last_fetched_at` in DuckDB, always fetch incrementally.
- Backfill (2 years of HN = ~2M stories): Solution: run once with a date-range loop, ~200 API calls at 1,000 stories/call — completes in under 5 minutes.
- DuckDB is local-only by default. Solution: commit pre-loaded `.duckdb` file to repo (LFS), mount in Streamlit Cloud — or use MotherDuck free tier (10 GB).
- Streamlit redeploys kill in-memory state. Solution: write all state to DuckDB, never rely on session.
- Keyword false positives ("Go" matching "going", "Rust" matching "rusty"). Solution: word-boundary regex + context window (require adjacent tech noun within 5 tokens for ambiguous terms).

### Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Ingestion | Python + `httpx` (async) | Async HTTP, lightweight, same pattern as prod pipelines |
| Keyword detection | Custom taxonomy dict + regex | Fast, deterministic, fully auditable — no black-box NLP |
| Emerging term detection | sklearn TF-IDF on weekly corpus | Catches unlisted tech rising in comments before it's famous |
| Orchestration | Prefect Cloud (free tier) | Prod-grade scheduler, visual run history, impresses in screenshots |
| Transform | DuckDB SQL + Pandas | Weekly aggregation, hype score, rolling avg — all in SQL |
| Storage | DuckDB (file-based) | Zero infra, columnar, analytics-native |
| Anomaly detection | Z-score (scipy.stats) | Flags overnight viral spikes — same method, richer domain |
| UI | Streamlit | Fast to build, free cloud deploy |
| Deploy | Streamlit Cloud (free) | One-click from GitHub |

**Why not spaCy/BERT for keyword extraction?** Overkill. A curated regex taxonomy is faster, more predictable, and easier to explain in an interview. Add TF-IDF for discovery of unlisted terms — that's the smart layer, not the brute-force layer.

**Why not Postgres?** DuckDB runs analytical queries 10–100× faster on flat files. For a portfolio project, this is the correct tool.

**Why HN over Reddit?** HN Algolia API is cleaner, free without OAuth, and the audience (developers) makes keyword signal much higher quality. Reddit requires app registration, OAuth, and has lower signal-to-noise for tech terms.

### General Flow

```
[Prefect Scheduler — daily at 06:00 UTC]
        ↓
[Fetch: HN Algolia API → all stories since last_fetched_at]
        ↓
[Validate: schema check, dedup on story_id, drop null titles]
        ↓
[Detect: scan title + URL domain → match against 150+ tech keyword taxonomy]
        ↓
[Enrich: attach story score, comment_count, created_at to each keyword hit]
        ↓
[Write: DuckDB → raw_stories, keyword_events]
        ↓
[Aggregate: weekly rollup → mention_count, weighted_score, avg_comments per keyword]
        ↓
[Score: hype_score = 0.5×mentions + 0.3×weighted_score + 0.2×avg_comments (normalized 0–100)]
        ↓
[Anomaly: rolling 12-week avg + z-score → flag |z| > 2 as trending/crashing]
        ↓
[Write: DuckDB → weekly_mentions, keyword_velocity, anomalies]
        ↓
[Streamlit reads DuckDB → hype cycle chart, velocity heatmap, anomaly feed, keyword compare]
```

### DuckDB Schema

```sql
-- Raw layer
raw_stories (
  story_id      INTEGER PRIMARY KEY,
  title         TEXT NOT NULL,
  url           TEXT,
  score         INTEGER,        -- HN upvotes
  num_comments  INTEGER,
  created_at    TIMESTAMP,
  fetched_at    TIMESTAMP
)

-- Keyword event layer (one row per keyword hit per story)
keyword_events (
  story_id      INTEGER,
  keyword       TEXT,           -- e.g. "Rust", "Next.js", "Kubernetes"
  category      TEXT,           -- Language / Framework / Tool / AI / Company
  score         INTEGER,        -- story score at detection time
  created_at    TIMESTAMP
)

-- Aggregated layer
weekly_mentions (
  keyword       TEXT,
  iso_week      TEXT,           -- e.g. "2024-W03"
  mention_count INTEGER,
  weighted_score FLOAT,         -- sum(score) / mention_count
  avg_comments  FLOAT,
  hype_score    FLOAT           -- 0–100 composite
)

-- Trend/anomaly layer
keyword_velocity (
  keyword       TEXT,
  iso_week      TEXT,
  velocity      FLOAT,          -- week-over-week % change in hype_score
  rolling_avg   FLOAT,          -- 12-week rolling average
  z_score       FLOAT,
  is_trending   BOOLEAN,        -- z > 2
  is_crashing   BOOLEAN         -- z < -2
)
```

### Keyword Taxonomy (excerpt)

```python
TAXONOMY = {
    "Languages":   ["Python", "Rust", "Go", "TypeScript", "JavaScript", "Zig", "Kotlin", "Swift", "Elixir", "Haskell"],
    "Frameworks":  ["Next.js", "FastAPI", "Django", "Rails", "Spring", "Svelte", "Remix", "Astro", "Laravel"],
    "Tools":       ["Docker", "Kubernetes", "Terraform", "dbt", "Kafka", "Airflow", "Prefect", "Grafana"],
    "AI/ML":       ["LLM", "GPT", "Claude", "Gemini", "PyTorch", "JAX", "Ollama", "RAG", "fine-tuning"],
    "Platforms":   ["Supabase", "Vercel", "Railway", "Fly.io", "MotherDuck", "Neon", "PlanetScale"],
    "Companies":   ["Anthropic", "OpenAI", "Google DeepMind", "Mistral", "Hugging Face"],
}

# Ambiguous terms requiring word-boundary + context check
AMBIGUOUS = {"Go": r"\bGo\b(?!\s+(to|ahead|back|through))", "Rust": r"\bRust\b(?!y\b)"}
```

### Build Phases

---

**Phase 1 — Foundation & Ingestion (Days 1–2)**

Goal: raw stories flowing into DuckDB, incrementally, reliably.

1. Init project with `uv init hn-tech-radar`, add deps: `httpx`, `duckdb`, `pandas`, `prefect`, `scipy`, `sklearn`
2. Create `src/` layout: `ingestion/`, `transforms/`, `dashboard/`, `tests/`
3. Implement `HNClient` in `ingestion/client.py`:
   - Method: `fetch_stories(since_ts: int, page_size=1000) -> list[dict]`
   - Endpoint: `https://hn.algolia.com/api/v1/search_by_date?tags=story&numericFilters=created_at_i>{ts}&hitsPerPage={page_size}`
   - Handle pagination: loop until `nbPages` exhausted or `created_at` exceeds now
   - Retry: exponential backoff on 429/5xx (3 retries max)
4. Create `storage/db.py` — `DuckDBStore`:
   - Method: `init_schema()` — creates all 4 tables if not exist
   - Method: `get_last_fetched_at() -> int` — reads `max(created_at)` from `raw_stories`
   - Method: `insert_stories(stories: list[dict])` — bulk insert with `ON CONFLICT DO NOTHING`
5. Implement `ingestion/backfill.py`:
   - Fetch from 2 years ago to now in 7-day windows
   - Log progress: `Fetched week 2022-W01: 14,302 stories`
   - Run once, idempotent (dedup on `story_id`)
6. Implement `ingestion/incremental.py`:
   - Call `get_last_fetched_at()`, fetch only new stories, insert
   - Log: `Fetched 847 new stories since 2024-01-15 06:00 UTC`
7. Verify: `duckdb hn.duckdb -c "SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM raw_stories"`
8. Write `tests/test_client.py`: mock httpx → assert correct pagination, retry on 429, schema of returned dicts

---

**Phase 2 — Keyword Detection System (Days 3–4)**

Goal: every story tagged with matching tech keywords, false positives eliminated.

1. Create `transforms/taxonomy.py`:
   - Define `TAXONOMY` dict (6 categories, 150+ terms)
   - Define `AMBIGUOUS` dict with context-aware regex patterns
   - Export: `ALL_KEYWORDS: list[str]`, `KEYWORD_TO_CATEGORY: dict[str, str]`
2. Implement `transforms/detector.py`:
   - Function: `detect_keywords(title: str, url: str) -> list[str]`
   - For non-ambiguous terms: `re.search(r'\b{kw}\b', text, re.IGNORECASE)`
   - For ambiguous terms: use regex from `AMBIGUOUS` dict
   - URL domain extraction: `"github.com/rust-lang/rust"` → extract "Rust" from domain path
   - Return deduplicated list of matched keywords
3. Implement `transforms/keyword_pipeline.py`:
   - Read `raw_stories` where `story_id NOT IN (SELECT story_id FROM keyword_events)`
   - Batch process 10,000 stories at a time
   - For each story: call `detect_keywords(title, url)`
   - Write results to `keyword_events` (one row per keyword hit)
4. Implement emerging term detection (`transforms/tfidf_discovery.py`):
   - Weekly: collect all story titles from that week
   - Run `TfidfVectorizer(ngram_range=(1,2), min_df=5)` on corpus
   - Extract top-20 terms NOT already in taxonomy
   - Write to `emerging_terms` table (keyword, week, tfidf_score) for manual review
   - This shows up in dashboard as "Watch List" — terms gaining traction before they're famous
5. Write `tests/test_detector.py`:
   - `"Rust is memory safe"` → assert `["Rust"]` detected
   - `"Getting rusty at piano"` → assert `[]` (no false positive)
   - `"Going to use Go for this"` → assert `["Go"]` (word boundary, not "going")
   - `"github.com/astral-sh/uv"` → assert `["uv"]` via URL path
   - `"Next.js 14 released"` → assert `["Next.js"]`

---

**Phase 3 — Aggregation, Scoring & Anomaly Detection (Days 5–6)**

Goal: weekly hype scores and z-score anomaly flags in DuckDB.

1. Implement `transforms/weekly_agg.py` — SQL via DuckDB:
   ```sql
   INSERT OR REPLACE INTO weekly_mentions
   SELECT
     keyword,
     strftime(created_at, '%Y-W%W') AS iso_week,
     COUNT(*)                        AS mention_count,
     SUM(score) / COUNT(*)           AS weighted_score,
     AVG(num_comments)               AS avg_comments
   FROM keyword_events ke
   JOIN raw_stories rs USING (story_id)
   WHERE strftime(rs.created_at, '%Y-W%W') = ?  -- current ISO week
   GROUP BY keyword, iso_week
   ```
2. Implement `transforms/hype_score.py`:
   - Per keyword per week: normalize each metric to 0–100 across all keywords that week
   - `hype_score = 0.5 * norm_mentions + 0.3 * norm_weighted_score + 0.2 * norm_avg_comments`
   - Update `weekly_mentions.hype_score` column
   - Rationale for weights: mentions = volume signal, weighted_score = quality signal (high-score stories = HN community validation), avg_comments = engagement signal
3. Implement `transforms/velocity.py`:
   - For each keyword, read last 13 weeks of `hype_score`
   - Compute `velocity = (this_week - last_week) / last_week * 100` (% change)
   - Compute `rolling_avg = avg(hype_score over 12 weeks)`
   - Compute `z_score = (this_week - rolling_avg) / std(hype_score over 12 weeks)`
   - Write to `keyword_velocity`
   - Set `is_trending = z_score > 2`, `is_crashing = z_score < -2`
4. Write `tests/test_aggregation.py`:
   - Inject 10 known stories with known keywords and scores
   - Assert `weekly_mentions` row has correct `mention_count`, `weighted_score`
   - Assert `hype_score` within expected range (0–100)
5. Write `tests/test_anomaly.py`:
   - Inject 12 weeks of baseline data (hype_score ~20 each week)
   - Inject week 13 with hype_score 80 (spike)
   - Assert `z_score > 2` and `is_trending = True` for that keyword/week
   - Assert non-spiked keywords have `is_trending = False`

---

**Phase 4 — Orchestration (Day 7)**

Goal: fully automated daily pipeline with failure alerts.

1. Create `pipeline/flow.py` — Prefect flow:
   ```python
   @flow(name="hn-tech-radar-daily")
   def daily_pipeline():
       fetch_new_stories()        # task: incremental HN fetch
       run_keyword_detection()    # task: detect keywords on new stories
       recompute_weekly_agg()     # task: recompute last 2 weeks (current + previous)
       update_hype_scores()       # task: normalize + score
       update_velocity()          # task: z-score + anomaly flags
       run_quality_checks()       # task: assert data quality
   ```
2. Each step is a `@task` with `retries=3, retry_delay_seconds=60`
3. Implement `run_quality_checks()`:
   - Assert `new_stories_count > 0` (fail if HN API returned nothing)
   - Assert `keyword_events` count increased (fail if detector produced zero hits)
   - Assert `MAX(created_at)` in `raw_stories` is within 26 hours of now
   - On assertion failure: raise `ValueError` → Prefect marks run as FAILED
4. Deploy to Prefect Cloud:
   - `prefect deploy pipeline/flow.py:daily_pipeline --name prod`
   - Schedule: `0 6 * * *` (06:00 UTC daily)
5. Configure failure webhook:
   - Prefect → Automations → On flow run failure → POST to Discord/Slack webhook
   - Message: `"TechPulse pipeline FAILED at {step}. Run ID: {run_id}"`
6. Verify: trigger manual run in Prefect Cloud UI, confirm all tasks green, check DuckDB row counts increased

---

**Phase 5 — Dashboard (Days 8–9)**

Goal: a dashboard hiring managers actually want to explore.

1. Create `dashboard/app.py` — Streamlit layout:
   ```
   Sidebar:
     - Category filter: All / Languages / Frameworks / Tools / AI / Platforms
     - Time window: Last 4 weeks / 12 weeks / 1 year / All time
     - Last pipeline run: {timestamp} ({N} new stories)

   Main — 3 tabs:
     Tab 1: Trending Now
     Tab 2: Hype Cycles
     Tab 3: Emerging Terms
   ```

2. **Tab 1 — Trending Now:**
   - "This Week's Risers": top 5 keywords by `velocity`, shown as metric cards with sparkline (last 8 weeks)
   - "This Week's Fallers": bottom 5 by velocity, same format
   - Anomaly feed: table of all `is_trending=True` events this week — keyword, z_score, link to top 3 HN stories that drove the spike
   - Story links: join `keyword_events` back to `raw_stories` to get HN URLs (`https://news.ycombinator.com/item?id={story_id}`)

3. **Tab 2 — Hype Cycles:**
   - Multi-keyword selector (default: Python, Rust, Go, TypeScript)
   - Line chart: x=iso_week, y=hype_score, one line per keyword (Altair/Plotly)
   - Overlay anomaly markers: red dot on weeks where `is_trending=True`
   - "Compare" mode: select exactly 2 keywords → show their hype cycle overlaid, highlight divergence weeks
   - Insight box: auto-generated text: `"Rust peaked in W03 2024 (z=3.2) following Linus Torvalds' Linux kernel comment"`

4. **Tab 3 — Emerging Terms:**
   - Table of top TF-IDF discovered terms this week (not in taxonomy)
   - Columns: term, first_seen_week, mention_count, top 3 story titles
   - Purpose: show the "discovery" layer — you're detecting the next Zig before it's famous

5. Add `@st.cache_data(ttl=3600)` on all DuckDB query functions — Streamlit re-runs on interaction, caching prevents repeated DB hits

6. Write `tests/test_dashboard.py` (Streamlit testing is limited — test the query layer):
   - `get_trending_keywords(week="2024-W03")` → assert returns list of dicts with expected keys
   - `get_hype_cycle(keyword="Rust", n_weeks=12)` → assert 12 rows, no nulls in hype_score

---

**Phase 6 — Polish, Deploy & Portfolio Assets (Day 10)**

Goal: the thing that gets you interviews.

1. Run backfill for 2 full years of HN data — commit resulting `.duckdb` file to repo via Git LFS (or upload to GitHub Release as asset, download in Streamlit `startup.sh`)
2. Deploy to Streamlit Cloud:
   - Set `DUCKDB_PATH` env var
   - `startup.sh`: download pre-loaded DuckDB if not present
3. README must contain:
   - Mermaid architecture diagram (copy from General Flow above)
   - Screenshot of Trending Now tab with real data
   - Screenshot of Hype Cycles tab showing Rust vs Go vs Python (3-year view)
   - "How hype score works" section — explain the formula, justify weights
   - "Anomaly detection" section — explain z-score, show a real historical spike (e.g., ChatGPT launch week in HN data)
   - Live demo link + Prefect run history screenshot
4. Add `ARCHITECTURE.md`:
   - Data lineage: `raw_stories → keyword_events → weekly_mentions → keyword_velocity`
   - Keyword taxonomy design rationale
   - Why TF-IDF for emerging terms vs. pure taxonomy
5. Performance verification:
   - Query `weekly_mentions` for 2-year range: assert < 500ms
   - Dashboard cold load on Streamlit Cloud: assert < 3s
   - Run `pytest` — all tests green — screenshot for README

### Success Metrics / Test Suite

**Functional tests**
- `test_client.py`: mock HTTP → assert correct pagination, retry on 429, dedup on story_id
- `test_detector.py`: 20 known title/URL pairs → assert correct keywords, zero false positives on ambiguous terms
- `test_aggregation.py`: known input data → assert `mention_count`, `weighted_score`, `hype_score` correct
- `test_anomaly.py`: inject synthetic spike → assert flagged at |z| > 2, non-spikes not flagged

**Pipeline health metrics**
- Pipeline success rate: 95%+ over 30-day period (Prefect dashboard shows this)
- Data freshness: `MAX(created_at)` in `raw_stories` < 26 hours ago (shown in UI sidebar)
- Story count assertion: each daily run must produce ≥ 100 new stories (fail if API returns empty)
- Keyword hit rate: ≥ 15% of stories must match at least 1 keyword (fail if detector is broken)

**Performance**
- Dashboard cold load < 3s (Streamlit Cloud)
- `weekly_mentions` query over 2-year range < 500ms (DuckDB columnar)
- Keyword detection on 10,000 stories < 5s (regex on CPU)

**Portfolio signal**
- Architecture diagram in README (proves systems thinking)
- Prefect run history screenshot (proves it ran unattended — most candidates fake this)
- Hype score formula explanation (proves analytical thinking, not just plumbing)
- Anomaly example with real historical data (ChatGPT launch week is visible in the data — use it)
- TF-IDF "emerging terms" section in README (proves you layered an additional intelligence beyond the obvious approach)

---

## Project 2: DataVault — dbt + DuckDB Analytics Engineering Project

### The Problem

"Analytics engineer" and "data engineer" roles increasingly require **dbt** as table stakes. Most candidates list it on a resume but have no project proving they can model data correctly: staging, intermediate, mart layers; tests; documentation; incremental models. Hiring managers who know dbt will immediately check if you understand the medallion pattern.

### The Solution

Take a rich public dataset — **NYC Taxi Trip data** (TLC, public domain, multi-GB) — and build a full dbt project on top of DuckDB that models it correctly. The deliverable: a Streamlit analytics dashboard showing trip patterns, borough-level revenue, surge-hour analysis, and driver efficiency metrics.

**The creative angle:** build a `driver_score` mart model — a composite score per taxi medallion using avg revenue/trip, trips/hour, and tip rate. This is a realistic business metric that shows modeling maturity.

**Gaps to address:**
- NYC Taxi data is large (multi-GB per month). Solution: use the Parquet files (not CSV), read a single month subset, use DuckDB's `read_parquet()` which streams without loading to memory.
- dbt-duckdb requires specific adapter. Solution: `dbt-duckdb` package, well-maintained, works exactly like dbt-core.
- Streamlit can't run dbt at runtime. Solution: pre-run `dbt build` in CI (GitHub Actions free), commit the output DuckDB file as an artifact, Streamlit reads static DuckDB.

### Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Raw data | NYC TLC Parquet (S3 public) | Free, real, large enough to matter |
| Transform | dbt-core + dbt-duckdb | Industry standard, shows AE maturity |
| Storage | DuckDB | Native Parquet reader, no infra |
| Testing | dbt built-in tests + Great Expectations lite | Schema + business rule tests |
| CI | GitHub Actions (free, 2000 min/mo) | Runs `dbt build` on PR |
| UI | Streamlit | Fast, free deploy |
| Deploy | Streamlit Cloud | One-click |

**Why not Snowflake/BigQuery free tier?** They have limits and require account setup. DuckDB is portable, runs in CI for free, and is increasingly used in production (MotherDuck). More impressive to use the right tool, not the "big" tool.

### General Flow

```
[NYC TLC S3 Parquet — public]
        ↓
[seeds / sources: define raw schema in dbt]
        ↓
[staging models: stg_trips, stg_zones — clean, rename, cast]
        ↓
[intermediate models: int_trips_enriched — join zones, add derived cols]
        ↓
[mart models: mart_daily_trips, mart_borough_revenue, mart_driver_score]
        ↓
[dbt tests: not_null, unique, accepted_values, custom SQL tests]
        ↓
[GitHub Actions: dbt build on every PR → fail if tests fail]
        ↓
[Streamlit reads mart tables from DuckDB → renders dashboard]
```

### Build Phases

**Phase 1 — Data & dbt Setup (Days 1–2)**
- Download 1 month of TLC Parquet data (Jan 2024, ~3 GB)
- Initialize dbt project with dbt-duckdb adapter
- Define sources and seeds (taxi zone lookup table)
- Verify raw data loads into DuckDB

**Phase 2 — Staging Layer (Days 3–4)**
- `stg_yellow_trips`: clean nulls, cast types, filter invalid trips (negative fare, zero distance)
- `stg_taxi_zones`: zone name, borough mapping
- dbt schema tests: not_null on PK, accepted_values for payment_type

**Phase 3 — Intermediate + Mart Layer (Days 5–6)**
- `int_trips_enriched`: join zones → add pickup/dropoff borough
- `mart_daily_trips`: daily aggregates per borough
- `mart_borough_revenue`: total fare, avg tip rate, trip count
- `mart_driver_score`: composite score (avg fare/trip × 0.4 + tip_rate × 0.3 + trips/hour × 0.3)
- Custom dbt test: assert driver_score between 0 and 100

**Phase 4 — CI Pipeline (Day 7)**
- GitHub Actions workflow: on push → install deps → `dbt build` → upload DuckDB artifact
- PR status check: fails if any dbt test fails
- Add `dbt docs generate` → host docs on GitHub Pages (free)

**Phase 5 — Dashboard + Polish (Days 8–9)**
- Streamlit: borough revenue map (use pydeck, free), daily trend, top 20 drivers by score
- Filter: date range, borough, payment type
- Deploy Streamlit Cloud
- README with dbt lineage DAG screenshot and data dictionary

### Success Metrics / Test Suite

**dbt tests (built-in)**
- `not_null` on all PK and critical columns
- `unique` on trip_id in staging
- `accepted_values` on payment_type, vendor_id
- `relationships` test: every dropoff_location_id exists in stg_taxi_zones

**Custom dbt tests**
- `assert_positive_fares`: no negative total_amount in mart
- `assert_driver_score_range`: score between 0–100 for all medallions
- `assert_trip_duration_realistic`: duration between 1 min and 6 hours

**CI metrics**
- All dbt tests pass on every PR (enforced via GitHub Actions status check)
- `dbt build` completes in < 3 minutes (reasonable for 1-month dataset)

**Dashboard metrics**
- Load time < 3s for full dashboard
- All mart queries < 1s in DuckDB

**Portfolio signal**
- dbt docs site (hosted on GitHub Pages) — shows documentation culture
- CI badge in README showing green build
- Data lineage DAG screenshot
- Explain `driver_score` formula in README (shows business logic thinking)

---

## Project 5: DocuMind — RAG Document Chat

### The Problem

Every company hiring AI engineers wants to see **RAG** (Retrieval-Augmented Generation) experience. The market is flooded with toy demos: upload PDF, ask question, get answer. They all use OpenAI (paid) and LangChain with zero engineering rigor. The gap: **production-quality retrieval** — proper chunking strategy, embedding quality evaluation, relevance scoring, citation support, and handling edge cases (questions with no relevant context).

### The Solution

A document intelligence platform where users upload research papers or technical docs, and get accurate answers **with citations** (which document, which page). The differentiating features:

1. **Hallucination guard**: if retrieved context relevance score < threshold, respond "I don't have enough information" instead of hallucinating
2. **Multi-document comparison**: "Compare the methodology in Doc A vs Doc B"
3. **Chunking strategy selector**: users can switch between fixed-size, sentence-boundary, and semantic chunking — and see how it affects answer quality

This turns a toy demo into an engineering project that demonstrates retrieval quality thinking.

**Gaps to address:**
- Local LLMs (Ollama) are slow on CPU-only machines. Solution: use Groq API (free tier: 30 req/min, Llama 3 70B) for inference, Ollama as local fallback.
- ChromaDB persistence in Streamlit Cloud is ephemeral. Solution: use `chromadb` with a local SQLite backend, commit the vector store to the repo for a pre-loaded demo dataset.
- PDF parsing quality varies. Solution: use `pdfplumber` (better than PyMuPDF for text-heavy docs), fallback to PyMuPDF for image-heavy PDFs.
- Embedding API costs. Solution: use `sentence-transformers` (local, free, `all-MiniLM-L6-v2` — fast, 384-dim, good quality).

### Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| LLM | Groq API (free: Llama 3.1 70B) | Fast inference, free tier, no vendor lock-in |
| LLM fallback | Ollama (local) | 100% free, offline capable |
| Embeddings | sentence-transformers (local) | Free, no API calls, runs on CPU |
| Vector DB | ChromaDB (local SQLite backend) | Zero infra, persistent, easy to inspect |
| PDF parsing | pdfplumber + PyMuPDF | Handles both text and scanned docs |
| Chunking | LangChain text splitters | Sentence, recursive, and semantic variants |
| Relevance scoring | Cosine similarity + MMR reranking | Reduces redundant chunks in retrieval |
| UI | Streamlit | Chat interface, file upload, citation display |
| Deploy | Streamlit Cloud (free) | One-click |
| Testing | pytest + ragas (free) | RAG evaluation framework |

**Why not LangChain for everything?** LangChain abstracts too much for a portfolio project. Use it only for chunking. Write the retrieval loop manually — it proves you understand the pipeline.

### General Flow

```
[User uploads PDF(s)]
        ↓
[Parse: pdfplumber → text + page numbers]
        ↓
[Chunk: RecursiveCharacterTextSplitter, 512 tokens, 50 overlap]
        ↓
[Embed: sentence-transformers all-MiniLM-L6-v2 → 384-dim vectors]
        ↓
[Store: ChromaDB collection with metadata: doc_name, page_num, chunk_id]
        ↓
[User asks question]
        ↓
[Embed question → cosine similarity search → top-5 chunks]
        ↓
[Relevance check: if max_score < 0.35 → "insufficient context" response]
        ↓
[Rerank: MMR (Maximal Marginal Relevance) to reduce redundancy]
        ↓
[Prompt: inject top-3 chunks as context → Groq LLM]
        ↓
[Response: answer + citations (doc name, page number)]
```

### Build Phases

**Phase 1 — Core Pipeline (Days 1–3)**
- PDF ingestion with pdfplumber, page metadata extraction
- Chunking with LangChain RecursiveCharacterTextSplitter
- Embedding with sentence-transformers
- ChromaDB store + query with metadata filter
- End-to-end test: upload 1 paper, ask 3 questions, verify citation accuracy

**Phase 2 — Retrieval Quality (Days 4–5)**
- Relevance threshold guard (cosine < 0.35 → refuse to answer)
- MMR reranking implementation (manual, ~30 lines)
- Multi-document query: retrieve from all docs, rank globally
- Test: questions with no relevant context must trigger the guard

**Phase 3 — LLM Integration (Days 6–7)**
- Groq API integration (Llama 3.1 70B)
- Ollama fallback (`llama3.2:3b` for local)
- Prompt template: strict "answer only from context" instruction
- Citation extraction: parse LLM response to link claims to source chunks

**Phase 4 — Chunking Comparison Feature (Day 8)**
- Add UI toggle: Fixed / Sentence / Semantic chunking
- Show chunk count and avg chunk size for each strategy
- Let user see retrieved chunks before the answer
- This feature alone differentiates from 99% of RAG demos

**Phase 5 — Evaluation + Deploy (Days 9–10)**
- ragas evaluation on 20 question-answer pairs (faithfulness, context_recall, answer_relevancy)
- Pre-load demo dataset: 3 ML papers (public domain) + 20 ground-truth Q&A pairs
- Deploy Streamlit Cloud with pre-loaded vector store
- README: evaluation metrics table, architecture diagram, chunking strategy comparison

### Success Metrics / Test Suite

**Retrieval quality (ragas)**
- Faithfulness score > 0.80 (answers grounded in context)
- Context recall > 0.75 (relevant chunks retrieved)
- Answer relevancy > 0.80 (answers the actual question)
- Measure before/after MMR reranking — show improvement in README

**Hallucination guard**
- `test_refusal.py`: 10 out-of-domain questions → assert all trigger refusal
- `test_citation_accuracy.py`: 10 known Q&As → assert citation page numbers correct

**Functional tests**
- `test_pdf_parse.py`: known PDF → assert expected text and page count
- `test_chunking.py`: known text → assert chunk count, no data loss between chunks
- `test_embedding.py`: two semantically similar sentences → cosine similarity > 0.85

**Performance**
- Embedding 100 chunks: < 10s on CPU
- Query latency (embed + retrieve + rerank): < 500ms
- LLM response (Groq): < 3s end-to-end

**Portfolio signal**
- ragas evaluation table in README (shows measurement culture)
- Chunking comparison screenshot
- "Hallucination guard" section in README (shows production thinking)

---

## Project 6: ShipFast — SaaS Starter Dashboard (No Billing)

### The Problem

Full-stack portfolio projects usually fall into two traps: (1) too simple — a CRUD todo app, or (2) fake "full-stack" — Next.js frontend with a single API route. Neither proves you can build a real multi-tenant product. The gap: **authentication architecture, row-level security, and real UX patterns** that appear in every SaaS product.

### The Solution

A multi-tenant team workspace tool — think a stripped-down Notion/Linear workspace. Users can create an organization, invite teammates, create projects, and assign tasks. Focus is entirely on **the infrastructure of SaaS**: auth flows, RLS policies, role-based access (admin/member), invitation email flow, and a dashboard that feels like a real product.

**Why this beats a generic dashboard:**
- Row-Level Security in Postgres (via Supabase) is a real skill — it appears in data privacy audits
- Invitation flow (send email → accept → join org) is a complete user journey, not just a login form
- Role-based access (admin can delete, member cannot) proves authorization thinking
- The project manager feature gives the app a real use case, not just "user settings"

**Gaps to address:**
- Supabase free tier: 500 MB storage, 50,000 monthly active users — more than enough.
- Resend free tier: 3,000 emails/month, 100/day — sufficient for a portfolio demo.
- Next.js + Supabase Auth SSR requires careful cookie handling. Solution: use `@supabase/ssr` (official, replaces deprecated `auth-helpers`).
- Multi-tenant RLS is complex to get right. Solution: design schema first, write RLS policies before any application code, verify with Supabase SQL editor.

### Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Framework | Next.js 14 App Router | Industry standard, SSR + RSC |
| Auth | Supabase Auth | Free, handles OAuth + email, SSR-ready |
| Database | Supabase Postgres | Free, RLS built-in, real-time subscriptions |
| Email | Resend (free: 3k/mo) | Best DX, React Email templates |
| Styling | Tailwind CSS + shadcn/ui | Fast, consistent, what companies actually use |
| State | Zustand (minimal) | Lightweight, no boilerplate |
| Forms | React Hook Form + Zod | Validation, type safety |
| Deploy | Vercel (free) | One-click, preview deployments |
| Testing | Vitest + Playwright | Unit + E2E |

**Why not Prisma?** Supabase has a JS client that's typed via generated types. Prisma adds complexity. For a portfolio, the Supabase client is the right tool.

**Why shadcn/ui?** Not a component library you install — it's copy-paste components you own. Hiring managers who know it respect it. It's what most modern Next.js projects use.

### General Flow

```
[User signs up → email verification]
        ↓
[Onboarding: create organization → become admin]
        ↓
[Admin: invite teammates by email → Resend sends invite link]
        ↓
[Invitee: clicks link → signs up / logs in → joins org]
        ↓
[Workspace: create projects → add tasks → assign to members]
        ↓
[RLS enforces: members only see their org's data]
        ↓
[Admin controls: remove members, delete projects, view all tasks]
        ↓
[Real-time: task status updates via Supabase subscriptions]
```

### Database Schema

```sql
-- Core multi-tenant pattern
organizations (id, name, created_at)
memberships (user_id, org_id, role: admin|member, joined_at)
invitations (id, org_id, email, token, expires_at, accepted_at)
projects (id, org_id, name, description, status, created_by)
tasks (id, project_id, org_id, title, status, assignee_id, due_date)

-- RLS: users only see rows where org_id matches their membership
```

### Build Phases

**Phase 1 — Auth & Database (Days 1–3)**
- Supabase project setup, schema creation
- Write all RLS policies before any app code (test in SQL editor)
- Next.js + `@supabase/ssr`: sign up, login, logout, email verification
- Middleware: protect all `/dashboard` routes, redirect unauthenticated users

**Phase 2 — Onboarding Flow (Days 4–5)**
- Create organization on first login
- Generate invitation token (UUID, 48h expiry)
- Resend email: React Email template for invitation
- Accept invitation: validate token, create membership, redirect to workspace

**Phase 3 — Core Workspace (Days 6–8)**
- Project CRUD (admin only: delete, all: create/read/update)
- Task management: create, assign, status (todo/in_progress/done), due date
- Member list page: show role badges, admin can remove members
- Real-time task updates via Supabase `on('postgres_changes')` subscription

**Phase 4 — Role-Based Access (Day 9)**
- Frontend: hide delete buttons for non-admins
- Backend: API routes check membership role before mutations
- Test: member account cannot call admin endpoints (expect 403)
- Audit: verify RLS policies block cross-org data access at DB level

**Phase 5 — Polish + Testing + Deploy (Days 10–11)**
- Playwright E2E: full invitation flow, task lifecycle, role enforcement
- Vitest unit tests: RLS policy logic, invitation token validation
- Seed script: demo org with 3 members and 10 tasks for portfolio demo
- Deploy Vercel, configure Supabase production project
- README: architecture diagram, feature list, RLS explanation

### Success Metrics / Test Suite

**Vitest unit tests**
- `invitation.test.ts`: token generation, expiry check, used-token rejection
- `auth.test.ts`: unauthenticated access returns redirect, not 200
- `rbac.test.ts`: admin vs member permission checks on all mutations

**Playwright E2E tests**
- `invite-flow.spec.ts`: full flow — admin invites → invitee accepts → appears in member list
- `task-lifecycle.spec.ts`: create project → add task → assign → complete → verify status
- `rbac.spec.ts`: login as member → attempt admin action → expect blocked UI + 403

**Security tests**
- Cross-org access test: user A cannot read user B's projects (test at API and DB level)
- Expired invitation test: token > 48h returns 410 Gone
- RLS verification: raw Supabase query from member account returns only their org's rows

**Performance**
- Dashboard first load < 1.5s (Vercel Edge, RSC)
- Real-time task update propagates in < 500ms
- Lighthouse score > 90 (performance, accessibility)

**Portfolio signal**
- RLS policy explanation in README (rare skill to document)
- Invitation flow recorded as a short screen recording (embedded in README)
- Role-based access architecture diagram
- Playwright test run screenshot in README

---

## Cross-Project Notes

### Build Order Recommendation

Start with **Project 6 (ShipFast)** if targeting full-stack/engineering roles — broadest HR appeal.
Start with **Project 2 (DataVault)** if targeting data engineering — most direct signal.
**Project 5 (DocuMind)** can be built in parallel since it has no dependencies on the others.
**Project 1 (WeatherFlow)** is the fastest to deploy and makes a good "warm-up" first project.

### Common Pitfalls to Avoid

1. **No README**: hiring managers decide in 30 seconds. Architecture diagram + 1 screenshot + live demo link is mandatory.
2. **No tests**: listing tests in a README without a test suite is worse than no mention. Every project above has a test suite — run them in CI.
3. **Broken demos**: a live demo that errors out is worse than no demo. Use seed data that always works.
4. **Overcomplicated infra**: none of these projects need Kubernetes, Redis, or a message queue. Adding them without justification signals bad judgment.
5. **No data**: a dashboard with no data is useless. Every project has a strategy for pre-loaded demo data.

### Shared Tooling

- All Python projects: use `uv` for dependency management (faster than pip, modern)
- All Next.js projects: use `pnpm` (faster installs, Vercel recommends it)
- All projects: Conventional Commits + GitHub Actions CI badge in README
- All projects: `pre-commit` hooks for linting/formatting
