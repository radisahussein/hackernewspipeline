#!/usr/bin/env bash
# Streamlit Cloud startup script
# Downloads pre-loaded hn.duckdb from GitHub Release if not present or invalid
set -euo pipefail

DB_PATH="hn.duckdb"
RELEASE_URL="${DUCKDB_DOWNLOAD_URL:-}"

is_valid_duckdb() {
  # DuckDB files start with magic bytes: 4 bytes little-endian uint32 = file size
  # Simpler check: first 4 bytes should be non-HTML (HTML starts with '<' = 0x3C)
  local magic
  magic=$(xxd -l 4 -p "$1" 2>/dev/null || true)
  # Valid DuckDB v0.x magic prefix is not "<htm" (3c68746d)
  [ "$magic" != "3c68746d" ] && [ -n "$magic" ]
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
