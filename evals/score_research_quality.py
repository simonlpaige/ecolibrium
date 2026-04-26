#!/usr/bin/env python3
"""
score_research_quality.py - Heuristic scorer for research / framework contributions.

Score is informational only.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


URL_PATTERN = re.compile(r"https?://[^\s\")>]+")
RESEARCH_FILES = {
    "CLAIMS.md",
    "FALSIFIERS.md",
    "ATTACK-VECTORS.md",
    "STEELMAN-ALTERNATIVES.md",
    "RESEARCH.md",
    "DEEP-DIVE.md",
    "CRITIQUE.md",
}


def score(files: Iterable[str]) -> dict:
    files = list(files)
    research = [f for f in files if f in RESEARCH_FILES]

    breakdown = {
        "claim_specificity": 0,
        "source_quality": 0,
        "falsifiability": 0,
        "counterargument_strength": 0,
        "framework_integration": 0,
        "next_task": 0,
    }
    notes: list[str] = []

    if not research:
        notes.append("No research-track files touched.")
        return {
            "type": "research",
            "total": 0,
            "breakdown": breakdown,
            "notes": notes,
        }

    # Claim specificity: heuristic - did the PR add a numbered claim/falsifier/vector?
    # Match e.g. "C1.", "### C1.", "F-PROJ-1.", "### AV-EXT-2.", "## A1." at line start.
    specificity_pattern = re.compile(
        r"^(?:#+\s+)?(?:C|F-PROJ-|F-FW-|F-DATA-|AV-EXT-|AV-INT-|A)\d+\.",
        re.MULTILINE,
    )
    for path in research:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        if specificity_pattern.search(text):
            breakdown["claim_specificity"] = 20
            break

    # Source quality: count URLs in research files.
    total_urls = 0
    for path in research:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        urls = URL_PATTERN.findall(text)
        urls = [u for u in urls if "github.com/simonlpaige/commonweave" not in u]
        total_urls += len(urls)
    if total_urls >= 5:
        breakdown["source_quality"] = 20
    elif total_urls >= 2:
        breakdown["source_quality"] = 12
    elif total_urls >= 1:
        breakdown["source_quality"] = 6
    else:
        notes.append("No external sources cited in research-track files.")

    # Falsifiability: did the PR add or reference a Falsifier?
    for path in research:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        if "Falsifiers:" in text or "Falsifier:" in text or "F-PROJ-" in text or "F-FW-" in text or "F-DATA-" in text:
            breakdown["falsifiability"] = 20
            break

    # Counterargument strength: did the PR touch STEELMAN-ALTERNATIVES.md or include a counterargument section?
    counter_signals_seen = False
    for path in research:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        if path.endswith("STEELMAN-ALTERNATIVES.md"):
            counter_signals_seen = True
            break
        if any(s in text.lower() for s in ("counterargument", "counterexample", "what it gets right")):
            counter_signals_seen = True
            break
    if counter_signals_seen:
        breakdown["counterargument_strength"] = 15

    # Framework integration: did the PR cross-reference README / CLAIMS / FALSIFIERS / ATTACK-VECTORS?
    cross_refs = 0
    for path in research:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        for ref in ("README.md", "CLAIMS.md", "FALSIFIERS.md", "ATTACK-VECTORS.md", "CRITIQUE.md", "GOVERNANCE.md"):
            if ref in text and Path(path).name != ref:
                cross_refs += 1
    if cross_refs >= 3:
        breakdown["framework_integration"] = 15
    elif cross_refs >= 1:
        breakdown["framework_integration"] = 8

    # Next task
    for path in research:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        if "Needed work:" in text or "next task" in text.lower() or "follow-up" in text.lower():
            breakdown["next_task"] = 10
            break

    total = sum(breakdown.values())
    return {
        "type": "research",
        "total": total,
        "breakdown": breakdown,
        "notes": notes,
    }


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(score(sys.argv[1:]), indent=2))
