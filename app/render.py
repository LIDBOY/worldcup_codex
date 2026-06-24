from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path
from typing import Any


DEFAULT_DATA = Path("data/latest.json")
DEFAULT_OUTPUT_DIR = Path("docs")


STATUS_LABELS = {
    "ready": "已就绪",
    "no_verified_fixtures": "暂无已验证赛程",
    "source_unavailable": "数据源暂不可用",
}


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def percent(value: Any) -> str:
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "0.0%"


def initials(name: str) -> str:
    parts = [part[0] for part in name.split() if part]
    return "".join(parts[:3]).upper() or "T"


def logo_or_initial(team: dict[str, Any]) -> str:
    name = team.get("name") or "Team"
    logo = team.get("logo")
    if logo:
        return f'<img class="team-logo" src="{esc(logo)}" alt="{esc(name)} logo" loading="lazy">'
    return f'<span class="team-initial">{esc(initials(name))}</span>'


def render_probability(label: str, value: Any) -> str:
    try:
        width = max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        width = 0.0
    return f"""
      <div class="prob-row">
        <span>{esc(label)}</span>
        <div class="prob-track" aria-hidden="true"><span style="width: {width:.1f}%"></span></div>
        <strong>{percent(value)}</strong>
      </div>
    """


def render_match(match: dict[str, Any]) -> str:
    teams = match.get("teams") or {}
    team_a = teams.get("team_a") or {}
    team_b = teams.get("team_b") or {}
    team_a_name = team_a.get("name") or "Team A"
    team_b_name = team_b.get("name") or "Team B"
    prediction = match.get("prediction") or {}
    probabilities = prediction.get("probabilities") or {}
    venue = match.get("venue") or {}
    status = match.get("status") or {}

    score_a = team_a.get("score")
    score_b = team_b.get("score")
    score = ""
    if score_a not in (None, "") or score_b not in (None, ""):
        score = f'<span class="score">{esc(score_a)} - {esc(score_b)}</span>'

    prediction_html = ""
    if probabilities:
        prediction_html = f"""
          <div class="probabilities">
            {render_probability(f"{team_a_name} 胜", probabilities.get("team_a_win"))}
            {render_probability("平局", probabilities.get("draw"))}
            {render_probability(f"{team_b_name} 胜", probabilities.get("team_b_win"))}
          </div>
        """
    else:
        prediction_html = '<p class="muted compact">已完赛，预测关闭。</p>'

    location_bits = [venue.get("name"), venue.get("city"), venue.get("country")]
    location = " - ".join(str(bit) for bit in location_bits if bit)

    return f"""
      <article class="match-card">
        <div class="match-meta">
          <time datetime="{esc(match.get("kickoff_utc"))}">{esc(match.get("kickoff_utc"))}</time>
          <span>{esc(status.get("detail") or status.get("state") or "scheduled")}</span>
        </div>
        <div class="teams">
          <div class="team">{logo_or_initial(team_a)}<strong>{esc(team_a_name)}</strong></div>
          <div class="versus">{score or "对阵"}</div>
          <div class="team right">{logo_or_initial(team_b)}<strong>{esc(team_b_name)}</strong></div>
        </div>
        {prediction_html}
        <div class="match-footer">
          <span>{esc(location or "场地待定")}</span>
          <a href="{esc((match.get("source") or {}).get("event_url"))}" rel="noopener" target="_blank">来源</a>
        </div>
      </article>
    """


def render_status(data: dict[str, Any]) -> str:
    status = data.get("status")
    if status == "ready":
        return ""
    warnings = data.get("warnings") or []
    warning_items = "".join(f"<li>{esc(item)}</li>" for item in warnings[:4])
    if not warning_items:
        warning_items = "<li>当前预测窗口内没有返回已验证赛程。</li>"
    return f"""
      <section class="notice">
        <h2>赛程状态</h2>
        <p>网站已上线，但只会发布经配置数据源验证过的比赛预测。</p>
        <ul>{warning_items}</ul>
      </section>
    """


