"""Tests for README/manifest extraction (Phase 6)."""

from __future__ import annotations

import json

import pytest

from github_tool.db import Database
from github_tool.extraction import (
    ExtractedCommand,
    HardwareRequirement,
    LLMExtractor,
    extract_for_repo,
    extract_from_readme,
    manifest_hints,
    parse_llm_payload,
    readme_hash,
)
from github_tool.models import Repo


INSTALL_README = """# Demo

A demo repository.

## Installation

```bash
pip install demo-pkg
npm install -g demo-cli
pip install demo-pkg
```

## Usage

Run it with `demo`.
"""


def _new_db(tmp_path) -> Database:
    db = Database(tmp_path / "test.db")
    db.initialize()
    db.upsert_repo(Repo(id=1, full_name="acme/demo", url="https://github.com/acme/demo"))
    return db


def test_install_fence_is_high_confidence_with_types_and_deduped_keys():
    result = extract_from_readme(INSTALL_README)

    assert [(c.cmd, c.source_line, c.command_type, c.confidence) for c in result.commands] == [
        ("pip install demo-pkg", 8, "install", "high"),
        ("npm install -g demo-cli", 9, "install", "high"),
        ("pip install demo-pkg", 10, "install", "high"),
    ]
    # Deduplicate by (cmd, source_line), not by command text alone.
    assert len({(c.cmd, c.source_line) for c in result.commands}) == 3


def test_command_types_cover_build_run_and_clone():
    readme = """# Tool

## Installation

```bash
docker compose up -d
make build
git clone https://github.com/acme/tool.git
```
"""
    result = extract_from_readme(readme)
    types = {c.cmd: c.command_type for c in result.commands}
    assert types == {
        "docker compose up -d": "run",
        "make build": "build",
        "git clone https://github.com/acme/tool.git": "clone",
    }
    assert all(c.confidence == "high" for c in result.commands)


def test_commands_outside_install_sections_are_medium_or_low():
    readme = """# Tool

## Notes

```bash
pip install elsewhere
```

Run it manually:

$ git clone https://github.com/acme/tool.git
"""
    result = extract_from_readme(readme)

    by_cmd = {c.cmd: c for c in result.commands}
    assert by_cmd["pip install elsewhere"].confidence == "medium"
    assert by_cmd["pip install elsewhere"].command_type == "install"
    assert by_cmd["git clone https://github.com/acme/tool.git"].confidence == "low"
    assert by_cmd["git clone https://github.com/acme/tool.git"].command_type == "clone"


def test_placeholders_and_comments_are_ignored():
    readme = """# Tool

## Installation

```bash
# pip install commented-out
pip install <your-token>
export YOUR_API_KEY=abc
pip install pkg=={version}
pip install superduper-<plugin_name>
docker run <...> ghcr.io/acme/tool:latest
pip install good-package
```
"""
    result = extract_from_readme(readme)
    assert [c.cmd for c in result.commands] == ["pip install good-package"]


def test_backslash_continuations_are_joined_with_first_line_number():
    readme = """# Tool

## Quickstart

```bash
docker run -d \\
  --name tool \\
  -p 8080:8080 \\
  ghcr.io/acme/tool:latest
pip install tool
```
"""
    result = extract_from_readme(readme)

    assert [c.cmd for c in result.commands] == [
        "docker run -d --name tool -p 8080:8080 ghcr.io/acme/tool:latest",
        "pip install tool",
    ]
    assert result.commands[0].source_line == 6
    assert result.commands[1].source_line == 10


def test_hardware_lines_are_parsed_individually():
    readme = """# Tool

Requires an NVIDIA GPU with 16GB VRAM and 32 GB RAM
At least 50 GB of free disk space
Runs on Linux.
Popularity: 1.5 GB of stars
"""
    result = extract_from_readme(readme)

    assert len(result.hardware) == 3
    gpu, disk, os_row = result.hardware
    assert gpu.gpu is True
    assert gpu.vram_gb == 16
    assert gpu.ram_gb == 32
    assert gpu.disk_gb is None
    assert gpu.source_line == 3
    assert gpu.confidence == "high"

    assert disk.gpu is None
    assert disk.disk_gb == 50
    assert disk.source_line == 4
    assert disk.confidence == "high"

    assert os_row.os == "Linux"
    assert os_row.source_line == 5
    assert os_row.confidence == "medium"


