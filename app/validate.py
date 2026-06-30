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
MATCHUP_NODE_KEYS = ("id", "label", "type", "side", "weight", "note")
MATCHUP_EDGE_KEYS = ("from", "to", "label", "impact", "direction", "note")
MATCHUP_IMPACTS = {"high", "medium", "low"}
MATCHUP_ADVANTAGES = {"home", "away", "balanced"}
STRUCTURE_STAGES = {"group", "knockout"}
BRACKET_KEYS = ("round_of_32", "round_of_16", "quarter_finals", "semi_finals", "final")
BRACKET_LABELS = ("32强", "16强", "8强", "4强", "决赛")
FORBIDDEN_PROBABILITY_TEXT = (
    "结构图概率",
    "对位概率",
    "比分概率",
    "matchup probability",
    "matchup probabilities",
    "score probability",
    "score probabilities",
    "score_probability",
    "structure graph probability",
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


def validate_matchup_graph(match: dict[str, Any], index: int, errors: list[str]) -> None:
    graph = match.get("matchup_graph")
    if not isinstance(graph, dict):
        errors.append(f"matches[{index}].matchup_graph must be an object")
        return
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or len(nodes) < 6:
        errors.append(f"matches[{index}].matchup_graph.nodes must contain at least 6 nodes")
    else:
        node_ids: set[str] = set()
        for node_index, node in enumerate(nodes):
            if not isinstance(node, dict):
                errors.append(f"matches[{index}].matchup_graph.nodes[{node_index}] must be an object")
                continue
            for key in MATCHUP_NODE_KEYS:
                if key not in node:
                    errors.append(f"matches[{index}].matchup_graph.nodes[{node_index}].{key} is required")
            node_id = node.get("id")
            if isinstance(node_id, str) and node_id.strip():
                node_ids.add(node_id)
            for key in ("id", "label", "type", "side", "note"):
                value = node.get(key)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"matches[{index}].matchup_graph.nodes[{node_index}].{key} must be a non-empty string")
            weight = node.get("weight")
            if not isinstance(weight, (int, float)) or weight < 0 or weight > 100:
                errors.append(f"matches[{index}].matchup_graph.nodes[{node_index}].weight must be 0-100")
            forbidden = [key for key in node if "prob" in str(key).lower() or "概率" in str(key)]
            if forbidden:
                errors.append(f"matches[{index}].matchup_graph.nodes[{node_index}] must not include probability fields")
    if not isinstance(edges, list) or len(edges) < 3:
        errors.append(f"matches[{index}].matchup_graph.edges must contain at least 3 edges")
    else:
        for edge_index, edge in enumerate(edges):
            if not isinstance(edge, dict):
                errors.append(f"matches[{index}].matchup_graph.edges[{edge_index}] must be an object")
                continue
            for key in MATCHUP_EDGE_KEYS:
                if key not in edge:
                    errors.append(f"matches[{index}].matchup_graph.edges[{edge_index}].{key} is required")
            for key in ("from", "to", "label", "direction", "note"):
                value = edge.get(key)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"matches[{index}].matchup_graph.edges[{edge_index}].{key} must be a non-empty string")
            if edge.get("impact") not in MATCHUP_IMPACTS:
                errors.append(f"matches[{index}].matchup_graph.edges[{edge_index}].impact must be high, medium, or low")
            forbidden = [key for key in edge if "prob" in str(key).lower() or "概率" in str(key)]
            if forbidden:
                errors.append(f"matches[{index}].matchup_graph.edges[{edge_index}] must not include probability fields")
    for key in ("summary", "key_battle", "risk_trigger"):
        value = graph.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"matches[{index}].matchup_graph.{key} is required")
    if graph.get("advantage_side") not in MATCHUP_ADVANTAGES:
        errors.append(f"matches[{index}].matchup_graph.advantage_side must be home, away, or balanced")


def match_identity(match: dict[str, Any]) -> str:
    return str(match.get("match_id") or match.get("id") or match.get("fifa_match_id") or "")


