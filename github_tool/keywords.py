"""Predefined keyword map and crawl profiles.

Generic terms such as "DB" or "API" are weak GitHub queries on their own, so
each keyword expands to a topic qualifier plus a couple of phrases. The crawler
runs every variant and merges the results locally by repo id.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


LANGUAGES: tuple[str, ...] = (
    "Python",
    "JavaScript",
    "TypeScript",
    "Go",
    "Rust",
    "C",
    "C++",
    "Java",
    "PHP",
    "Ruby",
    "C#",
    "Swift",
    "Kotlin",
    "Jupyter Notebook",
    "Zig",
)

# Display windows used everywhere (UI, links, trend engine).
WINDOWS: tuple[tuple[str, str, int], ...] = (
    ("today", "Today", 1),
    ("7d", "Last 7 days", 7),
    ("30d", "Last 30 days", 30),
    ("90d", "Last 90 days", 90),
    ("365d", "Last year", 365),
)

WINDOW_DAYS: dict[str, int] = {key: days for key, _, days in WINDOWS}
WINDOW_LABELS: dict[str, str] = {key: label for key, label, _ in WINDOWS}


@dataclass(frozen=True)
class Keyword:
    name: str
    slug: str
    topic: str | None
    phrases: tuple[str, ...] = ()
    description: str = ""

    def variants(self) -> list[str]:
        """Query fragments, one per variant (without language qualifier)."""
        out: list[str] = []
        if self.topic:
            out.append(f"topic:{self.topic}")
        for phrase in self.phrases:
            out.append(f'"{phrase}"' if " " in phrase else phrase)
        return out or [self.name]

    def search_queries(self, language: str | None = None, min_stars: int = 0) -> list[str]:
        queries = []
        for variant in self.variants():
            parts = [variant]
            if language:
                parts.append(f"language:{language}")
            if min_stars > 0:
                parts.append(f"stars:>={min_stars}")
            queries.append(" ".join(parts))
        return queries

    def link_query(self, language: str | None = None) -> str:
        """A single query for link-out views: topic when available, else phrase."""
        base = self.variants()[0]
        return f"{base} language:{language}" if language else base

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "slug": self.slug,
            "topic": self.topic,
            "phrases": list(self.phrases),
            "description": self.description,
            "variants": self.variants(),
        }


KEYWORDS: tuple[Keyword, ...] = (
    Keyword("RAG", "rag", "rag", ("retrieval augmented generation",), "Retrieval-augmented generation frameworks and tools"),
    Keyword("LLM", "llm", "llm", ("large language model", "llm inference"), "Large language model tooling and applications"),
    Keyword("DB", "db", "database", ("database engine", "sql database"), "Databases, storage engines, and SQL tooling"),
    Keyword("API", "api", "api", ("api framework", "rest api"), "API frameworks, gateways, and clients"),
    Keyword("Agents", "agents", "ai-agents", ("ai agent", "agentic framework"), "AI agents and agentic orchestration"),
    Keyword("Vector DB", "vector-db", "vector-database", ("vector database", "vector search"), "Vector databases and similarity search"),
    Keyword("MCP", "mcp", "mcp", ("model context protocol", "mcp server"), "Model Context Protocol servers and clients"),
    Keyword("Inference", "inference", "inference", ("llm inference", "model serving"), "Model inference and serving engines"),
    Keyword("Embeddings", "embeddings", "embeddings", ("embedding model", "vector embeddings"), "Embedding models and utilities"),
    Keyword("Fine-tuning", "finetuning", "fine-tuning", ("fine tuning", "lora"), "Fine-tuning and parameter-efficient training"),
    Keyword("Self-hosted", "self-hosted", "self-hosted", ("self hosted", "self-hosted"), "Self-hostable applications and tooling"),
    Keyword("Devtools", "devtools", "developer-tools", ("developer tools", "dev tooling"), "Developer tooling and productivity"),
)

KEYWORD_BY_SLUG: dict[str, Keyword] = {k.slug: k for k in KEYWORDS}
KEYWORD_BY_NAME: dict[str, Keyword] = {k.name: k for k in KEYWORDS}


@dataclass(frozen=True)
class CrawlProfile:
    name: str
    keywords: tuple[str, ...]
    languages: tuple[str, ...]
    min_stars: int = 20
    fetch_readmes: bool = True
    description: str = ""


PROFILES: dict[str, CrawlProfile] = {
    "default": CrawlProfile(
        "default",
        tuple(k.slug for k in KEYWORDS),
        ("Python", "TypeScript", "JavaScript", "Go", "Rust", "C", "C++", "Java", "PHP"),
        description="All keywords across the most common languages",
    ),
    "ai": CrawlProfile(
        "ai",
        ("rag", "llm", "agents", "vector-db", "mcp", "inference", "embeddings", "finetuning"),
        ("Python", "TypeScript", "Go", "Rust"),
        description="AI/LLM keywords",
    ),
    "systems": CrawlProfile(
        "systems",
        ("db", "inference", "api"),
        ("C", "C++", "Rust", "Go", "Zig"),
        description="Systems and infrastructure keywords",
    ),
    "web": CrawlProfile(
        "web",
        ("api", "self-hosted", "devtools", "llm"),
        ("TypeScript", "JavaScript", "Python", "Go", "PHP", "Ruby"),
        description="Web application and tooling keywords",
    ),
}


def get_keyword(name_or_slug: str) -> Keyword:
    key = name_or_slug.strip()
    if key in KEYWORD_BY_SLUG:
        return KEYWORD_BY_SLUG[key]
    if key in KEYWORD_BY_NAME:
        return KEYWORD_BY_NAME[key]
    raise KeyError(f"Unknown keyword: {name_or_slug!r}")


def keyword_map_document() -> dict[str, object]:
    return {
        "generated_for": "github-tool",
        "languages": list(LANGUAGES),
        "windows": [
            {"key": key, "label": label, "days": days} for key, label, days in WINDOWS
        ],
        "keywords": [k.to_dict() for k in KEYWORDS],
        "profiles": {
            name: {
                "keywords": list(p.keywords),
                "languages": list(p.languages),
                "min_stars": p.min_stars,
                "fetch_readmes": p.fetch_readmes,
                "description": p.description,
            }
            for name, p in PROFILES.items()
        },
    }


def write_keyword_map(path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(keyword_map_document(), indent=2) + "\n", encoding="utf-8")
    return path
