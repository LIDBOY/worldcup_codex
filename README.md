# Daily FIFA World Cup Predictions

Static GitHub Pages site that publishes daily FIFA World Cup fixture predictions.

## Pipeline

- `app/research.py` fetches verified fixtures from ESPN's public FIFA World Cup scoreboard and writes `data/latest.json`.
- `app/validate.py` checks schema, source links, fixture identity, and probability totals.
- `app/render.py` renders `docs/index.html` and `docs/latest.json`.
- `app/publish.py` runs the full research, validation, and render pipeline.

The model only predicts fixtures returned by the configured source. If the source is unavailable or no fixtures are returned, the site publishes that status instead of inventing matches.

## Local Run

```powershell
python app/publish.py
python app/validate.py data/latest.json
```

The pipeline uses only the Python standard library.

## GitHub Pages

Two workflows are configured:

- `.github/workflows/research.yml` runs daily, validates `data/latest.json`, and commits changed research data.
- `.github/workflows/publish.yml` deploys `docs/` to GitHub Pages through the official Pages artifact workflow.

After the first successful `daily-publish` run, the site URL is available from the workflow environment output.
