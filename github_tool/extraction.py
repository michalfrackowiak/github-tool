"""Heuristic (and optional LLM) extraction of install commands and hardware
requirements from repository READMEs and manifest files.

Everything here is pure text processing: nothing is executed, evaluated, or
fetched. The optional :class:`LLMExtractor` only calls the ``complete``
callable supplied by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import shlex
from typing import Any, Callable, Iterable, Mapping

try:  # Python 3.11+; kept optional so the module stays importable otherwise.
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - requires-python is >=3.11
    tomllib = None  # type: ignore[assignment]


# --------------------------------------------------------------------------- #
# Public models
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ExtractedCommand:
    cmd: str
    source_line: int
    confidence: str
    command_type: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "cmd": self.cmd,
            "source_line": self.source_line,
            "confidence": self.confidence,
            "command_type": self.command_type,
        }


@dataclass(frozen=True)
class HardwareRequirement:
    gpu: bool | None
    vram_gb: float | None
    ram_gb: float | None
    disk_gb: float | None
    os: str | None
    source_line: int
    confidence: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "gpu": self.gpu,
            "vram_gb": self.vram_gb,
            "ram_gb": self.ram_gb,
            "disk_gb": self.disk_gb,
            "os": self.os,
            "source_line": self.source_line,
            "confidence": self.confidence,
        }


@dataclass
class ExtractionResult:
    commands: list[ExtractedCommand]
    hardware: list[HardwareRequirement]
    readme_hash: str
    manifest: dict[str, Any] | None = None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def readme_hash(text: str) -> str:
    """Stable content hash used to skip unchanged READMEs."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


_INSTALL_SECTION_WORDS = (
    "install",
    "installation",
    "quickstart",
    "quick start",
    "getting started",
    "setup",
    "set up",
    "build",
    "usage",
    "run",
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_PLACEHOLDER_RE = re.compile(
    r"<your[-_ ]|\byour[_-]?(?:api[_-]?key|token|secret|key)\b|YOUR_API_KEY"
    r"|<\.\.\.>|<[A-Za-z_][A-Za-z0-9_.-]*>|\{[A-Za-z_][A-Za-z0-9_.-]*\}",
    re.IGNORECASE,
)
_NUMBER_UNIT_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(GiB|GB)\b", re.IGNORECASE)

_GPU_RE = re.compile(r"\b(?:gpu|cuda|nvidia)\b", re.IGNORECASE)
_VRAM_RE = re.compile(r"\b(?:vram|video\s+memory|gpu\s+memory)\b", re.IGNORECASE)
_RAM_RE = re.compile(r"\b(?:ram|system\s+memory|main\s+memory|memory)\b", re.IGNORECASE)
_DISK_RE = re.compile(r"\b(?:disk|storage|hard\s+drive|hard\s+disk|ssd)\b", re.IGNORECASE)
_HW_KEYWORD_RE = re.compile(
    r"\b(?:gpu|cuda|nvidia|vram|ram|memory|disk|storage|hard\s+drive|hard\s+disk|ssd)\b",
    re.IGNORECASE,
)

_OS_PATTERNS = (
    ("Ubuntu", re.compile(r"\bubuntu\b", re.IGNORECASE)),
    ("Windows", re.compile(r"\bwindows\b", re.IGNORECASE)),
    ("macOS", re.compile(r"\bmac\s*os(?:\s+x)?\b", re.IGNORECASE)),
    ("Linux", re.compile(r"\blinux\b", re.IGNORECASE)),
)

# Prefixes are matched case-insensitively and must be followed by whitespace
# (or be the entire command).
_COMMAND_TYPES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "install",
        (
            "pip install",
            "pip3 install",
            "python -m pip install",
            "python3 -m pip install",
            "uv add",
            "poetry add",
            "conda install",
            "conda create",
            "npm install",
            "npm i",
            "yarn add",
            "yarn install",
            "pnpm add",
            "pnpm install",
            "bun add",
            "bun install",
            "go install",
            "go get",
            "cargo install",
            "gem install",
            "composer require",
            "dotnet add",
            "docker pull",
            "brew install",
            "apt install",
            "apt-get install",
            "make install",
        ),
    ),
    (
        "build",
        (
            "docker build",
            "docker compose build",
            "docker-compose build",
            "make build",
        ),
    ),
    (
        "run",
        (
            "docker run",
            "docker compose up",
            "docker-compose up",
        ),
    ),
    ("clone", ("git clone",)),
)


