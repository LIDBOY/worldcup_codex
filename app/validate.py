from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_ANALYSIS_MODEL = "deepseek-v4-pro"
REQUIRED_RENDER_MODEL = "deepseek-v4-flash"
METHOD_FACTOR_KEYS = (
    "market_signal",
    "fifa_rank_prior",
    "recent_form",
    "group_context",
    "injury_rotation",
    "weather_venue",
    "tactical_key",
    "uncertainty",
)


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


def validate_probabilities(match: dict[str, Any], index: int, errors: list[str]) -> None:
    probs = match.get("win_draw_loss") or {}
    keys = ("home_win", "draw", "away_win")
    if any(key not in probs for key in keys):
        errors.append(f"matches[{index}].win_draw_loss missing required keys")
        return
    try:
        values = [float(probs[key]) for key in keys]
    except (TypeError, ValueError):
        errors.append(f"matches[{index}].win_draw_loss values must be numeric")
        return
    if any(value < 0 or value > 100 for value in values):
        errors.append(f"matches[{index}].win_draw_loss values must be between 0 and 100")
    if abs(sum(values) - 100.0) > 0.25:
        errors.append(f"matches[{index}].win_draw_loss must sum to 100")


def validate_score_options(match: dict[str, Any], index: int, errors: list[str]) -> None:
    options = match.get("score_options")
    if not isinstance(options, list) or len(options) != 3:
        errors.append(f"matches[{index}].score_options must contain exactly 3 score results")
        return
    ranks: set[int] = set()
    for option_index, option in enumerate(options):
        if not isinstance(option, dict):
            errors.append(f"matches[{index}].score_options[{option_index}] must be an object")
            continue
        forbidden = [key for key in option if "prob" in str(key).lower() or "概率" in str(key)]
        if forbidden:
            errors.append(f"matches[{index}].score_options[{option_index}] must not include score probability fields")
        score = option.get("score")
        reason = option.get("reason")
        rank = option.get("rank")
        if not isinstance(score, str) or not score.strip():
            errors.append(f"matches[{index}].score_options[{option_index}].score is required")
        if not isinstance(reason, str) or not reason.strip():
            errors.append(f"matches[{index}].score_options[{option_index}].reason is required")
        if not isinstance(rank, int):
            errors.append(f"matches[{index}].score_options[{option_index}].rank must be an integer")
        else:
            ranks.add(rank)
    if ranks != {1, 2, 3}:
        errors.append(f"matches[{index}].score_options ranks must be exactly 1, 2, and 3")


def validate_method_factors(match: dict[str, Any], index: int, errors: list[str]) -> None:
    factors = match.get("method_factors")
    if not isinstance(factors, dict):
        errors.append(f"matches[{index}].method_factors must be an object")
        return
    for key in METHOD_FACTOR_KEYS:
        value = factors.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"matches[{index}].method_factors.{key} is required")


def validate_match(match: dict[str, Any], index: int, errors: list[str]) -> None:
    validate_probabilities(match, index, errors)
    validate_score_options(match, index, errors)
    validate_method_factors(match, index, errors)
    score = match.get("predicted_score") or {}
    if not isinstance(score.get("home"), int) or not isinstance(score.get("away"), int):
        errors.append(f"matches[{index}].predicted_score must include integer home/away")
    xg = match.get("xg_prediction") or {}
    if not isinstance(xg.get("home"), (int, float)) or not isinstance(xg.get("away"), (int, float)):
        errors.append(f"matches[{index}].xg_prediction must include numeric home/away")
    if "tactical_matchup" not in match:
        errors.append(f"matches[{index}].tactical_matchup is required")
    if "injury_adjustment" not in match:
        errors.append(f"matches[{index}].injury_adjustment is required")
    if "risk_analysis" not in match:
        errors.append(f"matches[{index}].risk_analysis is required")
    if "odds_comparison" not in match:
        errors.append(f"matches[{index}].odds_comparison is required")
    upset = match.get("upset_probability")
    if not isinstance(upset, (int, float)) or upset < 0 or upset > 100:
        errors.append(f"matches[{index}].upset_probability must be 0-100")
    if match.get("confidence") not in {"low", "medium", "high"}:
        errors.append(f"matches[{index}].confidence must be low, medium, or high")
    if not isinstance(match.get("injuries"), dict):
        errors.append(f"matches[{index}].injuries must carry research injury data")
    if not isinstance(match.get("odds"), dict):
        errors.append(f"matches[{index}].odds must carry research odds data")


def validate(data: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []

    matches = data.get("matches")
    usage = data.get("usage")
    sources = data.get("data_sources")
    render = data.get("render")
    china_match_days = data.get("china_match_days")

    if not isinstance(matches, list):
        errors.append("matches must be a list")
    if data.get("analysis_model") != REQUIRED_ANALYSIS_MODEL:
        errors.append("analysis_model must be deepseek-v4-pro")
    if data.get("render_model") != REQUIRED_RENDER_MODEL:
        errors.append("render_model must be deepseek-v4-flash")
    if not isinstance(usage, dict):
        errors.append("usage must be an object")
    else:
        validate_usage(usage, "usage", errors)
    if not isinstance(sources, dict):
        errors.append("data_sources must be an object")
    else:
        for key in ("fifa", "injury", "odds"):
            if sources.get(key) is not True:
                errors.append(f"data_sources.{key} must be true")
    if not isinstance(render, str) or "<html" not in render.lower():
        errors.append("render must be a complete HTML string")
    if not isinstance(china_match_days, list) or len(china_match_days) < 2:
        errors.append("china_match_days must describe at least two China match days")

    if isinstance(matches, list):
        for index, match in enumerate(matches):
            if isinstance(match, dict):
                validate_match(match, index, errors)
            else:
                errors.append(f"matches[{index}] must be an object")

    if isinstance(render, str):
        for fragment in (
            "Token",
            "Cost",
            "风险",
            "伤停",
            "赔率",
            "xG",
            "爆冷概率",
            "比分结果 Top 3",
            "分析因子",
            "市场信号",
            "天气/场地",
        ):
            if fragment not in render:
                errors.append(f"render must visibly include {fragment}")
        for fragment in ("北京时间", "比赛日", "18:00"):
            if fragment not in render:
                errors.append(f"render must visibly include China match-day fragment {fragment}")
        for fragment in ("2026 世界杯 · 预测分析", "night-shell", "night-card", "match-card", ":hover"):
            if fragment not in render:
                errors.append(f"render must include dark UI fragment {fragment}")
        forbidden_score_probability = ("比分概率", "score probability", "score probabilities", "score_probability")
        lower_render = render.lower()
        for fragment in forbidden_score_probability:
            if fragment in lower_render:
                errors.append("render must not display score probability text")
        if "UTC" in render or "Z</time>" in render:
            errors.append("render must not visibly display UTC time")

    return not errors, errors


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DeepSeek V4 Agent World Cup prediction data.")
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