def validate_structure_score_options(options: Any, prefix: str, errors: list[str]) -> None:
    if not isinstance(options, list) or len(options) != 3:
        errors.append(f"{prefix} must contain exactly 3 score tab options")
        return
    ranks: set[int] = set()
    for option_index, option in enumerate(options):
        if not isinstance(option, dict):
            errors.append(f"{prefix}[{option_index}] must be an object")
            continue
        forbidden = [key for key in option if "prob" in str(key).lower() or "概率" in str(key)]
        if forbidden:
            errors.append(f"{prefix}[{option_index}] must not include score probability fields")
        score = option.get("score")
        rank = option.get("rank")
        if not isinstance(score, str) or not score.strip():
            errors.append(f"{prefix}[{option_index}].score is required")
        if not isinstance(rank, int):
            errors.append(f"{prefix}[{option_index}].rank must be an integer")
        else:
            ranks.add(rank)
    if ranks != {1, 2, 3}:
        errors.append(f"{prefix} ranks must be exactly 1, 2, and 3")


def validate_structure_node(
    node: Any,
    prefix: str,
    display_ids: set[str],
    errors: list[str],
) -> tuple[str, bool]:
    if not isinstance(node, dict):
        errors.append(f"{prefix} must be an object")
        return "", False
    match_id = str(node.get("match_id") or "")
    if not match_id:
        errors.append(f"{prefix}.match_id is required")
    if not isinstance(node.get("teams"), dict):
        errors.append(f"{prefix}.teams is required")
    if not isinstance(node.get("kickoff_display"), str) or "北京时间" not in node.get("kickoff_display", ""):
        errors.append(f"{prefix}.kickoff_display must use Beijing time")
    current = bool(node.get("current_window"))
    if match_id in display_ids:
        if not current:
            errors.append(f"{prefix}.current_window must be true for displayed match {match_id}")
        if not isinstance(node.get("win_draw_loss"), dict):
            errors.append(f"{prefix}.win_draw_loss is required for displayed match {match_id}")
        validate_structure_score_options(node.get("score_options"), f"{prefix}.score_options", errors)
    return match_id, current


