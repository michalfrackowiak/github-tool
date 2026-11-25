"""Application configuration.

Everything is read from the environment so secrets never live in the repo and
never end up in logs. The default database lives outside the source tree.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os


API_VERSION = "2026-03-10"
DEFAULT_DB = Path.home() / ".github-tool" / "github-tool.db"


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    db_path: Path = field(default_factory=lambda: Path(os.environ.get("GITHUB_TOOL_DB") or DEFAULT_DB))
    token: str | None = field(
        default_factory=lambda: os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or None,
        repr=False,
    )
    api_url: str = "https://api.github.com"
    graphql_url: str = "https://api.github.com/graphql"
    api_version: str = API_VERSION
    user_agent: str = "github-tool/0.1"
    offline: bool = field(default_factory=lambda: _env_bool("GITHUB_TOOL_OFFLINE"))
    request_timeout: float = 30.0
    max_retries: int = 3
    search_per_page: int = 100
    readme_max_bytes: int = 1_500_000
    # GitHub allows 30 authenticated search requests/minute (10 without token).
    search_min_interval: float = field(
        default_factory=lambda: 2.1 if (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")) else 6.1
    )
    llm_url: str | None = field(default_factory=lambda: os.environ.get("GITHUB_TOOL_LLM_URL") or None)
    llm_key: str | None = field(default_factory=lambda: os.environ.get("GITHUB_TOOL_LLM_KEY") or None, repr=False)
    llm_model: str | None = field(default_factory=lambda: os.environ.get("GITHUB_TOOL_LLM_MODEL") or None)

    @property
    def authenticated(self) -> bool:
        return bool(self.token)

    def redacted(self) -> dict[str, object]:
        """A safe representation for diagnostics."""
        return {
            "db_path": str(self.db_path),
            "api_url": self.api_url,
            "api_version": self.api_version,
            "authenticated": self.authenticated,
            "offline": self.offline,
            "llm_configured": bool(self.llm_url and self.llm_key and self.llm_model),
        }

    def require_online(self) -> None:
        if self.offline:
            raise RuntimeError("Offline mode is enabled; network access is disabled.")
