"""Keyword detection from story title and URL."""
import re
from urllib.parse import urlparse

from transforms.taxonomy import (
    ALL_KEYWORDS,
    KEYWORD_TO_CATEGORY,
    _AMBIGUOUS_PATTERNS,
    _SIMPLE_PATTERNS,
)


def _extract_url_text(url: str | None) -> str:
    """Extract readable text from URL path/domain for matching."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        # combine host + path, replace separators with spaces
        raw = f"{parsed.netloc} {parsed.path}"
        return re.sub(r"[-_./]", " ", raw)
    except Exception:
        return ""


def detect_keywords(title: str, url: str | None = None) -> list[str]:
    """Return deduplicated list of matched tech keywords from title and URL."""
    text = title or ""
    if url:
        text = f"{text} {_extract_url_text(url)}"

    found: set[str] = set()

    # Non-ambiguous: simple word-boundary match
    for kw, pattern in _SIMPLE_PATTERNS.items():
        if pattern.search(text):
            found.add(kw)

    # Ambiguous: custom patterns
    for kw, pattern in _AMBIGUOUS_PATTERNS.items():
        if kw in KEYWORD_TO_CATEGORY and pattern.search(text):
            found.add(kw)

    return sorted(found)
