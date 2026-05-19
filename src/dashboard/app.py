"""TechPulse — Streamlit dashboard: 3 tabs, DuckDB-backed, cached queries."""
import datetime
import os
import subprocess
import sys
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))
from storage.db import DEFAULT_DB_PATH

DB_PATH = str(DEFAULT_DB_PATH)

# Download pre-loaded DB on Streamlit Cloud if not present
if not Path(DB_PATH).exists() and os.getenv("DUCKDB_DOWNLOAD_URL"):
    subprocess.run(["bash", "startup.sh"], check=True)


def _connect() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(DB_PATH, read_only=True)


# ── Query layer (all cached) ─────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_trending_keywords(week: str) -> list[dict]:
    with _connect() as con:
        rows = con.execute("""
            SELECT kv.keyword, kv.velocity, kv.z_score, kv.is_trending, kv.is_crashing,
                   wm.hype_score, wm.mention_count
            FROM keyword_velocity kv
            JOIN weekly_mentions wm USING (keyword, iso_week)
            WHERE kv.iso_week = ?
            ORDER BY kv.velocity DESC
        """, [week]).fetchall()
    return [
        dict(zip(["keyword", "velocity", "z_score", "is_trending", "is_crashing", "hype_score", "mention_count"], r))
        for r in rows
    ]


@st.cache_data(ttl=3600)
def get_hype_cycle(keyword: str, n_weeks: int = 12) -> pd.DataFrame:
    with _connect() as con:
        rows = con.execute("""
            SELECT iso_week, hype_score, mention_count
            FROM weekly_mentions
            WHERE keyword = ? AND hype_score IS NOT NULL
            ORDER BY iso_week DESC
            LIMIT ?
        """, [keyword, n_weeks]).fetchall()
    df = pd.DataFrame(rows, columns=["iso_week", "hype_score", "mention_count"])
    return df.sort_values("iso_week").reset_index(drop=True)


@st.cache_data(ttl=3600)
def get_anomaly_feed(week: str, limit: int = 20) -> pd.DataFrame:
    with _connect() as con:
        rows = con.execute("""
            SELECT kv.keyword, kv.z_score, kv.velocity,
                   rs.story_id, rs.title, rs.score
            FROM keyword_velocity kv
            JOIN keyword_events ke ON ke.keyword = kv.keyword
            JOIN raw_stories rs ON rs.story_id = ke.story_id
            WHERE kv.iso_week = ? AND kv.is_trending = true
              AND strftime(rs.created_at, '%Y-W%W') = ?
            ORDER BY kv.z_score DESC, rs.score DESC
            LIMIT ?
        """, [week, week, limit]).fetchall()
    return pd.DataFrame(rows, columns=["keyword", "z_score", "velocity", "story_id", "title", "score"])


@st.cache_data(ttl=3600)
def get_emerging_terms(week: str, limit: int = 20) -> pd.DataFrame:
    with _connect() as con:
        # emerging_terms table created by tfidf_discovery if it exists
        tables = {r[0] for r in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()}
        if "emerging_terms" not in tables:
            return pd.DataFrame(columns=["term", "iso_week", "tfidf_score"])
        rows = con.execute("""
            SELECT term, iso_week, tfidf_score
            FROM emerging_terms
            WHERE iso_week = ?
            ORDER BY tfidf_score DESC
            LIMIT ?
        """, [week, limit]).fetchall()
    return pd.DataFrame(rows, columns=["term", "iso_week", "tfidf_score"])


@st.cache_data(ttl=3600)
def get_available_keywords() -> list[str]:
    with _connect() as con:
        rows = con.execute(
            "SELECT DISTINCT keyword FROM weekly_mentions ORDER BY keyword"
        ).fetchall()
    return [r[0] for r in rows]


@st.cache_data(ttl=3600)
def get_latest_week() -> str:
    with _connect() as con:
        row = con.execute("SELECT MAX(iso_week) FROM weekly_mentions").fetchone()
    if row and row[0]:
        return row[0]
    return datetime.date.today().strftime("%Y-W%W")


