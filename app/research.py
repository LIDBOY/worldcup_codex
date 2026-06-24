from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_LEAGUE = os.getenv("WORLDCUP_ESPN_LEAGUE", "fifa.world")
DEFAULT_DAYS = int(os.getenv("WORLDCUP_WINDOW_DAYS", "5"))
DEFAULT_OUTPUT = Path(os.getenv("WORLDCUP_OUTPUT", "data/latest.json"))
REQUEST_TIMEOUT = int(os.getenv("WORLDCUP_REQUEST_TIMEOUT", "12"))

ESPN_SCOREBOARD = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/"
    f"{DEFAULT_LEAGUE}/scoreboard"
)

# Static team-strength priors. They only shape probabilities for verified
# fixtures; they are not treated as a fixture source.
TEAM_RATINGS = {
    "argentina": 1895,
    "france": 1885,
    "spain": 1855,
    "england": 1845,
    "brazil": 1835,
    "portugal": 1815,
    "netherlands": 1805,
    "germany": 1795,
    "belgium": 1780,
    "uruguay": 1770,
    "colombia": 1760,
    "croatia": 1750,
    "italy": 1735,
    "morocco": 1715,
    "switzerland": 1705,
    "denmark": 1700,
    "japan": 1690,
    "united states": 1685,
    "usa": 1685,
    "mexico": 1670,
    "senegal": 1665,
    "austria": 1660,
    "ecuador": 1655,
    "iran": 1645,
    "korea republic": 1640,
    "south korea": 1640,
    "australia": 1625,
    "canada": 1620,
    "norway": 1615,
    "turkiye": 1610,
    "turkey": 1610,
    "egypt": 1605,
    "tunisia": 1590,
    "algeria": 1585,
    "paraguay": 1580,
    "saudi arabia": 1575,
    "scotland": 1570,
    "sweden": 1565,
    "czechia": 1560,
    "czech republic": 1560,
    "ivory coast": 1555,
    "cote d ivoire": 1555,
    "ghana": 1550,
    "south africa": 1535,
    "qatar": 1525,
    "uzbekistan": 1515,
    "iraq": 1505,
    "jordan": 1495,
    "panama": 1490,
    "new zealand": 1485,
    "cape verde": 1480,
    "haiti": 1465,
    "curacao": 1460,
}

HOST_TEAMS = {"canada", "mexico", "united states", "usa"}

