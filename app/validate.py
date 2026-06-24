from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_ANALYSIS_MODEL = "deepseek-v4-pro"
REQUIRED_RENDER_MODEL = "deepseek-v4-flash"


def validate_usage(usage: dict[str, Any], prefix: str, errors: list[str]) -> None:
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        if not isinstance(usage.get(key), int) or usage[key] < 0:
            errors.append(f"{prefix}.{key} must be a non-negative integer")
    if usage.get("total_tokens") != usage.get("input_tokens", 0) + usage.get("output_tokens", 0):
        errors.append(f"{prefix}.total_tokens must equal input_tokens + output_tokens")
    cost = usage.get("cost_estimate")
    if not isinstance(cost, (int, float)) or cost < 0:
        errors.append(f"{prefix}.cost_estimate must be a non-negative number")
    expected = round(int(usage.get("total_tokens", 0)) * 0.00001, 6)
    if isinstance(cost, (int, float)) and abs(float(cost) - expected) > 0.000001:
        errors.append(f"{prefix}.cost_estimate must equal total_tokens * 0.00001")


def prediction_list(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    predictions = analysis.get("predictions")
    return predictions if isinstance(predictions, list) else []


def validate_probabilities(analysis: dict[str, Any], errors: list[str]) -> None:
    for index, prediction in enumerate(prediction_list(analysis)):
        probs = prediction.get("win_draw_loss") or {}
        keys = ("home_win", "draw", "away_win")
        if any(key not in probs for key in keys):
            errors.append(f"analysis.predictions[{index}].win_draw_loss missing required keys")
            continue
        try:
            values = [float(probs[key]) for key in keys]
        except (TypeError, ValueError):
            errors.append(f"analysis.predictions[{index}].win_draw_loss values must be numeric")
            continue
        if any(value < 0 or value > 100 for value in values):
            errors.append(f"analysis.predictions[{index}].win_draw_loss values must be between 0 and 100")
        if abs(sum(values) - 100.0) > 0.25:
            errors.append(f"analysis.predictions[{index}].win_draw_loss must sum to 100")
        score = prediction.get("predicted_score") or {}
        if not isinstance(score.get("home"), int) or not isinstance(score.get("away"), int):
            errors.append(f"analysis.predictions[{index}].predicted_score must include integer home/away")


def validate(data: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []

    analysis = data.get("analysis")
    render = data.get("render")
    usage = data.get("usage")
    model = data.get("model") or {}

    if not isinstance(analysis, dict):
        errors.append("analysis must be an object")
    if not isinstance(render, str) or "<html" not in render.lower():
        errors.append("render must be a complete HTML string")
    if not isinstance(usage, dict):
        errors.append("usage must be an object")
    else:
        validate_usage(usage, "usage", errors)

    if model.get("analysis_model") != REQUIRED_ANALYSIS_MODEL:
        errors.append("model.analysis_model must be deepseek-v4-pro")
    if model.get("render_model") != REQUIRED_RENDER_MODEL:
        errors.append("model.render_model must be deepseek-v4-flash")

    if isinstance(analysis, dict):
        validate_probabilities(analysis, errors)

    if isinstance(render, str):
        if not any(fragment in render for fragment in ("Token", "token", "令牌")):
            errors.append("render must visibly include token usage")
        if not any(fragment in render for fragment in ("Cost", "cost", "成本", "费用")):
            errors.append("render must visibly include cost estimate")
        for fragment in ("胜", "平", "负"):
            if fragment not in render:
                errors.append(f"render must visibly include {fragment}")

    return not errors, errors


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DeepSeek V4 World Cup prediction data.")
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
