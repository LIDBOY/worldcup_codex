from __future__ import annotations

import argparse
import datetime as dt
import hashlib
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


ANALYSIS_MODEL = os.getenv("DEEPSEEK_ANALYSIS_MODEL", "deepseek-v4-pro")
RENDER_MODEL = os.getenv("DEEPSEEK_RENDER_MODEL", "deepseek-v4-flash")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
DEEPSEEK_API_KEY_ENV = "DEEPSEEK_API_KEY"
TOKEN_COST_RATE = float(os.getenv("DEEPSEEK_TOKEN_COST_RATE", "0.00001"))

DEFAULT_LEAGUE = os.getenv("WORLDCUP_ESPN_LEAGUE", "fifa.world")
DEFAULT_DAYS = int(os.getenv("WORLDCUP_WINDOW_DAYS", "5"))
REQUEST_TIMEOUT = int(os.getenv("WORLDCUP_REQUEST_TIMEOUT", "20"))
DEEPSEEK_REQUEST_TIMEOUT = int(os.getenv("DEEPSEEK_REQUEST_TIMEOUT", "180"))

DATA_DIR = Path("data")
DOCS_DIR = Path("docs")
FIXTURES_PATH = DATA_DIR / "fixtures.json"
ANALYSIS_PATH = DATA_DIR / "analysis.json"
LATEST_PATH = DATA_DIR / "latest.json"

ESPN_SCOREBOARD = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/"
    f"{DEFAULT_LEAGUE}/scoreboard"
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


def request_json(url: str, *, params: dict[str, str] | None = None, headers: dict[str, str] | None = None,
                 body: dict[str, Any] | None = None, retries: int = 3,
                 timeout: int = REQUEST_TIMEOUT) -> dict[str, Any]:
    full_url = f"{url}?{urlencode(params)}" if params else url
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request_headers = {"User-Agent": "worldcup-deepseek-pages/2.0", **(headers or {})}
    if body is not None:
        request_headers["Content-Type"] = "application/json"

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            request = Request(full_url, data=data, headers=request_headers)
            with urlopen(request, timeout=timeout) as response:  # noqa: S310 - configured sources only
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            last_error = RuntimeError(f"HTTP {exc.code} from {full_url}: {detail}")
        except Exception as exc:  # noqa: BLE001 - preserve upstream failure detail
            last_error = exc
        if attempt < retries:
            time.sleep(2 ** (attempt - 1))
    raise RuntimeError(f"failed to fetch {full_url}: {last_error}")


def espn_date_url(day: dt.date) -> str:
    return f"{ESPN_SCOREBOARD}?dates={day:%Y%m%d}"


def fetch_espn_events(start: dt.date, days: int) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    events: dict[str, dict[str, Any]] = {}
    urls: list[str] = []
    warnings: list[str] = []
    for offset in range(days):
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