def _command_type(cmd: str) -> str | None:
    low = cmd.lower()
    for kind, prefixes in _COMMAND_TYPES:
        for prefix in prefixes:
            if low == prefix or low.startswith(prefix + " "):
                return kind
    return None


def _strip_inline_comment(s: str) -> str:
    """Drop a trailing ``# comment`` while respecting quotes."""
    quote: str | None = None
    for i, ch in enumerate(s):
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in {"'", '"'}:
            quote = ch
        elif ch == "#" and i > 0 and s[i - 1].isspace():
            return s[:i].rstrip()
    return s


def _clean_command_line(line: str) -> str | None:
    """Strip shell prompts/markup. Return None when there is nothing left."""
    s = line.strip()
    if not s:
        return None
    if s.startswith("$"):
        s = s[1:].lstrip()
    elif s.startswith(">"):
        s = s[2:].strip() if s.startswith("> ") else s[1:].strip()
    if len(s) >= 2 and s.startswith("`") and s.endswith("`"):
        s = s[1:-1].strip()
    return _strip_inline_comment(s) or None


def _iter_lines(text: str) -> list[str]:
    # splitlines() tolerates \r\n, \n, and \r without inventing a final line.
    return text.splitlines()


# --------------------------------------------------------------------------- #
# README parsing
# --------------------------------------------------------------------------- #


def _extract_commands(text: str) -> list[ExtractedCommand]:
    lines = _iter_lines(text)
    commands: list[ExtractedCommand] = []
    seen: set[tuple[str, int]] = set()

    in_fence = False
    fence_marker = ""
    install_section = False

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        line_no = idx + 1
        stripped = line.strip()

        if in_fence:
            if stripped.startswith(fence_marker):
                in_fence = False
                fence_marker = ""
                idx += 1
                continue
        else:
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = True
                fence_marker = stripped[:3]
                idx += 1
                continue

            heading = _HEADING_RE.match(line)
            if heading:
                heading_text = heading.group(2).lower()
                install_section = any(word in heading_text for word in _INSTALL_SECTION_WORDS)
                idx += 1
                continue

        cmd = _clean_command_line(line)
        if cmd is None:
            idx += 1
            continue
        if cmd.startswith("#") and not cmd.startswith("#!"):
            idx += 1
            continue
        if _PLACEHOLDER_RE.search(cmd):
            idx += 1
            continue

        kind = _command_type(cmd)
        if kind is None:
            idx += 1
            continue

        # A trailing backslash means the instruction continues on the next
        # lines. Keep the whole command (and report the first line number).
        if cmd.endswith("\\"):
            parts = [cmd[:-1].rstrip()]
            continues = True
            j = idx + 1
            while continues and j < len(lines):
                cont_raw = lines[j].strip()
                if (fence_marker and cont_raw.startswith(fence_marker)) or (
                    not in_fence and (cont_raw.startswith("```") or cont_raw.startswith("~~~"))
                ):
                    break
                cont = _clean_command_line(lines[j])
                if cont is None or cont.startswith("#"):
                    break
                continues = cont.endswith("\\")
                parts.append(cont[:-1].rstrip() if continues else cont)
                j += 1
            cmd = " ".join(part for part in parts if part)
            idx = j - 1
            if _PLACEHOLDER_RE.search(cmd):
                idx += 1
                continue

        if in_fence and install_section:
            confidence = "high"
        elif in_fence or install_section:
            confidence = "medium"
        else:
            confidence = "low"

        key = (cmd, line_no)
        if key in seen:
            idx += 1
            continue
        seen.add(key)
        commands.append(
            ExtractedCommand(
                cmd=cmd,
                source_line=line_no,
                confidence=confidence,
                command_type=kind,
            )
        )
        if len(commands) >= 100:
            break
        idx += 1

    return commands


