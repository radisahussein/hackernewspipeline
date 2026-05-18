"""Keyword taxonomy for tech term detection."""
import re
from typing import Pattern

TAXONOMY: dict[str, list[str]] = {
    "Languages": [
        "Python", "Rust", "Go", "TypeScript", "JavaScript", "Zig", "Kotlin",
        "Swift", "Elixir", "Haskell", "Ruby", "Java", "C++", "C#", "Scala",
        "Clojure", "Erlang", "OCaml", "F#", "Nim", "Crystal", "Julia",
        "R", "Lua", "Dart", "PHP", "Perl",
    ],
    "Frameworks": [
        "Next.js", "FastAPI", "Django", "Rails", "Spring", "Svelte", "Remix",
        "Astro", "Laravel", "Express", "NestJS", "Nuxt", "SvelteKit",
        "Flask", "FastHTML", "Litestar", "Hono", "Elysia", "Bun",
        "React", "Vue", "Angular", "Solid", "Qwik",
    ],
    "Tools": [
        "Docker", "Kubernetes", "Terraform", "dbt", "Kafka", "Airflow",
        "Prefect", "Grafana", "Prometheus", "Helm", "Ansible", "Pulumi",
        "Nix", "Git", "GitHub", "GitLab", "Nginx", "Caddy", "Traefik",
        "Redis", "Elasticsearch", "OpenTelemetry", "Jaeger", "Temporal",
        "uv", "ruff", "mypy", "Pydantic",
    ],
    "AI/ML": [
        "LLM", "GPT", "Claude", "Gemini", "PyTorch", "JAX", "Ollama",
        "RAG", "fine-tuning", "TensorFlow", "Hugging Face", "Llama",
        "Mistral", "Whisper", "Stable Diffusion", "RLHF", "LoRA", "QLoRA",
        "embeddings", "vector search", "transformer", "diffusion model",
        "multimodal", "agentic", "MCP",
    ],
    "Platforms": [
        "Supabase", "Vercel", "Railway", "Fly.io", "MotherDuck", "Neon",
        "PlanetScale", "Cloudflare", "AWS", "GCP", "Azure", "Render",
        "Netlify", "Heroku", "DigitalOcean", "Hetzner", "Tailscale",
        "Coolify", "Kamal",
    ],
    "Companies": [
        "Anthropic", "OpenAI", "Google DeepMind", "Mistral", "Hugging Face",
        "Databricks", "Snowflake", "HashiCorp", "JetBrains", "Grafana Labs",
        "Confluent", "dbt Labs", "Posit",
    ],
}

# Terms requiring special regex (word boundary + negative lookahead)
# Values are raw regex patterns applied to the full title/url text
AMBIGUOUS: dict[str, str] = {
    "Go": r"\bGo\b(?!\s+(?:to|ahead|back|through|away|home|on|off|up|down|out|in|over|under))",
    "Rust": r"\bRust\b(?!y\b)",
    "R": r"\bR\b(?=\s+(?:language|programming|package|cran|tidyverse|\d)|\s*$)",
    "C": r"\bC\b(?=\s+(?:language|programming|\+\+|#))",
    "Lua": r"\bLua\b",
    "RAG": r"\bRAG\b",
    "MCP": r"\bMCP\b",
}

# Build lookup: keyword -> category
KEYWORD_TO_CATEGORY: dict[str, str] = {
    kw: cat
    for cat, keywords in TAXONOMY.items()
    for kw in keywords
}

# All keywords as a flat list
ALL_KEYWORDS: list[str] = list(KEYWORD_TO_CATEGORY.keys())

# Precompile patterns for non-ambiguous keywords
# Use word boundary; escape dots for things like "Next.js"
_SIMPLE_PATTERNS: dict[str, Pattern] = {}
for _kw in ALL_KEYWORDS:
    if _kw not in AMBIGUOUS:
        escaped = re.escape(_kw)
        _SIMPLE_PATTERNS[_kw] = re.compile(rf"\b{escaped}\b", re.IGNORECASE)

_AMBIGUOUS_PATTERNS: dict[str, Pattern] = {
    kw: re.compile(pattern, re.IGNORECASE) for kw, pattern in AMBIGUOUS.items()
}
