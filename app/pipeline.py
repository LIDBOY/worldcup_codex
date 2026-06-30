from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import shutil
import time
import unicodedata
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


ANALYSIS_MODEL = os.getenv("DEEPSEEK_ANALYSIS_MODEL", "deepseek-v4-pro")
RENDER_MODEL = os.getenv("DEEPSEEK_RENDER_MODEL", "deepseek-v4-flash")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
DEEPSEEK_API_KEY_ENV = "DEEPSEEK_API_KEY"
TOKEN_COST_RATE = float(os.getenv("DEEPSEEK_TOKEN_COST_RATE", "0.00001"))
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
MATCH_DAY_START_HOUR = 18

FIFA_COMPETITION_ID = os.getenv("FIFA_COMPETITION_ID", "17")
FIFA_SEASON_ID = os.getenv("FIFA_SEASON_ID", "285023")
FIFA_LANGUAGE = os.getenv("FIFA_LANGUAGE", "en")
FIFA_SEARCH_KEY = os.getenv(
    "FIFA_SEARCH_KEY",
    "2kD9zRYRT7xN6kSGs6EoHcvSyKOyK0B4YaKTf1Ygeaw8PM6bgfR6SQ==",
)

DEFAULT_LEAGUE = os.getenv("WORLDCUP_ESPN_LEAGUE", "fifa.world")
DEFAULT_DAYS = int(os.getenv("WORLDCUP_WINDOW_DAYS", "2"))
STRUCTURE_MATCH_DAYS = int(os.getenv("WORLDCUP_STRUCTURE_MATCH_DAYS", "21"))
REQUEST_TIMEOUT = int(os.getenv("WORLDCUP_REQUEST_TIMEOUT", "25"))
DEEPSEEK_REQUEST_TIMEOUT = int(os.getenv("DEEPSEEK_REQUEST_TIMEOUT", "180"))
INJURY_LOOKBACK_DAYS = int(os.getenv("WORLDCUP_INJURY_LOOKBACK_DAYS", "180"))
BRACKET_ROUND_ORDER = ("round_of_32", "round_of_16", "quarter_finals", "semi_finals", "final")
BRACKET_ROUND_SIZES = {
    "round_of_32": 16,
    "round_of_16": 8,
    "quarter_finals": 4,
    "semi_finals": 2,
    "final": 1,
}
BRACKET_MATCH_NUMBERS = {
    "round_of_32": tuple(range(73, 89)),
    "round_of_16": tuple(range(89, 97)),
    "quarter_finals": tuple(range(97, 101)),
    "semi_finals": (101, 102),
    "final": (104,),
}
BRACKET_WINNER_FEEDS = {
    89: (73, 74),
    90: (75, 76),
    91: (77, 78),
    92: (79, 80),
    93: (81, 82),
    94: (83, 84),
    95: (85, 86),
    96: (87, 88),
    97: (89, 90),
    98: (91, 92),
    99: (93, 94),
    100: (95, 96),
    101: (97, 98),
    102: (99, 100),
    104: (101, 102),
}
THIRD_PLACE_MATCH_NUMBERS = {103}

COUNTRY_CODE_ALPHA2 = {
    "ALG": "DZ",
    "ARG": "AR",
    "AUS": "AU",
    "AUT": "AT",
    "BEL": "BE",
    "BIH": "BA",
    "BRA": "BR",
    "CAN": "CA",
    "CIV": "CI",
    "CPV": "CV",
    "COL": "CO",
    "COD": "CD",
    "CRO": "HR",
    "CZE": "CZ",
    "DEN": "DK",
    "ECU": "EC",
    "EGY": "EG",
    "FRA": "FR",
    "GER": "DE",
    "GHA": "GH",
    "IRN": "IR",
    "ITA": "IT",
    "JPN": "JP",
    "KOR": "KR",
    "MAR": "MA",
    "MEX": "MX",
    "NED": "NL",
    "NOR": "NO",
    "PAR": "PY",
    "POR": "PT",
    "SEN": "SN",
    "ESP": "ES",
    "SUI": "CH",
    "SWE": "SE",
    "TUN": "TN",
    "URU": "UY",
    "USA": "US",
}

DATA_DIR = Path("data")
DOCS_DIR = Path("docs")
FIXTURES_PATH = DATA_DIR / "fixtures.json"
ANALYSIS_PATH = DATA_DIR / "analysis.json"
RENDER_PATH = DATA_DIR / "render.json"
LATEST_PATH = DATA_DIR / "latest.json"

FIFA_CALENDAR = "https://api.fifa.com/api/v3/calendar/matches"
FIFA_SEARCH = "https://cxm-api.fifa.com/fifacxmsearch/api/results"
ESPN_SCOREBOARD = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/"
    f"{DEFAULT_LEAGUE}/scoreboard"
)
ESPN_NEWS = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/"
    f"{DEFAULT_LEAGUE}/news"
)

TEAM_NAME_ZH = {
    "algeria": "\u963f\u5c14\u53ca\u5229\u4e9a",
    "argentina": "\u963f\u6839\u5ef7",
    "australia": "\u6fb3\u5927\u5229\u4e9a",
    "austria": "\u5965\u5730\u5229",
    "belgium": "\u6bd4\u5229\u65f6",
    "bosnia herzegovina": "\u6ce2\u9ed1",
    "brazil": "\u5df4\u897f",
    "canada": "\u52a0\u62ff\u5927",
    "cape verde": "\u4f5b\u5f97\u89d2",
    "colombia": "\u54e5\u4f26\u6bd4\u4e9a",
    "congo dr": "\u521a\u679c\u6c11\u4e3b\u5171\u548c\u56fd",
    "croatia": "\u514b\u7f57\u5730\u4e9a",
    "curacao": "\u5e93\u62c9\u7d22",
    "czechia": "\u6377\u514b",
    "czech republic": "\u6377\u514b",
    "denmark": "\u4e39\u9ea6",
    "ecuador": "\u5384\u74dc\u591a\u5c14",
    "egypt": "\u57c3\u53ca",
    "england": "\u82f1\u683c\u5170",
    "france": "\u6cd5\u56fd",
    "germany": "\u5fb7\u56fd",
    "ghana": "\u52a0\u7eb3",
    "haiti": "\u6d77\u5730",
    "iran": "\u4f0a\u6717",
    "iraq": "\u4f0a\u62c9\u514b",
    "italy": "\u610f\u5927\u5229",
    "ivory coast": "\u79d1\u7279\u8fea\u74e6",
    "cote d ivoire": "\u79d1\u7279\u8fea\u74e6",
    "japan": "\u65e5\u672c",
    "jordan": "\u7ea6\u65e6",
    "korea republic": "\u97e9\u56fd",
    "south korea": "\u97e9\u56fd",
    "mexico": "\u58a8\u897f\u54e5",
    "morocco": "\u6469\u6d1b\u54e5",
    "netherlands": "\u8377\u5170",
    "new zealand": "\u65b0\u897f\u5170",
    "norway": "\u632a\u5a01",
    "panama": "\u5df4\u62ff\u9a6c",
    "paraguay": "\u5df4\u62c9\u572d",
    "portugal": "\u8461\u8404\u7259",
    "qatar": "\u5361\u5854\u5c14",
    "saudi arabia": "\u6c99\u7279\u963f\u62c9\u4f2f",
    "scotland": "\u82cf\u683c\u5170",
    "senegal": "\u585e\u5185\u52a0\u5c14",
    "south africa": "\u5357\u975e",
    "spain": "\u897f\u73ed\u7259",
    "sweden": "\u745e\u5178",
    "switzerland": "\u745e\u58eb",
    "tunisia": "\u7a81\u5c3c\u65af",
    "turkiye": "\u571f\u8033\u5176",
    "turkey": "\u571f\u8033\u5176",
    "united states": "\u7f8e\u56fd",
    "usa": "\u7f8e\u56fd",
    "uruguay": "\u4e4c\u62c9\u572d",
    "uzbekistan": "\u4e4c\u5179\u522b\u514b\u65af\u5766",
}

INJURY_KEYWORDS = (
    "injury",
    "injured",
    "injuries",
    "fitness",
    "doubt",
    "doubtful",
    "ruled out",
    "out of",
    "misses",
    "withdrawn",
    "hamstring",
    "ankle",
    "knee",
    "calf",
    "groin",
    "suspension",
    "suspended",
)


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso_utc(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def parse_date(value: str) -> dt.datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return dt.datetime.fromisoformat(value).astimezone(dt.timezone.utc)


def to_shanghai(value: str | dt.datetime) -> dt.datetime:
    if isinstance(value, str):
        value = parse_date(value)
    return value.astimezone(SHANGHAI_TZ)


def cn_month_day(value: dt.date) -> str:
    return f"{value.month}\u6708{value.day}\u65e5"


def format_beijing_time(value: str | dt.datetime) -> str:
    local = to_shanghai(value)
    return f"\u5317\u4eac\u65f6\u95f4 {local:%m-%d %H:%M}"


def match_day_start(local: dt.datetime) -> dt.datetime:
    date = local.date()
    if local.hour < MATCH_DAY_START_HOUR:
        date -= dt.timedelta(days=1)
    return dt.datetime.combine(date, dt.time(MATCH_DAY_START_HOUR), SHANGHAI_TZ)


def match_day_info(value: str | dt.datetime) -> dict[str, str]:
    local = to_shanghai(value)
    start = match_day_start(local)
    end = start + dt.timedelta(days=1)
    return {
        "date": start.date().isoformat(),
        "title": f"{cn_month_day(start.date())}\u6bd4\u8d5b\u65e5",
        "range": f"\u5317\u4eac\u65f6\u95f4 {start:%m-%d %H:%M} - {end:%m-%d %H:%M}",
        "start_iso": start.isoformat(),
        "end_iso": end.isoformat(),
    }


def china_match_day_window(day_count: int = DEFAULT_DAYS, start_date: dt.date | None = None) -> dict[str, Any]:
    count = max(day_count, 1)
    if start_date:
        first_start = dt.datetime.combine(start_date, dt.time(MATCH_DAY_START_HOUR), SHANGHAI_TZ)
    else:
        first_start = match_day_start(to_shanghai(utc_now()))
    end = first_start + dt.timedelta(days=count)
    match_days = [match_day_info(first_start + dt.timedelta(days=offset)) for offset in range(count)]
    return {
        "timezone": "Asia/Shanghai",
        "match_day_count": count,
        "start_iso": first_start.isoformat(),
        "end_iso": end.isoformat(),
        "display_range": f"{match_days[0]['title']} - {match_days[-1]['title']}",
        "range": f"北京时间 {first_start:%m-%d %H:%M} - {end:%m-%d %H:%M}",
        "match_days": match_days,
    }


def fifa_fetch_span_for_china_window(window: dict[str, Any]) -> tuple[dt.date, int]:
    start = dt.datetime.fromisoformat(window["start_iso"])
    end = dt.datetime.fromisoformat(window["end_iso"])
    start_utc = start.astimezone(dt.timezone.utc)
    end_utc = (end - dt.timedelta(seconds=1)).astimezone(dt.timezone.utc)
    days = (end_utc.date() - start_utc.date()).days + 1
    return start_utc.date(), max(days, 1)


def filter_matches_to_china_window(matches: list[dict[str, Any]], window: dict[str, Any]) -> list[dict[str, Any]]:
    start = dt.datetime.fromisoformat(window["start_iso"])
    end = dt.datetime.fromisoformat(window["end_iso"])
    filtered = []
    for match in matches:
        kickoff = match.get("kickoff_utc")
        if not kickoff:
            continue
        local = to_shanghai(kickoff)
        if start <= local < end:
            filtered.append(match)
    return filtered


def normalize_team(name: str | None) -> str:
    if not name:
        return ""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-z0-9]+", " ", ascii_name.lower()).strip()
    aliases = {
        "us": "united states",
        "u s": "united states",
        "usa": "united states",
        "united states of america": "united states",
        "ir iran": "iran",
        "i r iran": "iran",
        "iran islamic republic of": "iran",
        "islamic republic of iran": "iran",
        "korea": "south korea",
        "korea republic": "south korea",
        "republic of korea": "south korea",
        "cote d ivoire": "ivory coast",
        "cote divoire": "ivory coast",
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
            "1st": "\u7b2c\u4e00\u540d",
            "first": "\u7b2c\u4e00\u540d",
            "2nd": "\u7b2c\u4e8c\u540d",
            "second": "\u7b2c\u4e8c\u540d",
            "3rd": "\u7b2c\u4e09\u540d",
            "third": "\u7b2c\u4e09\u540d",
            "4th": "\u7b2c\u56db\u540d",
            "fourth": "\u7b2c\u56db\u540d",
        }[group_match.group(2)]
        return f"{group_match.group(1).upper()}\u7ec4{place}"
    return TEAM_NAME_ZH.get(normalized, name)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def request_json(
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    retries: int = 3,
    timeout: int = REQUEST_TIMEOUT,
) -> dict[str, Any]:
    full_url = f"{url}?{urlencode(params)}" if params else url
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request_headers = {"User-Agent": "worldcup-agent-pages/3.0", **(headers or {})}
    if body is not None:
        request_headers["Content-Type"] = "application/json"

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            request = Request(full_url, data=data, headers=request_headers)
            with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed upstream APIs
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            last_error = RuntimeError(f"HTTP {exc.code} from {full_url}: {detail}")
        except Exception as exc:  # noqa: BLE001 - preserve upstream failure detail
            last_error = exc
        if attempt < retries:
            time.sleep(2 ** (attempt - 1))
    raise RuntimeError(f"failed to fetch {full_url}: {last_error}")