def collect_structure_nodes(structure: dict[str, Any], errors: list[str]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    stage = structure.get("stage")
    if stage == "group":
        groups = structure.get("groups")
        if not isinstance(groups, list):
            errors.append("tournament_structure.groups must be a list for group stage")
            return nodes
        if structure.get("bracket") not in (None, {}):
            errors.append("tournament_structure.bracket must be null for group stage")
        for group_index, group in enumerate(groups):
            if not isinstance(group, dict):
                errors.append(f"tournament_structure.groups[{group_index}] must be an object")
                continue
            if not isinstance(group.get("name"), str) or not group.get("name"):
                errors.append(f"tournament_structure.groups[{group_index}].name is required")
            days = group.get("match_days")
            if not isinstance(days, list):
                errors.append(f"tournament_structure.groups[{group_index}].match_days must be a list")
                continue
            for day_index, day in enumerate(days):
                if not isinstance(day, dict):
                    errors.append(f"tournament_structure.groups[{group_index}].match_days[{day_index}] must be an object")
                    continue
                matches = day.get("matches")
                if not isinstance(matches, list):
                    errors.append(f"tournament_structure.groups[{group_index}].match_days[{day_index}].matches must be a list")
                    continue
                nodes.extend(match for match in matches if isinstance(match, dict))
    elif stage == "knockout":
        bracket = structure.get("bracket")
        if not isinstance(bracket, dict):
            errors.append("tournament_structure.bracket must be an object for knockout stage")
            return nodes
        if structure.get("groups") not in (None, []):
            errors.append("tournament_structure.groups must be null for knockout stage")
        for key in BRACKET_KEYS:
            round_nodes = bracket.get(key)
            if not isinstance(round_nodes, list):
                errors.append(f"tournament_structure.bracket.{key} must be a list")
                continue
            nodes.extend(node for node in round_nodes if isinstance(node, dict))
    return nodes


def validate_tournament_structure(data: dict[str, Any], matches: Any, render: Any, errors: list[str]) -> None:
    structure = data.get("tournament_structure")
    if not isinstance(structure, dict):
        errors.append("tournament_structure must be an object")
        return
    stage = structure.get("stage")
    if stage not in STRUCTURE_STAGES:
        errors.append("tournament_structure.stage must be group or knockout")
    focus = structure.get("focus_window")
    if not isinstance(focus, dict):
        errors.append("tournament_structure.focus_window must be an object")
    else:
        if focus.get("timezone") != "Asia/Shanghai":
            errors.append("tournament_structure.focus_window.timezone must be Asia/Shanghai")
        days = focus.get("china_match_days")
        if not isinstance(days, list) or len(days) < 2:
            errors.append("tournament_structure.focus_window.china_match_days must contain at least two days")
    highlight_ids = structure.get("highlight_match_ids")
    if not isinstance(highlight_ids, list):
        errors.append("tournament_structure.highlight_match_ids must be a list")
        highlight_set: set[str] = set()
    else:
        highlight_set = {str(item) for item in highlight_ids}
    display_ids = {match_identity(match) for match in matches if isinstance(match, dict) and match_identity(match)} if isinstance(matches, list) else set()
    missing = display_ids - highlight_set
    if missing:
        errors.append(f"tournament_structure.highlight_match_ids missing displayed matches: {sorted(missing)}")
    nodes = collect_structure_nodes(structure, errors)
    node_ids: set[str] = set()
    current_node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        match_id, current = validate_structure_node(node, f"tournament_structure.node[{index}]", display_ids, errors)
        if match_id:
            node_ids.add(match_id)
        if current and match_id:
            current_node_ids.add(match_id)
    missing_nodes = display_ids - node_ids
    if missing_nodes:
        errors.append(f"tournament_structure nodes missing displayed matches: {sorted(missing_nodes)}")
    missing_current = display_ids - current_node_ids
    if missing_current:
        errors.append(f"tournament_structure current-window highlight missing for displayed matches: {sorted(missing_current)}")
    if isinstance(render, str):
        if stage == "group" and "小组对战结构图" not in render:
            errors.append("render must include 小组对战结构图 for group stage")
        if stage == "knockout":
            if "淘汰赛对阵树" not in render:
                errors.append("render must include 淘汰赛对阵树 for knockout stage")
            for label in BRACKET_LABELS:
                if label not in render:
                    errors.append(f"render must include knockout round label {label}")
            for fragment in ("bracket-board", "bracket-node-card", "bracket-match-number", "current-window-key"):
                if fragment not in render:
                    errors.append(f"render must include knockout bracket UI fragment {fragment}")
        for fragment in ("当前窗口", "前3预测比分", "主推荐", "Top 2", "Top 3"):
            if fragment not in render:
                errors.append(f"render must include tournament structure score tab fragment {fragment}")

def validate_match(match: dict[str, Any], index: int, errors: list[str]) -> None:
    validate_probabilities(match, index, errors)
    validate_score_options(match, index, errors)
    validate_method_factors(match, index, errors)
    validate_matchup_graph(match, index, errors)
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
    tournament_structure = data.get("tournament_structure")

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

    validate_tournament_structure(data, matches, render, errors)

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
            "前3预测比分",
            "分析因子",
            "市场信号",
            "天气/场地",
            "对战结构图",
            "关键对位",
            "风险触发点",
            "主推荐",
            "Top 2",
            "Top 3",
        ):
            if fragment not in render:
                errors.append(f"render must visibly include {fragment}")
        for fragment in ("北京时间", "比赛日", "18:00"):
            if fragment not in render:
                errors.append(f"render must visibly include China match-day fragment {fragment}")
        for fragment in ("2026 世界杯 · 预测分析", "night-shell", "night-card", "match-card", ":hover"):
            if fragment not in render:
                errors.append(f"render must include dark UI fragment {fragment}")
        lower_render = render.lower()
        for fragment in FORBIDDEN_PROBABILITY_TEXT:
            if fragment in lower_render:
                errors.append("render must not display forbidden probability text")
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