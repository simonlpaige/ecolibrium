#!/usr/bin/env python3
"""
score_data_quality.py - Heuristic scorer for directory contributions.

Score is informational only. It does NOT block merges.

Heuristics are deliberately simple:
- Did the PR touch data/search/<country>.json or an ingest script?
- Are there source URLs in the diff?
- Did it preserve the legibility column safely?
- Did it leave a next task?

Real review still happens by humans.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


SOURCE_URL_PATTERN = re.compile(r"https?://[^\s\")>]+")
LEGIBILITY_VALUES = {"formal", "hybrid", "informal", "unknown"}


def score(files: Iterable[str]) -> dict:
    files = list(files)

    touched_search = [f for f in files if f.startswith("data/search/") and f.endswith(".json")]
    touched_ingest = [f for f in files if f.startswith("data/ingest_") and f.endswith(".py")]
    touched_db_directly = "data/commonweave_directory.db" in files

    breakdown = {
        "source_quality": 0,
        "geography_correctness": 0,
        "framework_relevance": 0,
        "false_positive_reduction": 0,
        "vulnerable_group_safety": 0,
        "reproducibility": 0,
        "next_task": 0,
    }
    notes: list[str] = []

    if touched_db_directly:
        notes.append(
            "PR modifies data/commonweave_directory.db directly. Prefer an ingest script "
            "(see data/CONTRIBUTING-DATA.md). Reduces reproducibility score."
        )

    # Source quality: look for URLs in any changed search/ingest file.
    found_sources = 0
    for path in touched_search + touched_ingest:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        urls = SOURCE_URL_PATTERN.findall(text)
        # Filter out internal anchors and common non-source domains.
        urls = [u for u in urls if "github.com/simonlpaige/commonweave" not in u]
        found_sources += len(urls)

    if touched_search or touched_ingest:
        if found_sources >= 5:
            breakdown["source_quality"] = 25
        elif found_sources >= 2:
            breakdown["source_quality"] = 15
        elif found_sources >= 1:
            breakdown["source_quality"] = 8
        else:
            breakdown["source_quality"] = 0
            notes.append("No source URLs detected in changed files.")

    # Geography correctness: surface flag only; full check needs the DB.
    if touched_search:
        # Filename encodes the country code; trust the contributor for now.
        breakdown["geography_correctness"] = 15

    # Framework relevance: heuristic - did the PR touch framework_areas or alignment_score logic?
    framework_signal = False
    for path in touched_search + touched_ingest:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        if "framework_area" in text or "alignment_score" in text:
            framework_signal = True
            break
    if framework_signal:
        breakdown["framework_relevance"] = 15

    # False-positive reduction: heuristic - are there "broken", "fix", "correct", "remove" mentions in PR-touched JSON _notes?
    for path in touched_search:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        if any(k in text.lower() for k in ("broken", "fix", "correct", "remove", "deprecat")):
            breakdown["false_positive_reduction"] = 15
            break

    # Vulnerable-group safety: is legibility used and does it default conservatively?
    legibility_use = 0
    for path in touched_search + touched_ingest:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        for value in LEGIBILITY_VALUES:
            if f'"{value}"' in text or f"'{value}'" in text:
                legibility_use += 1
    if legibility_use >= 1:
        breakdown["vulnerable_group_safety"] = 15
    else:
        notes.append(
            "No legibility classification detected. If the PR adds orgs, classify "
            "legibility (formal/hybrid/informal/unknown). Default to 'unknown' if uncertain."
        )

    # Reproducibility: ingest scripts are inherently reproducible; raw DB edits are not.
    if touched_ingest and not touched_db_directly:
        breakdown["reproducibility"] = 10
    elif touched_search and not touched_db_directly:
        breakdown["reproducibility"] = 7
    else:
        breakdown["reproducibility"] = 0

    # Next task: heuristic - look for "TODO", "next", "follow-up" in the PR's notes block of any changed JSON.
    for path in touched_search:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        if any(k in text.lower() for k in ("todo", "next", "follow-up", "followup")):
            breakdown["next_task"] = 5
            break

    total = sum(breakdown.values())
    return {
        "type": "data",
        "total": total,
        "breakdown": breakdown,
        "notes": notes,
    }


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(score(sys.argv[1:]), indent=2))
