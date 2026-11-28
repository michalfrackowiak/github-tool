"""SQLite store: schema, FTS5, crawl checkpoints, saved searches, caches."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, timedelta
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Iterator, Mapping, Sequence

from .models import Repo, StarDay, utc_today


SCHEMA_VERSION = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS repos (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,
    description TEXT,
    language TEXT,
    topics TEXT NOT NULL DEFAULT '[]',
    created_at TEXT,
    pushed_at TEXT,
    updated_at TEXT,
    archived INTEGER NOT NULL DEFAULT 0,
    fork INTEGER NOT NULL DEFAULT 0,
    stars INTEGER NOT NULL DEFAULT 0,
    forks INTEGER NOT NULL DEFAULT 0,
    license TEXT,
    homepage TEXT,
    default_branch TEXT,
    readme_text TEXT,
    readme_etag TEXT,
    readme_hash TEXT,
    fetched_at TEXT,
    extracted_at TEXT,
    manifest_hints TEXT
);
CREATE INDEX IF NOT EXISTS idx_repos_language ON repos(language);
CREATE INDEX IF NOT EXISTS idx_repos_stars ON repos(stars DESC);
CREATE INDEX IF NOT EXISTS idx_repos_pushed ON repos(pushed_at DESC);

CREATE VIRTUAL TABLE IF NOT EXISTS repos_fts USING fts5(
    full_name,
    description,
    readme_text,
    content='repos',
    content_rowid='id',
    tokenize='unicode61'
);
CREATE TRIGGER IF NOT EXISTS repos_ai AFTER INSERT ON repos BEGIN
    INSERT INTO repos_fts(rowid, full_name, description, readme_text)
    VALUES (new.id, new.full_name, new.description, new.readme_text);
END;
CREATE TRIGGER IF NOT EXISTS repos_ad AFTER DELETE ON repos BEGIN
    INSERT INTO repos_fts(repos_fts, rowid, full_name, description, readme_text)
    VALUES ('delete', old.id, old.full_name, old.description, old.readme_text);
END;
CREATE TRIGGER IF NOT EXISTS repos_au AFTER UPDATE ON repos BEGIN
    INSERT INTO repos_fts(repos_fts, rowid, full_name, description, readme_text)
    VALUES ('delete', old.id, old.full_name, old.description, old.readme_text);
    INSERT INTO repos_fts(rowid, full_name, description, readme_text)
    VALUES (new.id, new.full_name, new.description, new.readme_text);
END;

CREATE TABLE IF NOT EXISTS repo_keywords (
    repo_id INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    PRIMARY KEY (repo_id, keyword)
);
CREATE INDEX IF NOT EXISTS idx_repo_keywords_keyword ON repo_keywords(keyword);

CREATE TABLE IF NOT EXISTS star_daily (
    repo_id INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    day TEXT NOT NULL,
    stars_gained INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (repo_id, day)
);

CREATE TABLE IF NOT EXISTS snapshots (
    repo_id INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    day TEXT NOT NULL,
    stars INTEGER NOT NULL,
    forks INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (repo_id, day)
);

CREATE TABLE IF NOT EXISTS crawl_runs (
    id TEXT PRIMARY KEY,
    profile TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    cursor TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'running',
    error TEXT
);

CREATE TABLE IF NOT EXISTS crawl_slices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES crawl_runs(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,
    query TEXT NOT NULL,
    keyword TEXT,
    language TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    total_count INTEGER,
    estimated_count INTEGER,
    overflow INTEGER NOT NULL DEFAULT 0,
    pages_done INTEGER NOT NULL DEFAULT 0,
    graphql_cursor TEXT,
    error TEXT,
    UNIQUE(run_id, idx)
);

CREATE TABLE IF NOT EXISTS saved_searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    params TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Automatic history is intentionally separate from named saves: names stay
-- unique and user-controlled, while every executed search leaves a row here.
CREATE TABLE IF NOT EXISTS search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    params TEXT NOT NULL,
    source TEXT NOT NULL,
    result_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crawl_jobs (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    profile TEXT NOT NULL,
    params TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    phase TEXT NOT NULL DEFAULT 'queued',
    summary TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    finished_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_status ON crawl_jobs(status);

CREATE TABLE IF NOT EXISTS http_cache (
    url TEXT PRIMARY KEY,
    etag TEXT,
    body TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS install_commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    cmd TEXT NOT NULL,
    source_line INTEGER NOT NULL,
    confidence TEXT NOT NULL,
    command_type TEXT NOT NULL DEFAULT 'install',
    seen_at TEXT NOT NULL,
    UNIQUE(repo_id, cmd, source_line)
);

CREATE TABLE IF NOT EXISTS hw_requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    gpu INTEGER,
    vram_gb REAL,
    ram_gb REAL,
    disk_gb REAL,
    os TEXT,
    source_line INTEGER NOT NULL,
    confidence TEXT NOT NULL,
    seen_at TEXT NOT NULL
);
"""