def render(data: dict[str, Any]) -> str:
    matches = data.get("matches") or []
    cards = "\n".join(render_match(match) for match in matches)
    if not cards:
        cards = '<p class="empty">当前窗口暂无已验证的世界杯赛程。</p>'

    source_urls = (data.get("source") or {}).get("urls") or []
    source_links = " ".join(
        f'<a href="{esc(url)}" rel="noopener" target="_blank">来源 {index + 1}</a>'
        for index, url in enumerate(source_urls[:5])
    )
    if source_links:
        source_links += " "
    status_label = STATUS_LABELS.get(data.get("status"), str(data.get("status", "未知状态")).replace("_", " "))

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>每日 FIFA 世界杯预测</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17201d;
      --muted: #60706a;
      --line: #d8e0dc;
      --paper: #f7faf8;
      --panel: #ffffff;
      --accent: #147a4a;
      --accent-2: #c83f31;
      --accent-3: #1c6aa7;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, "Microsoft YaHei", "PingFang SC", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--paper);
      letter-spacing: 0;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    .wrap {{
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
    }}
    .topbar {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 24px;
      align-items: end;
      padding: 30px 0 24px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: clamp(28px, 4vw, 48px);
      line-height: 1.02;
      font-weight: 800;
    }}
    .subtitle {{
      margin: 0;
      color: var(--muted);
      max-width: 760px;
      line-height: 1.5;
    }}
    .status-pill {{
      display: inline-flex;
      align-items: center;
      min-height: 38px;
      padding: 0 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f1f6f3;
      color: var(--accent);
      font-weight: 700;
      white-space: nowrap;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      padding: 18px 0 26px;
    }}
    .stat {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 14px 16px;
      min-height: 86px;
    }}
    .stat span {{
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 8px;
    }}
    .stat strong {{
      display: block;
      font-size: 20px;
      line-height: 1.25;
      overflow-wrap: anywhere;
    }}
    main {{ padding: 24px 0 42px; }}
    .notice {{
      border: 1px solid #e3c7bd;
      border-left: 4px solid var(--accent-2);
      border-radius: 8px;
      background: #fff8f5;
      padding: 16px 18px;
      margin-bottom: 18px;
    }}
    .notice h2 {{
      margin: 0 0 8px;
      font-size: 18px;
    }}
    .notice p {{ margin: 0 0 8px; color: var(--muted); }}
    .notice ul {{ margin: 0; padding-left: 20px; color: var(--muted); }}
    .section-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 14px;
    }}
    .section-head h2 {{
      margin: 0;
      font-size: 22px;
    }}
    .source-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      justify-content: flex-end;
    }}
    a {{ color: var(--accent-3); text-decoration: none; font-weight: 650; }}
    a:hover {{ text-decoration: underline; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 360px), 1fr));
      gap: 16px;
    }}
    .match-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 16px;
      min-height: 292px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}
    .match-meta, .match-footer {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      color: var(--muted);
      font-size: 13px;
    }}
    .match-footer {{
      border-top: 1px solid var(--line);
      padding-top: 12px;
      margin-top: auto;
    }}
    .teams {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 54px minmax(0, 1fr);
      align-items: center;
      gap: 10px;
    }}
    .team {{
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
    }}
    .team.right {{
      justify-content: flex-end;
      text-align: right;
    }}
    .team strong {{
      font-size: 17px;
      line-height: 1.25;
      overflow-wrap: anywhere;
    }}
    .team-logo, .team-initial {{
      width: 38px;
      height: 38px;
      flex: 0 0 38px;
      border-radius: 50%;
      border: 1px solid var(--line);
      background: #edf3ef;
      object-fit: contain;
      display: grid;
      place-items: center;
      font-size: 12px;
      font-weight: 800;
      color: var(--accent);
    }}
    .versus, .score {{
      min-width: 54px;
      text-align: center;
      font-weight: 800;
      color: var(--muted);
    }}
    .score {{ color: var(--ink); }}
    .probabilities {{
      display: grid;
      gap: 10px;
    }}
    .prob-row {{
      display: grid;
      grid-template-columns: minmax(92px, 1fr) minmax(92px, 1.4fr) 56px;
      gap: 10px;
      align-items: center;
      font-size: 13px;
    }}
    .prob-row span:first-child {{
      overflow-wrap: anywhere;
    }}
    .prob-track {{
      height: 10px;
      border-radius: 999px;
      background: #e9efec;
      overflow: hidden;
    }}
    .prob-track span {{
      display: block;
      height: 100%;
      background: var(--accent);
    }}
    .prob-row:nth-child(2) .prob-track span {{ background: var(--accent-3); }}
    .prob-row:nth-child(3) .prob-track span {{ background: var(--accent-2); }}
    .empty {{
      border: 1px dashed var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 24px;
      color: var(--muted);
    }}
    .muted {{ color: var(--muted); }}
    .compact {{ margin: 0; }}
    footer {{
      border-top: 1px solid var(--line);
      color: var(--muted);
      padding: 22px 0 30px;
      background: var(--panel);
      font-size: 13px;
    }}
    @media (max-width: 700px) {{
      .topbar, .stats {{
        grid-template-columns: 1fr;
      }}
      .status-pill {{
        justify-content: center;
        width: 100%;
      }}
      .section-head {{
        display: block;
      }}
      .source-links {{
        justify-content: flex-start;
        margin-top: 10px;
      }}
      .teams {{
        grid-template-columns: 1fr;
      }}
      .versus, .score {{
        min-width: 0;
        text-align: left;
      }}
      .team.right {{
        justify-content: flex-start;
        text-align: left;
      }}
      .prob-row {{
        grid-template-columns: 1fr 52px;
      }}
      .prob-track {{
        grid-column: 1 / -1;
        grid-row: 2;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <div class="topbar">
        <div>
          <h1>每日 FIFA 世界杯预测</h1>
          <p class="subtitle">每日自动抓取并校验世界杯赛程，只对来源确认的比赛生成预测；页面同步保留原始 JSON，方便核验。</p>
        </div>
        <span class="status-pill">{esc(status_label)}</span>
      </div>
      <div class="stats">
        <div class="stat"><span>生成时间</span><strong>{esc(data.get("generated_at"))}</strong></div>
        <div class="stat"><span>预测窗口</span><strong>{esc((data.get("window") or {}).get("start_date"))} / {esc((data.get("window") or {}).get("days"))} 天</strong></div>
        <div class="stat"><span>已验证赛程</span><strong>{esc(data.get("match_count", 0))}</strong></div>
      </div>
    </div>
  </header>
  <main class="wrap">
    {render_status(data)}
    <div class="section-head">
      <h2>未来赛程</h2>
      <div class="source-links">{source_links}<a href="latest.json">原始 JSON</a></div>
    </div>
    <section class="grid">
      {cards}
    </section>
  </main>
  <footer>
    <div class="wrap">{esc(data.get("disclaimer"))}</div>
  </footer>
</body>
</html>
"""


def load_data(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_site(data: dict[str, Any], output_dir: Path = DEFAULT_OUTPUT_DIR, source_data: Path = DEFAULT_DATA) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "index.html"
    index_path.write_text(render(data), encoding="utf-8")
    shutil.copyfile(source_data, output_dir / "latest.json")
    return index_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the World Cup prediction static site.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    index_path = write_site(load_data(args.data), args.output_dir, args.data)
    print(f"Wrote {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