def _spans(pattern: re.Pattern[str], text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in pattern.finditer(text)]


def _numbers(text: str) -> list[tuple[int, int, float]]:
    return [(m.start(), m.end(), float(m.group(1))) for m in _NUMBER_UNIT_RE.finditer(text)]


def _distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    a_start, a_end = a
    b_start, b_end = b
    if a_end <= b_start:
        return b_start - a_end
    if b_end <= a_start:
        return a_start - b_end
    return 0


def _nearest_number(
    numbers: list[tuple[int, int, float]],
    keyword_spans: Iterable[tuple[int, int]],
    used: set[int],
    *,
    max_distance: int = 50,
) -> int | None:
    spans = list(keyword_spans)
    if not spans:
        return None
    best_idx: int | None = None
    best_dist: int | None = None
    for num_idx, (start, end, _value) in enumerate(numbers):
        if num_idx in used:
            continue
        dist = min(_distance((start, end), span) for span in spans)
        if dist > max_distance:
            continue
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_idx = num_idx
    return best_idx


def _detect_os(lower_and_original: str) -> str | None:
    matches: list[tuple[int, str]] = []
    for name, pattern in _OS_PATTERNS:
        m = pattern.search(lower_and_original)
        if m:
            matches.append((m.start(), name))
    if not matches:
        return None
    # Ubuntu is more specific than Linux and wins when both are present.
    if any(candidate == "Ubuntu" for _pos, candidate in matches):
        return "Ubuntu"
    return min(matches, key=lambda item: item[0])[1]


def _extract_hardware(text: str) -> list[HardwareRequirement]:
    lines = _iter_lines(text)
    requirements: list[HardwareRequirement] = []
    seen: set[tuple[Any, ...]] = set()

    in_fence = False
    fence_marker = ""

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if in_fence:
            if stripped.startswith(fence_marker):
                in_fence = False
                fence_marker = ""
                continue
        else:
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = True
                fence_marker = stripped[:3]
                continue
            if _HEADING_RE.match(line):
                continue

        if not stripped:
            continue

        gpu_present = bool(_GPU_RE.search(line))
        vram_spans = _spans(_VRAM_RE, line)
        ram_spans = _spans(_RAM_RE, line)
        disk_spans = _spans(_DISK_RE, line)
        os_name = _detect_os(line)

        has_keyword = bool(_HW_KEYWORD_RE.search(line)) or os_name is not None
        if not has_keyword:
            continue

        numbers = _numbers(line)
        used: set[int] = set()

        vram_gb: float | None = None
        idx_vram = _nearest_number(numbers, vram_spans, used)
        if idx_vram is None and gpu_present and not ram_spans and not disk_spans:
            idx_vram = _nearest_number(numbers, _spans(_GPU_RE, line), used)
        if idx_vram is not None:
            vram_gb = numbers[idx_vram][2]
            used.add(idx_vram)

        ram_gb: float | None = None
        idx_ram = _nearest_number(numbers, ram_spans, used)
        if idx_ram is not None:
            ram_gb = numbers[idx_ram][2]
            used.add(idx_ram)

        disk_gb: float | None = None
        idx_disk = _nearest_number(numbers, disk_spans, used)
        if idx_disk is not None:
            disk_gb = numbers[idx_disk][2]
            used.add(idx_disk)

        if numbers and has_keyword:
            confidence = "high"
        elif has_keyword:
            confidence = "medium"
        else:  # pragma: no cover - has_keyword already guarantees one branch
            confidence = "low"

        key = (idx, gpu_present, vram_gb, ram_gb, disk_gb, os_name, confidence)
        if key in seen:
            continue
        seen.add(key)
        requirements.append(
            HardwareRequirement(
                gpu=True if gpu_present else None,
                vram_gb=vram_gb,
                ram_gb=ram_gb,
                disk_gb=disk_gb,
                os=os_name,
                source_line=idx,
                confidence=confidence,
            )
        )

    return requirements