def _iso_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _windows_from_rows(
    daily: Sequence[tuple[date, int]],
    snapshots: Sequence[tuple[date, int]],
    windows: Sequence[int],
    today: date,
    created: date | None,
) -> dict[int, tuple[int, bool]]:
    """Pure window math shared by single-repo and bulk trend queries."""

    def snapshot_gain(days: int) -> int | None:
        since = today - timedelta(days=days)
        latest = next(((d, s) for d, s in reversed(snapshots) if d <= today), None)
        baseline = next(((d, s) for d, s in reversed(snapshots) if d <= since), None)
        if latest is None or baseline is None:
            return None
        if (today - latest[0]).days > 2 or (since - baseline[0]).days > 2:
            return None
        return latest[1] - baseline[1]

    out: dict[int, tuple[int, bool]] = {}
    for days in windows:
        start = today - timedelta(days=max(days - 1, 0))
        in_window = [(d, g) for d, g in daily if start <= d <= today]
        if in_window:
            total = sum(g for _, g in in_window)
            first = min(d for d, _ in in_window)
            complete = first <= start + timedelta(days=2) or (
                created is not None and created >= start
            )
            if complete:
                out[days] = (total, True)
                continue
            snapped = snapshot_gain(days)
            out[days] = (snapped, True) if snapped is not None else (total, False)
            continue
        snapped = snapshot_gain(days)
        out[days] = (snapped, True) if snapped is not None else (0, False)
    return out


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._memory_conn: sqlite3.Connection | None = None
        if str(self.path) == ":memory:":
            self._memory_conn = self._new_connection()

    def _new_connection(self) -> sqlite3.Connection:
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        if str(self.path) != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL")
        return conn

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        if self._memory_conn is not None:
            try:
                yield self._memory_conn
                self._memory_conn.commit()
            except Exception:
                self._memory_conn.rollback()
                raise
            return
        conn = self._new_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            self._migrate(conn)
            conn.execute(
                "INSERT INTO schema_meta(key, value) VALUES('version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(SCHEMA_VERSION),),
            )
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        """Additive migrations for databases created by older builds."""
        columns = {row[1] for row in conn.execute("PRAGMA table_info(repos)").fetchall()}
        additions = {
            "description": "TEXT",
            "topics": "TEXT NOT NULL DEFAULT '[]'",
            "updated_at": "TEXT",
            "license": "TEXT",
            "homepage": "TEXT",
            "default_branch": "TEXT",
            "readme_etag": "TEXT",
            "readme_hash": "TEXT",
            "extracted_at": "TEXT",
            "manifest_hints": "TEXT",
        }
        for name, ddl in additions.items():
            if name not in columns:
                conn.execute(f"ALTER TABLE repos ADD COLUMN {name} {ddl}")
        slice_columns = {row[1] for row in conn.execute("PRAGMA table_info(crawl_slices)").fetchall()}
        slice_additions = {
            "estimated_count": "INTEGER",
            "overflow": "INTEGER NOT NULL DEFAULT 0",
            "graphql_cursor": "TEXT",
        }
        for name, ddl in slice_additions.items():
            if name not in slice_columns:
                conn.execute(f"ALTER TABLE crawl_slices ADD COLUMN {name} {ddl}")

    # ------------------------------------------------------------------ repos
    def upsert_repo(self, repo: Repo, keyword: str | None = None) -> bool:
        with self.connect() as conn:
            inserted = self._upsert_repo(conn, repo, keyword)
        return inserted

    @staticmethod
    def _upsert_repo(conn: sqlite3.Connection, repo: Repo, keyword: str | None = None) -> bool:
        # GitHub reuses names after renames. Free a name held by a different
        # numeric id so the current owner wins without aborting the crawl.
        stale = conn.execute(
            "SELECT id FROM repos WHERE full_name=? AND id<>?", (repo.full_name, repo.id)
        ).fetchall()
        for row in stale:
            conn.execute(
                "UPDATE repos SET full_name=? WHERE id=?",
                (f"{repo.full_name}#{row['id']}", row["id"]),
            )
        existed = conn.execute("SELECT 1 FROM repos WHERE id = ?", (repo.id,)).fetchone() is not None
        conn.execute(
            """
            INSERT INTO repos (id, full_name, url, description, language, topics,
                               created_at, pushed_at, updated_at, archived, fork,
                               stars, forks, license, homepage, default_branch,
                               readme_text, readme_etag, readme_hash, fetched_at)
            VALUES (:id, :full_name, :url, :description, :language, :topics,
                    :created_at, :pushed_at, :updated_at, :archived, :fork,
                    :stars, :forks, :license, :homepage, :default_branch,
                    :readme_text, :readme_etag, :readme_hash, :fetched_at)
            ON CONFLICT(id) DO UPDATE SET
                full_name=excluded.full_name,
                url=excluded.url,
                description=excluded.description,
                language=excluded.language,
                topics=excluded.topics,
                created_at=excluded.created_at,
                pushed_at=excluded.pushed_at,
                updated_at=excluded.updated_at,
                archived=excluded.archived,
                fork=excluded.fork,
                stars=excluded.stars,
                forks=excluded.forks,
                license=excluded.license,
                homepage=excluded.homepage,
                default_branch=excluded.default_branch,
                readme_text=COALESCE(excluded.readme_text, repos.readme_text),
                readme_etag=COALESCE(excluded.readme_etag, repos.readme_etag),
                readme_hash=COALESCE(excluded.readme_hash, repos.readme_hash),
                fetched_at=COALESCE(excluded.fetched_at, repos.fetched_at)
            """,
            {
                "id": repo.id,
                "full_name": repo.full_name,
                "url": repo.url,
                "description": repo.description,
                "language": repo.language,
                "topics": json.dumps(repo.topics or []),
                "created_at": repo.created_at,
                "pushed_at": repo.pushed_at,
                "updated_at": repo.updated_at,
                "archived": int(repo.archived),
                "fork": int(repo.fork),
                "stars": repo.stars,
                "forks": repo.forks,
                "license": repo.license,
                "homepage": repo.homepage,
                "default_branch": repo.default_branch,
                "readme_text": repo.readme_text,
                "readme_etag": repo.readme_etag,
                "readme_hash": repo.readme_hash,
                "fetched_at": repo.fetched_at or _iso_now(),
            },
        )
        if keyword:
            conn.execute(
                "INSERT OR IGNORE INTO repo_keywords(repo_id, keyword) VALUES(?, ?)",
                (repo.id, keyword),
            )
        return not existed

    @staticmethod
    def _row_to_repo(row: sqlite3.Row) -> Repo:
        try:
            topics = json.loads(row["topics"] or "[]")
        except (json.JSONDecodeError, TypeError):
            topics = []
        return Repo(
            id=row["id"],
            full_name=row["full_name"],
            url=row["url"],
            description=row["description"],
            language=row["language"],
            topics=topics,
            created_at=row["created_at"],
            pushed_at=row["pushed_at"],
            updated_at=row["updated_at"],
            archived=bool(row["archived"]),
            fork=bool(row["fork"]),
            stars=row["stars"],
            forks=row["forks"],
            license=row["license"],
            homepage=row["homepage"],
            default_branch=row["default_branch"],
            readme_text=row["readme_text"],
            readme_etag=row["readme_etag"],
            readme_hash=row["readme_hash"],
            fetched_at=row["fetched_at"],
        )

    def get_repo(self, repo_id_or_name: int | str) -> Repo | None:
        with self.connect() as conn:
            if isinstance(repo_id_or_name, int) or str(repo_id_or_name).isdigit():
                row = conn.execute("SELECT * FROM repos WHERE id = ?", (int(repo_id_or_name),)).fetchone()
            else:
                row = conn.execute("SELECT * FROM repos WHERE full_name = ?", (str(repo_id_or_name),)).fetchone()
        return self._row_to_repo(row) if row else None

    def list_repos(
        self,
        language: str | None = None,
        min_stars: int = 0,
        limit: int = 100,
        include_archived: bool = False,
        include_forks: bool = False,
    ) -> list[Repo]:
        clauses = ["stars >= ?"]
        params: list[Any] = [min_stars]
        if language:
            clauses.append("language = ?")
            params.append(language)
        if not include_archived:
            clauses.append("archived = 0")
        if not include_forks:
            clauses.append("fork = 0")
        params.append(limit)
        sql = f"SELECT * FROM repos WHERE {' AND '.join(clauses)} ORDER BY stars DESC LIMIT ?"
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_repo(r) for r in rows]

    def count_repos(self) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM repos").fetchone()[0])

    def keyword_counts(self) -> dict[str, int]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT keyword, COUNT(*) AS n FROM repo_keywords GROUP BY keyword ORDER BY n DESC"
            ).fetchall()
        return {r["keyword"]: int(r["n"]) for r in rows}

    @staticmethod
    def _fts_query(query: str) -> str:
        terms = [t for t in query.replace('"', " ").split() if t]
        return " ".join(f'"{t.replace(chr(34), chr(34) * 2)}"' for t in terms)

    def search_fts(self, query: str, limit: int = 50) -> list[Repo]:
        match = self._fts_query(query)
        if not match:
            return []
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT r.* FROM repos_fts f
                JOIN repos r ON r.id = f.rowid
                WHERE repos_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (match, limit),
            ).fetchall()
        return [self._row_to_repo(r) for r in rows]

    def update_readme(self, repo_id: int, text: str | None, etag: str | None, readme_hash: str | None) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE repos SET readme_text=?, readme_etag=?, readme_hash=?, fetched_at=? WHERE id=?",
                (text, etag, readme_hash, _iso_now(), repo_id),
            )

    def readme_etag(self, repo_id: int) -> str | None:
        with self.connect() as conn:
            row = conn.execute("SELECT readme_etag FROM repos WHERE id=?", (repo_id,)).fetchone()
        return row["readme_etag"] if row else None

    def set_keywords(self, repo_id: int, keywords: Iterable[str]) -> None:
        with self.connect() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO repo_keywords(repo_id, keyword) VALUES(?, ?)",
                [(repo_id, k) for k in keywords],
            )

    # --------------------------------------------------------------- star data
    def save_star_days(self, repo_id: int, days: Iterable[StarDay]) -> None:
        rows = [(repo_id, d.day.isoformat(), d.gained) for d in days]
        if not rows:
            return
        with self.connect() as conn:
            conn.executemany(
                "INSERT INTO star_daily(repo_id, day, stars_gained) VALUES(?, ?, ?) "
                "ON CONFLICT(repo_id, day) DO UPDATE SET stars_gained=excluded.stars_gained",
                rows,
            )

    def get_star_days(self, repo_id: int, since: date | None = None, until: date | None = None) -> list[StarDay]:
        clauses = ["repo_id = ?"]
        params: list[Any] = [repo_id]
        if since:
            clauses.append("day >= ?")
            params.append(since.isoformat())
        if until:
            clauses.append("day <= ?")
            params.append(until.isoformat())
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT day, stars_gained FROM star_daily WHERE {' AND '.join(clauses)} ORDER BY day",
                params,
            ).fetchall()
        return [StarDay(date.fromisoformat(r["day"]), int(r["stars_gained"])) for r in rows]

    def sum_star_days(self, repo_id: int, days: int, today: date | None = None) -> tuple[int, int]:
        """Return (number of daily rows, sum) for the inclusive window."""
        today = today or utc_today()
        since = today - timedelta(days=max(days - 1, 0))
        with self.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) n, COALESCE(SUM(stars_gained), 0) s FROM star_daily "
                "WHERE repo_id=? AND day >= ? AND day <= ?",
                (repo_id, since.isoformat(), today.isoformat()),
            ).fetchone()
        return int(row["n"]), int(row["s"])

    def trend_windows(
        self,
        repo_id: int,
        windows: Sequence[int],
        today: date | None = None,
        created: date | None = None,
    ) -> dict[int, tuple[int, bool]]:
        """All window gains for one repo using a single database connection."""
        today = today or utc_today()
        windows = list(windows)
        if not windows:
            return {}
        earliest = today - timedelta(days=max(max(windows) - 1, 0))
        with self.connect() as conn:
            daily_rows = conn.execute(
                "SELECT day, stars_gained FROM star_daily "
                "WHERE repo_id=? AND day>=? AND day<=? ORDER BY day",
                (repo_id, earliest.isoformat(), today.isoformat()),
            ).fetchall()
            snapshot_rows = conn.execute(
                "SELECT day, stars FROM snapshots WHERE repo_id=? AND day<=? ORDER BY day",
                (repo_id, today.isoformat()),
            ).fetchall()

        daily = [(date.fromisoformat(r["day"]), int(r["stars_gained"])) for r in daily_rows]
        snapshots = [(date.fromisoformat(r["day"]), int(r["stars"])) for r in snapshot_rows]
        return _windows_from_rows(daily, snapshots, windows, today, created)

    def bulk_trend_windows(
        self,
        repo_ids: Sequence[int],
        windows: Sequence[int],
        today: date | None = None,
        created_by_id: Mapping[int, date | None] | None = None,
    ) -> dict[int, dict[int, tuple[int, bool]]]:
        """Window gains for many repos using a single connection.

        ``get_trending`` used to open one connection per candidate repo, which
        made large local indexes unusably slow. Rows are fetched in batches so
        SQLite's variable limit is never approached.
        """
        today = today or utc_today()
        ids = list(dict.fromkeys(repo_ids))
        if not ids or not windows:
            return {}
        earliest = (today - timedelta(days=max(max(windows) - 1, 0))).isoformat()
        through = today.isoformat()
        daily_by_id: dict[int, list[tuple[date, int]]] = {rid: [] for rid in ids}
        snaps_by_id: dict[int, list[tuple[date, int]]] = {rid: [] for rid in ids}
        created_by_id = created_by_id or {}
        with self.connect() as conn:
            for start in range(0, len(ids), 500):
                chunk = ids[start : start + 500]
                marks = ",".join("?" for _ in chunk)
                for row in conn.execute(
                    f"SELECT repo_id, day, stars_gained FROM star_daily "
                    f"WHERE repo_id IN ({marks}) AND day>=? AND day<=? ORDER BY repo_id, day",
                    (*chunk, earliest, through),
                ):
                    daily_by_id[row["repo_id"]].append(
                        (date.fromisoformat(row["day"]), int(row["stars_gained"]))
                    )
                for row in conn.execute(
                    f"SELECT repo_id, day, stars FROM snapshots "
                    f"WHERE repo_id IN ({marks}) AND day<=? ORDER BY repo_id, day",
                    (*chunk, through),
                ):
                    snaps_by_id[row["repo_id"]].append(
                        (date.fromisoformat(row["day"]), int(row["stars"]))
                    )
        return {
            rid: _windows_from_rows(
                daily_by_id[rid], snaps_by_id[rid], windows, today, created_by_id.get(rid)
            )
            for rid in ids
        }

    def star_day_bounds(
        self, repo_id: int, days: int, today: date | None = None
    ) -> tuple[date | None, date | None]:
        """First and last stored day inside the inclusive window."""
        today = today or utc_today()
        since = today - timedelta(days=max(days - 1, 0))
        with self.connect() as conn:
            row = conn.execute(
                "SELECT MIN(day) lo, MAX(day) hi FROM star_daily "
                "WHERE repo_id=? AND day >= ? AND day <= ?",
                (repo_id, since.isoformat(), today.isoformat()),
            ).fetchone()
        if not row or row["lo"] is None:
            return None, None
        return date.fromisoformat(row["lo"]), date.fromisoformat(row["hi"])

    def save_snapshot(self, repo_id: int, stars: int, forks: int = 0, day: date | None = None) -> None:
        day = day or utc_today()
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO snapshots(repo_id, day, stars, forks) VALUES(?, ?, ?, ?) "
                "ON CONFLICT(repo_id, day) DO UPDATE SET stars=excluded.stars, forks=excluded.forks",
                (repo_id, day.isoformat(), stars, forks),
            )

    def snapshot_gain(self, repo_id: int, days: int, today: date | None = None) -> int | None:
        today = today or utc_today()
        since = today - timedelta(days=days)
        with self.connect() as conn:
            latest = conn.execute(
                "SELECT day, stars FROM snapshots WHERE repo_id=? AND day<=? ORDER BY day DESC LIMIT 1",
                (repo_id, today.isoformat()),
            ).fetchone()
            baseline = conn.execute(
                "SELECT day, stars FROM snapshots WHERE repo_id=? AND day<=? ORDER BY day DESC LIMIT 1",
                (repo_id, since.isoformat()),
            ).fetchone()
        if not latest or not baseline:
            return None
        # Only use snapshots that actually bracket the requested window. An
        # arbitrarily old baseline would report e.g. months of growth as a
        # "1-day" gain.
        if (today - date.fromisoformat(latest["day"])).days > 2:
            return None
        if (since - date.fromisoformat(baseline["day"])).days > 2:
            return None
        return int(latest["stars"]) - int(baseline["stars"])

    def snapshot_count(self, repo_id: int) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM snapshots WHERE repo_id=?", (repo_id,)).fetchone()[0])

    def get_snapshots(self, repo_id: int, since: date | None = None, until: date | None = None) -> list[dict[str, Any]]:
        clauses = ["repo_id = ?"]
        params: list[Any] = [repo_id]
        if since:
            clauses.append("day >= ?")
            params.append(since.isoformat())
        if until:
            clauses.append("day <= ?")
            params.append(until.isoformat())
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT day, stars, forks FROM snapshots WHERE {' AND '.join(clauses)} ORDER BY day",
                params,
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------- crawl runs
    def start_run(self, profile: str) -> str:
        import uuid

        run_id = uuid.uuid4().hex
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO crawl_runs(id, profile, started_at, status, cursor) VALUES(?, ?, ?, 'running', '{}')",
                (run_id, profile, _iso_now()),
            )
        return run_id

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM crawl_runs WHERE id=?", (run_id,)).fetchone()
        return dict(row) if row else None

    def latest_run(self) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM crawl_runs ORDER BY started_at DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    def latest_run_since(self, started_at: str) -> dict[str, Any] | None:
        """Find the run a web job started without assuming it is the newest run."""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM crawl_runs WHERE started_at >= ? ORDER BY started_at DESC LIMIT 1",
                (started_at,),
            ).fetchone()
        return dict(row) if row else None

    def update_run(self, run_id: str, **fields: Any) -> None:
        if not fields:
            return
        allowed = {"status", "cursor", "finished_at", "error"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        assignments = ", ".join(f"{k}=?" for k in updates)
        with self.connect() as conn:
            conn.execute(f"UPDATE crawl_runs SET {assignments} WHERE id=?", (*updates.values(), run_id))

    def add_slices(self, run_id: str, slices: list[dict[str, Any]]) -> None:
        with self.connect() as conn:
            for idx, sl in enumerate(slices):
                conn.execute(
                    "INSERT OR IGNORE INTO crawl_slices"
                    "(run_id, idx, query, keyword, language, total_count, estimated_count, overflow) "
                    "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        run_id,
                        idx,
                        sl["query"],
                        sl.get("keyword"),
                        sl.get("language"),
                        sl.get("total_count"),
                        sl.get("estimated_count"),
                        1 if sl.get("overflow") else 0,
                    ),
                )

    def pending_slices(self, run_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM crawl_slices WHERE run_id=? AND status NOT IN ('done', 'partial') "
                "ORDER BY idx",
                (run_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def update_slice(self, slice_id: int, **fields: Any) -> None:
        allowed = {
            "status",
            "total_count",
            "estimated_count",
            "overflow",
            "pages_done",
            "graphql_cursor",
            "error",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        assignments = ", ".join(f"{k}=?" for k in updates)
        with self.connect() as conn:
            conn.execute(f"UPDATE crawl_slices SET {assignments} WHERE id=?", (*updates.values(), slice_id))

    def slice_counts(self, run_id: str) -> dict[str, int]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) n FROM crawl_slices WHERE run_id=? GROUP BY status", (run_id,)
            ).fetchall()
        return {r["status"]: int(r["n"]) for r in rows}

    # ----------------------------------------------------------- saved searches
    def save_search(self, name: str, params: dict[str, Any]) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO saved_searches(name, params, created_at) VALUES(?, ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET params=excluded.params",
                (name, json.dumps(params), _iso_now()),
            )
            return int(cur.lastrowid or 0)

    def list_saved_searches(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM saved_searches ORDER BY name").fetchall()
        return [
            {"id": r["id"], "name": r["name"], "params": json.loads(r["params"]), "created_at": r["created_at"]}
            for r in rows
        ]

    def delete_saved_search(self, name: str) -> bool:
        with self.connect() as conn:
            cur = conn.execute("DELETE FROM saved_searches WHERE name=?", (name,))
            return cur.rowcount > 0

    # --------------------------------------------------------- search history
    def record_search(
        self, params: dict[str, Any], *, source: str = "api", result_count: int = 0
    ) -> int:
        """Append an automatic search-history entry; named saves are untouched."""
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO search_history(params, source, result_count, created_at) "
                "VALUES(?, ?, ?, ?)",
                (json.dumps(params, sort_keys=True), source, int(result_count), _iso_now()),
            )
            return int(cur.lastrowid or 0)

    def list_search_history(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM search_history ORDER BY id DESC LIMIT ?", (max(1, int(limit)),)
            ).fetchall()
        return [
            {
                "id": r["id"],
                "params": json.loads(r["params"]),
                "source": r["source"],
                "result_count": int(r["result_count"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def clear_search_history(self) -> int:
        with self.connect() as conn:
            cur = conn.execute("DELETE FROM search_history")
            return cur.rowcount

    # ------------------------------------------------------------- crawl jobs
    def claim_crawl_job(
        self, job_id: str, profile: str, params: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Claim the single active web crawl slot, or return ``None`` if busy.

        ``BEGIN IMMEDIATE`` makes the check-and-insert atomic even if the app is
        later run with more than one worker process against the same database.
        """
        now = _iso_now()
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._reap_stale_crawl_jobs_conn(conn)
            active = conn.execute(
                "SELECT id FROM crawl_jobs WHERE status IN ('queued', 'running') LIMIT 1"
            ).fetchone()
            if active is not None:
                return None
            conn.execute(
                "INSERT INTO crawl_jobs(id, profile, params, status, phase, created_at, updated_at) "
                "VALUES(?, ?, ?, 'queued', 'queued', ?, ?)",
                (job_id, profile, json.dumps(params, sort_keys=True), now, now),
            )
            return {
                "id": job_id,
                "profile": profile,
                "params": dict(params),
                "status": "queued",
                "phase": "queued",
                "created_at": now,
                "updated_at": now,
            }

    def get_crawl_job(self, job_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM crawl_jobs WHERE id=?", (job_id,)).fetchone()
        return self._crawl_job_row(row) if row is not None else None

    def active_crawl_job(self) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM crawl_jobs WHERE status IN ('queued', 'running') "
                "ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        return self._crawl_job_row(row) if row is not None else None

    @staticmethod
    def _reap_stale_crawl_jobs_conn(
        conn: sqlite3.Connection, max_age_seconds: int = 900
    ) -> int:
        """Release jobs idle long enough to be considered abandoned."""
        from datetime import datetime, timedelta, timezone

        cutoff = (
            datetime.now(timezone.utc) - timedelta(seconds=max(0, int(max_age_seconds)))
        ).isoformat(timespec="seconds").replace("+00:00", "Z")
        error = f"Interrupted by a server restart or stale worker (idle > {max_age_seconds}s)."
        now = _iso_now()
        cur = conn.execute(
            "UPDATE crawl_jobs SET status='failed', phase='error', error=?, finished_at=?, "
            "updated_at=? WHERE status IN ('queued', 'running') AND updated_at < ?",
            (error, now, now, cutoff),
        )
        return cur.rowcount

    def reap_stale_crawl_jobs(self, max_age_seconds: int = 900) -> int:
        """Release jobs left behind by a killed/restarted web process.

        Called at app startup and again while claiming a slot. Heartbeats keep
        a live crawl's ``updated_at`` fresh so it is never reaped mid-run.
        """
        with self.connect() as conn:
            return self._reap_stale_crawl_jobs_conn(conn, max_age_seconds)

    def update_crawl_job(self, job_id: str, **fields: Any) -> None:
        if not fields:
            return
        allowed = {"run_id", "status", "phase", "summary", "error", "finished_at"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        updates["updated_at"] = _iso_now()
        if "summary" in updates and updates["summary"] is not None:
            updates["summary"] = json.dumps(updates["summary"], sort_keys=True)
        assignments = ", ".join(f"{k}=?" for k in updates)
        with self.connect() as conn:
            conn.execute(f"UPDATE crawl_jobs SET {assignments} WHERE id=?", (*updates.values(), job_id))

    @staticmethod
    def _crawl_job_row(row: sqlite3.Row) -> dict[str, Any]:
        summary = row["summary"]
        return {
            "id": row["id"],
            "run_id": row["run_id"],
            "profile": row["profile"],
            "params": json.loads(row["params"]),
            "status": row["status"],
            "phase": row["phase"],
            "summary": json.loads(summary) if summary else None,
            "error": row["error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "finished_at": row["finished_at"],
        }

    # ---------------------------------------------------------------- http cache
    def get_http_cache(self, url: str) -> tuple[str | None, str] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT etag, body FROM http_cache WHERE url=?", (url,)).fetchone()
        return (row["etag"], row["body"]) if row else None

    def put_http_cache(self, url: str, etag: str | None, body: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO http_cache(url, etag, body, fetched_at) VALUES(?, ?, ?, ?) "
                "ON CONFLICT(url) DO UPDATE SET etag=excluded.etag, body=excluded.body, fetched_at=excluded.fetched_at",
                (url, etag, body, _iso_now()),
            )

    # --------------------------------------------------------------- extraction
    def replace_install_commands(self, repo_id: int, commands: Iterable[dict[str, Any]]) -> None:
        now = _iso_now()
        with self.connect() as conn:
            conn.execute("DELETE FROM install_commands WHERE repo_id=?", (repo_id,))
            conn.executemany(
                "INSERT OR IGNORE INTO install_commands(repo_id, cmd, source_line, confidence, command_type, seen_at) "
                "VALUES(?, ?, ?, ?, ?, ?)",
                [
                    (repo_id, c["cmd"], c["source_line"], c["confidence"], c.get("command_type", "install"), now)
                    for c in commands
                ],
            )

    def replace_hw_requirements(self, repo_id: int, reqs: Iterable[dict[str, Any]]) -> None:
        now = _iso_now()
        with self.connect() as conn:
            conn.execute("DELETE FROM hw_requirements WHERE repo_id=?", (repo_id,))
            conn.executemany(
                "INSERT INTO hw_requirements(repo_id, gpu, vram_gb, ram_gb, disk_gb, os, source_line, confidence, seen_at) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        repo_id,
                        r.get("gpu"),
                        r.get("vram_gb"),
                        r.get("ram_gb"),
                        r.get("disk_gb"),
                        r.get("os"),
                        r["source_line"],
                        r["confidence"],
                        now,
                    )
                    for r in reqs
                ],
            )

    def get_install_commands(self, repo_id: int) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM install_commands WHERE repo_id=? ORDER BY source_line", (repo_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_hw_requirements(self, repo_id: int) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM hw_requirements WHERE repo_id=? ORDER BY source_line", (repo_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_extracted(self, repo_id: int, readme_hash: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE repos SET readme_hash=?, extracted_at=? WHERE id=?",
                (readme_hash, _iso_now(), repo_id),
            )

    def extraction_status(self, repo_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT readme_hash, extracted_at FROM repos WHERE id=?", (repo_id,)
            ).fetchone()
        return dict(row) if row else None

    def update_manifest_hints(self, repo_id: int, hints: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE repos SET manifest_hints=? WHERE id=?",
                (json.dumps(hints), repo_id),
            )

    def get_manifest_hints(self, repo_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT manifest_hints FROM repos WHERE id=?", (repo_id,)
            ).fetchone()
        if not row or not row["manifest_hints"]:
            return None
        try:
            value = json.loads(row["manifest_hints"])
        except (TypeError, ValueError):
            return None
        return value if isinstance(value, dict) else None

    # ----------------------------------------------------------------- exports
    def export_rows(
        self,
        language: str | None = None,
        min_stars: int = 0,
        limit: int = 1000,
        include_archived: bool = False,
        include_forks: bool = False,
        keyword: str | None = None,
        license: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses = ["r.stars >= ?"]
        params: list[Any] = [min_stars]
        join = ""
        if keyword:
            join = "JOIN repo_keywords rk ON rk.repo_id = r.id"
            clauses.append("rk.keyword = ?")
            params.append(keyword)
        if language:
            clauses.append("r.language = ?")
            params.append(language)
        if license:
            clauses.append("LOWER(r.license) = ?")
            params.append(license.strip().lower())
        if not include_archived:
            clauses.append("r.archived = 0")
        if not include_forks:
            clauses.append("r.fork = 0")
        params.append(limit)
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT DISTINCT r.* FROM repos r {join} WHERE {' AND '.join(clauses)} "
                f"ORDER BY r.stars DESC LIMIT ?",
                params,
            ).fetchall()
        rows_out = []
        for row in rows:
            repo = self._row_to_repo(row)
            rows_out.append(
                {
                    "id": repo.id,
                    "full_name": repo.full_name,
                    "url": repo.url,
                    "description": repo.description or "",
                    "language": repo.language or "",
                    "stars": repo.stars,
                    "forks": repo.forks,
                    "license": repo.license or "",
                    "created_at": repo.created_at or "",
                    "pushed_at": repo.pushed_at or "",
                    "archived": repo.archived,
                    "fork": repo.fork,
                }
            )
        return rows_out
