#!/usr/bin/env bash
# Streamlit Cloud startup script
# Downloads pre-loaded hn.duckdb from GitHub Release if not present
set -euo pipefail

DB_PATH="hn.duckdb"
RELEASE_URL="${DUCKDB_DOWNLOAD_URL:-}"

if [ ! -f "$DB_PATH" ]; then
  if [ -n "$RELEASE_URL" ]; then
    echo "Downloading pre-loaded database from $RELEASE_URL"
    curl -fsSL "$RELEASE_URL" -o "$DB_PATH"
    echo "Download complete: $(du -sh $DB_PATH | cut -f1)"
  else
    echo "No DUCKDB_DOWNLOAD_URL set and hn.duckdb not present."
    echo "Dashboard will start with empty database."
  fi
fi