def transform_event(event: dict[str, Any]) -> dict[str, Any] | None:
    pair = pick_competitors(event)
    if not pair:
        return None
    home_raw, away_raw = pair
    home_en = competitor_name(home_raw)
    away_en = competitor_name(away_raw)
    home_zh = team_name_zh(home_en)
    away_zh = team_name_zh(away_en)
    event_id = str(event.get("id") or stable_id(event))
    competition = (event.get("competitions") or [{}])[0]
    status_type = (event.get("status") or {}).get("type") or {}
    kickoff = parse_date(event["date"]) if event.get("date") else utc_now()
    venue = competition.get("venue") or {}
    address = venue.get("address") or {}
    return {
        "id": event_id,
        "match_name": f"{home_zh} vs {away_zh}",
        "match_name_en": event.get("name") or f"{home_en} vs {away_en}",
        "kickoff_utc": iso_utc(kickoff),
        "competition": (event.get("league") or {}).get("name") or "FIFA World Cup",
        "status": {
            "state": status_type.get("state") or "pre",
            "detail": status_type.get("description") or status_type.get("detail") or "scheduled",
            "completed": bool(status_type.get("completed")),
        },
        "teams": {
            "home": {
                "name": home_zh,
                "name_en": home_en,
                "abbreviation": (home_raw.get("team") or {}).get("abbreviation"),
                "logo": competitor_logo(home_raw),
                "score": home_raw.get("score"),
            },
            "away": {
                "name": away_zh,
                "name_en": away_en,
                "abbreviation": (away_raw.get("team") or {}).get("abbreviation"),
                "logo": competitor_logo(away_raw),
                "score": away_raw.get("score"),
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
    }


def run_research(output: Path = FIXTURES_PATH, start: dt.date | None = None, days: int = DEFAULT_DAYS) -> dict[str, Any]:
    start_date = start or utc_now().date()
    raw_events, source_urls, warnings = fetch_espn_events(start_date, days)
    fixtures = [fixture for event in raw_events if (fixture := transform_event(event))]
    fixtures.sort(key=lambda item: item["kickoff_utc"])
    payload = {
        "schema_version": 2,
        "stage": "research",
        "generated_at": iso_utc(utc_now()),
        "window": {"start_date": start_date.isoformat(), "days": days, "timezone": "UTC"},
        "source": {"fixture_provider": "ESPN public scoreboard", "league": DEFAULT_LEAGUE, "urls": source_urls},
        "warnings": warnings,
        "fixture_count": len(fixtures),
        "fixtures": fixtures,
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


def deepseek_chat(model: str, messages: list[dict[str, str]], *, json_object: bool = False,
                  analysis_layer: bool = False) -> tuple[str, dict[str, Any], dict[str, Any]]:
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


def analysis_messages(fixtures_payload: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are the mandatory analysis layer for a FIFA World Cup prediction system. "
                "Use model deepseek-v4-pro with high reasoning. Analyze only the verified fixtures "
                "provided by the user. Do not invent fixtures, teams, injuries, results, odds, or facts. "
                "Return strict JSON only. Write user-facing text in Simplified Chinese."
            ),
        },
        {
            "role": "user",
            "content": (
                "Analyze these verified fixtures and return JSON with this exact shape: "
                "{"
                "\"generated_at\":\"ISO-8601\","
                "\"summary\":\"Chinese summary\","
                "\"predictions\":[{"
                "\"fixture_id\":\"string\","
                "\"match_name\":\"Chinese home vs away\","
                "\"kickoff_utc\":\"ISO-8601\","
                "\"teams\":{\"home\":{\"name\":\"Chinese\",\"name_en\":\"English\"},"
                "\"away\":{\"name\":\"Chinese\",\"name_en\":\"English\"}},"
                "\"win_draw_loss\":{\"home_win\":0,\"draw\":0,\"away_win\":0},"
                "\"predicted_score\":{\"home\":0,\"away\":0},"
                "\"tactical_analysis\":\"Chinese tactical analysis\","
                "\"risk_analysis\":\"Chinese risk analysis\","
                "\"confidence\":\"low|medium|high\""
                "}],"
                "\"risk_overview\":\"Chinese risk overview\","
                "\"data_quality\":\"Chinese source quality note\""
                "}. Probabilities must be percentages and sum to 100 for every fixture. "
                "If fixtures is empty, return an empty predictions array and explain no verified fixtures. "
                f"Verified fixture payload:\n{json.dumps(fixtures_payload, ensure_ascii=False)}"
            ),
        },
    ]


def run_analysis(fixtures_path: Path = FIXTURES_PATH, output: Path = ANALYSIS_PATH) -> dict[str, Any]:
    fixtures_payload = read_json(fixtures_path) if fixtures_path.exists() else run_research(fixtures_path)
    content, usage, _response = deepseek_chat(
        ANALYSIS_MODEL,
        analysis_messages(fixtures_payload),
        json_object=True,
        analysis_layer=True,
    )
    analysis = parse_json_content(content)
    payload = {
        "schema_version": 2,
        "stage": "analysis",
        "generated_at": iso_utc(utc_now()),
        "analysis": analysis,
        "fixtures": fixtures_payload,
        "usage": usage,
        "model": {"analysis_model": ANALYSIS_MODEL},
        "daily_log": [
            {"time": fixtures_payload.get("generated_at"), "stage": "08:15 research pipeline", "status": "completed"},
            {"time": iso_utc(utc_now()), "stage": "09:40 analysis completed", "status": "completed"},
        ],
    }
    write_json(output, payload)
    return payload


def render_messages(analysis_payload: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are the mandatory HTML generation layer for a FIFA World Cup prediction system. "
                "Use model deepseek-v4-flash. Convert the supplied analysis JSON into a production-ready "
                "single-file GitHub Pages HTML document. Return raw HTML only, starting with <!doctype html>. "
                "Do not wrap the HTML in JSON or markdown fences. Write all visible UI text in Simplified Chinese."
            ),
        },
        {
            "role": "user",
            "content": (
                "Generate complete responsive HTML. The page must visibly include: "
                "today match predictions, win/draw/loss probabilities, predicted scores, risk analysis, "
                "a token usage panel, and cost estimate. Use these exact placeholders inside the token panel: "
                "{{INPUT_TOKENS}}, {{OUTPUT_TOKENS}}, {{TOTAL_TOKENS}}, {{COST_ESTIMATE}}. "
                "Do not use markdown fences. Analysis payload:\n"
                f"{json.dumps(analysis_payload, ensure_ascii=False)}"
            ),
        },
    ]


