#!/usr/bin/env python3
"""
score_pr.py - Top-level dispatch for Commonweave PR scoring.

Reads a diff (from `gh pr diff`, a local diff file, or a list of changed files)
and classifies the contribution type, then routes to the matching rubric.

Score is informational only - it does NOT block merges.

Usage:
  python evals/score_pr.py --pr 42
  python evals/score_pr.py --diff /path/to/file.diff
  python evals/score_pr.py --files data/search/ZA.json README.md
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable

# Local rubric scorers (import lazily so the script still runs if one is missing).
ROOT = Path(__file__).resolve().parent


def classify(changed_files: list[str]) -> str:
    """Classify the contribution type from changed file paths.

    Returns one of: data, code, research, documentation, mixed.
    """
    has_data = any(
        f.startswith("data/search/")
        or f.startswith("data/ingest_")
        or f == "data/commonweave_directory.db"
        for f in changed_files
    )
    has_code = any(
        f.endswith(".py")
        and (f.startswith("data/") or f.startswith("evals/") or f.startswith("benchmarks/"))
        for f in changed_files
    )
    has_map = any(f in ("map.html", "directory.html") for f in changed_files) or any(
        f.startswith("data/build_map") for f in changed_files
    )
    has_research = any(
        f in (
            "CLAIMS.md",
            "FALSIFIERS.md",
            "ATTACK-VECTORS.md",
            "STEELMAN-ALTERNATIVES.md",
            "RESEARCH.md",
            "DEEP-DIVE.md",
            "CRITIQUE.md",
        )
        for f in changed_files
    )
    has_docs = any(
        f.endswith(".md") and not f.endswith(("/README.md", "/CRITIQUE.md")) for f in changed_files
    )

    types = []
    if has_data:
        types.append("data")
    if has_code or has_map:
        types.append("code")
    if has_research:
        types.append("research")
    if has_docs and not types:
        types.append("documentation")

    if len(types) == 0:
        return "documentation"
    if len(types) == 1:
        return types[0]
    return "mixed"


def get_changed_files_from_pr(pr: int) -> list[str]:
    out = subprocess.check_output(
        ["gh", "pr", "view", str(pr), "--json", "files", "--jq", ".files[].path"],
        text=True,
    )
    return [line.strip() for line in out.splitlines() if line.strip()]


def get_changed_files_from_diff(path: str) -> list[str]:
    files: set[str] = set()
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("+++ b/"):
                files.add(line[6:].strip())
            elif line.startswith("--- a/"):
                files.add(line[6:].strip())
    return sorted(f for f in files if f and f != "/dev/null")


def score_data(files: list[str]) -> dict:
    try:
        from score_data_quality import score as data_score  # type: ignore
    except ImportError:
        sys.path.insert(0, str(ROOT))
        from score_data_quality import score as data_score  # type: ignore
    return data_score(files)


def score_map(files: list[str]) -> dict:
    sys.path.insert(0, str(ROOT))
    from score_map_quality import score as map_score  # type: ignore
    return map_score(files)


def score_research(files: list[str]) -> dict:
    sys.path.insert(0, str(ROOT))
    from score_research_quality import score as research_score  # type: ignore
    return research_score(files)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--pr", type=int, help="PR number (uses gh CLI)")
    src.add_argument("--diff", type=str, help="Path to a local diff file")
    src.add_argument("--files", nargs="+", help="Explicit list of changed files")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args(argv)

    if args.pr is not None:
        files = get_changed_files_from_pr(args.pr)
    elif args.diff:
        files = get_changed_files_from_diff(args.diff)
    else:
        files = list(args.files or [])

    contribution_type = classify(files)

    result = {
        "contribution_type": contribution_type,
        "files_changed": files,
        "score": None,
        "notes": [],
    }

    if contribution_type == "data":
        result["score"] = score_data(files)
    elif contribution_type == "code":
        result["score"] = score_map(files)
    elif contribution_type == "research":
        result["score"] = score_research(files)
    elif contribution_type == "mixed":
        result["score"] = {
            "data": score_data(files),
            "code": score_map(files),
            "research": score_research(files),
        }
        result["notes"].append(
            "Mixed contribution; consider splitting into smaller PRs."
        )
    else:  # documentation
        result["notes"].append(
            "Documentation-only PR; no rubric applied. Manual review recommended."
        )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Contribution type: {contribution_type}")
        print(f"Files changed: {len(files)}")
        if result["score"] is not None:
            print(json.dumps(result["score"], indent=2))
        for note in result["notes"]:
            print(f"NOTE: {note}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
