# Daily FIFA World Cup AI Agent

Production GitHub Pages system for daily FIFA World Cup predictions.

## V3 Agent Architecture

Data layer:

- FIFA official calendar API is the primary fixture source.
- ESPN FIFA World Cup scoreboard is the second source used to verify match authenticity.
- ESPN odds feed is used for moneyline odds and implied probability conversion when available.
- FIFA official search plus ESPN World Cup news are scanned for injury/suspension signals.
- Injury labels are source-bound: `confirmed injury` requires an official FIFA article, `probable injury` requires media evidence, and `unknown` means no supported source was found.

Analysis layer:

- Model: `deepseek-v4-pro`
- Purpose: match analysis, tactical matchup, win/draw/loss probabilities, xG, injury adjustment, risk, and upset probability.
- Parameters: `reasoning_effort = "high"` and `thinking = enabled`.
- No other model is used for match analysis.

Generation layer:

- Model: `deepseek-v4-flash`
- Purpose: HTML page generation, JSON shaping, visible token usage, and cost UI.

API configuration:

```text
base_url = https://api.deepseek.com
api_key = os.environ["DEEPSEEK_API_KEY"]
```

The pipeline fails instead of producing mock data when required upstream data or DeepSeek credentials are unavailable.

## Daily Schedule

All cron values are UTC, aligned to Asia/Shanghai local time:

- 08:15 CST: `.github/workflows/research.yml` fetches FIFA fixtures, verifies ESPN source, scans injuries, and extracts odds.
- 08:30 CST: `.github/workflows/analysis.yml` calls `deepseek-v4-pro`.
- 09:00 CST: `.github/workflows/render.yml` calls `deepseek-v4-flash` and writes HTML.
- 09:30 CST: `.github/workflows/finalize.yml` writes `data/latest.json`, token usage, and Pages JSON.
- 10:00 CST: `.github/workflows/publish.yml` validates and deploys GitHub Pages.

## Output Contract

`data/latest.json` contains:

```json
{
  "matches": [],
  "analysis_model": "deepseek-v4-pro",
  "render_model": "deepseek-v4-flash",
  "usage": {
    "input_tokens": 0,
    "output_tokens": 0,
    "total_tokens": 0,
    "cost_estimate": 0
  },
  "data_sources": {
    "fifa": true,
    "injury": true,
    "odds": true
  }
}
```

`cost_estimate` is calculated as:

```text
total_tokens * 0.00001
```

## Local Commands

```powershell
python app/pipeline.py research
python app/pipeline.py analysis
python app/pipeline.py render
python app/pipeline.py finalize
python app/validate.py data/latest.json
```

Running `analysis`, `render`, or `full` requires `DEEPSEEK_API_KEY`.

## Project Requirements Log

The upgrade/build history is tracked in `项目基本要求.md`. Every future system update should append a dated entry there.