def test_no_false_positive_from_star_count_without_hardware_keyword():
    result = extract_from_readme("# Tool\n\nA popular project with 1.5 GB of stars.\n")
    assert result.hardware == []


def test_readme_hash_is_stable_and_changes_with_content():
    assert readme_hash("hello") == readme_hash("hello")
    assert readme_hash("hello") != readme_hash("hello!")


def test_extract_for_repo_stores_and_skips_unchanged(tmp_path):
    db = _new_db(tmp_path)

    first = extract_for_repo(db, 1, INSTALL_README)
    assert first is not None
    stored = db.get_install_commands(1)
    assert len(stored) == 3
    assert {row["cmd"] for row in stored} == {"pip install demo-pkg", "npm install -g demo-cli"}
    assert db.extraction_status(1)["readme_hash"] == first.readme_hash

    assert extract_for_repo(db, 1, INSTALL_README) is None
    assert extract_for_repo(db, 1, None) is None

    forced = extract_for_repo(db, 1, INSTALL_README, force=True)
    assert forced is not None

    changed = extract_for_repo(db, 1, INSTALL_README + "\nMore text.\n")
    assert changed is not None
    assert changed.readme_hash != first.readme_hash


# --------------------------------------------------------------------------- #
# LLM pass
# --------------------------------------------------------------------------- #


VALID_LLM_JSON = {
    "install_commands": [
        {"cmd": "pip install x", "source_line": 3, "confidence": "high", "command_type": "install"}
    ],
    "hardware": [
        {
            "gpu": True,
            "vram_gb": 16,
            "ram_gb": 32,
            "disk_gb": 50,
            "os": "Linux",
            "source_line": 4,
            "confidence": "medium",
        }
    ],
}


def test_parse_llm_payload_accepts_fenced_json():
    raw = "Here is the result:\n```json\n" + json.dumps(VALID_LLM_JSON) + "\n```\n"
    payload = parse_llm_payload(raw)
    assert payload["install_commands"][0]["cmd"] == "pip install x"
    assert payload["hardware"][0]["vram_gb"] == 16
    assert payload["hardware"][0]["gpu"] is True


@pytest.mark.parametrize(
    "raw",
    [
        "not json at all",
        json.dumps({"install_commands": "nope", "hardware": []}),
        json.dumps(
            {
                "install_commands": [
                    {"cmd": "pip install x", "source_line": 0, "confidence": "high", "command_type": "install"}
                ],
                "hardware": [],
            }
        ),
        json.dumps(
            {
                "install_commands": [
                    {"cmd": "pip install x", "source_line": 1, "confidence": "certain", "command_type": "install"}
                ],
                "hardware": [],
            }
        ),
        json.dumps(
            {
                "install_commands": [
                    {"cmd": "pip install x", "source_line": 1, "confidence": "high", "command_type": "execute"}
                ],
                "hardware": [],
            }
        ),
        json.dumps({"install_commands": [], "hardware": [{"gpu": "yes", "source_line": 1, "confidence": "high"}]}),
        json.dumps({"install_commands": [], "hardware": [{"vram_gb": "16", "source_line": 1, "confidence": "high"}]}),
    ],
)
def test_parse_llm_payload_rejects_invalid_shapes(raw):
    with pytest.raises(ValueError):
        parse_llm_payload(raw)


def test_llm_extractor_clamps_out_of_range_source_lines():
    readme = "# A\n\n## Installation\n\n```bash\npip install x\n```\n"
    line_count = len(readme.splitlines())
    payload = {
        "install_commands": [
            {"cmd": "pip install y", "source_line": 999, "confidence": "high", "command_type": "install"}
        ],
        "hardware": [
            {"gpu": True, "vram_gb": 8, "source_line": 100, "confidence": "medium"}
        ],
    }
    extractor = LLMExtractor(lambda prompt: "```json\n" + json.dumps(payload) + "\n```")
    result = extractor.extract(readme)

    assert result.commands[0].source_line == line_count
    assert result.hardware[0].source_line == line_count
    assert result.readme_hash == readme_hash(readme)


