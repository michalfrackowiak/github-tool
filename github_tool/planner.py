"""Phase 3 query planner: slice GitHub search queries to stay under the
1,000-result cap.

The planner uses logarithmic star buckets first, then splits large buckets by
star midpoint and finally by creation-date ranges. Each slice is a standalone
query the crawler can run and checkpoint independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable

from .keywords import Keyword
from .models import utc_today


MAX_RESULTS = 1000
GITHUB_EPOCH = date(2008, 1, 1)

STAR_SEGMENTS: tuple[tuple[int, int | None], ...] = (
    (0, 9),
    (10, 49),
    (50, 199),
    (200, 999),
    (1000, 4999),
    (5000, 19999),
    (20000, 99999),
    (100000, None),
)


@dataclass(frozen=True)
class QuerySlice:
    query: str
    keyword: str | None = None
    language: str | None = None
    stars: tuple[int, int | None] = (0, None)
    created: tuple[date | None, date | None] = (None, None)
    estimated_count: int | None = None
    overflow: bool = False
    # True only for the summary slice emitted when max_slices cut the plan short.
    truncated: bool = False

    @property
    def label(self) -> str:
        bits = []
        if self.keyword:
            bits.append(self.keyword)
        if self.language:
            bits.append(self.language)
        lo, hi = self.stars
        bits.append(f"stars {lo}+" if hi is None else f"stars {lo}-{hi}")
        if self.created[0] or self.created[1]:
            bits.append(f"created {self.created[0] or '...'}..{self.created[1] or '...'}")
        return " · ".join(bits)

    def as_dict(self) -> dict[str, object]:
        return {
            "query": self.query,
            "keyword": self.keyword,
            "language": self.language,
            "estimated_count": self.estimated_count,
            "overflow": self.overflow,
        }


def _stars_qualifier(stars: tuple[int, int | None]) -> str:
    lo, hi = stars
    if hi is None:
        return f"stars:>={lo}"
    return f"stars:{lo}..{hi}"


def _created_qualifier(created: tuple[date | None, date | None]) -> str | None:
    start, end = created
    if not start and not end:
        return None
    if start and end:
        return f"created:{start.isoformat()}..{end.isoformat()}"
    if start:
        return f"created:>={start.isoformat()}"
    return f"created:<={end.isoformat()}"  # type: ignore[union-attr]


def compose_query(
    base: str,
    language: str | None,
    stars: tuple[int, int | None],
    created: tuple[date | None, date | None] = (None, None),
    min_stars: int = 0,
    in_readme: bool = False,
    include_forks: bool = False,
) -> str:
    parts = [base]
    if in_readme:
        parts.append("in:readme")
    if include_forks:
        parts.append("fork:true")
    if language:
        parts.append(f"language:{language}")
    if stars[1] is not None or stars[0] > 0 or min_stars > 0:
        parts.append(_stars_qualifier((max(stars[0], min_stars), stars[1])))
    created_q = _created_qualifier(created)
    if created_q:
        parts.append(created_q)
    return " ".join(parts)


def plan_slices(
    keyword: str,
    language: str | None,
    count_fn: Callable[[str], int],
    *,
    base_query: str | None = None,
    min_stars: int = 0,
    max_results: int = MAX_RESULTS,
    today: date | None = None,
    max_slices: int = 60,
    max_count_calls: int | None = None,
    memo: dict[str, int] | None = None,
    in_readme: bool = False,
    include_forks: bool = False,
) -> list[QuerySlice]:
    """Return slices whose estimated result count is <= ``max_results``.

    ``count_fn(query)`` must return GitHub's ``total_count`` for one query.
    Results that cannot be split below the cap are marked ``overflow`` and
    still returned, so no data is silently dropped. ``max_count_calls`` bounds
    the number of live count requests (each is a search call); once the budget
    is exhausted the remaining ranges are emitted flagged as overflow. When
    ``max_slices`` cuts the plan short, one broad overflow slice marks the
    omitted ranges instead of dropping them silently.
    """
    today = today or utc_today()
    base = base_query if base_query is not None else keyword
    memo = memo if memo is not None else {}
    calls = 0

    def build(
        stars: tuple[int, int | None],
        created: tuple[date | None, date | None],
    ) -> str:
        return compose_query(
            base, language, stars, created, min_stars, in_readme, include_forks
        )

    def count(stars: tuple[int, int | None], created: tuple[date | None, date | None]) -> int:
        nonlocal calls
        query = build(stars, created)
        if query not in memo:
            memo[query] = count_fn(query)
            calls += 1
        return memo[query]

    def exhausted() -> bool:
        return max_count_calls is not None and calls >= max_count_calls

    def overflow_slice(
        stars: tuple[int, int | None],
        created: tuple[date | None, date | None],
        *,
        truncated: bool = False,
    ) -> QuerySlice:
        return QuerySlice(
            query=build(stars, created),
            keyword=keyword,
            language=language,
            stars=stars,
            created=created,
            estimated_count=None,
            overflow=True,
            truncated=truncated,
        )

    out: list[QuerySlice] = []
    truncated_by_cap = False

    # Cheap path: one count for the whole (language, min-stars) query. Most
    # keyword/language combos are under the cap, so this avoids 8 bucket counts.
    base_total = count((0, None), (None, None))
    if base_total <= max_results:
        out.append(
            QuerySlice(
                query=build((0, None), (None, None)),
                keyword=keyword,
                language=language,
                stars=(min_stars if min_stars > 0 else 0, None),
                created=(None, None),
                estimated_count=base_total,
                overflow=False,
            )
        )
        return out

    def emit(
        stars: tuple[int, int | None],
        created: tuple[date | None, date | None],
        known: int | None = None,
    ) -> None:
        nonlocal truncated_by_cap
        if len(out) >= max_slices:
            truncated_by_cap = True
            return
        if known is None:
            if exhausted():
                out.append(overflow_slice(stars, created))
                return
            known = count(stars, created)
        n = known
        out.append(
            QuerySlice(
                query=build(stars, created),
                keyword=keyword,
                language=language,
                stars=stars,
                created=created,
                estimated_count=n,
                overflow=n > max_results,
            )
        )

    def split_date(stars: tuple[int, int | None], lo: date, hi: date, depth: int) -> None:
        nonlocal truncated_by_cap
        if len(out) >= max_slices:
            truncated_by_cap = True
            return
        if exhausted():
            out.append(overflow_slice(stars, (lo, hi)))
            return
        n = count(stars, (lo, hi))
        if n <= max_results or depth >= 8 or (hi - lo).days <= 31:
            out.append(
                QuerySlice(
                    query=build(stars, (lo, hi)),
                    keyword=keyword,
                    language=language,
                    stars=stars,
                    created=(lo, hi),
                    estimated_count=n,
                    overflow=n > max_results,
                )
            )
            return
        mid = lo + timedelta(days=(hi - lo).days // 2)
        split_date(stars, lo, mid, depth + 1)
        split_date(stars, mid + timedelta(days=1), hi, depth + 1)

    def split_stars(lo: int, hi: int | None, depth: int) -> None:
        nonlocal truncated_by_cap
        if len(out) >= max_slices:
            truncated_by_cap = True
            return
        stars = (lo, hi)
        if exhausted():
            out.append(overflow_slice(stars, (None, None)))
            return
        n = count(stars, (None, None))
        if n <= max_results:
            # Pass the count we already paid for: emit() must not mistake the
            # exhausted budget for an unknown/overflowing slice.
            emit(stars, (None, None), n)
            return
        if hi is None:
            # Open-ended upper bucket: split by creation date instead.
            split_date(stars, GITHUB_EPOCH, today, 0)
            return
        if lo >= hi or depth >= 6:
            split_date(stars, GITHUB_EPOCH, today, 0)
            return
        mid = (lo + hi) // 2
        split_stars(lo, mid, depth + 1)
        split_stars(mid + 1, hi, depth + 1)

    for lo, hi in STAR_SEGMENTS:
        if hi is not None and hi < min_stars:
            continue
        lo = max(lo, min_stars)
        if hi is not None and lo > hi:
            continue
        if len(out) >= max_slices:
            truncated_by_cap = True
            break
        split_stars(lo, hi, 0)

    if truncated_by_cap and max_slices > 0:
        # One broad, explicitly flagged slice stands in for the ranges that
        # did not fit the cap, so the crawler still sees the omission.
        marker = overflow_slice((0, None), (GITHUB_EPOCH, today), truncated=True)
        if marker.query not in {sl.query for sl in out}:
            out.append(marker)

    return out


def plan_keyword(
    keyword: Keyword | str,
    language: str | None,
    count_fn: Callable[[str], int],
    *,
    min_stars: int = 0,
    max_results: int = MAX_RESULTS,
    today: date | None = None,
    max_count_calls: int | None = None,
    memo: dict[str, int] | None = None,
    in_readme: bool = False,
    include_forks: bool = False,
) -> list[QuerySlice]:
    """Plan every variant of a keyword and merge by query.

    Generic keywords ("DB", "API") get a topic query plus phrase queries, so the
    crawler sees more than one slice family per keyword. ``in_readme`` and
    ``include_forks`` are forwarded to every generated slice, matching
    ``plan_slices`` and ``Crawler.plan_profile``.
    """
    from .keywords import get_keyword

    kw = get_keyword(keyword) if isinstance(keyword, str) else keyword
    memo = memo if memo is not None else {}
    slices: list[QuerySlice] = []
    seen: set[str] = set()
    for base in kw.variants():
        for sl in plan_slices(
            kw.slug,
            language,
            count_fn,
            base_query=base,
            min_stars=min_stars,
            max_results=max_results,
            today=today,
            max_count_calls=max_count_calls,
            memo=memo,
            in_readme=in_readme,
            include_forks=include_forks,
        ):
            if sl.query in seen:
                continue
            seen.add(sl.query)
            slices.append(sl)
    return slices
