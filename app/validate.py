from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def validate(data: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if not data.get("generated_at"):
        errors.append("generated_at is required")
    if data.get("status") not in {"ready", "no_verified_fixtures", "source_unavailable"}:
        errors.append("status must be ready, no_verified_fixtures, or source_unavailable")

    matches = data.get("matches")
    if not isinstance(matches, list):
        errors.append("matches must be a list")
        return False, errors

    if data.get("status") == "ready" and not matches:
        errors.append("ready payloads must contain at least one verified fixture")

    seen_ids: set[str] = set()
    for index, match in enumerate(matches):
        prefix = f"matches[{index}]"
        match_id = str(match.get("id") or "")
        if not match_id:
            errors.append(f"{prefix}.id is required")
        elif match_id in seen_ids:
            errors.append(f"{prefix}.id duplicates {match_id}")
        seen_ids.add(match_id)

        if not match.get("kickoff_utc"):
            errors.append(f"{prefix}.kickoff_utc is required")
        if not (match.get("source") or {}).get("event_url"):
            errors.append(f"{prefix}.source.event_url is required")

        teams = match.get("teams") or {}
        team_a = (teams.get("team_a") or {}).get("name")
        team_b = (teams.get("team_b") or {}).get("name")
        if not team_a or not team_b:
            errors.append(f"{prefix} must include both team names")

        state = ((match.get("status") or {}).get("state") or "pre").lower()
        prediction = match.get("prediction")
        if state != "post":
            if not prediction:
                errors.append(f"{prefix}.prediction is required for non-completed matches")
                continue
            probabilities = prediction.get("probabilities") or {}
            keys = {"team_a_win", "draw", "team_b_win"}
            if set(probabilities) != keys:
                errors.append(f"{prefix}.prediction.probabilities must contain {sorted(keys)}")
                continue
            try:
                total = sum(float(probabilities[key]) for key in keys)
            except (TypeError, ValueError):
                errors.append(f"{prefix}.prediction probabilities must be numeric")
                continue
            if abs(total - 100.0) > 0.15:
                errors.append(f"{prefix}.prediction probabilities sum to {total:.2f}, not 100")

    if data.get("match_count") != len(matches):
        errors.append("match_count must equal len(matches)")

    return not errors, errors


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated World Cup prediction data.")
    parser.add_argument("path", nargs="?", type=Path, default=Path("data/latest.json"))
    args = parser.parse_args()

    ok, errors = validate(load(args.path))
    if ok:
        print(f"Validation passed: {args.path}")
        return 0
    for error in errors:
        print(f"ERROR: {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