def extract_from_readme(text: str) -> ExtractionResult:
    """Run the dependency-free heuristics over a README."""
    return ExtractionResult(
        commands=_extract_commands(text),
        hardware=_extract_hardware(text),
        readme_hash=readme_hash(text),
    )


# --------------------------------------------------------------------------- #
# Optional LLM pass
# --------------------------------------------------------------------------- #


LLM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["install_commands", "hardware"],
    "properties": {
        "install_commands": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["cmd", "source_line", "confidence", "command_type"],
                "properties": {
                    "cmd": {"type": "string"},
                    "source_line": {"type": "integer", "minimum": 1},
                    "confidence": {"enum": ["high", "medium", "low"]},
                    "command_type": {"enum": ["install", "run", "build", "clone"]},
                },
            },
        },
        "hardware": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["source_line", "confidence"],
                "properties": {
                    "gpu": {"type": ["boolean", "null"]},
                    "vram_gb": {"type": ["number", "null"]},
                    "ram_gb": {"type": ["number", "null"]},
                    "disk_gb": {"type": ["number", "null"]},
                    "os": {"type": ["string", "null"]},
                    "source_line": {"type": "integer", "minimum": 1},
                    "confidence": {"enum": ["high", "medium", "low"]},
                },
            },
        },
    },
}

_CONFIDENCES = {"high", "medium", "low"}
_COMMAND_TYPES_ALLOWED = {"install", "run", "build", "clone"}


def _coerce_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def _coerce_confidence(value: Any, field: str) -> str:
    if not isinstance(value, str) or value not in _CONFIDENCES:
        raise ValueError(f"{field} must be one of high, medium, low")
    return value