def extract_html(raw_content: str) -> str:
    html = raw_content.strip()
    if html.startswith("```"):
        html = re.sub(r"^```(?:html)?\s*", "", html)
        html = re.sub(r"\s*```$", "", html).strip()
    if "<html" in html.lower():
        return html
    raise RuntimeError("DeepSeek V4-Flash render response did not contain HTML")


def inject_usage(html: str, usage: dict[str, Any]) -> str:
    replacements = {
        "{{INPUT_TOKENS}}": str(usage["input_tokens"]),
        "{{OUTPUT_TOKENS}}": str(usage["output_tokens"]),
        "{{TOTAL_TOKENS}}": str(usage["total_tokens"]),
        "{{COST_ESTIMATE}}": f"{usage['cost_estimate']:.6f}",
    }
    for marker, value in replacements.items():
        html = html.replace(marker, value)
    return html


def run_render(analysis_path: Path = ANALYSIS_PATH, latest_path: Path = LATEST_PATH,
               docs_dir: Path = DOCS_DIR) -> dict[str, Any]:
    analysis_payload = read_json(analysis_path)
    content, render_usage, _response = deepseek_chat(
        RENDER_MODEL,
        render_messages(analysis_payload),
        json_object=False,
    )
    analysis_usage = analysis_payload.get("usage") or zero_usage()
    total_usage = combine_usage(analysis_usage, render_usage)
    html = inject_usage(extract_html(content), total_usage)

    payload = {
        "analysis": analysis_payload["analysis"],
        "render": html,
        "usage": total_usage,
        "usage_breakdown": {"analysis": analysis_usage, "render": render_usage},
        "model": {"analysis_model": ANALYSIS_MODEL, "render_model": RENDER_MODEL},
        "generated_at": iso_utc(utc_now()),
        "source": analysis_payload.get("fixtures", {}).get("source", {}),
        "daily_log": [
            *analysis_payload.get("daily_log", []),
            {"time": iso_utc(utc_now()), "stage": "09:45 flash render HTML", "status": "completed"},
        ],
    }
    write_json(latest_path, payload)
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "index.html").write_text(html, encoding="utf-8")
    shutil.copyfile(latest_path, docs_dir / "latest.json")
    (docs_dir / ".nojekyll").write_text("\n", encoding="utf-8")
    return payload


def run_full() -> dict[str, Any]:
    run_research()
    run_analysis()
    return run_render()


def main() -> int:
    parser = argparse.ArgumentParser(description="DeepSeek V4 dual-model World Cup pipeline.")
    subparsers = parser.add_subparsers(dest="stage", required=True)

    research_parser = subparsers.add_parser("research")
    research_parser.add_argument("--start-date")
    research_parser.add_argument("--days", type=int, default=DEFAULT_DAYS)

    subparsers.add_parser("analysis")
    subparsers.add_parser("render")
    subparsers.add_parser("full")

    args = parser.parse_args()
    if args.stage == "research":
        start = dt.date.fromisoformat(args.start_date) if args.start_date else None
        payload = run_research(start=start, days=args.days)
        print(f"research completed fixtures={payload['fixture_count']}")
    elif args.stage == "analysis":
        payload = run_analysis()
        print(f"analysis completed model={payload['model']['analysis_model']}")
    elif args.stage == "render":
        payload = run_render()
        print(f"render completed model={payload['model']['render_model']} tokens={payload['usage']['total_tokens']}")
    elif args.stage == "full":
        payload = run_full()
        print(f"full pipeline completed tokens={payload['usage']['total_tokens']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
