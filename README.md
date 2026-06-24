# Daily FIFA World Cup Predictions

Production GitHub Pages system for daily FIFA World Cup predictions.

## DeepSeek V4 Model Strategy

- Analysis engine: `deepseek-v4-pro`
  - Used for football match analysis, win/draw/loss probabilities, score prediction, tactical analysis, and risk analysis.
  - Request parameters include `reasoning_effort = "high"` and `thinking = "enabled"`.
- Generation engine: `deepseek-v4-flash`
  - Used for HTML generation, output formatting, JSON organization, and token/cost UI.

API configuration:

```text
base_url = https://api.deepseek.com
api_key = os.environ["DEEPSEEK_API_KEY"]
```

The pipeline never fabricates fixtures or DeepSeek responses. ESPN's public FIFA World Cup scoreboard is used only as the verified fixture source.

## Daily Schedule

All cron values are UTC, aligned to Asia/Shanghai local time:

- 08:15 CST: `.github/workflows/research.yml` fetches verified fixtures and writes `data/fixtures.json`.
- 09:40 CST: `.github/workflows/analysis.yml` calls `deepseek-v4-pro` and writes `data/analysis.json`.
- 09:45 CST: `.github/workflows/render.yml` calls `deepseek-v4-flash`, writes `data/latest.json`, `docs/index.html`, and `docs/latest.json`.
- 10:00 CST: `.github/workflows/publish.yml` validates `data/latest.json` and triggers a GitHub Pages build.

## Output Contract

`data/latest.json` uses this top-level contract:

```json
{
  "analysis": {},
  "render": "<!doctype html>...",
  "usage": {
    "input_tokens": 0,
    "output_tokens": 0,
    "total_tokens": 0,
    "cost_estimate": 0
  },
  "model": {
    "analysis_model": "deepseek-v4-pro",
    "render_model": "deepseek-v4-flash"
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
python app/validate.py data/latest.json
```

Running `analysis`, `render`, or `full` requires `DEEPSEEK_API_KEY`.

## GitHub Secret

Set repository secret:

```text
DEEPSEEK_API_KEY
```

Without this secret, the analysis/render workflows fail intentionally instead of producing mock data.