def _coerce_optional_number(value: Any, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number or null")
    return float(value)


def parse_llm_payload(raw: str) -> dict[str, Any]:
    """Parse and strictly validate the JSON returned by an LLM.

    A fenced ```json block is accepted. Raises :class:`ValueError` for invalid
    JSON or an unexpected shape.
    """
    if not isinstance(raw, str):
        raise ValueError("LLM payload must be a string")

    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        # Be a little forgiving about prose around a JSON object.
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("LLM payload is not valid JSON") from None
        try:
            payload = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM payload is not valid JSON: {exc}") from None

    if not isinstance(payload, dict):
        raise ValueError("LLM payload must be a JSON object")

    commands_raw = payload.get("install_commands", [])
    hardware_raw = payload.get("hardware", [])
    if not isinstance(commands_raw, list):
        raise ValueError("install_commands must be a list")
    if not isinstance(hardware_raw, list):
        raise ValueError("hardware must be a list")

    commands: list[dict[str, Any]] = []
    for i, item in enumerate(commands_raw):
        if not isinstance(item, dict):
            raise ValueError(f"install_commands[{i}] must be an object")
        cmd = item.get("cmd")
        if not isinstance(cmd, str) or not cmd.strip():
            raise ValueError(f"install_commands[{i}].cmd must be a non-empty string")
        source_line = _coerce_int(item.get("source_line"), f"install_commands[{i}].source_line")
        if source_line < 1:
            raise ValueError(f"install_commands[{i}].source_line must be >= 1")
        confidence = _coerce_confidence(item.get("confidence"), f"install_commands[{i}].confidence")
        command_type = item.get("command_type")
        if not isinstance(command_type, str) or command_type not in _COMMAND_TYPES_ALLOWED:
            raise ValueError(
                f"install_commands[{i}].command_type must be one of install, run, build, clone"
            )
        commands.append(
            {
                "cmd": cmd.strip(),
                "source_line": source_line,
                "confidence": confidence,
                "command_type": command_type,
            }
        )

    hardware: list[dict[str, Any]] = []
    for i, item in enumerate(hardware_raw):
        if not isinstance(item, dict):
            raise ValueError(f"hardware[{i}] must be an object")
        gpu = item.get("gpu")
        if gpu is not None and not isinstance(gpu, bool):
            raise ValueError(f"hardware[{i}].gpu must be a boolean or null")
        source_line = _coerce_int(item.get("source_line"), f"hardware[{i}].source_line")
        if source_line < 1:
            raise ValueError(f"hardware[{i}].source_line must be >= 1")
        confidence = _coerce_confidence(item.get("confidence"), f"hardware[{i}].confidence")
        os_name = item.get("os")
        if os_name is not None and not isinstance(os_name, str):
            raise ValueError(f"hardware[{i}].os must be a string or null")
        hardware.append(
            {
                "gpu": gpu,
                "vram_gb": _coerce_optional_number(item.get("vram_gb"), f"hardware[{i}].vram_gb"),
                "ram_gb": _coerce_optional_number(item.get("ram_gb"), f"hardware[{i}].ram_gb"),
                "disk_gb": _coerce_optional_number(item.get("disk_gb"), f"hardware[{i}].disk_gb"),
                "os": os_name,
                "source_line": source_line,
                "confidence": confidence,
            }
        )

    return {"install_commands": commands, "hardware": hardware}


def _build_llm_prompt(readme_text: str) -> str:
    schema = json.dumps(LLM_SCHEMA, indent=2)
    example = (
        '{"install_commands":[{"cmd":"pip install x","source_line":12,'
        '"confidence":"high","command_type":"install"}],'
        '"hardware":[{"gpu":true,"vram_gb":16,"ram_gb":32,"disk_gb":50,'
        '"os":"Linux","source_line":42,"confidence":"medium"}]}'
    )
    return (
        "Extract the install/run/build/clone commands and the hardware "
        "requirements from the GitHub README below.\n"
        "Return ONLY strict JSON (no prose, no markdown around it) matching "
        "this JSON Schema:\n"
        f"{schema}\n\n"
        f"Example output: {example}\n\n"
        "Rules: source_line is the 1-based line number in the README; use only "
        '"high", "medium", or "low" for confidence; omit unknown hardware values '
        "by using null.\n\n"
        "README:\n<<<\n"
        f"{readme_text[:12000]}\n"
        ">>>\n"
    )


class LLMExtractor:
    """Strict optional LLM extraction layer.

    ``complete`` is any callable taking a prompt and returning the model's raw
    string response. It is invoked exactly once per extraction.
    """

    def __init__(self, complete: Callable[[str], str]):
        self.complete = complete

    def extract(self, readme_text: str) -> ExtractionResult:
        raw = self.complete(_build_llm_prompt(readme_text))
        payload = parse_llm_payload(raw)

        line_count = len(_iter_lines(readme_text))
        commands: list[ExtractedCommand] = []
        for item in payload["install_commands"]:
            if line_count < 1:
                continue
            line = max(1, min(item["source_line"], line_count))
            commands.append(
                ExtractedCommand(
                    cmd=item["cmd"],
                    source_line=line,
                    confidence=item["confidence"],
                    command_type=item["command_type"],
                )
            )

        hardware: list[HardwareRequirement] = []
        for item in payload["hardware"]:
            if line_count < 1:
                continue
            line = max(1, min(item["source_line"], line_count))
            hardware.append(
                HardwareRequirement(
                    gpu=item["gpu"],
                    vram_gb=item["vram_gb"],
                    ram_gb=item["ram_gb"],
                    disk_gb=item["disk_gb"],
                    os=item["os"],
                    source_line=line,
                    confidence=item["confidence"],
                )
            )

        return ExtractionResult(
            commands=commands[:100],
            hardware=hardware,
            readme_hash=readme_hash(readme_text),
        )


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #


def _merge_results(
    heuristic: ExtractionResult,
    llm_result: ExtractionResult,
) -> ExtractionResult:
    commands: list[ExtractedCommand] = []
    seen_commands: set[tuple[str, int]] = set()
    for command in [*heuristic.commands, *llm_result.commands]:
        key = (command.cmd, command.source_line)
        if key in seen_commands:
            continue
        seen_commands.add(key)
        commands.append(command)

    hardware: list[HardwareRequirement] = list(heuristic.hardware)
    seen_hardware = {
        (
            req.gpu,
            req.vram_gb,
            req.ram_gb,
            req.disk_gb,
            req.os,
            req.source_line,
            req.confidence,
        )
        for req in hardware
    }
    for req in llm_result.hardware:
        key = (
            req.gpu,
            req.vram_gb,
            req.ram_gb,
            req.disk_gb,
            req.os,
            req.source_line,
            req.confidence,
        )
        if key in seen_hardware:
            continue
        seen_hardware.add(key)
        hardware.append(req)

    return ExtractionResult(
        commands=commands[:100],
        hardware=hardware,
        readme_hash=heuristic.readme_hash,
    )


def extract_for_repo(
    db: Any,
    repo_id: int,
    readme_text: str | None,
    *,
    force: bool = False,
    llm: Any | None = None,
    manifests: Mapping[str, str] | None = None,
) -> ExtractionResult | None:
    """Extract, persist, and return results for one repo.

    Returns ``None`` when the README is missing or its hash matches the last
    successful extraction (unless ``force`` is true). ``manifests`` is an
    optional mapping of file path to text (requirements/pyproject/Dockerfile).
    """
    if readme_text is None:
        return None

    digest = readme_hash(readme_text)
    # Manifest hints are independent of the README hash: persist them even
    # when the README was already extracted and the rest of this call skips.
    hints = manifest_hints(manifests) if manifests else None
    if hints is not None and db.get_manifest_hints(repo_id) != hints:
        db.update_manifest_hints(repo_id, hints)
    status = db.extraction_status(repo_id)
    # The crawler also stores readme_hash when it fetches a README, so a hash
    # match alone does not mean extraction has run. Require extracted_at.
    if (
        not force
        and status
        and status.get("readme_hash") == digest
        and status.get("extracted_at")
    ):
        return None

    result = extract_from_readme(readme_text)

    if llm is not None:
        extractor = llm if hasattr(llm, "extract") else LLMExtractor(llm)
        llm_result = extractor.extract(readme_text)
        result = _merge_results(result, llm_result)

    result.manifest = hints

    db.replace_install_commands(repo_id, [command.as_dict() for command in result.commands])
    db.replace_hw_requirements(repo_id, [req.as_dict() for req in result.hardware])
    db.mark_extracted(repo_id, result.readme_hash)
    return result


# --------------------------------------------------------------------------- #
# Manifest hints
# --------------------------------------------------------------------------- #

_MAX_HINTS = 100


def _dedupe(items: Iterable[str], limit: int = _MAX_HINTS) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
        if len(out) >= limit:
            break
    return out


def _requirements_deps(text: str) -> list[str]:
    deps: list[str] = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        deps.append(line)
    return deps


def _pyproject_deps(text: str) -> list[str]:
    deps: list[str] = []
    if tomllib is not None:
        try:
            data = tomllib.loads(text)
        except Exception:
            data = None
        if isinstance(data, dict):
            project = data.get("project", {})
            if isinstance(project, dict):
                for dep in project.get("dependencies", []) or []:
                    if isinstance(dep, str):
                        deps.append(dep)
            poetry = data.get("tool", {})
            if isinstance(poetry, dict):
                poetry = poetry.get("poetry", {})
            if isinstance(poetry, dict):
                poetry_deps = poetry.get("dependencies", {})
                if isinstance(poetry_deps, dict):
                    for name in poetry_deps:
                        if isinstance(name, str) and name.lower() != "python":
                            deps.append(name)
            if deps:
                return deps

    # Crude fallback for malformed TOML.
    for block in re.findall(r"dependencies\s*=\s*\[(.*?)\]", text, re.DOTALL):
        deps.extend(re.findall(r"[\"']([^\"']+)[\"']", block))
    poetry_match = re.search(
        r"\[tool\.poetry\.dependencies\](.*?)(?:^\[|\Z)", text, re.DOTALL | re.MULTILINE
    )
    if poetry_match:
        for name in re.findall(r"^\s*([A-Za-z0-9_.-]+)\s*=", poetry_match.group(1), re.MULTILINE):
            if name.lower() != "python":
                deps.append(name)
    return deps


def _docker_base_images(text: str) -> list[str]:
    images: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not re.match(r"(?i)^from\s+", stripped):
            continue
        rest = re.sub(r"(?i)^from\s+", "", stripped)
        rest = rest.split("#", 1)[0].strip()
        tokens = rest.split()
        while tokens and tokens[0].startswith("--"):
            tokens.pop(0)
        if tokens:
            images.append(tokens[0])
    return images


def _docker_env(text: str) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not re.match(r"(?i)^env\s+", stripped):
            continue
        if "cuda" not in stripped.lower() and "gpu" not in stripped.lower():
            continue
        rest = re.sub(r"(?i)^env\s+", "", stripped)
        try:
            tokens = shlex.split(rest)
        except ValueError:
            tokens = rest.split()
        if not tokens:
            continue
        if "=" in tokens[0]:
            for token in tokens:
                if "=" in token:
                    key, value = token.split("=", 1)
                    if key:
                        env[key] = value
        else:
            key = tokens[0]
            value = " ".join(tokens[1:])
            env[key] = value
    return env


def _is_requirements_file(path: str) -> bool:
    name = Path(path).name.lower()
    return bool(re.fullmatch(r"requirements.*\.txt", name))


def _is_pyproject(path: str) -> bool:
    return Path(path).name.lower() == "pyproject.toml"


def _is_dockerfile(path: str) -> bool:
    name = Path(path).name.lower()
    return name == "dockerfile" or name.startswith("dockerfile.") or name.endswith(".dockerfile")


def manifest_hints(files: Mapping[str, str]) -> dict[str, Any]:
    """Small, bounded hints from requirements/pyproject/Dockerfile files."""
    deps: list[str] = []
    base_images: list[str] = []
    env: dict[str, str] = {}
    gpu_hints: list[str] = []

    for path, text in files.items():
        if not isinstance(text, str):
            continue
        if _is_requirements_file(path):
            deps.extend(_requirements_deps(text))
        elif _is_pyproject(path):
            deps.extend(_pyproject_deps(text))
        elif _is_dockerfile(path):
            images = _docker_base_images(text)
            base_images.extend(images)
            env.update(_docker_env(text))
            for line in text.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                low = stripped.lower()
                if "cuda" in low or "gpu" in low or "rocm" in low:
                    gpu_hints.append(stripped)
            for image in images:
                low = image.lower()
                if "cuda" in low or "gpu" in low or "rocm" in low:
                    gpu_hints.append(image)

    return {
        "python_dependencies": _dedupe(deps),
        "docker_base_images": _dedupe(base_images),
        "docker_env": dict(list(env.items())[:_MAX_HINTS]),
        "gpu_hints": _dedupe(gpu_hints),
    }