def stable_id(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def localized(values: Any, default: str = "") -> str:
    if isinstance(values, list):
        for item in values:
            if not isinstance(item, dict):
                continue
            locale = str(item.get("Locale") or "").lower()
            if locale.startswith("en") and item.get("Description"):
                return str(item["Description"])
        for item in values:
            if isinstance(item, dict) and item.get("Description"):
                return str(item["Description"])
    if isinstance(values, str):
        return values
    return default


def clean_asset_url(value: Any) -> str:
    if not value:
        return ""
    return str(value).replace("{format}", "png").replace("{size}", "3")


def first_logo_from_espn(team: dict[str, Any]) -> str:
    for key in ("flag", "logo"):
        if team.get(key):
            return clean_asset_url(team.get(key))
    logos = team.get("logos")
    if isinstance(logos, list):
        for item in logos:
            if isinstance(item, dict) and item.get("href"):
                return clean_asset_url(item.get("href"))
    return ""


def normalize_country_code(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"[^A-Za-z]", "", str(value)).upper()


def country_alpha2(code: Any) -> str:
    normalized = normalize_country_code(code)
    if len(normalized) == 2:
        return normalized
    return COUNTRY_CODE_ALPHA2.get(normalized, "")


def flag_emoji_from_code(code: Any) -> str:
    alpha2 = country_alpha2(code)
    if len(alpha2) != 2 or not alpha2.isalpha():
        return ""
    base = 0x1F1E6
    return "".join(chr(base + ord(char) - ord("A")) for char in alpha2.upper())


def team_flag_metadata(*codes: Any, flag_url_value: Any = None) -> dict[str, str]:
    country_code = ""
    for code in codes:
        country_code = normalize_country_code(code)
        if country_code:
            break
    flag_url_value = clean_asset_url(flag_url_value)
    return {
        "country_code": country_code,
        "flag_url": flag_url_value,
        "flag_emoji": flag_emoji_from_code(country_code),
    }

def team_from_fifa(raw: dict[str, Any], placeholder: str | None = None) -> dict[str, Any]:
    name_en = localized(raw.get("TeamName"), raw.get("ShortClubName") or placeholder or "Unknown team")
    if not name_en or name_en == "Unknown team":
        name_en = placeholder or "Unknown team"
    country_code = raw.get("IdCountry") or raw.get("CountryCode") or raw.get("Abbreviation")
    metadata = team_flag_metadata(country_code, raw.get("Abbreviation"), flag_url_value=raw.get("PictureUrl"))
    return {
        "name": team_name_zh(name_en),
        "name_en": name_en,
        "abbreviation": raw.get("Abbreviation") or raw.get("IdCountry") or placeholder,
        "id_team": raw.get("IdTeam"),
        "id_country": raw.get("IdCountry"),
        "logo": clean_asset_url(raw.get("PictureUrl")),
        "score": raw.get("Score"),
        "tactics": raw.get("Tactics"),
        **metadata,
    }


def fetch_fifa_matches(start: dt.date, days: int) -> tuple[list[dict[str, Any]], str, list[str]]:
    end = start + dt.timedelta(days=max(days, 1))
    params = {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "language": FIFA_LANGUAGE,
        "count": "500",
        "idCompetition": FIFA_COMPETITION_ID,
        "idSeason": FIFA_SEASON_ID,
    }
    url = f"{FIFA_CALENDAR}?{urlencode(params)}"
    warnings: list[str] = []
    payload = request_json(FIFA_CALENDAR, params=params)
    matches = []
    for item in payload.get("Results", []) or []:
        if str(item.get("IdCompetition")) != FIFA_COMPETITION_ID:
            continue
        competition_name = localized(item.get("CompetitionName"))
        if "World Cup" not in competition_name:
            warnings.append(f"filtered non-world-cup FIFA match {item.get('IdMatch')}")
            continue
        matches.append(transform_fifa_match(item))
    return matches, url, warnings


def transform_fifa_match(item: dict[str, Any]) -> dict[str, Any]:
    home = team_from_fifa(item.get("Home") or {}, item.get("PlaceHolderA"))
    away = team_from_fifa(item.get("Away") or {}, item.get("PlaceHolderB"))
    kickoff = parse_date(item["Date"]) if item.get("Date") else utc_now()
    stadium = item.get("Stadium") or {}
    match_id = str(item.get("IdMatch") or stable_id(item))
    return {
        "id": match_id,
        "fifa_match_id": match_id,
        "match_name": f"{home['name']} vs {away['name']}",
        "match_name_en": f"{home['name_en']} vs {away['name_en']}",
        "kickoff_utc": iso_utc(kickoff),
        "competition": localized(item.get("CompetitionName"), "FIFA World Cup"),
        "season": localized(item.get("SeasonName"), "FIFA World Cup 2026"),
        "stage": localized(item.get("StageName")),
        "stage_name": localized(item.get("StageName")),
        "round_name": localized(item.get("RoundName") or item.get("Round") or item.get("MatchRoundName")),
        "phase": localized(item.get("PhaseName") or item.get("Phase") or item.get("StageType")),
        "group": localized(item.get("GroupName")),
        "match_number": item.get("MatchNumber"),
        "status": {
            "match_status": item.get("MatchStatus"),
            "officiality_status": item.get("OfficialityStatus"),
            "result_type": item.get("ResultType"),
        },
        "teams": {"home": home, "away": away},
        "venue": {
            "name": localized(stadium.get("Name")),
            "city": localized(stadium.get("CityName")),
            "country": stadium.get("IdCountry"),
        },
        "sources": {
            "fifa": {
                "name": "FIFA official calendar API",
                "url": FIFA_CALENDAR,
                "id_competition": item.get("IdCompetition"),
                "id_season": item.get("IdSeason"),
                "id_match": match_id,
            }
        },
    }


def espn_date_url(day: dt.date) -> str:
    return f"{ESPN_SCOREBOARD}?dates={day:%Y%m%d}&limit=100"


def fetch_espn_events(start: dt.date, days: int) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    events: dict[str, dict[str, Any]] = {}
    urls: list[str] = []
    warnings: list[str] = []
    for offset in range(max(days, 1)):
        day = start + dt.timedelta(days=offset)
        params = {"dates": f"{day:%Y%m%d}", "limit": "100"}
        urls.append(espn_date_url(day))
        try:
            payload = request_json(ESPN_SCOREBOARD, params=params)
        except RuntimeError as exc:
            warnings.append(str(exc))
            continue
        for event in payload.get("events", []) or []:
            event_id = str(event.get("id") or stable_id(event))
            events[event_id] = event
    return list(events.values()), urls, warnings


def competitor_name(competitor: dict[str, Any]) -> str:
    team = competitor.get("team") or {}
    return (
        team.get("displayName")
        or team.get("shortDisplayName")
        or team.get("name")
        or competitor.get("displayName")
        or "Unknown team"
    )


def pick_competitors(event: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    competitions = event.get("competitions") or []
    if not competitions:
        return None
    competitors = competitions[0].get("competitors") or []
    if len(competitors) < 2:
        return None
    home = next((item for item in competitors if item.get("homeAway") == "home"), None)
    away = next((item for item in competitors if item.get("homeAway") == "away"), None)
    return (home, away) if home and away else (competitors[0], competitors[1])


def american_to_probability(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    if text in {"EVEN", "EVENS"}:
        return 0.5
    match = re.search(r"[-+]?\d+", text)
    if not match:
        return None
    odds = int(match.group(0))
    if odds > 0:
        return 100 / (odds + 100)
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    return None


def odds_value(node: dict[str, Any] | None) -> str | None:
    if not isinstance(node, dict):
        return None
    market = node.get("close") or node.get("open") or node
    if not isinstance(market, dict):
        return None
    raw = market.get("odds")
    return str(raw) if raw is not None else None


def extract_odds(competition: dict[str, Any]) -> dict[str, Any]:
    for offer in competition.get("odds", []) or []:
        if not isinstance(offer, dict):
            continue
        moneyline = offer.get("moneyline") or {}
        home = odds_value(moneyline.get("home"))
        draw = odds_value(moneyline.get("draw"))
        away = odds_value(moneyline.get("away"))
        raw_probs = {
            "home_win": american_to_probability(home),
            "draw": american_to_probability(draw),
            "away_win": american_to_probability(away),
        }
        if any(value is None for value in raw_probs.values()):
            continue
        total = sum(float(value) for value in raw_probs.values())
        implied = {key: round(float(value) * 100, 2) for key, value in raw_probs.items() if value is not None}
        normalized = {key: round(float(value) / total * 100, 2) for key, value in raw_probs.items()}
        provider = offer.get("provider") or {}
        return {
            "available": True,
            "source": "ESPN odds feed",
            "provider": provider.get("name") or offer.get("details") or "ESPN listed sportsbook",
            "moneyline_american": {"home": home, "draw": draw, "away": away},
            "implied_probability": implied,
            "normalized_probability": normalized,
            "overround": round(total * 100 - 100, 2),
            "details": offer.get("details"),
        }
    return {"available": False, "source": "ESPN odds feed", "reason": "moneyline odds unavailable"}


def transform_espn_event(event: dict[str, Any]) -> dict[str, Any] | None:
    pair = pick_competitors(event)
    if not pair:
        return None
    home_raw, away_raw = pair
    competition = (event.get("competitions") or [{}])[0]
    event_id = str(event.get("id") or stable_id(event))

    def espn_team(raw: dict[str, Any]) -> dict[str, Any]:
        team = raw.get("team") or {}
        abbreviation = team.get("abbreviation") or raw.get("abbreviation")
        metadata = team_flag_metadata(
            team.get("countryCode"),
            team.get("country"),
            abbreviation,
            flag_url_value=first_logo_from_espn(team),
        )
        return {
            "name_en": competitor_name(raw),
            "abbreviation": abbreviation,
            "id_team": team.get("id"),
            "logo": first_logo_from_espn(team),
            **metadata,
        }

    return {
        "id": event_id,
        "kickoff_utc": iso_utc(parse_date(event["date"])) if event.get("date") else None,
        "teams": {
            "home": espn_team(home_raw),
            "away": espn_team(away_raw),
        },
        "odds": extract_odds(competition),
        "source": {
            "name": "ESPN public FIFA World Cup scoreboard",
            "event_url": f"https://www.espn.com/soccer/match/_/gameId/{event_id}",
        },
    }


def team_pair_key(match: dict[str, Any]) -> frozenset[str]:
    teams = match.get("teams") or {}
    return frozenset(
        normalize_team((teams.get(side) or {}).get("name_en") or (teams.get(side) or {}).get("name"))
        for side in ("home", "away")
    )


def merge_team_metadata(base: dict[str, Any] | None, incoming: dict[str, Any] | None) -> dict[str, Any]:
    base = base or {}
    incoming = incoming or {}
    merged = dict(base)
    for key, value in incoming.items():
        if value not in (None, "", []):
            merged[key] = value
    for key in ("country_code", "flag_url", "flag_emoji", "logo", "id_country", "id_team", "abbreviation"):
        if not merged.get(key) and base.get(key):
            merged[key] = base[key]
    if not merged.get("name") and merged.get("name_en"):
        merged["name"] = team_name_zh(str(merged["name_en"]))
    if not merged.get("country_code"):
        merged["country_code"] = normalize_country_code(merged.get("id_country") or merged.get("abbreviation"))
    if not merged.get("flag_url") and merged.get("logo"):
        merged["flag_url"] = clean_asset_url(merged.get("logo"))
    if not merged.get("flag_emoji") and merged.get("country_code"):
        merged["flag_emoji"] = flag_emoji_from_code(merged.get("country_code"))
    return merged


def merge_match_teams(base: dict[str, Any] | None, incoming: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    base = base or {}
    incoming = incoming or {}
    return {
        "home": merge_team_metadata(base.get("home"), incoming.get("home")),
        "away": merge_team_metadata(base.get("away"), incoming.get("away")),
    }

def find_espn_match(fifa_match: dict[str, Any], espn_matches: list[dict[str, Any]]) -> dict[str, Any] | None:
    fifa_key = team_pair_key(fifa_match)
    fifa_time = parse_date(fifa_match["kickoff_utc"])
    best: tuple[float, dict[str, Any]] | None = None
    for espn_match in espn_matches:
        if team_pair_key(espn_match) != fifa_key:
            continue
        if not espn_match.get("kickoff_utc"):
            continue
        delta = abs((parse_date(espn_match["kickoff_utc"]) - fifa_time).total_seconds())
        if delta <= 12 * 3600 and (best is None or delta < best[0]):
            best = (delta, espn_match)
    return best[1] if best else None


def verify_fifa_matches(
    fifa_matches: list[dict[str, Any]],
    espn_matches: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    verified: list[dict[str, Any]] = []
    unverified: list[str] = []
    for fifa_match in fifa_matches:
        espn_match = find_espn_match(fifa_match, espn_matches)
        if not espn_match:
            unverified.append(fifa_match.get("match_name_en") or fifa_match.get("match_name") or str(fifa_match.get("id")))
            continue
        item = {**fifa_match, "sources": dict(fifa_match.get("sources") or {})}
        item["espn_event_id"] = espn_match["id"]
        item["sources"]["espn"] = espn_match["source"]
        item["source_verification"] = {
            "verified": True,
            "sources": ["FIFA official calendar API", "ESPN public FIFA World Cup scoreboard"],
            "method": "team-pair and kickoff-time cross-check",
        }
        item["odds"] = espn_match["odds"]
        item["teams"] = merge_match_teams(fifa_match.get("teams"), espn_match.get("teams"))
        verified.append(item)
    return verified, unverified

def fetch_espn_news() -> tuple[list[dict[str, Any]], str, list[str]]:
    params = {"limit": "100"}
    url = f"{ESPN_NEWS}?{urlencode(params)}"
    try:
        payload = request_json(ESPN_NEWS, params=params)
    except RuntimeError as exc:
        return [], url, [str(exc)]
    return payload.get("articles", []) or [], url, []


def fifa_search_articles(query: str) -> tuple[list[dict[str, Any]], list[str]]:
    params = {
        "locale": "en",
        "searchString": query,
        "clientType": "fifaplus",
        "type": "search",
        "context": "default",
        "dateFrom": (utc_now().date() - dt.timedelta(days=INJURY_LOOKBACK_DAYS)).isoformat(),
        "size": "5",
        "from": "0",
        "contentType": "article",
        "sort": "relevance",
    }
    headers = {"X-Functions-Key": FIFA_SEARCH_KEY, "Content-Type": "application/json"}
    try:
        payload = request_json(FIFA_SEARCH, params=params, headers=headers)
    except RuntimeError as exc:
        return [], [str(exc)]
    return (payload.get("hits") or {}).get("hits", []) or [], []


def compact_fifa_article(hit: dict[str, Any]) -> dict[str, Any]:
    source = hit.get("_source") or {}
    extra = source.get("additionalInformation")
    url = None
    if isinstance(extra, str):
        try:
            url = json.loads(extra).get("RelativeUrl")
        except json.JSONDecodeError:
            url = None
    return {
        "source": "FIFA official search",
        "title": source.get("title"),
        "description": source.get("description") or source.get("summary"),
        "published": source.get("date") or source.get("publicationDate"),
        "url": f"https://www.fifa.com{url}" if url and url.startswith("/") else url,
    }


def compact_espn_article(article: dict[str, Any]) -> dict[str, Any]:
    links = article.get("links") or {}
    web = links.get("web") or {}
    return {
        "source": "ESPN World Cup news",
        "title": article.get("headline"),
        "description": article.get("description"),
        "published": article.get("published") or article.get("lastModified"),
        "url": web.get("href") or article.get("link"),
    }


def text_has_injury_signal(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in INJURY_KEYWORDS)


def text_mentions_team(text: str, team: dict[str, Any]) -> bool:
    normalized_text = normalize_team(text)
    candidates = {
        normalize_team(team.get("name_en")),
        normalize_team(team.get("name")),
        normalize_team(team.get("abbreviation")),
    }
    return any(candidate and candidate in normalized_text for candidate in candidates)


def article_text(article: dict[str, Any]) -> str:
    return " ".join(str(article.get(key) or "") for key in ("title", "headline", "description", "summary"))


def injury_record_for_team(
    team: dict[str, Any],
    fifa_hits: list[dict[str, Any]],
    espn_articles: list[dict[str, Any]],
) -> dict[str, Any]:
    official_records = []
    for hit in fifa_hits:
        article = compact_fifa_article(hit)
        if text_has_injury_signal(article_text(article)):
            official_records.append(article)

    media_records = []
    for raw in espn_articles:
        article = compact_espn_article(raw)
        text = article_text(article)
        if text_has_injury_signal(text) and text_mentions_team(text, team):
            media_records.append(article)

    if official_records:
        status = "confirmed injury"
        records = official_records[:3]
    elif media_records:
        status = "probable injury"
        records = media_records[:3]
    else:
        status = "unknown"
        records = []
    return {
        "team": team.get("name"),
        "team_en": team.get("name_en"),
        "status": status,
        "records": records,
        "source_policy": "confirmed injury requires FIFA official article; probable injury requires media article; otherwise unknown",
    }


def attach_injuries(matches: list[dict[str, Any]], espn_articles: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    cache: dict[str, list[dict[str, Any]]] = {}
    for match in matches:
        for side in ("home", "away"):
            team = (match.get("teams") or {}).get(side) or {}
            key = normalize_team(team.get("name_en"))
            if key and key not in cache:
                hits, errors = fifa_search_articles(f"{team.get('name_en', '')} injury")
                cache[key] = hits
                warnings.extend(errors)
            match.setdefault("injuries", {})[side] = injury_record_for_team(team, cache.get(key, []), espn_articles)
    return matches, warnings


def run_research(output: Path = FIXTURES_PATH, start: dt.date | None = None, days: int = DEFAULT_DAYS) -> dict[str, Any]:
    display_window = china_match_day_window(days, start)
    display_start_date, display_fetch_days = fifa_fetch_span_for_china_window(display_window)
    structure_start = dt.date.fromisoformat(display_window["match_days"][0]["date"])
    structure_days = max(days, STRUCTURE_MATCH_DAYS)
    structure_window = china_match_day_window(structure_days, structure_start)
    structure_start_date, structure_fetch_days = fifa_fetch_span_for_china_window(structure_window)

    fifa_matches_all, fifa_url, fifa_warnings = fetch_fifa_matches(structure_start_date, structure_fetch_days)
    raw_fifa_fixture_count = len(fifa_matches_all)
    structure_fifa_matches = filter_matches_to_china_window(fifa_matches_all, structure_window)
    fifa_matches = filter_matches_to_china_window(fifa_matches_all, display_window)

    espn_raw_events, espn_urls, espn_warnings = fetch_espn_events(
        structure_start_date - dt.timedelta(days=1),
        structure_fetch_days + 2,
    )
    espn_matches = [match for event in espn_raw_events if (match := transform_espn_event(event))]

    structure_verified, structure_unverified = verify_fifa_matches(structure_fifa_matches, espn_matches)
    structure_verified.sort(key=lambda item: item.get("kickoff_utc") or "")
    verified_by_id = {str(item.get("id")): item for item in structure_verified}
    verified = [verified_by_id[str(match.get("id"))] for match in fifa_matches if str(match.get("id")) in verified_by_id]
    unverified = [
        match.get("match_name_en") or match.get("match_name") or str(match.get("id"))
        for match in fifa_matches
        if str(match.get("id")) not in verified_by_id
    ]

    espn_articles, news_url, news_warnings = fetch_espn_news()
    verified, injury_warnings = attach_injuries(verified, espn_articles)
    odds_available = sum(1 for match in verified if (match.get("odds") or {}).get("available"))

    warnings = [*fifa_warnings, *espn_warnings, *news_warnings, *injury_warnings]
    payload = {
        "schema_version": 3,
        "stage": "research",
        "generated_at": iso_utc(utc_now()),
        "window": {
            "start_date": display_start_date.isoformat(),
            "days": display_fetch_days,
            "timezone": "UTC",
            "mode": "derived from China match-day display window",
        },
        "structure_utc_window": {
            "start_date": structure_start_date.isoformat(),
            "days": structure_fetch_days,
            "timezone": "UTC",
            "mode": "derived from China match-day structure window",
        },
        "display_window": display_window,
        "structure_window": structure_window,
        "china_match_days": display_window["match_days"],
        "data_sources": {
            "fifa": True,
            "injury": True,
            "odds": True,
            "verification": True,
        },
        "source": {
            "fifa": {"name": "FIFA official calendar API", "url": fifa_url},
            "verification": {"name": "ESPN public FIFA World Cup scoreboard", "urls": espn_urls},
            "injury": {
                "official": "FIFA official search API",
                "media": "ESPN World Cup news API",
                "media_url": news_url,
            },
            "odds": {"name": "ESPN odds feed", "urls": espn_urls},
        },
        "warnings": warnings,
        "unverified_fifa_matches": unverified,
        "structure_unverified_fifa_matches": structure_unverified,
        "fixture_count": len(verified),
        "fifa_fixture_count": len(fifa_matches),
        "raw_fifa_fixture_count": raw_fifa_fixture_count,
        "structure_fixture_count": len(structure_verified),
        "structure_fifa_fixture_count": len(structure_fifa_matches),
        "odds_available_count": odds_available,
        "matches": verified,
        "fixtures": verified,
        "structure_matches": structure_verified,
        "daily_log": [
            {
                "time": iso_utc(utc_now()),
                "stage": "08:15 automatic FIFA schedule + injury + odds research, with tournament structure context",
                "status": "completed",
            }
        ],
    }
    write_json(output, payload)
    return payload

def zero_usage() -> dict[str, Any]:
    return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_estimate": 0.0}


def usage_from_response(response: dict[str, Any]) -> dict[str, Any]:
    raw = response.get("usage") or {}
    input_tokens = int(raw.get("input_tokens") or raw.get("prompt_tokens") or 0)
    output_tokens = int(raw.get("output_tokens") or raw.get("completion_tokens") or 0)
    total_tokens = int(raw.get("total_tokens") or input_tokens + output_tokens)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_estimate": round(total_tokens * TOKEN_COST_RATE, 6),
    }


def combine_usage(*items: dict[str, Any]) -> dict[str, Any]:
    input_tokens = sum(int(item.get("input_tokens", 0)) for item in items)
    output_tokens = sum(int(item.get("output_tokens", 0)) for item in items)
    total_tokens = sum(int(item.get("total_tokens", 0)) for item in items)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_estimate": round(total_tokens * TOKEN_COST_RATE, 6),
    }


def deepseek_chat(
    model: str,
    messages: list[dict[str, str]],
    *,
    json_object: bool = False,
    analysis_layer: bool = False,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    api_key = os.environ.get(DEEPSEEK_API_KEY_ENV)
    if not api_key:
        raise RuntimeError(f"{DEEPSEEK_API_KEY_ENV} is required for DeepSeek production pipeline")
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "stream": False,
    }
    if json_object:
        payload["response_format"] = {"type": "json_object"}
    if analysis_layer:
        payload["reasoning_effort"] = "high"
        payload["thinking"] = {"type": "enabled"}
    response = request_json(
        f"{DEEPSEEK_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        body=payload,
        timeout=DEEPSEEK_REQUEST_TIMEOUT,
    )
    choices = response.get("choices") or []
    if not choices:
        raise RuntimeError(f"DeepSeek returned no choices for model {model}")
    content = (choices[0].get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(f"DeepSeek returned empty content for model {model}")
    return content.strip(), usage_from_response(response), response


def parse_json_text(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(text, strict=False)


def parse_json_content(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return parse_json_text(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return parse_json_text(text[start:end + 1])


def analysis_messages(research_payload: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are the only analysis layer for a FIFA World Cup AI Agent. "
                "You must use deepseek-v4-pro reasoning only. Do not invent fixtures, injuries, odds, results, "
                "or sources. Use only the verified FIFA/ESPN/injury/odds payload provided; structure_matches is schedule context only. "
                "Return strict JSON only. Write all user-facing analysis in Simplified Chinese."
            ),
        },
        {
            "role": "user",
            "content": (
                "Analyze every verified match in research_payload.matches and return JSON with this exact shape. Use research_payload.structure_matches only as real schedule context for tournament_structure; do not create predictions for structure context matches outside research_payload.matches: "
                "{"
                "\"generated_at\":\"ISO-8601\","
                "\"summary\":\"Chinese summary\","
                "\"matches\":[{"
                "\"match_id\":\"string\","
                "\"match_name\":\"Chinese home vs away\","
                "\"kickoff_utc\":\"ISO-8601\","
                "\"teams\":{\"home\":{\"name\":\"Chinese\",\"name_en\":\"English\"},"
                "\"away\":{\"name\":\"Chinese\",\"name_en\":\"English\"}},"
                "\"win_draw_loss\":{\"home_win\":0,\"draw\":0,\"away_win\":0},"
                "\"xg_prediction\":{\"home\":0.0,\"away\":0.0},"
                "\"predicted_score\":{\"home\":0,\"away\":0},"
                "\"score_options\":["
                "{\"score\":\"0-2\",\"rank\":1,\"reason\":\"Chinese concise reason\"},"
                "{\"score\":\"0-1\",\"rank\":2,\"reason\":\"Chinese concise reason\"},"
                "{\"score\":\"0-3\",\"rank\":3,\"reason\":\"Chinese concise reason\"}"
                "],"
                "\"method_factors\":{"
                "\"market_signal\":\"Chinese note or unavailable\","
                "\"fifa_rank_prior\":\"Chinese FIFA ranking or long-term strength prior; do not invent ranking numbers\","
                "\"recent_form\":\"Chinese recent form note\","
                "\"group_context\":\"Chinese group context note\","
                "\"injury_rotation\":\"Chinese injury and rotation note\","
                "\"weather_venue\":\"Chinese weather/venue note or unknown\","
                "\"tactical_key\":\"Chinese tactical key\","
                "\"uncertainty\":\"Chinese uncertainty note\""
                "},"
                "\"matchup_graph\":{"
                "\"nodes\":["
                "{\"id\":\"home_attack\",\"label\":\"主队进攻\",\"type\":\"team_phase\",\"side\":\"home\",\"weight\":0,\"note\":\"Chinese note\"},"
                "{\"id\":\"home_midfield\",\"label\":\"主队中场/转换\",\"type\":\"team_phase\",\"side\":\"home\",\"weight\":0,\"note\":\"Chinese note\"},"
                "{\"id\":\"home_defense\",\"label\":\"主队防守\",\"type\":\"team_phase\",\"side\":\"home\",\"weight\":0,\"note\":\"Chinese note\"},"
                "{\"id\":\"away_attack\",\"label\":\"客队进攻\",\"type\":\"team_phase\",\"side\":\"away\",\"weight\":0,\"note\":\"Chinese note\"},"
                "{\"id\":\"away_midfield\",\"label\":\"客队中场/转换\",\"type\":\"team_phase\",\"side\":\"away\",\"weight\":0,\"note\":\"Chinese note\"},"
                "{\"id\":\"away_defense\",\"label\":\"客队防守\",\"type\":\"team_phase\",\"side\":\"away\",\"weight\":0,\"note\":\"Chinese note\"}"
                "],"
                "\"edges\":["
                "{\"from\":\"home_attack\",\"to\":\"away_defense\",\"label\":\"Chinese key relation\",\"impact\":\"high\",\"direction\":\"home_to_away\",\"note\":\"Chinese note\"},"
                "{\"from\":\"away_attack\",\"to\":\"home_defense\",\"label\":\"Chinese key relation\",\"impact\":\"medium\",\"direction\":\"away_to_home\",\"note\":\"Chinese note\"},"
                "{\"from\":\"home_midfield\",\"to\":\"away_midfield\",\"label\":\"Chinese key relation\",\"impact\":\"low\",\"direction\":\"balanced\",\"note\":\"Chinese note\"}"
                "],"
                "\"summary\":\"Chinese graph summary\","
                "\"advantage_side\":\"home|away|balanced\","
                "\"key_battle\":\"Chinese key battle\","
                "\"risk_trigger\":\"Chinese risk trigger\""
                "},"
                "\"tactical_matchup\":\"Chinese tactical matchup\","
                "\"injury_adjustment\":{\"home\":\"Chinese note\",\"away\":\"Chinese note\",\"summary\":\"Chinese note\"},"
                "\"risk_analysis\":\"Chinese risk analysis\","
                "\"upset_probability\":0,"
                "\"odds_comparison\":{\"market_implied\":{\"home_win\":0,\"draw\":0,\"away_win\":0},"
                "\"model_edge\":{\"home_win\":0,\"draw\":0,\"away_win\":0},"
                "\"deviation_analysis\":\"Chinese odds deviation analysis\"},"
                "\"confidence\":\"low|medium|high\""
                "}],"
                "\"risk_overview\":\"Chinese risk overview\","
                "\"data_quality\":\"Chinese source quality note\""
                "}. Win/draw/loss probabilities must be percentages and sum exactly to 100 for every match. "
                "xG must be numeric. upset_probability is percentage 0-100. "
                "score_options must contain exactly three likely score results ranked 1, 2, and 3. "
                "Use predicted_score as the rank 1 score. Each score option must include only score, rank, and reason. "
                "Do not output, calculate, or mention score probabilities. "
                "method_factors must contain market_signal, fifa_rank_prior, recent_form, group_context, "
                "injury_rotation, weather_venue, tactical_key, and uncertainty. "
                "If FIFA ranking source is unavailable, do not invent ranking numbers; use a long-term strength prior note. "
                "If weather data has no reliable source in the payload, write unknown. "
                "Each match must include matchup_graph with at least six nodes: home attack, home midfield/transition, home defense, away attack, away midfield/transition, and away defense. "
                "Each matchup_graph must include at least three edges describing key matchup relations. "
                "Node weight must be a 0-100 relative analytical strength score, not a probability, win rate, matchup probability, or score probability. "
                "Edge impact must be high, medium, or low. advantage_side must be home, away, or balanced. "
                "Do not output or mention structure graph probability, matchup probability, duel probability, or score probability. "
                "Preserve match_id, kickoff_utc, stage, group, match_number, teams, and score_options so the deterministic renderer can build tournament_structure and score tabs. "
                "If injury status is unknown, say it is unknown; do not invent player names. "
                "If odds are unavailable, say odds are unavailable; do not invent market prices. "
                f"Verified Agent research payload:\n{json.dumps(research_payload, ensure_ascii=False)}"
            ),
        },
    ]


def match_id_of(match: dict[str, Any]) -> str:
    return str(match.get("match_id") or match.get("fixture_id") or match.get("id") or match.get("fifa_match_id") or "")


def merge_analysis_matches(analysis: dict[str, Any], research_payload: dict[str, Any]) -> list[dict[str, Any]]:
    source_matches: dict[str, dict[str, Any]] = {}
    for source_item in research_payload.get("matches", []) or []:
        if not isinstance(source_item, dict):
            continue
        for key in (match_id_of(source_item), str(source_item.get("id") or ""), str(source_item.get("fifa_match_id") or "")):
            if key:
                source_matches[key] = source_item
    analyzed = analysis.get("matches")
    if not isinstance(analyzed, list):
        analyzed = analysis.get("predictions") if isinstance(analysis.get("predictions"), list) else []
    merged: list[dict[str, Any]] = []
    for item in analyzed:
        if not isinstance(item, dict):
            continue
        match_id = match_id_of(item)
        source = source_matches.get(match_id, {})
        merged_item = {**source, **item}
        merged_item["match_id"] = match_id or str(source.get("id") or "")
        if source:
            merged_item.setdefault("match_name", source.get("match_name"))
            merged_item.setdefault("kickoff_utc", source.get("kickoff_utc"))
            merged_item["teams"] = merge_match_teams(source.get("teams"), item.get("teams"))
            merged_item["injuries"] = source.get("injuries", {})
            merged_item["odds"] = source.get("odds", {"available": False})
            merged_item["source_verification"] = source.get("source_verification", {})
            merged_item["sources"] = source.get("sources", {})
        merged.append(merged_item)
    return merged


def run_analysis(fixtures_path: Path = FIXTURES_PATH, output: Path = ANALYSIS_PATH) -> dict[str, Any]:
    research_payload = read_json(fixtures_path) if fixtures_path.exists() else run_research(fixtures_path)
    content, usage, _response = deepseek_chat(
        ANALYSIS_MODEL,
        analysis_messages(research_payload),
        json_object=True,
        analysis_layer=True,
    )
    analysis = parse_json_content(content)
    matches = merge_analysis_matches(analysis, research_payload)
    analysis["matches"] = matches
    tournament_structure = build_tournament_structure(
        matches,
        research_payload.get("display_window", {}),
        research_payload.get("structure_matches", []),
        research_payload.get("structure_window", {}),
    )
    analysis["tournament_structure"] = tournament_structure
    payload = {
        "schema_version": 3,
        "stage": "analysis",
        "generated_at": iso_utc(utc_now()),
        "analysis": analysis,
        "matches": matches,
        "tournament_structure": tournament_structure,
        "structure_window": research_payload.get("structure_window", {}),
        "research": research_payload,
        "display_window": research_payload.get("display_window", {}),
        "china_match_days": research_payload.get("china_match_days", []),
        "usage": usage,
        "analysis_model": ANALYSIS_MODEL,
        "model": {"analysis_model": ANALYSIS_MODEL},
        "data_sources": research_payload.get("data_sources", {}),
        "daily_log": [
            *research_payload.get("daily_log", []),
            {"time": iso_utc(utc_now()), "stage": "08:30 deepseek-v4-pro analysis", "status": "completed"},
        ],
    }
    write_json(output, payload)
    return payload

def render_messages(analysis_payload: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are the GitHub Pages generation layer for the FIFA World Cup AI Agent. "
                "Use deepseek-v4-flash. Convert the supplied analysis JSON into one complete responsive HTML file. "
                "Return raw HTML only, starting with <!doctype html>. Do not wrap HTML in JSON or markdown fences. "
                "All visible UI text must be Simplified Chinese."
            ),
        },
        {
            "role": "user",
            "content": (
                "Generate complete HTML for GitHub Pages. The page must visibly include: "
                "match predictions, win/draw/loss probabilities, predicted score, xG, tactical matchup, "
                "front-three score tabs without score probabilities, method factors, matchup graph, tournament structure graph, risk analysis, upset probability, "
                "injury information, odds comparison, token usage, and cost. "
                "All visible match times must use Asia/Shanghai, never UTC. "
                "Group main match cards by China match day, where each match day runs from 18:00 to next-day 18:00. Render tournament_structure as 小组对战结构图 or 淘汰赛对阵树 with current-window highlights and score tabs. "
                "Use these exact placeholders inside the token panel: "
                "{{INPUT_TOKENS}}, {{OUTPUT_TOKENS}}, {{TOTAL_TOKENS}}, {{COST_ESTIMATE}}. "
                "Do not invent data. If source data says unknown or unavailable, display that clearly. "
                "Do not display or mention score probability, matchup probability, duel probability, or structure graph probability. "
                f"Analysis payload:\n{json.dumps(analysis_payload, ensure_ascii=False)}"
            ),
        },
    ]


def extract_html(raw_content: str) -> str:
    page = raw_content.strip()
    if page.startswith("```"):
        page = re.sub(r"^```(?:html)?\s*", "", page)
        page = re.sub(r"\s*```$", "", page).strip()
    if "<html" in page.lower():
        return page
    raise RuntimeError("DeepSeek V4-Flash render response did not contain HTML")


def inject_usage(page: str, usage: dict[str, Any]) -> str:
    replacements = {
        "{{INPUT_TOKENS}}": str(usage["input_tokens"]),
        "{{OUTPUT_TOKENS}}": str(usage["output_tokens"]),
        "{{TOTAL_TOKENS}}": str(usage["total_tokens"]),
        "{{COST_ESTIMATE}}": f"{usage['cost_estimate']:.6f}",
    }
    for marker, value in replacements.items():
        page = page.replace(marker, value)
    return page


def render_probability_line(probabilities: dict[str, Any] | None) -> str:
    if not probabilities:
        return "\u4e0d\u53ef\u7528"
    return (
        f"\u4e3b\u80dc {probabilities.get('home_win', 0)}% / "
        f"\u5e73 {probabilities.get('draw', 0)}% / "
        f"\u5ba2\u80dc {probabilities.get('away_win', 0)}%"
    )


def pct(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    if number.is_integer():
        return f"{int(number)}%"
    return f"{number:.1f}%"


def number_text(value: Any, digits: int = 2) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "0.00"


def status_text(value: str | None) -> str:
    mapping = {
        "confirmed injury": "\u5b98\u65b9\u786e\u8ba4\u4f24\u505c",
        "probable injury": "\u5a92\u4f53\u4f24\u505c\u7ebf\u7d22",
        "unknown": "unknown",
    }
    return mapping.get(value or "unknown", value or "unknown")


def confidence_text(value: str | None) -> str:
    return {"low": "\u4f4e", "medium": "\u4e2d", "high": "\u9ad8"}.get(value or "", value or "unknown")


def html_escape(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def placeholder_team_node(team: dict[str, Any] | None) -> bool:
    team = team or {}
    if team.get("placeholder"):
        return True
    value = str(team.get("name") or team.get("name_en") or "")
    normalized = normalize_team(value)
    return not value.strip() or normalized in {"tbd", "to be determined", "unknown", "none", "null"} or normalized.startswith("group ") or value.startswith("胜者") or value == "待定" or "组第" in value


def flag_url(team: dict[str, Any]) -> str | None:
    raw = team.get("flag_url") or team.get("logo")
    if not raw:
        return None
    return clean_asset_url(raw)


def team_flag_html(team: dict[str, Any], *, small: bool = False) -> str:
    classes = "team-flag small" if small else "team-flag"
    if placeholder_team_node(team):
        return f'<span class="{classes} placeholder" aria-hidden="true"></span>'
    name = html_escape(team.get("name") or team.get("name_en") or "Unknown")
    logo = flag_url(team)
    if logo:
        return f'<img class="{classes}" src="{html_escape(logo)}" alt="{name} 国旗" loading="lazy">'
    emoji = team.get("flag_emoji")
    if emoji:
        return f'<span class="{classes} emoji" role="img" aria-label="{name} 国旗">{html_escape(emoji)}</span>'
    return f'<span class="{classes} placeholder" aria-hidden="true"></span>'


def team_inline_html(team: dict[str, Any], *, reverse: bool = False, small: bool = False) -> str:
    name = html_escape(team.get("name") or team.get("name_en") or "Unknown")
    flag = team_flag_html(team, small=small)
    reverse_class = " reverse" if reverse else ""
    return f'<span class="team-inline{reverse_class}">{flag}<span>{name}</span></span>'


def team_visual(team: dict[str, Any], *, right: bool = False) -> str:
    content = team_inline_html(team, reverse=right)
    if right:
        return f'<div class="team right">{content}</div>'
    return f'<div class="team">{content}</div>'


def enrich_matches_for_display(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for match in matches:
        item = dict(match)
        kickoff = item.get("kickoff_utc")
        if kickoff:
            local = to_shanghai(kickoff)
            item["kickoff_beijing"] = local.isoformat()
            item["kickoff_display"] = format_beijing_time(kickoff)
            item["match_day"] = match_day_info(kickoff)
        enriched.append(item)
    enriched.sort(key=lambda item: item.get("kickoff_beijing") or "")
    return enriched


def group_matches_by_china_day(matches: list[dict[str, Any]]) -> list[tuple[dict[str, str], list[dict[str, Any]]]]:
    groups: dict[str, tuple[dict[str, str], list[dict[str, Any]]]] = {}
    for match in matches:
        info = match.get("match_day") or match_day_info(match.get("kickoff_utc"))
        key = info["date"]
        if key not in groups:
            groups[key] = (info, [])
        groups[key][1].append(match)
    ordered = []
    for key in sorted(groups):
        info, items = groups[key]
        items.sort(key=lambda item: item.get("kickoff_beijing") or "")
        ordered.append((info, items))
    return ordered


def venue_text(match: dict[str, Any]) -> str:
    venue = match.get("venue") or {}
    parts = [venue.get("name"), venue.get("city"), venue.get("country")]
    return " - ".join(str(part) for part in parts if part)


def source_link(match: dict[str, Any]) -> str:
    sources = match.get("sources") or {}
    espn = sources.get("espn") or {}
    fifa = sources.get("fifa") or {}
    return str(espn.get("event_url") or fifa.get("url") or "#")


def probability_number(value: Any) -> float:
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def percent_width(value: Any) -> str:
    return f"{probability_number(value):.3f}%"


def probability_segments(match: dict[str, Any]) -> str:
    probs = match.get("win_draw_loss") or {}
    home_win = probability_number(probs.get("home_win"))
    draw = probability_number(probs.get("draw"))
    away_win = probability_number(probs.get("away_win"))
    return f"""
      <div class="prob-heading">主胜 / 平 / 客胜概率</div>
      <div class="prob-labels">
        <span><i class="dot home"></i>主胜 {pct(home_win)}</span>
        <span><i class="dot draw"></i>平局 {pct(draw)}</span>
        <span><i class="dot away"></i>客胜 {pct(away_win)}</span>
      </div>
      <div class="prob-stack" aria-hidden="true">
        <span class="seg home" style="width:{percent_width(home_win)}"></span>
        <span class="seg draw" style="width:{percent_width(draw)}"></span>
        <span class="seg away" style="width:{percent_width(away_win)}"></span>
      </div>
      <div class="prob-values">
        <span>{pct(home_win)}</span>
        <span>{pct(draw)}</span>
        <span>{pct(away_win)}</span>
      </div>
    """


def injury_summary(match: dict[str, Any]) -> str:
    injuries = match.get("injuries") or {}
    home = injuries.get("home") or {}
    away = injuries.get("away") or {}
    return (
        f"\u4e3b\u961f: {status_text(home.get('status'))}; "
        f"\u5ba2\u961f: {status_text(away.get('status'))}"
    )


def odds_summary(match: dict[str, Any]) -> str:
    odds = match.get("odds") or {}
    if not odds.get("available"):
        return "\u771f\u5b9e\u8d54\u7387\u6e90\u672a\u63d0\u4f9b moneyline\uff0c\u663e\u793a unavailable\u3002"
    market = render_probability_line(odds.get("normalized_probability"))
    details = odds.get("details") or odds.get("provider") or "ESPN odds feed"
    comparison = match.get("odds_comparison") or {}
    deviation = comparison.get("deviation_analysis") or ""
    return f"{details}: {market}. {deviation}".strip()


def compact_note(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(str(part) for part in value.values() if part)
    return str(value or "")


def odds_badge(match: dict[str, Any]) -> str:
    odds = match.get("odds") or {}
    if not odds.get("available"):
        return "unavailable"
    return render_probability_line(odds.get("normalized_probability"))


def confidence_class(value: str | None) -> str:
    return {"low": "low", "medium": "medium", "high": "high"}.get(value or "", "unknown")


def display_window_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    for candidate in (payload, payload.get("research") or {}):
        window = candidate.get("display_window") if isinstance(candidate, dict) else None
        if isinstance(window, dict) and window.get("match_days"):
            return window
    return {}


def match_days_from_payload(payload: dict[str, Any], matches: list[dict[str, Any]]) -> list[dict[str, str]]:
    window = display_window_from_payload(payload)
    days = window.get("match_days") or payload.get("china_match_days")
    if not days and isinstance(payload.get("research"), dict):
        days = (payload["research"].get("display_window") or {}).get("match_days") or payload["research"].get("china_match_days")
    if isinstance(days, list) and all(isinstance(day, dict) for day in days):
        return days
    return [info for info, _items in group_matches_by_china_day(matches)]


def group_matches_for_expected_days(
    payload: dict[str, Any],
    matches: list[dict[str, Any]],
) -> list[tuple[dict[str, str], list[dict[str, Any]]]]:
    grouped = {info["date"]: (info, items) for info, items in group_matches_by_china_day(matches)}
    expected_days = match_days_from_payload(payload, matches)
    sections: list[tuple[dict[str, str], list[dict[str, Any]]]] = []
    used: set[str] = set()
    for info in expected_days:
        key = info.get("date")
        if not key:
            continue
        _existing_info, items = grouped.get(key, (info, []))
        sections.append((info, items))
        used.add(key)
    for key in sorted(grouped):
        if key not in used:
            sections.append(grouped[key])
    return sections


def display_range_text(payload: dict[str, Any], matches: list[dict[str, Any]]) -> str:
    window = display_window_from_payload(payload)
    if window:
        return f"{window.get('display_range', '')} · {window.get('range', '')}".strip(" ·")
    days = match_days_from_payload(payload, matches)
    if days:
        return f"{days[0].get('title', '')} - {days[-1].get('title', '')}"
    return "两个中国比赛日"


def safe_dom_id(value: Any) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value or "")).strip("-")
    return text or stable_id(value)


def ordered_score_options(match_or_options: Any) -> list[dict[str, Any]]:
    raw_options = match_or_options.get("score_options") if isinstance(match_or_options, dict) else match_or_options
    options = [item for item in (raw_options or []) if isinstance(item, dict)]

    def rank_key(item: dict[str, Any]) -> int:
        try:
            return int(item.get("rank", 99))
        except (TypeError, ValueError):
            return 99

    options.sort(key=rank_key)
    return options[:3]


def score_option_label(rank: Any) -> str:
    try:
        rank_number = int(rank)
    except (TypeError, ValueError):
        rank_number = 0
    return "主推荐" if rank_number == 1 else f"Top {rank_number or '?'}"


def group_label_for_match(match: dict[str, Any]) -> str:
    group = str(match.get("group") or "").strip()
    stage = str(match.get("stage") or "").strip()
    match = re.fullmatch(r"Group\s+([A-Za-z])", group, flags=re.IGNORECASE)
    if match:
        return f"{match.group(1).upper()}组"
    if group:
        return group
    return stage or "未分组"


def group_sort_key(name: str) -> tuple[int, str]:
    match = re.match(r"([A-Z])组", name)
    if match:
        return (0, match.group(1))
    match = re.match(r"Group\s+([A-Z])", name, flags=re.IGNORECASE)
    if match:
        return (0, match.group(1).upper())
    return (1, name)


def stage_text(match: dict[str, Any]) -> str:
    keys = (
        "round_key",
        "round_name",
        "stage_name",
        "stage",
        "phase",
        "group",
        "competition",
        "match_name",
        "match_number",
    )
    return " ".join(str(match.get(key) or "") for key in keys)


def match_number_int(match: dict[str, Any]) -> int | None:
    value = match.get("match_number")
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        found = re.search(r"\d+", str(value))
        return int(found.group(0)) if found else None


def is_third_place_match(match: dict[str, Any]) -> bool:
    number = match_number_int(match)
    if number in THIRD_PLACE_MATCH_NUMBERS:
        return True
    text = normalize_team(stage_text(match))
    raw = stage_text(match)
    return any(fragment in text for fragment in ("third place", "3rd place", "bronze")) or "季军" in raw


def is_knockout_match(match: dict[str, Any]) -> bool:
    text = normalize_team(stage_text(match))
    knockout_hints = (
        "knockout",
        "round of",
        "round 32",
        "round 16",
        "last 32",
        "last 16",
        "quarter final",
        "quarterfinal",
        "semi final",
        "semifinal",
        "final",
        "third place",
    )
    chinese_text = stage_text(match)
    chinese_hints = ("淘汰", "32强", "16强", "八分之一", "四分之一", "半决赛", "决赛", "季军")
    if any(hint in text for hint in knockout_hints) or any(hint in chinese_text for hint in chinese_hints):
        if "first stage" not in text and "group stage" not in text:
            return True
    number = match_number_int(match)
    return bool(number and number >= 73)


def determine_tournament_stage(matches: list[dict[str, Any]]) -> str:
    return "knockout" if any(is_knockout_match(match) for match in matches) else "group"


def round_key_for_match(match: dict[str, Any]) -> str:
    explicit = str(match.get("round_key") or "")
    if explicit in BRACKET_ROUND_ORDER:
        return explicit
    if is_third_place_match(match):
        return "third_place"
    raw_text = stage_text(match)
    text = normalize_team(raw_text)
    if re.search(r"round\s+of\s+32|round\s*32|last\s*32", text) or "32强" in raw_text:
        return "round_of_32"
    if re.search(r"round\s+of\s+16|round\s*16|last\s*16", text) or "16强" in raw_text or "八分之一" in raw_text:
        return "round_of_16"
    if "quarter final" in text or "quarterfinal" in text or "四分之一" in raw_text or "8强" in raw_text:
        return "quarter_finals"
    if "semi final" in text or "semifinal" in text or "半决赛" in raw_text or "4强" in raw_text:
        return "semi_finals"
    if "final" in text or "决赛" in raw_text:
        return "final"
    number = match_number_int(match)
    if number is None:
        return "round_of_32"
    if 73 <= number <= 88:
        return "round_of_32"
    if 89 <= number <= 96:
        return "round_of_16"
    if 97 <= number <= 100:
        return "quarter_finals"
    if 101 <= number <= 102:
        return "semi_finals"
    if number == 104:
        return "final"
    if number == 103:
        return "third_place"
    return "round_of_32"


def placeholder_team(label: str) -> dict[str, Any]:
    return {
        "name": label,
        "name_en": label,
        "country_code": "",
        "flag_url": "",
        "flag_emoji": "",
        "placeholder": True,
    }


def unresolved_team_label(team: dict[str, Any]) -> bool:
    value = normalize_team(str(team.get("name_en") or team.get("name") or ""))
    return not value or value in {"tbd", "to be determined", "unknown", "none", "null", "dai ding"} or value.startswith("winner") or value.startswith("loser") or "待定" in str(team.get("name") or "") or "胜者" in str(team.get("name") or "")


def bracket_placeholder_node(match_number: int, round_key: str) -> dict[str, Any]:
    feeds = BRACKET_WINNER_FEEDS.get(match_number)
    if feeds:
        home_label = f"胜者 M{feeds[0]}"
        away_label = f"胜者 M{feeds[1]}"
    else:
        home_label = "待定"
        away_label = "待定"
    return {
        "match_id": f"placeholder-M{match_number}",
        "match_number": match_number,
        "round_key": round_key,
        "stage": round_key,
        "group": "淘汰赛",
        "match_name": f"{home_label} vs {away_label}",
        "teams": {"home": placeholder_team(home_label), "away": placeholder_team(away_label)},
        "kickoff_utc": None,
        "kickoff_beijing": None,
        "kickoff_display": "北京时间 待定",
        "match_day": {},
        "win_draw_loss": None,
        "score_options": [],
        "current_window": False,
        "placeholder": True,
    }


def bracket_sort_key(match: dict[str, Any]) -> tuple[int, str, str]:
    number = match_number_int(match)
    return (number if number is not None else 9999, str(match.get("kickoff_beijing") or match.get("kickoff_utc") or ""), match_id_of(match))


def build_knockout_bracket(
    context_matches: list[dict[str, Any]],
    current_by_id: dict[str, dict[str, Any]],
    highlight_ids: set[str],
) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, dict[int, dict[str, Any]]] = {key: {} for key in BRACKET_ROUND_ORDER}
    overflow: dict[str, list[dict[str, Any]]] = {key: [] for key in BRACKET_ROUND_ORDER}
    for match in sorted(context_matches, key=bracket_sort_key):
        if not is_knockout_match(match) or is_third_place_match(match):
            continue
        key = round_key_for_match(match)
        if key not in BRACKET_ROUND_ORDER:
            continue
        node = structure_match_node(match, current_by_id, highlight_ids)
        node["round_key"] = key
        node["placeholder"] = False
        number = match_number_int(node)
        expected_numbers = set(BRACKET_MATCH_NUMBERS[key])
        if number in expected_numbers:
            existing = buckets[key].get(number)
            if existing is None or node.get("current_window") or not existing.get("current_window"):
                buckets[key][number] = node
        else:
            overflow[key].append(node)

    bracket: dict[str, list[dict[str, Any]]] = {key: [] for key in BRACKET_ROUND_ORDER}
    for key in BRACKET_ROUND_ORDER:
        spill = list(overflow[key])
        for slot_number in BRACKET_MATCH_NUMBERS[key]:
            node = buckets[key].get(slot_number)
            if node is None and spill:
                node = spill.pop(0)
                node["match_number"] = node.get("match_number") or slot_number
                node["round_key"] = key
            if node is None:
                node = bracket_placeholder_node(slot_number, key)
            bracket[key].append(node)
    return bracket


def merge_structure_context(
    matches: list[dict[str, Any]],
    structure_matches: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for match in structure_matches or []:
        match_id = match_id_of(match)
        if match_id:
            by_id[match_id] = dict(match)
    for match in matches:
        match_id = match_id_of(match)
        if not match_id:
            continue
        by_id[match_id] = {**by_id.get(match_id, {}), **match}
    return enrich_matches_for_display(list(by_id.values()))


def structure_match_node(
    match: dict[str, Any],
    current_by_id: dict[str, dict[str, Any]],
    highlight_ids: set[str],
) -> dict[str, Any]:
    match_id = match_id_of(match)
    source = {**match, **current_by_id.get(match_id, {})}
    source["teams"] = merge_match_teams(match.get("teams"), (current_by_id.get(match_id, {}) or {}).get("teams"))
    teams = source.get("teams") or {}
    kickoff = source.get("kickoff_utc")
    match_day = source.get("match_day") or (match_day_info(kickoff) if kickoff else {})
    is_current = match_id in highlight_ids
    key = round_key_for_match(source)
    return {
        "match_id": match_id,
        "match_number": source.get("match_number"),
        "round_key": key if key in BRACKET_ROUND_ORDER else None,
        "stage": source.get("stage"),
        "stage_name": source.get("stage_name") or source.get("stage"),
        "round_name": source.get("round_name"),
        "phase": source.get("phase"),
        "group": group_label_for_match(source),
        "match_name": source.get("match_name") or f"{(teams.get('home') or {}).get('name', '待定')} vs {(teams.get('away') or {}).get('name', '待定')}",
        "teams": teams,
        "kickoff_utc": kickoff,
        "kickoff_beijing": source.get("kickoff_beijing"),
        "kickoff_display": source.get("kickoff_display") or (format_beijing_time(kickoff) if kickoff else "北京时间 待定"),
        "match_day": match_day,
        "win_draw_loss": source.get("win_draw_loss") if is_current else None,
        "score_options": ordered_score_options(source) if is_current else [],
        "current_window": is_current,
        "placeholder": False,
    }


def build_tournament_structure(
    matches: list[dict[str, Any]],
    display_window: dict[str, Any] | None,
    structure_matches: list[dict[str, Any]] | None = None,
    structure_window: dict[str, Any] | None = None,
) -> dict[str, Any]:
    display_window = display_window or {}
    current_matches = enrich_matches_for_display(matches)
    context_matches = merge_structure_context(current_matches, structure_matches)
    stage_basis = current_matches or context_matches
    stage = determine_tournament_stage(stage_basis)
    highlight_ids = {match_id_of(match) for match in current_matches if match_id_of(match)}
    current_by_id = {match_id_of(match): match for match in current_matches if match_id_of(match)}
    focus_window = {
        "timezone": "Asia/Shanghai",
        "china_match_days": display_window.get("match_days") or [],
    }
    structure = {
        "stage": stage,
        "focus_window": focus_window,
        "highlight_match_ids": sorted(highlight_ids),
        "groups": None,
        "bracket": None,
        "structure_window": structure_window or {},
    }
    if stage == "group":
        group_map: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for match in [item for item in context_matches if not is_knockout_match(item)]:
            node = structure_match_node(match, current_by_id, highlight_ids)
            group_name = node.get("group") or "未分组"
            day = node.get("match_day") or {}
            day_key = day.get("date") or "unknown"
            group_map.setdefault(group_name, {}).setdefault(day_key, []).append(node)
        groups = []
        for group_name in sorted(group_map, key=group_sort_key):
            day_sections = []
            for day_key in sorted(group_map[group_name]):
                nodes = sorted(group_map[group_name][day_key], key=lambda item: item.get("kickoff_beijing") or item.get("kickoff_utc") or "")
                first_day = nodes[0].get("match_day") or {"date": day_key, "title": day_key, "range": ""}
                day_sections.append({
                    "date": first_day.get("date", day_key),
                    "title": first_day.get("title", day_key),
                    "range": first_day.get("range", ""),
                    "matches": nodes,
                })
            groups.append({"name": group_name, "match_days": day_sections})
        structure["groups"] = groups
    else:
        structure["bracket"] = build_knockout_bracket(context_matches, current_by_id, highlight_ids)
    return structure


def mini_score_tabs_html(options: list[dict[str, Any]]) -> str:
    ordered = ordered_score_options(options)
    if len(ordered) < 3:
        return '<div class="mini-score-wrap unavailable"><span>前3预测比分</span><em>当前窗口外不展开</em></div>'
    tabs = []
    for option in ordered:
        rank = option.get("rank")
        try:
            rank_number = int(rank)
        except (TypeError, ValueError):
            rank_number = len(tabs) + 1
        active = " active" if rank_number == 1 else ""
        tabs.append(
            '<span class="mini-score-tab{active}">{label} <b>{score}</b></span>'.format(
                active=active,
                label=html_escape(score_option_label(rank_number)),
                score=html_escape(option.get("score", "unknown")),
            )
        )
    return f'<div class="mini-score-wrap"><span>前3预测比分</span><div class="mini-score-tabs">{"".join(tabs)}</div></div>'


def structure_wdl_text(node: dict[str, Any]) -> str:
    wdl = node.get("win_draw_loss")
    if isinstance(wdl, dict):
        return render_probability_line(wdl)
    return "当前窗口外未生成分析"


def structure_match_node_html(node: dict[str, Any]) -> str:
    teams = node.get("teams") or {}
    home = teams.get("home") or {}
    away = teams.get("away") or {}
    home_name = home.get("name") or home.get("name_en") or "待定"
    away_name = away.get("name") or away.get("name_en") or "待定"
    current = bool(node.get("current_window"))
    classes = "structure-match-node current-window" if current else "structure-match-node"
    badge = '<span class="window-badge">当前窗口</span>' if current else '<span class="outside-badge">结构上下文</span>'
    return f"""
      <article class="{classes}" data-match-id="{html_escape(node.get('match_id', ''))}">
        <div class="structure-node-head"><span>{html_escape(node.get('group') or node.get('stage') or '未分组')}</span>{badge}</div>
        <strong>{html_escape(home_name)} vs {html_escape(away_name)}</strong>
        <p>{html_escape(node.get('kickoff_display', '北京时间 待定'))} · 比赛 ID: {html_escape(node.get('match_id') or 'unknown')}</p>
        <p class="structure-wdl">胜平负摘要：{html_escape(structure_wdl_text(node))}</p>
        {mini_score_tabs_html(node.get('score_options') or [])}
      </article>
    """


def group_structure_html(structure: dict[str, Any]) -> str:
    group_sections = []
    for group in structure.get("groups") or []:
        day_sections = []
        for day in group.get("match_days") or []:
            nodes = "".join(structure_match_node_html(node) for node in day.get("matches") or [])
            if not nodes:
                nodes = '<div class="structure-empty">该比赛日暂无双源校验赛程。</div>'
            day_sections.append(
                f"""
          <section class="structure-day">
            <h4>{html_escape(day.get('title', '比赛日'))}</h4>
            <p class="muted compact">{html_escape(day.get('range', ''))}</p>
            <div class="structure-node-grid">{nodes}</div>
          </section>
                """
            )
        group_sections.append(
            f"""
        <details class="structure-group" open>
          <summary>{html_escape(group.get('name', '未分组'))}</summary>
          {''.join(day_sections)}
        </details>
            """
        )
    if not group_sections:
        group_sections.append('<div class="structure-empty">暂无可用于小组结构图的双源校验赛程。</div>')
    return "".join(group_sections)


def bracket_match_number(node: dict[str, Any]) -> str:
    value = node.get("match_number") or node.get("match_no")
    if value not in (None, ""):
        text = str(value).strip()
        return text if text.upper().startswith("M") else f"M{text}"
    match_id = str(node.get("match_id") or "").strip()
    if match_id and match_id.isdigit() and len(match_id) <= 4:
        return f"M{match_id}"
    return "M--"


def bracket_team_label(entity: dict[str, Any] | str | None) -> str:
    if isinstance(entity, dict):
        raw = entity.get("name") or entity.get("name_en") or entity.get("short_name") or ""
    else:
        raw = entity or ""
    value = str(raw).strip()
    if not value:
        return "待定"
    lowered = value.lower()
    if lowered in {"tbd", "to be determined", "unknown", "none", "null", "待定"}:
        return "待定"
    winner = re.search(r"winner\s+(?:of\s+)?(?:match\s*)?(\d+)", value, re.I)
    if winner:
        return f"胜者 M{winner.group(1)}"
    loser = re.search(r"loser\s+(?:of\s+)?(?:match\s*)?(\d+)", value, re.I)
    if loser:
        return f"负者 M{loser.group(1)}"
    return team_name_zh(value)


def bracket_team_html(entity: dict[str, Any] | str | None) -> str:
    if isinstance(entity, dict):
        team = dict(entity)
        team["name"] = bracket_team_label(team)
    else:
        team = placeholder_team(bracket_team_label(entity))
    return team_inline_html(team, small=True)


def bracket_node_time(node: dict[str, Any]) -> str:
    text = str(node.get("kickoff_display") or "北京时间 待定")
    text = text.replace("北京时间 ", "")
    return text or "待定"


def bracket_wdl_html(node: dict[str, Any]) -> str:
    wdl = node.get("win_draw_loss")
    if not isinstance(wdl, dict):
        return '<div class="bracket-status">待定</div>'
    return "".join(
        [
            f'<span class="home">胜 {pct(wdl.get("home_win", 0))}</span>',
            f'<span class="draw">平 {pct(wdl.get("draw", 0))}</span>',
            f'<span class="away">负 {pct(wdl.get("away_win", 0))}</span>',
        ]
    )


def placeholder_bracket_node(match_number: int, home_label: str, away_label: str, round_key: str) -> dict[str, Any]:
    return {
        "match_id": f"placeholder-{round_key}-{match_number}",
        "match_number": match_number,
        "stage": round_key,
        "teams": {"home": {"name": home_label}, "away": {"name": away_label}},
        "kickoff_display": "北京时间 待定",
        "score_options": [],
        "current_window": False,
        "placeholder": True,
    }


def bracket_with_placeholders(bracket: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    order = ["round_of_32", "round_of_16", "quarter_finals", "semi_finals", "final"]
    display: dict[str, list[dict[str, Any]]] = {}
    for key in order:
        display[key] = [node for node in bracket.get(key, []) if isinstance(node, dict)]
    next_number = 57
    existing_numbers = []
    for nodes in display.values():
        for node in nodes:
            value = node.get("match_number")
            try:
                existing_numbers.append(int(value))
            except (TypeError, ValueError):
                continue
    if existing_numbers:
        next_number = max(existing_numbers) + 1
    for index, key in enumerate(order[1:], start=1):
        if display[key]:
            continue
        previous = display[order[index - 1]]
        if not previous:
            continue
        generated: list[dict[str, Any]] = []
        for pair_index in range(0, len(previous), 2):
            first = previous[pair_index]
            second = previous[pair_index + 1] if pair_index + 1 < len(previous) else None
            first_label = f"胜者 {bracket_match_number(first)}"
            second_label = f"胜者 {bracket_match_number(second)}" if second else "待定"
            generated.append(placeholder_bracket_node(next_number, first_label, second_label, key))
            next_number += 1
        display[key] = generated
    return display


def bracket_score_tabs_html(node: dict[str, Any]) -> str:
    options = ordered_score_options(node.get("score_options") or [])
    if len(options) < 3:
        return '<div class="bracket-node-divider"></div><div class="bracket-node-pending">待定</div>'
    return f'<div class="bracket-mini-title">前3预测比分</div>{mini_score_tabs_html(options)}'


def bracket_structure_node_html(node: dict[str, Any], round_key: str) -> str:
    teams = node.get("teams") or {}
    home_html = bracket_team_html(teams.get("home"))
    away_html = bracket_team_html(teams.get("away"))
    current = bool(node.get("current_window"))
    placeholder = bool(node.get("placeholder"))
    classes = ["bracket-node", f"round-{round_key}"]
    if current:
        classes.append("current-window")
    if placeholder:
        classes.append("placeholder")
    badge = '<span class="window-badge">当前窗口</span>' if current else ""
    match_no = bracket_match_number(node)
    return f"""
      <article class="{' '.join(classes)}" data-match-id="{html_escape(node.get('match_id', ''))}">
        <span class="bracket-match-number">{html_escape(match_no)}</span>
        <div class="bracket-node-card">
          <div class="bracket-node-top"><span>{html_escape(match_no)}</span>{badge}</div>
          <strong>{home_html}<em>vs</em>{away_html}</strong>
          <time>{html_escape(bracket_node_time(node))}</time>
          {bracket_score_tabs_html(node)}
          <div class="bracket-wdl-mini">{bracket_wdl_html(node)}</div>
        </div>
      </article>
    """


def bracket_structure_html(structure: dict[str, Any]) -> str:
    labels = {
        "round_of_32": "32强",
        "round_of_16": "16强",
        "quarter_finals": "8强",
        "semi_finals": "4强",
        "final": "决赛",
    }
    raw_bracket = structure.get("bracket") or {}
    bracket = bracket_with_placeholders(raw_bracket)
    rounds = []
    for key, label in labels.items():
        nodes = "".join(bracket_structure_node_html(node, key) for node in bracket.get(key, []) if isinstance(node, dict))
        if not nodes:
            nodes = '<div class="structure-empty">待定</div>'
        rounds.append(
            f"""
        <section class="bracket-round bracket-round-{key}">
          <h3>{label}</h3>
          <div class="bracket-node-list">{nodes}</div>
        </section>
            """
        )
    return f"""
      <div class="bracket-shell">
        <div class="bracket-stage-labels">{' '.join(f'<span>{label}</span>' for label in labels.values())}</div>
        <div class="bracket-board">
          <div class="bracket-grid">{''.join(rounds)}</div>
        </div>
        <div class="bracket-legend">
          <span><i class="dot home"></i>胜率高</span>
          <span><i class="dot draw"></i>平局倾向</span>
          <span><i class="dot away"></i>负率高</span>
          <span class="current-window-key">当前窗口：当前和下一个中国比赛日</span>
        </div>
      </div>
    """


def tournament_structure_html(payload: dict[str, Any]) -> str:
    structure = payload.get("tournament_structure")
    if not isinstance(structure, dict):
        structure = build_tournament_structure(
            payload.get("matches") or [],
            payload.get("display_window") or {},
            (payload.get("research") or {}).get("structure_matches") or payload.get("structure_matches"),
            (payload.get("research") or {}).get("structure_window") or payload.get("structure_window"),
        )
    stage = structure.get("stage")
    title = "淘汰赛对阵树" if stage == "knockout" else "小组对战结构图"
    body = bracket_structure_html(structure) if stage == "knockout" else group_structure_html(structure)
    highlight_count = len(structure.get("highlight_match_ids") or [])
    context_count = 0
    if stage == "knockout":
        context_count = sum(len(items or []) for items in (structure.get("bracket") or {}).values())
    else:
        for group in structure.get("groups") or []:
            for day in group.get("match_days") or []:
                context_count += len(day.get("matches") or [])
    return f"""
    <section class="tournament-panel night-card">
      <div class="structure-title-row">
        <div>
          <h2>{title}</h2>
          <p class="muted compact">结构图基于 FIFA 官方赛程与 ESPN 第二来源校验；当前两个中国比赛日内 {highlight_count} 场已高亮。</p>
        </div>
        <div class="structure-count">结构赛程 {context_count} 场</div>
      </div>
      {body}
    </section>
    """

METHOD_FACTOR_LABELS = (
    ("market_signal", "市场信号"),
    ("fifa_rank_prior", "FIFA 实力先验"),
    ("recent_form", "近期状态"),
    ("group_context", "小组形势"),
    ("injury_rotation", "伤停/轮换"),
    ("weather_venue", "天气/场地"),
    ("tactical_key", "战术关键"),
    ("uncertainty", "不确定性"),
)


def score_options_html(match: dict[str, Any]) -> str:
    options = ordered_score_options(match)
    match_id = safe_dom_id(match_id_of(match) or match.get("match_name") or stable_id(match))
    if not options:
        options = [{"score": "unknown", "rank": 1, "reason": "unknown"}]
    buttons = []
    panels = []
    for index, option in enumerate(options[:3]):
        rank = option.get("rank")
        try:
            rank_number = int(rank)
        except (TypeError, ValueError):
            rank_number = index + 1
        label = score_option_label(rank_number)
        active = " active" if index == 0 else ""
        tab_id = f"score-{match_id}-{rank_number}"
        buttons.append(
            '<button class="score-tab{active}" type="button" role="tab" aria-selected="{selected}" data-score-tab="{tab_id}">'
            '<span>{label}</span><strong>{score}</strong></button>'.format(
                active=active,
                selected="true" if index == 0 else "false",
                tab_id=html_escape(tab_id),
                label=html_escape(label),
                score=html_escape(option.get("score", "unknown")),
            )
        )
        panels.append(
            '<article class="score-tab-panel{active}" role="tabpanel" data-score-panel="{tab_id}">'
            '<h5>{label} · {score}</h5><p>{reason}</p></article>'.format(
                active=active,
                tab_id=html_escape(tab_id),
                label=html_escape(label),
                score=html_escape(option.get("score", "unknown")),
                reason=html_escape(option.get("reason", "unknown")),
            )
        )
    return f"""
        <section class="score-options" data-score-tabs>
          <h4>前3预测比分</h4>
          <div class="score-tab-labels" role="tablist">{''.join(buttons)}</div>
          <div class="score-tab-panels">{''.join(panels)}</div>
        </section>
    """

def method_factors_html(match: dict[str, Any]) -> str:
    factors = match.get("method_factors") or {}
    items = []
    for key, label in METHOD_FACTOR_LABELS:
        value = factors.get(key, "unknown") if isinstance(factors, dict) else "unknown"
        items.append(
            f"<section class=\"factor-item\"><h5>{html_escape(label)}</h5><p>{html_escape(value or 'unknown')}</p></section>"
        )
    return f"""
        <details class="factor-panel" open>
          <summary>分析因子</summary>
          <div class="factor-grid">{''.join(items)}</div>
        </details>
    """


def impact_text(value: str | None) -> str:
    return {"high": "高", "medium": "中", "low": "低"}.get(value or "", value or "unknown")


def advantage_text(value: str | None) -> str:
    return {"home": "主队", "away": "客队", "balanced": "均衡"}.get(value or "", value or "unknown")


def graph_weight(value: Any) -> str:
    try:
        number = max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        number = 0.0
    if number.is_integer():
        return str(int(number))
    return f"{number:.1f}"


def graph_nodes_html(nodes: list[Any], side: str) -> str:
    side_nodes = [node for node in nodes if isinstance(node, dict) and node.get("side") == side]
    if not side_nodes:
        side_nodes = [{"label": "unknown", "weight": 0, "note": "unknown"}]
    cards = []
    for node in side_nodes:
        cards.append(
            "<article class=\"graph-node {side}\">"
            "<div><strong>{label}</strong><span>强度 {weight}/100</span></div>"
            "<p>{note}</p>"
            "</article>".format(
                side=html_escape(side),
                label=html_escape(node.get("label", "unknown")),
                weight=graph_weight(node.get("weight")),
                note=html_escape(node.get("note", "unknown")),
            )
        )
    return "".join(cards)


def graph_edges_html(edges: list[Any]) -> str:
    valid_edges = [edge for edge in edges if isinstance(edge, dict)]
    if not valid_edges:
        valid_edges = [{"label": "unknown", "impact": "low", "direction": "unknown", "note": "unknown"}]
    cards = []
    for edge in valid_edges[:6]:
        impact = str(edge.get("impact", "low"))
        if impact not in {"high", "medium", "low"}:
            impact = "low"
        cards.append(
            "<article class=\"graph-edge impact-{impact}\">"
            "<div><strong>{label}</strong><span>{impact_text}</span></div>"
            "<p>{note}</p>"
            "<small>{source} → {target} · {direction}</small>"
            "</article>".format(
                impact=html_escape(impact),
                label=html_escape(edge.get("label", "unknown")),
                impact_text=html_escape(impact_text(impact)),
                note=html_escape(edge.get("note", "unknown")),
                source=html_escape(edge.get("from", "unknown")),
                target=html_escape(edge.get("to", "unknown")),
                direction=html_escape(edge.get("direction", "unknown")),
            )
        )
    return "".join(cards)


def matchup_graph_html(match: dict[str, Any]) -> str:
    graph = match.get("matchup_graph") or {}
    nodes = graph.get("nodes") if isinstance(graph, dict) else []
    edges = graph.get("edges") if isinstance(graph, dict) else []
    if not isinstance(nodes, list):
        nodes = []
    if not isinstance(edges, list):
        edges = []
    return f"""
        <details class="matchup-panel" open>
          <summary>对战结构图</summary>
          <div class="graph-summary-grid">
            <span><b>优势方</b>{html_escape(advantage_text(graph.get('advantage_side') if isinstance(graph, dict) else None))}</span>
            <span><b>关键对位</b>{html_escape(graph.get('key_battle', 'unknown') if isinstance(graph, dict) else 'unknown')}</span>
            <span><b>风险触发点</b>{html_escape(graph.get('risk_trigger', 'unknown') if isinstance(graph, dict) else 'unknown')}</span>
          </div>
          <p class="graph-summary">{html_escape(graph.get('summary', 'unknown') if isinstance(graph, dict) else 'unknown')}</p>
          <div class="graph-node-grid">
            <section><h5>主队结构</h5>{graph_nodes_html(nodes, 'home')}</section>
            <section><h5>客队结构</h5>{graph_nodes_html(nodes, 'away')}</section>
          </div>
          <div class="graph-edge-list">
            <h5>关键关系</h5>
            {graph_edges_html(edges)}
          </div>
        </details>
    """
def match_card(match: dict[str, Any]) -> str:
    teams = match.get("teams") or {}
    home = teams.get("home") or {}
    away = teams.get("away") or {}
    score = match.get("predicted_score") or {}
    xg = match.get("xg_prediction") or {}
    confidence = confidence_text(match.get("confidence"))
    kickoff_display = match.get("kickoff_display") or format_beijing_time(match.get("kickoff_utc"))
    kickoff_iso = html_escape(match.get("kickoff_beijing") or "")
    tactical = match.get("tactical_matchup") or match.get("tactical_analysis") or ""
    risk = match.get("risk_analysis") or ""
    injury_adjustment = compact_note(match.get("injury_adjustment"))
    upset = match.get("upset_probability", 0)
    venue = venue_text(match)
    source = source_link(match)
    match_id = match.get("match_id") or match.get("id") or match.get("fifa_match_id") or "unknown"
    home_name = home.get("name") or home.get("name_en") or "主队"
    away_name = away.get("name") or away.get("name_en") or "客队"
    home_inline = team_inline_html(home)
    away_inline = team_inline_html(away, reverse=True)
    confidence_raw = match.get("confidence")
    return f"""
      <article class="match-card">
        <div class="match-topline">
          <h3 class="match-title-teams">{home_inline}<span class="versus">vs</span>{team_inline_html(away)}</h3>
          <time datetime="{kickoff_iso}">{html_escape(kickoff_display)}</time>
        </div>
        <div class="scoreboard">
          <div class="score-side">
            <span class="score-team-name">{home_inline}</span>
            <strong>{html_escape(score.get("home", 0))}</strong>
          </div>
          <div class="score-separator">:</div>
          <div class="score-side away-side">
            <span class="score-team-name">{away_inline}</span>
            <strong>{html_escape(score.get("away", 0))}</strong>
          </div>
        </div>
        <div class="probability-panel">
          {probability_segments(match)}
        </div>
        <div class="metric-grid">
          <span><b>xG</b>{html_escape(home_name)} {number_text(xg.get("home"))}</span>
          <span><b>xG</b>{html_escape(away_name)} {number_text(xg.get("away"))}</span>
          <span><b>爆冷概率</b>{pct(upset)}</span>
          <span><b>赔率</b>{html_escape(odds_badge(match))}</span>
        </div>
        {score_options_html(match)}
        {matchup_graph_html(match)}
        {method_factors_html(match)}
        <div class="analysis-block">
          <section><h4>战术分析</h4><p>{html_escape(tactical)}</p></section>
          <section><h4>风险分析</h4><p class="risk-text">{html_escape(risk)}</p></section>
          <section><h4>伤停信息</h4><p>{html_escape(injury_summary(match))}</p><p class="muted compact">{html_escape(injury_adjustment)}</p></section>
          <section><h4>赔率对比</h4><p>{html_escape(odds_summary(match))}</p></section>
        </div>
        <div class="match-footer">
          <span>置信度 <b class="confidence {confidence_class(confidence_raw)}">{html_escape(confidence)}</b></span>
          <span>比赛 ID: {html_escape(match_id)}</span>
          <a class="source-link" href="{html_escape(source)}" rel="noopener" target="_blank">来源</a>
        </div>
        <p class="venue-line">{html_escape(venue)}</p>
      </article>
    """


def build_legacy_agent_html(payload: dict[str, Any]) -> str:
    matches = payload.get("matches") or []
    usage = payload.get("usage") or zero_usage()
    generated_display = format_beijing_time(payload.get("generated_at", iso_utc(utc_now())))
    groups = group_matches_for_expected_days(payload, matches)
    analysis = payload.get("analysis") or {}
    summary = analysis.get("summary") or "V3 Agent 使用 FIFA 官方赛程作为主源，ESPN 完成第二来源校验和赔率读取，伤停信息按官方/媒体/unknown 规则展示。"
    risk_overview = analysis.get("risk_overview") or "整体风险以赛程真实性、伤停可信度、赔率可用性和模型置信度共同评估。"
    range_text = display_range_text(payload, matches)
    structure = payload.get("tournament_structure") if isinstance(payload.get("tournament_structure"), dict) else {}
    stage_label = "淘汰赛" if structure.get("stage") == "knockout" else "小组赛"
    if structure.get("stage") == "knockout":
        structure_count = sum(len(items or []) for items in (structure.get("bracket") or {}).values())
    else:
        structure_count = 0
        for group in structure.get("groups") or []:
            for day in group.get("match_days") or []:
                structure_count += len(day.get("matches") or [])
    total_count_label = structure_count or len(matches)
    structure_section = tournament_structure_html(payload)
    group_sections = []
    for info, items in groups:
        cards = "\n".join(match_card(match) for match in items)
        if not cards:
            cards = '<div class="empty">该中国比赛日暂无通过 FIFA + ESPN 双源校验的世界杯比赛。</div>'
        group_sections.append(
            f"""
    <section class="match-day" data-match-day="{html_escape(info['date'])}">
      <div class="section-head">
        <div>
          <h2>{html_escape(info['title'])}</h2>
          <p class="muted compact">{html_escape(info['range'])}，按北京时间升序排列</p>
        </div>
        <div class="day-count">{len(items)} 场</div>
      </div>
      <section class="match-grid">{cards}</section>
    </section>
            """
        )
    if not group_sections:
        group_sections.append('<div class="empty">当前两个中国比赛日暂无双源验证的世界杯比赛。</div>')
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>2026 世界杯 · 预测分析</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #10111f;
      --bg-2: #141727;
      --panel: #1b2838;
      --panel-2: #202d3d;
      --panel-3: #172232;
      --line: rgba(104, 136, 174, 0.28);
      --line-hot: rgba(83, 171, 255, 0.58);
      --text: #f5f7fb;
      --muted: #a5afc1;
      --green: #2bd16f;
      --yellow: #f6bd27;
      --red: #ef5049;
      --blue: #66aaff;
      --pink: #f05b78;
      --shadow: 0 18px 48px rgba(0, 0, 0, 0.42);
    }}
    * {{ box-sizing: border-box; }}
    html {{ background: var(--bg); }}
    body {{
      margin: 0;
      font-family: Inter, "Microsoft YaHei", "PingFang SC", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at 50% -20%, rgba(32, 93, 156, 0.32), transparent 38%),
        linear-gradient(180deg, #171729 0%, #10111f 42%, #0c0f19 100%);
      letter-spacing: 0;
      min-height: 100vh;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image: linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px);
      background-size: 42px 42px;
      mask-image: linear-gradient(180deg, rgba(0,0,0,0.85), transparent 70%);
    }}
    a {{ color: var(--blue); text-decoration: none; font-weight: 700; transition: color .18s ease, text-shadow .18s ease; }}
    a:hover {{ color: #91c4ff; text-shadow: 0 0 16px rgba(102, 170, 255, .45); }}
    .page {{ width: min(1180px, calc(100% - 28px)); margin: 0 auto; padding: 22px 0 44px; }}
    .night-card {{
      position: relative;
      border: 1px solid rgba(0, 174, 255, .36);
      border-radius: 18px;
      background: linear-gradient(145deg, rgba(5, 18, 31, .96), rgba(10, 27, 43, .95));
      box-shadow: 0 22px 60px rgba(0, 0, 0, .52), inset 0 1px 0 rgba(255,255,255,.05);
      overflow: hidden;
    }}
    .night-card::before {{
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background:
        radial-gradient(circle at 91% 8%, rgba(0, 170, 255, .26), transparent 24%),
        linear-gradient(120deg, rgba(0, 174, 255, .12), transparent 40%, rgba(246, 189, 39, .05));
      opacity: .9;
    }}
    .hero {{
      padding: 20px 22px 18px;
      margin-bottom: 16px;
      border-color: rgba(0, 174, 255, .62);
      background: linear-gradient(140deg, rgba(3, 12, 23, .98), rgba(8, 35, 61, .94));
    }}
    .hero > * {{ position: relative; z-index: 1; }}
    .hero h1 {{ display: flex; align-items: center; gap: 14px; margin: 0 0 14px; font-size: clamp(28px, 4.2vw, 44px); line-height: 1.08; font-weight: 900; text-shadow: 0 0 22px rgba(0, 174, 255, .2); }}
    .hero-ball {{
      display: inline-grid;
      place-items: center;
      width: 54px;
      height: 54px;
      border-radius: 50%;
      border: 1px solid rgba(0, 217, 255, .62);
      background: radial-gradient(circle at 35% 30%, rgba(120, 235, 255, .95), rgba(0, 112, 205, .86) 52%, rgba(0, 27, 58, .96));
      box-shadow: 0 0 22px rgba(0, 217, 255, .42), inset 0 0 16px rgba(255,255,255,.16);
      font-size: 28px;
      flex: 0 0 auto;
    }}
    .range-pill {{
      display: inline-flex;
      align-items: center;
      max-width: 100%;
      min-height: 32px;
      padding: 0 14px;
      border-radius: 999px;
      background: rgba(246, 189, 39, .14);
      color: #ffdb54;
      border: 1px solid rgba(246, 189, 39, .34);
      font-weight: 850;
      overflow-wrap: anywhere;
    }}
    .hero-meta {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 0;
      margin: 16px 0 0;
      border: 1px solid rgba(104, 190, 255, .18);
      border-radius: 12px;
      background: rgba(2, 12, 23, .32);
      overflow: hidden;
    }}
    .hero-meta div {{ min-width: 0; padding: 15px 18px; color: var(--muted); line-height: 1.45; border-right: 1px solid rgba(104, 190, 255, .14); border-bottom: 1px solid rgba(104, 190, 255, .12); overflow-wrap: anywhere; }}
    .hero-meta div:nth-child(3n) {{ border-right: 0; }}
    .hero-meta div:nth-last-child(-n+3) {{ border-bottom: 0; }}
    .hero-meta strong {{ display: block; margin-top: 4px; color: var(--text); font-size: 18px; font-weight: 760; }}
    .hero-meta .meta-icon {{ color: #8feaff; margin-right: 7px; text-shadow: 0 0 12px rgba(0, 217, 255, .36); }}
    .overview {{
      padding: 24px;
      margin-bottom: 24px;
    }}
    .overview h2, .usage-panel h2, .match-day h2 {{ margin: 0; font-size: 24px; color: #ffd64a; }}
    .overview p {{ position: relative; z-index: 1; margin: 14px 0 0; color: var(--muted); line-height: 1.8; font-size: 16px; }}
    .usage-panel {{
      padding: 22px;
      margin-bottom: 24px;
      border-color: rgba(246, 189, 39, .24);
    }}
    .usage-grid {{
      position: relative;
      z-index: 1;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-top: 18px;
    }}
    .usage-card {{
      border: 1px solid var(--line);
      border-radius: 14px;
      background: rgba(24, 35, 51, .72);
      padding: 18px;
      min-height: 116px;
      transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
    }}
    .usage-card:hover {{ transform: translateY(-2px); border-color: var(--line-hot); box-shadow: 0 0 22px rgba(83, 171, 255, .14); }}
    .usage-card span {{ display: block; color: var(--muted); letter-spacing: .08em; font-size: 13px; margin-bottom: 14px; }}
    .usage-card strong {{ font-size: clamp(26px, 6vw, 36px); line-height: 1; overflow-wrap: anywhere; }}
    .usage-card.input strong {{ color: var(--blue); }}
    .usage-card.output strong {{ color: var(--green); }}
    .usage-card.total strong {{ color: #ffd64a; }}
    .usage-card.cost strong {{ color: var(--pink); }}
    .legend {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 14px 22px;
      padding: 18px 20px;
      margin-bottom: 28px;
    }}
    .legend span {{ position: relative; z-index: 1; color: var(--muted); font-weight: 700; }}
    .tournament-panel {{ padding: 16px; margin-bottom: 16px; border-color: rgba(0, 174, 255, .58); background: linear-gradient(145deg, rgba(2, 12, 23, .98), rgba(5, 25, 41, .96)); }}
    .structure-title-row {{ position: relative; z-index: 2; display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 14px; align-items: start; margin-bottom: 12px; }}
    .structure-title-row h2 {{ margin: 0 0 8px; font-size: 26px; color: #eaf8ff; text-shadow: 0 0 16px rgba(0, 217, 255, .26); }}
    .structure-title-row h2::before {{ content: "⌗"; color: #15d9ff; margin-right: 10px; }}
    .structure-count {{ border: 1px solid rgba(0, 217, 255, .42); border-radius: 999px; padding: 8px 14px; color: #9beeff; background: rgba(0, 174, 255, .11); font-weight: 850; white-space: nowrap; box-shadow: 0 0 18px rgba(0, 174, 255, .12); }}
    .structure-group {{ position: relative; z-index: 1; border: 1px solid rgba(104, 136, 174, .24); border-radius: 16px; background: rgba(12, 20, 31, .38); padding: 12px; margin-top: 12px; }}
    .structure-group summary {{ cursor: pointer; color: #ffd64a; font-size: 18px; font-weight: 850; list-style-position: inside; }}
    .structure-day {{ margin-top: 14px; border-top: 1px solid rgba(104, 136, 174, .18); padding-top: 12px; }}
    .structure-day h4 {{ margin: 0 0 6px; color: var(--text); font-size: 15px; }}
    .structure-node-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-top: 10px; }}
    .structure-match-node {{ border: 1px solid rgba(104, 136, 174, .24); border-radius: 15px; background: rgba(10, 18, 30, .58); padding: 12px; min-width: 0; transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease, background .18s ease; }}
    .structure-match-node:hover {{ transform: translateY(-2px); border-color: var(--line-hot); box-shadow: 0 0 20px rgba(83, 171, 255, .13); }}
    .structure-match-node.current-window {{ border-color: rgba(83, 217, 255, .72); box-shadow: 0 0 24px rgba(83, 217, 255, .16), inset 0 0 0 1px rgba(83, 217, 255, .1); background: linear-gradient(145deg, rgba(20, 42, 60, .8), rgba(10, 18, 30, .68)); }}
    .structure-node-head {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; color: var(--muted); font-size: 12px; font-weight: 850; margin-bottom: 8px; }}
    .window-badge, .outside-badge {{ border-radius: 999px; padding: 4px 8px; white-space: nowrap; }}
    .window-badge {{ color: #8df3ff; background: rgba(83, 217, 255, .14); border: 1px solid rgba(83, 217, 255, .34); }}
    .outside-badge {{ color: var(--muted); background: rgba(104, 136, 174, .1); border: 1px solid rgba(104, 136, 174, .18); }}
    .structure-match-node > strong {{ display: block; color: var(--text); font-size: 15px; line-height: 1.35; overflow-wrap: anywhere; }}
    .structure-match-node p {{ margin: 7px 0 0; color: var(--muted); font-size: 12px; line-height: 1.5; overflow-wrap: anywhere; }}
    .structure-wdl {{ color: #d8deea !important; }}
    .mini-score-wrap {{ margin-top: 10px; }}
    .mini-score-wrap > span {{ display: block; margin-bottom: 7px; color: #ffd64a; font-size: 12px; font-weight: 900; }}
    .mini-score-wrap em {{ color: var(--muted); font-style: normal; font-size: 12px; }}
    .mini-score-tabs {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .mini-score-tab {{ border: 1px solid rgba(83, 171, 255, .34); border-radius: 999px; padding: 6px 9px; color: #bed8f6; background: rgba(12, 20, 31, .72); font-size: 12px; font-weight: 850; }}
    .mini-score-tab.active {{ border-color: rgba(246, 189, 39, .65); color: #ffe184; background: rgba(246, 189, 39, .16); box-shadow: 0 0 14px rgba(246, 189, 39, .14); }}
    .bracket-shell {{ position: relative; z-index: 1; }}
    .bracket-stage-labels {{ display: none; }}
    .bracket-board {{ position: relative; overflow-x: auto; border: 1px solid rgba(104, 190, 255, .18); border-radius: 14px; background: linear-gradient(90deg, rgba(5, 20, 33, .82), rgba(1, 10, 19, .68)); box-shadow: inset 0 0 42px rgba(0, 174, 255, .07); }}
    .bracket-grid {{ position: relative; z-index: 1; display: grid; grid-template-columns: repeat(5, minmax(190px, 1fr)); gap: 18px; min-width: 1080px; padding: 14px 12px 18px; }}
    .bracket-round {{ position: relative; min-width: 190px; display: flex; flex-direction: column; border-left: 1px solid rgba(0, 174, 255, .14); padding-left: 10px; }}
    .bracket-round:first-child {{ border-left: 0; padding-left: 0; }}
    .bracket-round h3 {{ margin: 0 0 12px; color: #a8bbd4; font-size: 17px; font-weight: 780; text-align: center; }}
    .bracket-node-list {{ flex: 1; display: flex; flex-direction: column; gap: 12px; min-height: 860px; }}
    .bracket-round-round_of_16 .bracket-node-list, .bracket-round-quarter_finals .bracket-node-list, .bracket-round-semi_finals .bracket-node-list, .bracket-round-final .bracket-node-list {{ justify-content: space-around; }}
    .bracket-node {{ position: relative; min-height: 132px; padding-left: 34px; transition: transform .18s ease; }}
    .bracket-node:hover {{ transform: translateY(-2px); }}
    .bracket-node:not(.round-final)::after {{ content: ""; position: absolute; right: -18px; top: 50%; width: 18px; height: 2px; background: linear-gradient(90deg, rgba(0, 217, 255, .88), rgba(0, 217, 255, .2)); box-shadow: 0 0 12px rgba(0, 217, 255, .45); }}
    .bracket-match-number {{ position: absolute; left: 0; top: 50%; transform: translateY(-50%); color: #9fb5cf; font-size: 13px; font-weight: 850; }}
    .bracket-node-card {{ position: relative; min-height: 132px; border: 1px solid rgba(104, 190, 255, .42); border-radius: 10px; background: linear-gradient(180deg, rgba(8, 23, 38, .94), rgba(3, 14, 25, .92)); padding: 10px; box-shadow: inset 0 0 0 1px rgba(255,255,255,.02); transition: border-color .18s ease, box-shadow .18s ease, background .18s ease; }}
    .bracket-node:hover .bracket-node-card {{ border-color: rgba(0, 217, 255, .7); box-shadow: 0 0 18px rgba(0, 217, 255, .16), inset 0 0 0 1px rgba(255,255,255,.04); }}
    .bracket-node.current-window .bracket-node-card {{ border-color: #12dcff; background: linear-gradient(180deg, rgba(9, 44, 67, .96), rgba(3, 20, 34, .95)); box-shadow: 0 0 24px rgba(0, 217, 255, .48), inset 0 0 18px rgba(0, 217, 255, .1); }}
    .bracket-node.placeholder .bracket-node-card {{ border-color: rgba(104, 190, 255, .28); background: rgba(7, 20, 33, .68); }}
    .bracket-node-top {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; min-height: 22px; color: #91a8c2; font-size: 12px; font-weight: 850; }}
    .bracket-node-card strong {{ display: grid; gap: 3px; margin-top: 5px; color: #edf7ff; font-size: 16px; line-height: 1.22; text-align: center; overflow-wrap: anywhere; }}
    .bracket-node-card strong em {{ color: #9fb5cf; font-style: normal; font-size: 12px; font-weight: 700; }}
    .bracket-node-card strong .team-inline {{ justify-content: center; gap: 6px; }}
    .bracket-node-card time {{ display: block; margin-top: 5px; color: #a8bbd4; font-size: 13px; text-align: center; }}
    .bracket-mini-title {{ display: flex; align-items: center; gap: 8px; margin: 8px 0 6px; color: #a8bbd4; font-size: 12px; text-align: center; }}
    .bracket-mini-title::before, .bracket-mini-title::after {{ content: ""; flex: 1; height: 1px; background: rgba(104, 190, 255, .34); }}
    .bracket-node-card .mini-score-wrap {{ margin-top: 0; }}
    .bracket-node-card .mini-score-wrap > span {{ display: none; }}
    .bracket-node-card .mini-score-tabs {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 5px; }}
    .bracket-node-card .mini-score-tab {{ display: grid; place-items: center; min-height: 46px; border-radius: 7px; padding: 5px; text-align: center; font-size: 11px; line-height: 1.15; }}
    .bracket-node-card .mini-score-tab b {{ display: block; margin-top: 3px; color: #edf7ff; font-size: 18px; }}
    .bracket-node-card .mini-score-tab.active {{ border-color: rgba(246, 189, 39, .82); color: #ffd64a; box-shadow: 0 0 14px rgba(246, 189, 39, .22); }}
    .bracket-node-divider {{ height: 1px; margin: 10px 0 8px; background: linear-gradient(90deg, transparent, rgba(104, 190, 255, .32), transparent); }}
    .bracket-node-pending {{ display: grid; place-items: center; min-height: 46px; border: 1px dashed rgba(104, 190, 255, .28); border-radius: 8px; color: #a8bbd4; background: rgba(4, 14, 24, .55); }}
    .bracket-wdl-mini {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 4px; margin-top: 7px; font-size: 12px; font-weight: 850; text-align: center; }}
    .bracket-wdl-mini span.home {{ color: var(--green); }}
    .bracket-wdl-mini span.draw {{ color: var(--yellow); }}
    .bracket-wdl-mini span.away {{ color: var(--red); }}
    .bracket-status {{ grid-column: 1 / -1; color: #a8bbd4; font-weight: 700; }}
    .bracket-legend {{ display: flex; flex-wrap: wrap; align-items: center; gap: 10px 18px; margin-top: 9px; padding: 0 4px; color: #9fb5cf; font-size: 13px; }}
    .bracket-legend span {{ display: inline-flex; align-items: center; }}
    .current-window-key {{ margin-left: auto; border: 1px solid rgba(0, 174, 255, .32); border-radius: 999px; padding: 4px 10px; color: #8feaff; background: rgba(0, 174, 255, .1); }}
    .structure-empty {{ border: 1px dashed rgba(104, 136, 174, .26); border-radius: 14px; background: rgba(12, 20, 31, .35); padding: 12px; color: var(--muted); font-size: 13px; }}
    .dot {{
      display: inline-block;
      width: 11px;
      height: 11px;
      border-radius: 50%;
      margin-right: 7px;
      box-shadow: 0 0 14px currentColor;
      vertical-align: middle;
    }}
    .dot.home {{ background: var(--green); color: var(--green); }}
    .dot.draw {{ background: var(--yellow); color: var(--yellow); }}
    .dot.away {{ background: var(--red); color: var(--red); }}
    .team-inline {{ display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-width: 0; max-width: 100%; vertical-align: middle; }}
    .team-inline.reverse {{ flex-direction: row-reverse; }}
    .team-inline span:last-child {{ min-width: 0; overflow-wrap: anywhere; }}
    .team-flag {{ width: 28px; height: 28px; flex: 0 0 auto; border-radius: 50%; object-fit: cover; background: rgba(255,255,255,.08); box-shadow: 0 0 12px rgba(0, 217, 255, .18); }}
    .team-flag.small {{ width: 18px; height: 18px; }}
    .team-flag.emoji {{ display: inline-grid; place-items: center; font-size: 22px; line-height: 1; background: transparent; box-shadow: none; }}
    .team-flag.small.emoji {{ font-size: 16px; }}
    .team-flag.placeholder {{ display: inline-block; border: 1px dashed rgba(159, 181, 207, .38); background: rgba(159, 181, 207, .12); box-shadow: none; }}
    .match-title-teams {{ display: flex; flex-wrap: wrap; align-items: center; gap: 10px 12px; }}
    .match-title-teams .versus {{ color: var(--muted); font-size: .72em; font-weight: 760; }}
    .match-day {{ margin-top: 28px; }}
    .section-head {{ display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; margin-bottom: 14px; }}
    .section-head p {{ margin-top: 8px; line-height: 1.5; }}
    .day-count {{
      flex: 0 0 auto;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 8px 14px;
      color: #ffdb54;
      background: rgba(246, 189, 39, .12);
      font-weight: 800;
    }}
    .match-grid {{ display: grid; grid-template-columns: 1fr; gap: 22px; }}
    .match-card {{
      border: 1px solid var(--line);
      border-radius: 20px;
      background: linear-gradient(145deg, rgba(30, 43, 59, .97), rgba(23, 34, 50, .98));
      padding: 22px;
      min-height: 360px;
      display: flex;
      flex-direction: column;
      gap: 18px;
      box-shadow: 0 14px 38px rgba(0,0,0,.34), inset 0 1px 0 rgba(255,255,255,.035);
      transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease, background .18s ease;
    }}
    .match-card:hover {{
      transform: translateY(-4px);
      border-color: var(--line-hot);
      box-shadow: 0 22px 58px rgba(0,0,0,.45), 0 0 24px rgba(83, 171, 255, .18), inset 0 1px 0 rgba(255,255,255,.06);
    }}
    .match-card:hover .prob-stack .seg {{ filter: brightness(1.12) saturate(1.08); }}
    .match-topline {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 14px; }}
    .match-topline h3 {{ margin: 0; font-size: clamp(22px, 5vw, 32px); line-height: 1.2; overflow-wrap: anywhere; }}
    .match-topline time {{
      border-radius: 999px;
      background: rgba(255,255,255,.06);
      border: 1px solid rgba(255,255,255,.06);
      color: var(--muted);
      padding: 8px 14px;
      white-space: nowrap;
      font-weight: 750;
    }}
    .scoreboard {{ display: grid; grid-template-columns: minmax(0, 1fr) 42px minmax(0, 1fr); align-items: center; gap: 12px; text-align: center; }}
    .score-side > .score-team-name {{ display: flex; justify-content: center; color: var(--text); font-size: 18px; font-weight: 760; overflow-wrap: anywhere; }}
    .score-side strong {{ display: block; margin-top: 6px; font-size: clamp(42px, 12vw, 62px); line-height: .95; color: #ffd11e; }}
    .score-separator {{ color: var(--muted); font-size: 34px; font-weight: 600; }}
    .probability-panel {{ display: grid; gap: 10px; }}
    .prob-heading {{ color: var(--muted); font-weight: 760; }}
    .prob-labels, .prob-values {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; color: var(--muted); font-weight: 700; }}
    .prob-labels span:nth-child(2), .prob-values span:nth-child(2) {{ text-align: center; }}
    .prob-labels span:nth-child(3), .prob-values span:nth-child(3) {{ text-align: right; }}
    .prob-values span:nth-child(1) {{ color: var(--green); }}
    .prob-values span:nth-child(2) {{ color: var(--yellow); }}
    .prob-values span:nth-child(3) {{ color: var(--red); }}
    .prob-stack {{
      display: flex;
      height: 16px;
      border-radius: 999px;
      overflow: hidden;
      background: rgba(255,255,255,.08);
      box-shadow: inset 0 0 0 1px rgba(255,255,255,.04);
    }}
    .prob-stack .seg {{ min-width: 2px; transition: filter .18s ease, transform .18s ease; }}
    .prob-stack .home {{ background: var(--green); }}
    .prob-stack .draw {{ background: var(--yellow); }}
    .prob-stack .away {{ background: var(--red); }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }}
    .metric-grid span {{
      border: 1px solid var(--line);
      border-radius: 13px;
      background: rgba(18, 28, 42, .62);
      color: var(--muted);
      min-height: 72px;
      padding: 12px;
      line-height: 1.45;
      overflow-wrap: anywhere;
    }}
    .metric-grid b {{ display: block; color: var(--text); margin-bottom: 4px; }}
    .score-options, .factor-panel, .matchup-panel {{
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(18, 28, 42, .48);
      padding: 14px;
    }}
    .score-options h4 {{ margin: 0 0 12px; color: #ffd64a; font-size: 17px; }}
    .score-option-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
    .score-option {{
      border: 1px solid rgba(104, 136, 174, .26);
      border-radius: 14px;
      background: rgba(14, 22, 34, .62);
      padding: 12px;
      min-width: 0;
      transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
    }}
    .score-option.primary {{
      border-color: rgba(246, 189, 39, .5);
      background: linear-gradient(160deg, rgba(246, 189, 39, .16), rgba(14, 22, 34, .68));
      box-shadow: 0 0 18px rgba(246, 189, 39, .12);
    }}
    .match-card:hover .score-option.primary {{ box-shadow: 0 0 24px rgba(246, 189, 39, .18); }}
    .score-option:hover {{ transform: translateY(-2px); border-color: var(--line-hot); }}
    .score-rank {{ display: block; color: var(--muted); font-size: 12px; font-weight: 800; margin-bottom: 8px; }}
    .score-option strong {{ display: block; color: #ffd11e; font-size: 30px; line-height: 1; margin-bottom: 10px; }}
    .score-option p {{ margin: 0; color: #d8deea; font-size: 13px; line-height: 1.55; overflow-wrap: anywhere; }}
    .score-tab-labels {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }}
    .score-tab {{ border: 1px solid rgba(104, 136, 174, .34); border-radius: 14px; background: rgba(12, 20, 31, .62); color: var(--muted); padding: 11px; text-align: left; cursor: pointer; transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease, background .18s ease; min-width: 0; }}
    .score-tab:hover, .score-tab:focus-visible {{ transform: translateY(-2px); border-color: var(--line-hot); outline: none; box-shadow: 0 0 18px rgba(83, 171, 255, .16); }}
    .score-tab span {{ display: block; font-size: 12px; font-weight: 900; margin-bottom: 6px; }}
    .score-tab strong {{ display: block; color: #ffd11e; font-size: 24px; line-height: 1; }}
    .score-tab.active {{ border-color: rgba(246, 189, 39, .62); background: linear-gradient(160deg, rgba(246, 189, 39, .2), rgba(12, 20, 31, .7)); box-shadow: 0 0 20px rgba(246, 189, 39, .14); color: #ffe184; }}
    .score-tab-panel {{ display: none; margin-top: 10px; border: 1px solid rgba(104, 136, 174, .24); border-radius: 14px; background: rgba(12, 20, 31, .5); padding: 12px; }}
    .score-tab-panel.active {{ display: block; }}
    .score-tab-panel h5 {{ margin: 0 0 7px; color: var(--text); font-size: 14px; }}
    .score-tab-panel p {{ margin: 0; color: #d8deea; font-size: 14px; line-height: 1.65; overflow-wrap: anywhere; }}
    .factor-panel {{ color: var(--muted); }}
    .factor-panel summary {{
      cursor: pointer;
      color: #ffd64a;
      font-size: 17px;
      font-weight: 800;
      list-style-position: inside;
    }}
    .factor-panel summary:hover {{ color: #ffe784; }}
    .factor-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }}
    .factor-item {{
      border: 1px solid rgba(104, 136, 174, .22);
      border-radius: 13px;
      background: rgba(12, 20, 31, .48);
      padding: 12px;
      min-width: 0;
    }}
    .factor-item h5 {{ margin: 0 0 7px; color: var(--text); font-size: 13px; }}
    .factor-item p {{ margin: 0; color: var(--muted); font-size: 13px; line-height: 1.55; overflow-wrap: anywhere; }}
    .matchup-panel summary {{
      cursor: pointer;
      color: #ffd64a;
      font-size: 17px;
      font-weight: 800;
      list-style-position: inside;
    }}
    .matchup-panel summary:hover {{ color: #ffe784; }}
    .graph-summary-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }}
    .graph-summary-grid span {{
      border: 1px solid rgba(104, 136, 174, .22);
      border-radius: 13px;
      background: rgba(12, 20, 31, .5);
      padding: 12px;
      color: var(--muted);
      line-height: 1.45;
      overflow-wrap: anywhere;
    }}
    .graph-summary-grid b {{ display: block; color: var(--text); margin-bottom: 5px; }}
    .graph-summary {{ margin: 12px 0 0; color: #d8deea; font-size: 14px; line-height: 1.65; overflow-wrap: anywhere; }}
    .graph-node-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 12px; }}
    .graph-node-grid h5, .graph-edge-list h5 {{ margin: 0 0 9px; color: var(--text); font-size: 14px; }}
    .graph-node {{
      border: 1px solid rgba(104, 136, 174, .24);
      border-radius: 14px;
      background: rgba(12, 20, 31, .5);
      padding: 11px;
      margin-top: 8px;
      transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
    }}
    .graph-node.home {{ border-left: 3px solid var(--green); }}
    .graph-node.away {{ border-left: 3px solid var(--red); }}
    .graph-node:hover {{ transform: translateY(-2px); border-color: var(--line-hot); }}
    .graph-node div {{ display: flex; justify-content: space-between; gap: 8px; align-items: baseline; }}
    .graph-node strong {{ color: var(--text); font-size: 14px; }}
    .graph-node span {{ color: #ffd64a; font-size: 12px; font-weight: 800; white-space: nowrap; }}
    .graph-node p {{ margin: 7px 0 0; color: var(--muted); font-size: 13px; line-height: 1.5; overflow-wrap: anywhere; }}
    .graph-edge-list {{ margin-top: 12px; }}
    .graph-edge {{
      border: 1px solid rgba(104, 136, 174, .24);
      border-radius: 14px;
      background: rgba(12, 20, 31, .46);
      padding: 12px;
      margin-top: 9px;
      transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
    }}
    .graph-edge:hover {{ transform: translateY(-2px); border-color: var(--line-hot); }}
    .graph-edge.impact-high {{ border-color: rgba(239,80,73,.54); box-shadow: inset 0 0 0 1px rgba(239,80,73,.12); }}
    .graph-edge.impact-medium {{ border-color: rgba(246,189,39,.45); }}
    .graph-edge.impact-low {{ border-color: rgba(104,136,174,.3); }}
    .graph-edge div {{ display: flex; justify-content: space-between; gap: 10px; align-items: center; }}
    .graph-edge strong {{ color: var(--text); font-size: 14px; overflow-wrap: anywhere; }}
    .graph-edge span {{ border-radius: 999px; padding: 4px 9px; font-size: 12px; font-weight: 900; }}
    .graph-edge.impact-high span {{ color: #ffb7b3; background: rgba(239,80,73,.16); }}
    .graph-edge.impact-medium span {{ color: #ffe184; background: rgba(246,189,39,.14); }}
    .graph-edge.impact-low span {{ color: #c5d1e4; background: rgba(104,136,174,.13); }}
    .graph-edge p {{ margin: 8px 0 0; color: #d8deea; font-size: 13px; line-height: 1.55; overflow-wrap: anywhere; }}
    .graph-edge small {{ display: block; margin-top: 8px; color: var(--muted); overflow-wrap: anywhere; }}
    .analysis-block {{ display: grid; gap: 14px; }}
    .analysis-block section {{ border-top: 1px solid var(--line); padding-top: 14px; }}
    .analysis-block h4 {{ margin: 0 0 8px; font-size: 17px; color: var(--muted); }}
    .analysis-block p {{ margin: 0; color: #d8deea; font-size: 15px; line-height: 1.75; }}
    .analysis-block .risk-text {{ color: #ffbd35; }}
    .match-footer {{ display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 10px; border-top: 1px solid var(--line); padding-top: 14px; margin-top: auto; color: var(--muted); }}
    .confidence {{ display: inline-flex; align-items: center; min-width: 38px; justify-content: center; border-radius: 999px; padding: 4px 11px; margin-left: 4px; }}
    .confidence.high {{ color: var(--green); background: rgba(43,209,111,.13); }}
    .confidence.medium {{ color: var(--yellow); background: rgba(246,189,39,.13); }}
    .confidence.low {{ color: var(--red); background: rgba(239,80,73,.13); }}
    .source-link {{ border: 1px solid var(--line); border-radius: 999px; padding: 6px 12px; }}
    .venue-line {{ margin: -6px 0 0; color: var(--muted); font-size: 13px; line-height: 1.5; }}
    .empty {{ border: 1px dashed var(--line); border-radius: 18px; background: rgba(27,40,56,.68); padding: 24px; color: var(--muted); }}
    .muted {{ color: var(--muted); }}
    .compact {{ margin: 0; }}
    .page-footer {{ color: var(--muted); padding-top: 30px; font-size: 13px; line-height: 1.8; }}
    @media (min-width: 1080px) {{
      .match-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 760px) {{
      .page {{ width: min(100% - 24px, 640px); padding-top: 18px; }}
      .hero, .overview, .usage-panel, .tournament-panel, .match-card {{ border-radius: 18px; padding: 16px; }}
      .hero-meta, .usage-grid, .metric-grid, .score-tab-labels, .factor-grid, .graph-summary-grid, .graph-node-grid, .structure-title-row, .structure-node-grid {{ grid-template-columns: 1fr 1fr; }}
      .hero-meta div:nth-child(3n) {{ border-right: 1px solid rgba(104, 190, 255, .14); }}
      .hero-meta div:nth-child(2n) {{ border-right: 0; }}
      .hero-meta div:nth-last-child(-n+3) {{ border-bottom: 1px solid rgba(104, 190, 255, .12); }}
      .hero-meta div:nth-last-child(-n+2) {{ border-bottom: 0; }}
      .section-head, .match-topline {{ display: block; }}
      .day-count {{ display: inline-flex; margin-top: 12px; }}
      .match-topline time {{ display: inline-flex; margin-top: 12px; white-space: normal; }}
      .scoreboard {{ grid-template-columns: minmax(0, 1fr) 24px minmax(0, 1fr); gap: 6px; }}
      .score-side > .score-team-name {{ font-size: 16px; }}
      .prob-labels {{ font-size: 14px; }}
      .match-footer {{ display: grid; grid-template-columns: 1fr; }}
    }}
    @media (max-width: 460px) {{
      .hero-meta, .usage-grid, .metric-grid, .score-tab-labels, .factor-grid, .graph-summary-grid, .graph-node-grid, .structure-title-row, .structure-node-grid {{ grid-template-columns: 1fr; }}
      .hero-meta div, .hero-meta div:nth-child(2n), .hero-meta div:nth-child(3n) {{ border-right: 0; }}
      .hero-meta div, .hero-meta div:nth-last-child(-n+2), .hero-meta div:nth-last-child(-n+3) {{ border-bottom: 1px solid rgba(104, 190, 255, .12); }}
      .hero-meta div:last-child {{ border-bottom: 0; }}
      .prob-labels {{ grid-template-columns: 1fr; gap: 6px; }}
      .prob-labels span, .prob-labels span:nth-child(2), .prob-labels span:nth-child(3) {{ text-align: left; }}
    }}
  </style>
</head>
<body class="night-shell">
  <main class="page">
    <header class="hero night-card">
      <h1><span class="hero-ball">⚽</span><span>2026 世界杯 · 预测分析</span></h1>
      <span class="range-pill">{html_escape(range_text)}</span>
      <div class="hero-meta">
        <div><span class="meta-icon">▦</span>比赛阶段<strong>{html_escape(stage_label)}</strong></div>
        <div><span class="meta-icon">◷</span>生成时间<strong>{html_escape(generated_display)}</strong></div>
        <div><span class="meta-icon">◎</span>总比赛场次<strong>{total_count_label} 场</strong></div>
        <div><span class="meta-icon">◇</span>分析模型<strong>{ANALYSIS_MODEL}</strong></div>
        <div><span class="meta-icon">⬡</span>渲染模型<strong>{RENDER_MODEL}</strong></div>
        <div><span class="meta-icon">▥</span>数据来源<strong>FIFA + ESPN + DeepSeek</strong></div>
      </div>
    </header>

    {structure_section}

    <section class="usage-panel night-card">
      <h2>Token / Cost</h2>
      <div class="usage-grid">
        <div class="usage-card input"><span>输入 TOKEN</span><strong>{usage.get("input_tokens", 0)}</strong></div>
        <div class="usage-card output"><span>输出 TOKEN</span><strong>{usage.get("output_tokens", 0)}</strong></div>
        <div class="usage-card total"><span>总 TOKEN</span><strong>{usage.get("total_tokens", 0)}</strong></div>
        <div class="usage-card cost"><span>预计成本</span><strong>{float(usage.get("cost_estimate", 0)):.6f}</strong></div>
      </div>
    </section>

    <section class="overview night-card">
      <h2>总览</h2>
      <p>{html_escape(summary)}</p>
    </section>

    <section class="overview night-card">
      <h2>风险概览</h2>
      <p>{html_escape(risk_overview)}</p>
    </section>

    <section class="legend night-card">
      <span><i class="dot home"></i>主胜</span>
      <span><i class="dot draw"></i>平局</span>
      <span><i class="dot away"></i>客胜</span>
      <span>置信度：高 / 中 / 低</span>
      <span><a href="latest.json">查看 data/latest.json</a></span>
    </section>
    {''.join(group_sections)}
    <footer class="page-footer">
      V3 Agent：FIFA 官方赛程为主源，ESPN 用于第二来源校验和赔率；伤停无可靠来源时显示 unknown，赔率无真实源时显示 unavailable。所有可见比赛时间均为北京时间，比赛日按 18:00 至次日 18:00 划分。
    </footer>
  </main>
  <script>
    document.querySelectorAll('[data-score-tabs]').forEach((set) => {{
      const tabs = Array.from(set.querySelectorAll('[data-score-tab]'));
      const panels = Array.from(set.querySelectorAll('[data-score-panel]'));
      tabs.forEach((tab) => {{
        tab.addEventListener('click', () => {{
          const target = tab.getAttribute('data-score-tab');
          tabs.forEach((item) => {{
            const active = item === tab;
            item.classList.toggle('active', active);
            item.setAttribute('aria-selected', active ? 'true' : 'false');
          }});
          panels.forEach((panel) => panel.classList.toggle('active', panel.getAttribute('data-score-panel') === target));
        }});
      }});
    }});
  </script></body>
</html>
"""


def append_agent_panels(page: str, payload: dict[str, Any]) -> str:
    return page

def run_render(analysis_path: Path = ANALYSIS_PATH, output: Path = RENDER_PATH, docs_dir: Path = DOCS_DIR) -> dict[str, Any]:
    analysis_payload = read_json(analysis_path)
    content, render_usage, _response = deepseek_chat(
        RENDER_MODEL,
        render_messages(analysis_payload),
        json_object=False,
    )
    flash_draft = extract_html(content)
    analysis_usage = analysis_payload.get("usage") or zero_usage()
    total_usage = combine_usage(analysis_usage, render_usage)
    matches = enrich_matches_for_display(analysis_payload.get("matches", []))
    tournament_structure = analysis_payload.get("tournament_structure") or build_tournament_structure(
        matches,
        analysis_payload.get("display_window") or (analysis_payload.get("research") or {}).get("display_window", {}),
        (analysis_payload.get("research") or {}).get("structure_matches", []),
        analysis_payload.get("structure_window") or (analysis_payload.get("research") or {}).get("structure_window", {}),
    )
    payload = {
        "schema_version": 3,
        "stage": "render",
        "generated_at": iso_utc(utc_now()),
        "analysis": analysis_payload.get("analysis", {}),
        "matches": matches,
        "tournament_structure": tournament_structure,
        "structure_window": analysis_payload.get("structure_window") or (analysis_payload.get("research") or {}).get("structure_window", {}),
        "render": "",
        "render_draft_sha": stable_id(flash_draft),
        "usage": total_usage,
        "usage_breakdown": {"analysis": analysis_usage, "render": render_usage},
        "analysis_model": ANALYSIS_MODEL,
        "render_model": RENDER_MODEL,
        "model": {"analysis_model": ANALYSIS_MODEL, "render_model": RENDER_MODEL},
        "display_window": analysis_payload.get("display_window") or (analysis_payload.get("research") or {}).get("display_window", {}),
        "china_match_days": analysis_payload.get("china_match_days") or (analysis_payload.get("research") or {}).get("china_match_days", []),
        "data_sources": analysis_payload.get("data_sources", {}),
        "source": (analysis_payload.get("research") or {}).get("source", {}),
        "daily_log": [
            *analysis_payload.get("daily_log", []),
            {"time": iso_utc(utc_now()), "stage": "09:00 deepseek-v4-flash HTML generation", "status": "completed"},
        ],
    }
    payload["render"] = inject_usage(build_legacy_agent_html(payload), total_usage)
    write_json(output, payload)
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "index.html").write_text(payload["render"], encoding="utf-8")
    (docs_dir / ".nojekyll").write_text("\n", encoding="utf-8")
    return payload

def run_finalize(render_path: Path = RENDER_PATH, latest_path: Path = LATEST_PATH, docs_dir: Path = DOCS_DIR) -> dict[str, Any]:
    render_payload = read_json(render_path)
    matches = enrich_matches_for_display(render_payload.get("matches", []))
    render_payload["matches"] = matches
    tournament_structure = render_payload.get("tournament_structure") or build_tournament_structure(
        matches,
        render_payload.get("display_window", {}),
        render_payload.get("structure_matches", []),
        render_payload.get("structure_window", {}),
    )
    render_payload["tournament_structure"] = tournament_structure
    if render_payload.get("render"):
        render_payload["render"] = build_legacy_agent_html(render_payload)
    payload = {
        "schema_version": 3,
        "stage": "latest",
        "generated_at": iso_utc(utc_now()),
        "matches": matches,
        "tournament_structure": tournament_structure,
        "analysis_model": ANALYSIS_MODEL,
        "render_model": RENDER_MODEL,
        "usage": render_payload.get("usage") or zero_usage(),
        "data_sources": {
            "fifa": bool((render_payload.get("data_sources") or {}).get("fifa")),
            "injury": bool((render_payload.get("data_sources") or {}).get("injury")),
            "odds": bool((render_payload.get("data_sources") or {}).get("odds")),
        },
        "render": render_payload.get("render", ""),
        "analysis": render_payload.get("analysis", {}),
        "usage_breakdown": render_payload.get("usage_breakdown", {}),
        "model": {"analysis_model": ANALYSIS_MODEL, "render_model": RENDER_MODEL},
        "display_window": render_payload.get("display_window", {}),
        "structure_window": render_payload.get("structure_window", {}),
        "china_match_days": render_payload.get("china_match_days", []),
        "source": render_payload.get("source", {}),
        "daily_log": [
            *render_payload.get("daily_log", []),
            {"time": iso_utc(utc_now()), "stage": "09:30 write JSON + token statistics", "status": "completed"},
        ],
    }
    write_json(latest_path, payload)
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "index.html").write_text(payload["render"], encoding="utf-8")
    shutil.copyfile(latest_path, docs_dir / "latest.json")
    (docs_dir / ".nojekyll").write_text("\n", encoding="utf-8")
    return payload

def run_full() -> dict[str, Any]:
    run_research()
    run_analysis()
    run_render()
    return run_finalize()


def main() -> int:
    parser = argparse.ArgumentParser(description="DeepSeek V4 Agent World Cup pipeline.")
    subparsers = parser.add_subparsers(dest="stage", required=True)

    research_parser = subparsers.add_parser("research")
    research_parser.add_argument("--start-date")
    research_parser.add_argument("--days", type=int, default=DEFAULT_DAYS)

    subparsers.add_parser("analysis")
    subparsers.add_parser("render")
    subparsers.add_parser("finalize")
    subparsers.add_parser("full")

    args = parser.parse_args()
    if args.stage == "research":
        start = dt.date.fromisoformat(args.start_date) if args.start_date else None
        payload = run_research(start=start, days=args.days)
        print(f"research completed fixtures={payload['fixture_count']} odds={payload['odds_available_count']}")
    elif args.stage == "analysis":
        payload = run_analysis()
        print(f"analysis completed model={payload['analysis_model']} matches={len(payload['matches'])}")
    elif args.stage == "render":
        payload = run_render()
        print(f"render completed model={payload['render_model']} tokens={payload['usage']['total_tokens']}")
    elif args.stage == "finalize":
        payload = run_finalize()
        print(f"finalize completed matches={len(payload['matches'])} tokens={payload['usage']['total_tokens']}")
    elif args.stage == "full":
        payload = run_full()
        print(f"full pipeline completed matches={len(payload['matches'])} tokens={payload['usage']['total_tokens']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