TEAM_NAME_ZH = {
    "algeria": "阿尔及利亚",
    "argentina": "阿根廷",
    "australia": "澳大利亚",
    "austria": "奥地利",
    "belgium": "比利时",
    "bosnia herzegovina": "波黑",
    "brazil": "巴西",
    "canada": "加拿大",
    "cape verde": "佛得角",
    "colombia": "哥伦比亚",
    "congo dr": "刚果民主共和国",
    "croatia": "克罗地亚",
    "curacao": "库拉索",
    "czechia": "捷克",
    "czech republic": "捷克",
    "denmark": "丹麦",
    "ecuador": "厄瓜多尔",
    "egypt": "埃及",
    "england": "英格兰",
    "france": "法国",
    "germany": "德国",
    "ghana": "加纳",
    "haiti": "海地",
    "iran": "伊朗",
    "iraq": "伊拉克",
    "italy": "意大利",
    "ivory coast": "科特迪瓦",
    "cote d ivoire": "科特迪瓦",
    "japan": "日本",
    "jordan": "约旦",
    "korea republic": "韩国",
    "south korea": "韩国",
    "mexico": "墨西哥",
    "morocco": "摩洛哥",
    "netherlands": "荷兰",
    "new zealand": "新西兰",
    "norway": "挪威",
    "panama": "巴拿马",
    "paraguay": "巴拉圭",
    "portugal": "葡萄牙",
    "qatar": "卡塔尔",
    "saudi arabia": "沙特阿拉伯",
    "scotland": "苏格兰",
    "senegal": "塞内加尔",
    "south africa": "南非",
    "spain": "西班牙",
    "sweden": "瑞典",
    "switzerland": "瑞士",
    "tunisia": "突尼斯",
    "turkiye": "土耳其",
    "turkey": "土耳其",
    "united states": "美国",
    "usa": "美国",
    "uruguay": "乌拉圭",
    "uzbekistan": "乌兹别克斯坦",
}


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso_utc(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def parse_date(value: str) -> dt.datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return dt.datetime.fromisoformat(value).astimezone(dt.timezone.utc)


def normalize_team(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-z0-9]+", " ", ascii_name.lower()).strip()
    aliases = {
        "us": "usa",
        "u s": "usa",
        "united states of america": "united states",
        "korea": "south korea",
        "republic of korea": "south korea",
        "cote divoire": "cote d ivoire",
        "cabo verde": "cape verde",
        "bosnia and herzegovina": "bosnia herzegovina",
        "bosnia herz": "bosnia herzegovina",
        "dr congo": "congo dr",
        "democratic republic of congo": "congo dr",
        "democratic republic of the congo": "congo dr",
    }
    return aliases.get(cleaned, cleaned)


def team_name_zh(name: str) -> str:
    normalized = normalize_team(name)
    group_match = re.fullmatch(r"group ([a-z]) (1st|2nd|3rd|4th|first|second|third|fourth) place", normalized)
    if group_match:
        place = {
            "1st": "第一名",
            "first": "第一名",
            "2nd": "第二名",
            "second": "第二名",
            "3rd": "第三名",
            "third": "第三名",
            "4th": "第四名",
            "fourth": "第四名",
        }[group_match.group(2)]
        return f"{group_match.group(1).upper()}组{place}"
    return TEAM_NAME_ZH.get(normalized, name)


def team_rating(name: str) -> int:
    return TEAM_RATINGS.get(normalize_team(name), 1540)


def fetch_json(url: str, params: dict[str, str], retries: int = 3) -> dict[str, Any]:
    last_error: Exception | None = None
    full_url = f"{url}?{urlencode(params)}"
    for attempt in range(1, retries + 1):
        try:
            request = Request(full_url, headers={"User-Agent": "worldcup-pages-predictor/1.0"})
            with urlopen(request, timeout=REQUEST_TIMEOUT) as response:  # noqa: S310 - configured public source
                raw = response.read().decode("utf-8")
            return json.loads(raw)
        except Exception as exc:  # noqa: BLE001 - preserve source failure detail
            last_error = exc
            if attempt < retries:
                time.sleep(2 ** (attempt - 1))
    raise RuntimeError(f"failed to fetch {full_url}: {last_error}")


def ESPN_date_url(day: dt.date) -> str:
    return f"{ESPN_SCOREBOARD}?dates={day:%Y%m%d}"


def fetch_espn_events(start: dt.date, days: int) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    if os.getenv("WORLDCUP_OFFLINE") == "1":
        return [], [], ["Offline mode enabled; external fixture lookup skipped."]

    events: dict[str, dict[str, Any]] = {}
    urls: list[str] = []
    warnings: list[str] = []

    for offset in range(days):
        day = start + dt.timedelta(days=offset)
        params = {"dates": f"{day:%Y%m%d}", "limit": "100"}
        urls.append(ESPN_date_url(day))
        try:
            payload = fetch_json(ESPN_SCOREBOARD, params=params)
        except RuntimeError as exc:
            warnings.append(str(exc))
            continue

        for event in payload.get("events", []) or []:
            event_id = str(event.get("id") or stable_id(event))
            events[event_id] = event

    return list(events.values()), urls, warnings


def stable_id(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def competitor_name(competitor: dict[str, Any]) -> str:
    team = competitor.get("team") or {}
    return (
        team.get("displayName")
        or team.get("shortDisplayName")
        or team.get("name")
        or competitor.get("displayName")
        or "Unknown team"
    )


def competitor_logo(competitor: dict[str, Any]) -> str | None:
    team = competitor.get("team") or {}
    logo = team.get("logo")
    if logo:
        return str(logo)
    logos = team.get("logos") or []
    if logos:
        href = logos[0].get("href")
        return str(href) if href else None
    return None


def pick_competitors(event: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    competitions = event.get("competitions") or []
    if not competitions:
        return None
    competitors = competitions[0].get("competitors") or []
    if len(competitors) < 2:
        return None

    home = next((item for item in competitors if item.get("homeAway") == "home"), None)
    away = next((item for item in competitors if item.get("homeAway") == "away"), None)
    if home and away:
        return home, away
    return competitors[0], competitors[1]


def prediction_for(team_a: str, team_b: str, status_state: str) -> dict[str, Any] | None:
    if status_state == "post":
        return None

    rating_a = team_rating(team_a)
    rating_b = team_rating(team_b)
    if normalize_team(team_a) in HOST_TEAMS:
        rating_a += 35
    if normalize_team(team_b) in HOST_TEAMS:
        rating_b += 35

    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 600))
    rating_gap = abs(rating_a - rating_b)
    draw_probability = 0.17 + 0.12 * math.exp(-rating_gap / 260)
    draw_probability = min(0.31, max(0.17, draw_probability))
    remaining = 1 - draw_probability

    a_win = remaining * expected_a
    b_win = remaining * (1 - expected_a)
    values = [round(a_win * 100, 1), round(draw_probability * 100, 1), round(b_win * 100, 1)]
    delta = round(100.0 - sum(values), 1)
    values[values.index(max(values))] = round(values[values.index(max(values))] + delta, 1)

    return {
        "model": "deterministic-strength-prior-v1",
        "probabilities": {
            "team_a_win": values[0],
            "draw": values[1],
            "team_b_win": values[2],
        },
        "inputs": {
            "team_a_rating": rating_a,
            "team_b_rating": rating_b,
            "host_adjustment_points": 35,
        },
        "note": "基于球队强度先验生成的编辑模型估计，不构成投注建议。",
    }


def transform_event(event: dict[str, Any]) -> dict[str, Any] | None:
    pair = pick_competitors(event)
    if not pair:
        return None

    team_a_raw, team_b_raw = pair
    team_a = competitor_name(team_a_raw)
    team_b = competitor_name(team_b_raw)
    team_a_zh = team_name_zh(team_a)
    team_b_zh = team_name_zh(team_b)
    event_id = str(event.get("id") or stable_id(event))
    competition = (event.get("competitions") or [{}])[0]
    status_type = (event.get("status") or {}).get("type") or {}
    state = status_type.get("state") or "pre"
    kickoff = parse_date(event["date"]) if event.get("date") else utc_now()
    venue = competition.get("venue") or {}
    address = venue.get("address") or {}

    return {
        "id": event_id,
        "name": f"{team_a_zh} 对阵 {team_b_zh}",
        "name_en": event.get("name") or f"{team_a} vs {team_b}",
        "short_name": f"{team_a_zh} vs {team_b_zh}",
        "short_name_en": event.get("shortName") or f"{team_a} vs {team_b}",
        "competition": (event.get("league") or {}).get("name") or "FIFA World Cup",
        "kickoff_utc": iso_utc(kickoff),
        "status": {
            "state": state,
            "detail": status_type.get("description") or status_type.get("detail") or state,
            "completed": bool(status_type.get("completed")),
        },
        "teams": {
            "team_a": {
                "name": team_a_zh,
                "name_en": team_a,
                "abbreviation": (team_a_raw.get("team") or {}).get("abbreviation"),
                "logo": competitor_logo(team_a_raw),
                "score": team_a_raw.get("score"),
            },
            "team_b": {
                "name": team_b_zh,
                "name_en": team_b,
                "abbreviation": (team_b_raw.get("team") or {}).get("abbreviation"),
                "logo": competitor_logo(team_b_raw),
                "score": team_b_raw.get("score"),
            },
        },
        "venue": {
            "name": venue.get("fullName") or venue.get("name"),
            "city": address.get("city"),
            "country": address.get("country"),
        },
        "source": {
            "name": "ESPN public scoreboard",
            "event_url": f"https://www.espn.com/soccer/match/_/gameId/{event_id}",
        },
        "prediction": prediction_for(team_a, team_b, state),
    }


def build_payload(start: dt.date, days: int) -> dict[str, Any]:
    now = utc_now()
    raw_events, source_urls, warnings = fetch_espn_events(start, days)
    matches = [match for event in raw_events if (match := transform_event(event))]
    matches.sort(key=lambda item: item["kickoff_utc"])

    source_failed = bool(warnings) and not raw_events
    status = "ready"
    if source_failed:
        status = "source_unavailable"
    elif not matches:
        status = "no_verified_fixtures"

    return {
        "schema_version": 1,
        "generated_at": iso_utc(now),
        "window": {
            "start_date": start.isoformat(),
            "days": days,
            "timezone": "UTC",
        },
        "status": status,
        "source": {
            "fixture_provider": "ESPN public scoreboard",
            "league": DEFAULT_LEAGUE,
            "urls": source_urls,
        },
        "warnings": warnings,
        "match_count": len(matches),
        "matches": matches,
        "disclaimer": "预测结果是针对已验证赛程的确定性编辑模型估计，不构成投注建议。",
    }


def write_payload(payload: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(output: Path = DEFAULT_OUTPUT, start: dt.date | None = None, days: int = DEFAULT_DAYS) -> dict[str, Any]:
    start_date = start or utc_now().date()
    payload = build_payload(start_date, days)
    write_payload(payload, output)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch verified World Cup fixtures and generate predictions.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--start-date", help="UTC start date in YYYY-MM-DD format")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    args = parser.parse_args()

    start = dt.date.fromisoformat(args.start_date) if args.start_date else None
    payload = run(output=args.output, start=start, days=args.days)
    print(f"Wrote {args.output} with status={payload['status']} matches={payload['match_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