def test_extract_for_repo_merges_llm_when_heuristic_finds_nothing(tmp_path):
    db = _new_db(tmp_path)
    readme = "# Sparse\n\nNothing the heuristics recognise here.\n"
    payload = {
        "install_commands": [
            {"cmd": "docker run acme/tool", "source_line": 3, "confidence": "medium", "command_type": "run"}
        ],
        "hardware": [
            {"gpu": True, "vram_gb": 24, "source_line": 3, "confidence": "medium"}
        ],
    }
    extractor = LLMExtractor(lambda prompt: json.dumps(payload))

    result = extract_for_repo(db, 1, readme, llm=extractor)

    assert result is not None
    assert [c.cmd for c in result.commands] == ["docker run acme/tool"]
    assert result.hardware[0].vram_gb == 24
    assert [row["cmd"] for row in db.get_install_commands(1)] == ["docker run acme/tool"]
    assert db.get_hw_requirements(1)[0]["vram_gb"] == 24


def test_extract_for_repo_merges_and_dedupes_llm_commands(tmp_path):
    db = _new_db(tmp_path)
    payload = {
        "install_commands": [
            {"cmd": "pip install demo-pkg", "source_line": 8, "confidence": "high", "command_type": "install"},
            {"cmd": "pip install extra", "source_line": 9, "confidence": "high", "command_type": "install"},
        ],
        "hardware": [],
    }
    extractor = LLMExtractor(lambda prompt: json.dumps(payload))

    result = extract_for_repo(db, 1, INSTALL_README, llm=extractor)

    assert result is not None
    # The duplicate heuristic/LLM pair is kept once; the new command is added.
    commands = [c.cmd for c in result.commands]
    assert commands.count("pip install demo-pkg") == 2  # lines 8 and 10 from heuristics
    assert "pip install extra" in commands


# --------------------------------------------------------------------------- #
# Manifest hints
# --------------------------------------------------------------------------- #


def test_manifest_hints_reads_requirements_pyproject_and_dockerfile():
    files = {
        "requirements.txt": """
# runtime
numpy>=1.0
-r other.txt
requests
""",
        "pyproject.toml": """
[project]
name = "demo"
dependencies = ["flask>=2", "httpx"]

[tool.poetry.dependencies]
python = "^3.11"
torch = "^2.0"
""",
        "Dockerfile": """
FROM --platform=linux/amd64 nvidia/cuda:12.1.0-runtime-ubuntu22.04
ENV CUDA_HOME=/usr/local/cuda
ENV MY_VAR=plain
ENV GPU_DRIVER=535
""",
    }

    hints = manifest_hints(files)

    assert "numpy>=1.0" in hints["python_dependencies"]
    assert "requests" in hints["python_dependencies"]
    assert "flask>=2" in hints["python_dependencies"]
    assert "httpx" in hints["python_dependencies"]
    assert "torch" in hints["python_dependencies"]
    assert "python" not in hints["python_dependencies"]
    assert "-r other.txt" not in hints["python_dependencies"]

    assert hints["docker_base_images"] == ["nvidia/cuda:12.1.0-runtime-ubuntu22.04"]
    assert hints["docker_env"]["CUDA_HOME"] == "/usr/local/cuda"
    assert hints["docker_env"]["GPU_DRIVER"] == "535"
    assert "MY_VAR" not in hints["docker_env"]
    assert any("cuda" in hint.lower() for hint in hints["gpu_hints"])
    assert any("gpu" in hint.lower() for hint in hints["gpu_hints"])


def test_manifest_hints_bounds_and_missing_files():
    files = {"requirements.txt": "\n".join(f"pkg{i}" for i in range(150))}
    hints = manifest_hints(files)
    assert len(hints["python_dependencies"]) == 100
    assert hints["docker_base_images"] == []
    assert hints["docker_env"] == {}
    assert hints["gpu_hints"] == []


def test_as_dict_round_trip():
    command = ExtractedCommand("pip install x", 1, "high", "install")
    assert command.as_dict() == {
        "cmd": "pip install x",
        "source_line": 1,
        "confidence": "high",
        "command_type": "install",
    }
    hardware = HardwareRequirement(True, 16, 32, 50, "Linux", 2, "medium")
    assert hardware.as_dict() == {
        "gpu": True,
        "vram_gb": 16,
        "ram_gb": 32,
        "disk_gb": 50,
        "os": "Linux",
        "source_line": 2,
        "confidence": "medium",
    }
