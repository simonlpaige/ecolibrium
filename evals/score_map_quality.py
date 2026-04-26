#!/usr/bin/env python3
"""
score_map_quality.py - Heuristic scorer for map / code contributions.

Score is informational only.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


def score(files: Iterable[str]) -> dict:
    files = list(files)

    touched_map = [f for f in files if f in ("map.html", "directory.html") or f.startswith("data/build_map")]
    touched_code = [f for f in files if f.endswith(".py") and f.startswith("data/")]

    breakdown = {
        "feature_works": 0,
        "no_regression": 0,
        "user_comprehension": 0,
        "preserves_provenance": 0,
        "mobile_accessibility": 0,
        "next_task": 0,
    }
    notes: list[str] = []

    # Feature works: heuristic - did the PR add or modify a non-trivial chunk?
    total_added_lines = 0
    for path in touched_map + touched_code:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        total_added_lines += text.count("\n")
    if total_added_lines > 0:
        breakdown["feature_works"] = 25  # human review needed for real verdict
        notes.append(
            "feature_works is awarded by default on any code change; human review confirms."
        )

    # No regression: heuristic - did the PR remove existing event handlers or large chunks?
    # (Without the prior version we can't tell; default to 20 unless the PR description flags otherwise.)
    if touched_map or touched_code:
        breakdown["no_regression"] = 20
        notes.append("no_regression is heuristic; CI/visual review confirms.")

    # User comprehension: did the PR add help text, tooltips, or filter explanations?
    comprehension_signals = ("aria-label", "title=", "tooltip", "explain", "help-text", "<label")
    for path in touched_map:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        if any(sig in text for sig in comprehension_signals):
            breakdown["user_comprehension"] = 20
            break

    # Provenance preservation: did the PR mention edge_type, confidence, source_script?
    provenance_signals = ("edge_type", "confidence", "source_script", "explanation", "created_at")
    for path in touched_map + touched_code:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        if sum(1 for sig in provenance_signals if sig in text) >= 2:
            breakdown["preserves_provenance"] = 15
            break

    # Mobile / accessibility: did the PR mention viewport, mobile, touch, aria, or media queries?
    mobile_signals = ("@media", "viewport", "mobile", "touch", "aria-", "tabindex")
    for path in touched_map:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        if any(sig in text for sig in mobile_signals):
            breakdown["mobile_accessibility"] = 10
            break

    # Next task: did the PR leave a TODO comment or extend AGENT-TASKS.json?
    for path in touched_map + touched_code:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        if "TODO" in text or "FIXME" in text or "next:" in text.lower():
            breakdown["next_task"] = 10
            break

    total = sum(breakdown.values())
    return {
        "type": "code",
        "total": total,
        "breakdown": breakdown,
        "notes": notes,
    }


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(score(sys.argv[1:]), indent=2))
