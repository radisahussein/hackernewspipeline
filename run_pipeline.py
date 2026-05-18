"""Run full transform pipeline on existing raw_stories."""
import sys
sys.path.insert(0, "src")

from storage.db import DuckDBStore
from transforms.keyword_pipeline import run_keyword_pipeline
from transforms.weekly_agg import run_weekly_aggregation_all
from transforms.hype_score import compute_hype_scores
from transforms.velocity import compute_velocity

db = DuckDBStore()

print("Step 1 — keyword detection...")
hits = run_keyword_pipeline(db)
print(f"  keyword_events rows: {hits}")

print("Step 2 — weekly aggregation...")
run_weekly_aggregation_all(db)
count = db.row_count("weekly_mentions")
print(f"  weekly_mentions rows: {count}")

print("Step 3 — hype scores + velocity...")
weeks = [r[0] for r in db._conn.execute(
    "SELECT DISTINCT iso_week FROM weekly_mentions ORDER BY iso_week"
).fetchall()]
print(f"  processing {len(weeks)} weeks...")
for w in weeks:
    compute_hype_scores(db, w)
    compute_velocity(db, w)
print("  done")

print("\nFinal counts:")
for table in ("keyword_events", "weekly_mentions", "keyword_velocity"):
    print(f"  {table}: {db.row_count(table)}")

print("\nTop trending this week:")
rows = db._conn.execute(
    "SELECT keyword, z_score FROM keyword_velocity WHERE is_trending=true ORDER BY z_score DESC LIMIT 10"
).fetchall()
for kw, z in rows:
    print(f"  {kw}: z={z:.2f}")

db.close()
