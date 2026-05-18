"""Compute week-over-week velocity and z-score anomaly flags."""
import logging

import pandas as pd
from scipy import stats

from storage.db import DuckDBStore

log = logging.getLogger(__name__)

ROLLING_WINDOW = 12
Z_THRESHOLD = 2.0


def compute_velocity(db: DuckDBStore, iso_week: str) -> int:
    """
    For each keyword with data in iso_week, compute:
      - velocity: WoW % change in hype_score
      - rolling_avg: 12-week rolling mean
      - z_score: (this_week - rolling_avg) / rolling_std
      - is_trending: z_score > 2
      - is_crashing: z_score < -2

    Writes results to keyword_velocity. Returns rows written.
    """
    keywords = db._conn.execute(
        "SELECT DISTINCT keyword FROM weekly_mentions WHERE iso_week = ?", [iso_week]
    ).fetchall()

    rows_written = 0
    for (keyword,) in keywords:
        history = db._conn.execute("""
            SELECT iso_week, hype_score
            FROM weekly_mentions
            WHERE keyword = ? AND hype_score IS NOT NULL
            ORDER BY iso_week
        """, [keyword]).fetchall()

        if not history:
            continue

        df = pd.DataFrame(history, columns=["iso_week", "hype_score"])
        df["hype_score"] = df["hype_score"].astype(float)

        current_idx = df[df["iso_week"] == iso_week].index
        if len(current_idx) == 0:
            continue
        idx = current_idx[0]

        current_score = df.loc[idx, "hype_score"]

        # velocity: WoW % change
        if idx > 0:
            prev_score = df.loc[idx - 1, "hype_score"]
            velocity = ((current_score - prev_score) / prev_score * 100) if prev_score != 0 else 0.0
        else:
            velocity = 0.0

        # rolling window: up to 12 weeks ending at previous week
        window_df = df.iloc[max(0, idx - ROLLING_WINDOW):idx]
        if len(window_df) >= 2:
            rolling_avg = float(window_df["hype_score"].mean())
            rolling_std = float(window_df["hype_score"].std())
            if rolling_std > 0:
                z_score = (current_score - rolling_avg) / rolling_std
            elif rolling_avg > 0:
                # flat baseline: use synthetic z proportional to % deviation
                # scale: 2× baseline ≈ z=2, 0.5× baseline ≈ z=-2
                pct_change = (current_score - rolling_avg) / rolling_avg
                z_score = pct_change * 2.0 / 0.5  # 50% change → |z|=2
            else:
                z_score = 0.0
        else:
            rolling_avg = current_score
            z_score = 0.0

        is_trending = bool(z_score > Z_THRESHOLD)
        is_crashing = bool(z_score < -Z_THRESHOLD)

        db._conn.execute("""
            INSERT OR REPLACE INTO keyword_velocity
                (keyword, iso_week, velocity, rolling_avg, z_score, is_trending, is_crashing)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [keyword, iso_week, round(velocity, 4), round(rolling_avg, 4),
              round(z_score, 4), is_trending, is_crashing])

        rows_written += 1

    log.info("velocity: week=%s rows=%d", iso_week, rows_written)
    return rows_written
