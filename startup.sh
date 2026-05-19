#!/usr/bin/env bash
# Streamlit Cloud startup script
# Downloads pre-loaded hn.duckdb from GitHub Release if not present or invalid
set -euo pipefail

DB_PATH="hn.duckdb"
RELEASE_URL="${DUCKDB_DOWNLOAD_URL:-}"

is_valid_duckdb() {
  python3 - "$1" <<'PYEOF'
import sys, duckdb
try:
    duckdb.connect(sys.argv[1], read_only=True).close()
    sys.exit(0)
except Exception:
    sys.exit(1)
PYEOF
}

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

needs_download=false
if [ ! -f "$DB_PATH" ]; then
  needs_download=true
elif ! is_valid_duckdb "$DB_PATH"; then
  echo "Existing $DB_PATH is not a valid DuckDB file — re-downloading."
  rm -f "$DB_PATH"
  needs_download=true
fi

if [ "$needs_download" = true ]; then
  if [ -n "$RELEASE_URL" ]; then
    DOWNLOAD_URL="$(normalize_url "$RELEASE_URL")"
    echo "Downloading pre-loaded database from $DOWNLOAD_URL"
    curl -fsSL "$DOWNLOAD_URL" -o "$DB_PATH"
    echo "Download complete: $(du -sh $DB_PATH | cut -f1)"
    if ! is_valid_duckdb "$DB_PATH"; then
      echo "ERROR: Downloaded file is not a valid DuckDB database." >&2
      rm -f "$DB_PATH"
      exit 1
    fi
  else
    echo "No DUCKDB_DOWNLOAD_URL set and hn.duckdb not present."
    echo "Dashboard will start with empty database."
  fi
fi
