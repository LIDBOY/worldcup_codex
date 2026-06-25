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
REQUEST_TIMEOUT = int(os.getenv("WORLDCUP_REQUEST_TIMEOUT", "25"))
DEEPSEEK_REQUEST_TIMEOUT = int(os.getenv("DEEPSEEK_REQUEST_TIMEOUT", "180"))
INJURY_LOOKBACK_DAYS = int(os.getenv("WORLDCUP_INJURY_LOOKBACK_DAYS", "180"))

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


def team_from_fifa(raw: dict[str, Any], placeholder: str | None = None) -> dict[str, Any]:
    name_en = localized(raw.get("TeamName"), raw.get("ShortClubName") or placeholder or "Unknown team")
    if not name_en or name_en == "Unknown team":
        name_en = placeholder or "Unknown team"
    return {
        "name": team_name_zh(name_en),
        "name_en": name_en,
        "abbreviation": raw.get("Abbreviation") or raw.get("IdCountry") or placeholder,
        "id_team": raw.get("IdTeam"),
        "id_country": raw.get("IdCountry"),
        "logo": raw.get("PictureUrl"),
        "score": raw.get("Score"),
        "tactics": raw.get("Tactics"),
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
    return {
        "id": event_id,
        "kickoff_utc": iso_utc(parse_date(event["date"])) if event.get("date") else None,
        "teams": {
            "home": {
                "name_en": competitor_name(home_raw),
                "abbreviation": (home_raw.get("team") or {}).get("abbreviation"),
            },
            "away": {
                "name_en": competitor_name(away_raw),
                "abbreviation": (away_raw.get("team") or {}).get("abbreviation"),
            },
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
    start_date, fetch_days = fifa_fetch_span_for_china_window(display_window)
    fifa_matches, fifa_url, fifa_warnings = fetch_fifa_matches(start_date, fetch_days)
    raw_fifa_fixture_count = len(fifa_matches)
    fifa_matches = filter_matches_to_china_window(fifa_matches, display_window)
    espn_raw_events, espn_urls, espn_warnings = fetch_espn_events(start_date - dt.timedelta(days=1), fetch_days + 2)
    espn_matches = [match for event in espn_raw_events if (match := transform_espn_event(event))]

    verified: list[dict[str, Any]] = []
    unverified: list[str] = []
    for fifa_match in fifa_matches:
        espn_match = find_espn_match(fifa_match, espn_matches)
        if not espn_match:
            unverified.append(fifa_match["match_name_en"])
            continue
        fifa_match["espn_event_id"] = espn_match["id"]
        fifa_match["sources"]["espn"] = espn_match["source"]
        fifa_match["source_verification"] = {
            "verified": True,
            "sources": ["FIFA official calendar API", "ESPN public FIFA World Cup scoreboard"],
            "method": "team-pair and kickoff-time cross-check",
        }
        fifa_match["odds"] = espn_match["odds"]
        verified.append(fifa_match)

    espn_articles, news_url, news_warnings = fetch_espn_news()
    verified, injury_warnings = attach_injuries(verified, espn_articles)
    odds_available = sum(1 for match in verified if (match.get("odds") or {}).get("available"))

    warnings = [*fifa_warnings, *espn_warnings, *news_warnings, *injury_warnings]
    payload = {
        "schema_version": 3,
        "stage": "research",
        "generated_at": iso_utc(utc_now()),
        "window": {
            "start_date": start_date.isoformat(),
            "days": fetch_days,
            "timezone": "UTC",
            "mode": "derived from China match-day display window",
        },
        "display_window": display_window,
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
        "fixture_count": len(verified),
        "fifa_fixture_count": len(fifa_matches),
        "raw_fifa_fixture_count": raw_fifa_fixture_count,
        "odds_available_count": odds_available,
        "matches": verified,
        "fixtures": verified,
        "daily_log": [
            {
                "time": iso_utc(utc_now()),
                "stage": "08:15 automatic FIFA schedule + injury + odds research",
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


def parse_json_content(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start:end + 1])


def analysis_messages(research_payload: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are the only analysis layer for a FIFA World Cup AI Agent. "
                "You must use deepseek-v4-pro reasoning only. Do not invent fixtures, injuries, odds, results, "
                "or sources. Use only the verified FIFA/ESPN/injury/odds payload provided. "
                "Return strict JSON only. Write all user-facing analysis in Simplified Chinese."
            ),
        },
        {
            "role": "user",
            "content": (
                "Analyze every verified match and return JSON with this exact shape: "
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
                "If injury status is unknown, say it is unknown; do not invent player names. "
                "If odds are unavailable, say odds are unavailable; do not invent market prices. "
                f"Verified Agent research payload:\n{json.dumps(research_payload, ensure_ascii=False)}"
            ),
        },
    ]


def match_id_of(match: dict[str, Any]) -> str:
    return str(match.get("match_id") or match.get("fixture_id") or match.get("id") or match.get("fifa_match_id") or "")


def merge_analysis_matches(analysis: dict[str, Any], research_payload: dict[str, Any]) -> list[dict[str, Any]]:
    source_matches = {str(item.get("id")): item for item in research_payload.get("matches", [])}
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
            merged_item.setdefault("teams", source.get("teams"))
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
    payload = {
        "schema_version": 3,
        "stage": "analysis",
        "generated_at": iso_utc(utc_now()),
        "analysis": analysis,
        "matches": matches,
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
                "risk analysis, upset probability, injury information, odds comparison, token usage, and cost. "
                "All visible match times must use Asia/Shanghai, never UTC. "
                "Group matches by China match day, where each match day runs from 18:00 to next-day 18:00. "
                "Use these exact placeholders inside the token panel: "
                "{{INPUT_TOKENS}}, {{OUTPUT_TOKENS}}, {{TOTAL_TOKENS}}, {{COST_ESTIMATE}}. "
                "Do not invent data. If source data says unknown or unavailable, display that clearly. "
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


def flag_url(team: dict[str, Any]) -> str | None:
    raw = team.get("logo")
    if not raw:
        return None
    return str(raw).replace("{format}", "png").replace("{size}", "3")


def team_visual(team: dict[str, Any], *, right: bool = False) -> str:
    name = html_escape(team.get("name") or team.get("name_en") or "Unknown")
    logo = flag_url(team)
    if logo:
        visual = f'<img class="team-logo" src="{html_escape(logo)}" alt="{name}">'
    else:
        initial = html_escape((team.get("abbreviation") or name or "?")[:3])
        visual = f'<span class="team-initial">{initial}</span>'
    if right:
        return f'<div class="team right"><strong>{name}</strong>{visual}</div>'
    return f'<div class="team">{visual}<strong>{name}</strong></div>'


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
    confidence_raw = match.get("confidence")
    return f"""
      <article class="match-card">
        <div class="match-topline">
          <h3>{html_escape(home_name)} vs {html_escape(away_name)}</h3>
          <time datetime="{kickoff_iso}">{html_escape(kickoff_display)}</time>
        </div>
        <div class="scoreboard">
          <div class="score-side">
            <span>{html_escape(home_name)}</span>
            <strong>{html_escape(score.get("home", 0))}</strong>
          </div>
          <div class="score-separator">:</div>
          <div class="score-side away-side">
            <span>{html_escape(away_name)}</span>
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
    .page {{ width: min(980px, calc(100% - 28px)); margin: 0 auto; padding: 28px 0 44px; }}
    .night-card {{
      position: relative;
      border: 1px solid var(--line);
      border-radius: 22px;
      background: linear-gradient(145deg, rgba(31, 46, 66, .96), rgba(24, 35, 51, .96));
      box-shadow: var(--shadow), inset 0 1px 0 rgba(255,255,255,.04);
      overflow: hidden;
    }}
    .night-card::before {{
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: linear-gradient(120deg, rgba(86, 169, 255, .18), transparent 36%, rgba(43, 209, 111, .08));
      opacity: .55;
    }}
    .hero {{
      padding: 30px;
      margin-bottom: 24px;
    }}
    .hero > * {{ position: relative; z-index: 1; }}
    .hero h1 {{ margin: 0 0 18px; font-size: clamp(30px, 7vw, 46px); line-height: 1.08; font-weight: 850; }}
    .range-pill {{
      display: inline-flex;
      align-items: center;
      max-width: 100%;
      min-height: 40px;
      padding: 0 18px;
      border-radius: 999px;
      background: rgba(246, 189, 39, .13);
      color: #ffdb54;
      border: 1px solid rgba(246, 189, 39, .28);
      font-weight: 800;
      overflow-wrap: anywhere;
    }}
    .hero-meta {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px 22px;
      margin: 26px 0 0;
    }}
    .hero-meta div {{ color: var(--muted); line-height: 1.55; min-width: 0; overflow-wrap: anywhere; }}
    .hero-meta strong {{ display: block; color: var(--text); font-weight: 780; }}
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
    .score-side span {{ display: block; color: var(--text); font-size: 18px; font-weight: 760; overflow-wrap: anywhere; }}
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
      .hero, .overview, .usage-panel, .match-card {{ border-radius: 20px; padding: 20px; }}
      .hero-meta, .usage-grid, .metric-grid {{ grid-template-columns: 1fr 1fr; }}
      .section-head, .match-topline {{ display: block; }}
      .day-count {{ display: inline-flex; margin-top: 12px; }}
      .match-topline time {{ display: inline-flex; margin-top: 12px; white-space: normal; }}
      .scoreboard {{ grid-template-columns: minmax(0, 1fr) 24px minmax(0, 1fr); gap: 6px; }}
      .score-side span {{ font-size: 16px; }}
      .prob-labels {{ font-size: 14px; }}
      .match-footer {{ display: grid; grid-template-columns: 1fr; }}
    }}
    @media (max-width: 460px) {{
      .hero-meta, .usage-grid, .metric-grid {{ grid-template-columns: 1fr; }}
      .prob-labels {{ grid-template-columns: 1fr; gap: 6px; }}
      .prob-labels span, .prob-labels span:nth-child(2), .prob-labels span:nth-child(3) {{ text-align: left; }}
    }}
  </style>
</head>
<body class="night-shell">
  <main class="page">
    <header class="hero night-card">
      <h1>2026 世界杯 · 预测分析</h1>
      <span class="range-pill">{html_escape(range_text)}</span>
      <div class="hero-meta">
        <div>生成时间<strong>{html_escape(generated_display)}</strong></div>
        <div>总比赛场次<strong>{len(matches)} 场</strong></div>
        <div>分析模型<strong>{ANALYSIS_MODEL}</strong></div>
        <div>生成模型<strong>{RENDER_MODEL}</strong></div>
      </div>
    </header>

    <section class="overview night-card">
      <h2>总览</h2>
      <p>{html_escape(summary)}</p>
    </section>

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
</body>
</html>
"""


def append_agent_panels(page: str, payload: dict[str, Any]) -> str:
    if 'id="deepseek-agent-runtime"' in page:
        return page
    usage = payload["usage"]
    sources = payload.get("data_sources") or {}
    rows = []
    for match in payload.get("matches", []):
        injuries = match.get("injuries") or {}
        odds = match.get("odds") or {}
        home_injury = (injuries.get("home") or {}).get("status", "unknown")
        away_injury = (injuries.get("away") or {}).get("status", "unknown")
        odds_text = "\u4e0d\u53ef\u7528"
        if odds.get("available"):
            odds_text = render_probability_line(odds.get("normalized_probability"))
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(match.get('match_name') or ''))}</td>"
            f"<td>{html.escape(str(home_injury))}</td>"
            f"<td>{html.escape(str(away_injury))}</td>"
            f"<td>{html.escape(odds_text)}</td>"
            "</tr>"
        )
    table = "\n".join(rows) if rows else "<tr><td colspan=\"4\">\u4eca\u65e5\u65e0\u53cc\u6e90\u9a8c\u8bc1\u7684\u4e16\u754c\u676f\u6bd4\u8d5b</td></tr>"
    panel = f"""
<section id="deepseek-agent-runtime" style="max-width:1120px;margin:24px auto;padding:16px;border:1px solid #d8e0dc;border-radius:8px;background:#fff;font-family:Inter,'Microsoft YaHei','PingFang SC',system-ui,sans-serif;color:#17201d;">
  <h2 style="margin:0 0 12px;font-size:20px;">\u8fd0\u884c\u7528\u91cf</h2>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;">
    <div><strong>\u5206\u6790\u6a21\u578b</strong><br>{ANALYSIS_MODEL}</div>
    <div><strong>\u751f\u6210\u6a21\u578b</strong><br>{RENDER_MODEL}</div>
    <div><strong>Input tokens</strong><br>{usage["input_tokens"]}</div>
    <div><strong>Output tokens</strong><br>{usage["output_tokens"]}</div>
    <div><strong>Total tokens</strong><br>{usage["total_tokens"]}</div>
    <div><strong>Cost</strong><br>{usage["cost_estimate"]:.6f}</div>
  </div>
  <h2 style="margin:20px 0 12px;font-size:20px;">\u6570\u636e\u6e90\u4e0eAgent\u6821\u9a8c</h2>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;">
    <div><strong>FIFA</strong><br>{str(bool(sources.get("fifa"))).lower()}</div>
    <div><strong>\u4f24\u505c\u4fe1\u606f</strong><br>{str(bool(sources.get("injury"))).lower()}</div>
    <div><strong>\u8d54\u7387\u5bf9\u6bd4</strong><br>{str(bool(sources.get("odds"))).lower()}</div>
  </div>
  <h2 style="margin:20px 0 12px;font-size:20px;">\u4f24\u505c\u4fe1\u606f / \u8d54\u7387\u5bf9\u6bd4</h2>
  <div style="overflow:auto;">
    <table style="width:100%;border-collapse:collapse;font-size:14px;">
      <thead><tr><th style="text-align:left;border-bottom:1px solid #d8e0dc;padding:8px;">\u6bd4\u8d5b</th><th style="text-align:left;border-bottom:1px solid #d8e0dc;padding:8px;">\u4e3b\u961f\u4f24\u505c</th><th style="text-align:left;border-bottom:1px solid #d8e0dc;padding:8px;">\u5ba2\u961f\u4f24\u505c</th><th style="text-align:left;border-bottom:1px solid #d8e0dc;padding:8px;">\u9690\u542b\u6982\u7387</th></tr></thead>
      <tbody>{table}</tbody>
    </table>
  </div>
</section>
"""
    if "</body>" in page:
        return page.replace("</body>", panel + "\n</body>", 1)
    return page + panel


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
    payload = {
        "schema_version": 3,
        "stage": "render",
        "generated_at": iso_utc(utc_now()),
        "analysis": analysis_payload.get("analysis", {}),
        "matches": matches,
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
    if render_payload.get("render"):
        render_payload["render"] = build_legacy_agent_html(render_payload)
    payload = {
        "schema_version": 3,
        "stage": "latest",
        "generated_at": iso_utc(utc_now()),
        "matches": matches,
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
