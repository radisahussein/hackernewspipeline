# TechPulse — HN Tech Trend Radar

End-to-end data pipeline. Daily HN ingestion → keyword detection → hype scoring → Streamlit dashboard.

---

## Engineering Workflow

Every change follows this loop. No exceptions.

### 1. What is the issue?

State the problem in one sentence before touching any code.

- What is broken or missing?
- What is the expected behavior?
- What is the actual behavior?

If you cannot state the issue in one sentence, you do not understand it yet. Read more.

### 2. Next steps

Write out the plan before writing code.

- Which files are affected?
- What is the minimum change that fixes the issue?
- What could this break downstream?

Do not begin implementation until the plan is clear.

### 3. Explore

Read the relevant code first.

- Find where the issue lives (exact file + line)
- Trace the data flow: what calls what, what writes what
- Check tests — does a test already cover this case?
- Check the DuckDB schema if the change touches data

Stop at 90% confidence. Do not read the entire codebase for a scoped change.

### 4. Implement minimum code

Write the smallest change that solves the problem.

- No speculative abstractions
- No extra error handling for cases that cannot happen
- No comments explaining what the code does — only *why* if it is non-obvious
- Follow existing patterns in the file you are editing
- Functions under 50 lines. Files under 400 lines.

### 5. Write tests

Write tests before or immediately after implementing. Never skip.

Test locations:
- `src/tests/test_client.py` — HN API client, pagination, retry
- `src/tests/test_detector.py` — keyword detection, false positive cases
- `src/tests/test_aggregation.py` — weekly rollup SQL correctness
- `src/tests/test_anomaly.py` — z-score, trending/crashing flags
- `src/tests/test_dashboard.py` — Streamlit data layer (not UI)

Test rules:
- One assertion per test when possible
- Name tests: `test_<what>_<condition>_<expected>`
- Use `pytest` with fixtures in `conftest.py`
- Mock `httpx` for all API calls — never hit the real HN API in tests
- For DuckDB tests: use an in-memory DB (`duckdb.connect(':memory:')`)

### 6. Execute tests — minimum twice

```bash
uv run pytest src/tests/ -v
# Wait for all to pass.
uv run pytest src/tests/ -v
# Must pass again. Flaky = broken.
```

Tests must pass twice in a row to be considered stable. If you see a pass then fail, find the race condition or shared state before committing.

### 7. If tests fail — start over from step 1

Do not patch tests to pass. Do not add `# noqa`. Do not skip a failing test.

Go back to step 1. Reread the problem. Something in your plan was wrong.

---

## Branch Strategy

Base branch: `stage`

One branch per project phase:

| Phase | Branch name | What it covers |
|-------|-------------|----------------|
| 1 | `phase/1-ingestion` | HNClient, DuckDBStore, backfill, incremental fetch |
| 2 | `phase/2-keyword-detection` | Taxonomy, detector, URL extraction |
| 3 | `phase/3-scoring` | Weekly aggregation, hype score, velocity, anomaly |
| 4 | `phase/4-orchestration` | Prefect flow, schedule, quality checks |
| 5 | `phase/5-dashboard` | Streamlit app, all 3 tabs, caching |
| 6 | `phase/6-deploy` | Streamlit Cloud config, Git LFS, startup script |

### Create branch

Always branch from `stage`:

```bash
git checkout stage
git pull origin stage
git checkout -b phase/1-ingestion
```

### Commit rules

- Commit every logical unit of work — not everything at once
- Only commit when tests for newly written code pass
- Message format: `<type>: <description>` (types: `feat`, `fix`, `test`, `chore`, `refactor`)
- Keep commits small and focused. A commit should answer: "what changed and why?"

Example commit cadence for Phase 1:
```
feat: add HNClient with pagination and retry logic
test: add tests for HNClient pagination and 429 handling
feat: add DuckDBStore with schema init and upsert
test: add DuckDB in-memory tests for insert_stories
feat: add backfill script with 7-day window loop
feat: add incremental fetch using last_fetched_at
chore: verify row counts in hn.duckdb
```

### After every commit — log

After each commit, append to `progress.md` in the repo root:

```
## <commit hash> — <date>
**Done:** <one sentence: what this commit added or fixed>
**Next:** <one sentence: what comes immediately after>
```

### Phase done — stop

When a phase is complete:
1. All tests pass twice
2. All commits are on the phase branch
3. Append a phase summary to `progress.md`:

```
## Phase <N> complete — <date>
**Done:** <bullet list of everything built in this phase>
**Next:** <bullet list of first tasks for next phase>
```

4. Stop. Do not start the next phase until told to.

Do not open a PR or merge unless explicitly asked.

---

## Project Layout

```
e2e_data_pipeline/
├── CLAUDE.md
├── project_plans.md
├── pyproject.toml
├── hn.duckdb              # committed via Git LFS after backfill
└── src/
    ├── ingestion/
    │   ├── client.py      # HNClient — fetch_stories()
    │   ├── backfill.py    # one-time 2-year historical load
    │   └── incremental.py # daily delta fetch
    ├── storage/
    │   └── db.py          # DuckDBStore — schema, insert, query helpers
    ├── transforms/
    │   ├── taxonomy.py    # TAXONOMY dict, AMBIGUOUS patterns
    │   ├── detector.py    # detect_keywords(title, url)
    │   ├── keyword_pipeline.py  # batch detection over raw_stories
    │   ├── tfidf_discovery.py   # emerging term detection
    │   ├── weekly_agg.py        # SQL rollup → weekly_mentions
    │   ├── hype_score.py        # 0–100 composite score
    │   └── velocity.py          # z-score, rolling avg, trending flags
    ├── pipeline/
    │   └── flow.py        # Prefect @flow — daily_pipeline()
    ├── dashboard/
    │   └── app.py         # Streamlit — 3 tabs, cached DuckDB queries
    └── tests/
        ├── conftest.py
        ├── test_client.py
        ├── test_detector.py
        ├── test_aggregation.py
        ├── test_anomaly.py
        └── test_dashboard.py
```

---

## Key Constraints

**DuckDB**: All state lives here. No in-memory state that survives a redeploy.

**Idempotency**: Every insert uses `ON CONFLICT DO NOTHING` on `story_id`. Running twice must produce the same result.

**Ambiguous keywords**: `"Go"` and `"Rust"` use word-boundary regex with negative lookahead. Never match "going", "rusty", "go to". Test these explicitly.

**No real API calls in tests**: Mock `httpx.AsyncClient` in all client tests. HN Algolia has a 10k req/hr limit — tests must not consume it.

**Hype score formula**: `0.5 × norm_mentions + 0.3 × norm_weighted_score + 0.2 × norm_avg_comments` — normalize each component 0–100 per week before combining.

**Anomaly threshold**: `|z_score| > 2` on 12-week rolling average. `is_trending = z > 2`, `is_crashing = z < -2`.

**Streamlit caching**: All DuckDB query functions decorated with `@st.cache_data(ttl=3600)`.

---

## Python Stack

```toml
[tool.uv]
python = "3.12"

[dependencies]
httpx = "*"
duckdb = "*"
pandas = "*"
prefect = "*"
scipy = "*"
scikit-learn = "*"
streamlit = "*"
pytest = { optional = true }
pytest-asyncio = { optional = true }
```

Run tests: `uv run pytest src/tests/ -v`
Run dashboard: `uv run streamlit run src/dashboard/app.py`
Run backfill: `uv run python src/ingestion/backfill.py`
