#!/usr/bin/env bash
# Streamlit Cloud startup script
# Downloads pre-loaded hn.duckdb from GitHub Release if not present.
# Validation is handled by app.py using the venv Python+DuckDB.
set -euo pipefail

DB_PATH="hn.duckdb"
RELEASE_URL="${DUCKDB_DOWNLOAD_URL:-}"

# Convert release tag page URL to direct asset download URL if needed
# e.g. .../releases/tag/v1.0.0 → .../releases/download/v1.0.0/hn.duckdb
normalize_url() {
  local url="$1"
  if [[ "$url" =~ /releases/tag/([^/]+)$ ]]; then
    local tag="${BASH_REMATCH[1]}"
    local base="${url%/releases/tag/*}"
    echo "${base}/releases/download/${tag}/hn.duckdb"
  else
    echo "$url"
  fi
}

if [ ! -f "$DB_PATH" ]; then
  if [ -n "$RELEASE_URL" ]; then
    DOWNLOAD_URL="$(normalize_url "$RELEASE_URL")"
    echo "Downloading pre-loaded database from $DOWNLOAD_URL"
    curl -fsSL "$DOWNLOAD_URL" -o "$DB_PATH"
    echo "Download complete: $(du -sh $DB_PATH | cut -f1)"
  else
    echo "No DUCKDB_DOWNLOAD_URL set and hn.duckdb not present."
    echo "Dashboard will start with empty database."
  fi
fi