@st.cache_data(ttl=3600)
def get_pipeline_metadata() -> dict:
    with _connect() as con:
        row = con.execute(
            "SELECT MAX(fetched_at), COUNT(*) FROM raw_stories"
        ).fetchone()
    return {"last_run": row[0], "total_stories": row[1] if row else 0}


# ── UI helpers ────────────────────────────────────────────────────────────────

def _hn_url(story_id: int) -> str:
    return f"https://news.ycombinator.com/item?id={story_id}"


def _render_trending_now(week: str, category_filter: str) -> None:
    data = get_trending_keywords(week)
    if not data:
        st.info("No velocity data for this week yet.")
        return

    df = pd.DataFrame(data)
    if category_filter != "All":
        # import taxonomy here to avoid circular at module level
        from transforms.taxonomy import KEYWORD_TO_CATEGORY
        df = df[df["keyword"].map(lambda k: KEYWORD_TO_CATEGORY.get(k, "")) == category_filter]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Risers")
        top = df.nlargest(5, "velocity")
        for _, row in top.iterrows():
            delta = f"+{row['velocity']:.1f}% WoW"
            st.metric(label=row["keyword"], value=f"{row['hype_score']:.1f}", delta=delta)

    with col2:
        st.subheader("Fallers")
        bottom = df.nsmallest(5, "velocity")
        for _, row in bottom.iterrows():
            delta = f"{row['velocity']:.1f}% WoW"
            st.metric(label=row["keyword"], value=f"{row['hype_score']:.1f}", delta=delta)

    st.subheader("Anomaly Feed")
    anomaly_df = get_anomaly_feed(week)
    if anomaly_df.empty:
        st.info("No anomalies this week.")
    else:
        for _, row in anomaly_df.drop_duplicates("keyword").iterrows():
            url = _hn_url(row["story_id"])
            st.markdown(
                f"**{row['keyword']}** — z={row['z_score']:.2f} · "
                f"[{row['title'][:80]}]({url}) (↑{row['score']})"
            )


def _render_hype_cycles(week: str) -> None:
    keywords = get_available_keywords()
    if not keywords:
        st.info("No data yet.")
        return

    defaults = [k for k in ["Python", "Rust", "Go", "TypeScript"] if k in keywords][:4]
    selected = st.multiselect("Keywords", keywords, default=defaults or keywords[:4])
    n_weeks = st.select_slider("Weeks of history", options=[4, 8, 12, 26, 52], value=12)

    if not selected:
        return

    frames = []
    for kw in selected:
        df = get_hype_cycle(kw, n_weeks)
        df["keyword"] = kw
        frames.append(df)

    combined = pd.concat(frames)
    pivot = combined.pivot(index="iso_week", columns="keyword", values="hype_score")
    st.line_chart(pivot)

    if len(selected) == 2:
        st.caption(f"Comparing {selected[0]} vs {selected[1]}")
        diff = pivot[selected[0]] - pivot[selected[1]]
        st.bar_chart(diff.rename("Score difference"))


def _render_emerging_terms(week: str) -> None:
    df = get_emerging_terms(week)
    if df.empty:
        st.info("No emerging term data for this week. Run `tfidf_discovery.py` to populate.")
        return
    df["tfidf_score"] = df["tfidf_score"].round(4)
    st.dataframe(df, use_container_width=True)


# ── Main app ──────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="TechPulse — HN Tech Trend Radar",
        page_icon="📡",
        layout="wide",
    )
    st.title("TechPulse — HN Tech Trend Radar")

    # Sidebar
    with st.sidebar:
        st.header("Filters")
        category_filter = st.selectbox(
            "Category",
            ["All", "Languages", "Frameworks", "Tools", "AI/ML", "Platforms", "Companies"],
        )
        week = get_latest_week()
        st.caption(f"Current week: **{week}**")

        meta = get_pipeline_metadata()
        st.caption(f"Total stories: **{meta['total_stories']:,}**")
        if meta["last_run"]:
            st.caption(f"Last fetch: **{meta['last_run']}**")

    tab1, tab2, tab3 = st.tabs(["Trending Now", "Hype Cycles", "Emerging Terms"])

    with tab1:
        _render_trending_now(week, category_filter)

    with tab2:
        _render_hype_cycles(week)

    with tab3:
        _render_emerging_terms(week)


if __name__ == "__main__":
    main()
