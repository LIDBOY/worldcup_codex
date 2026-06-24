from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import render
import research
import validate


DEFAULT_DATA = Path("data/latest.json")
DEFAULT_DOCS = Path("docs")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def publish(data_path: Path = DEFAULT_DATA, docs_dir: Path = DEFAULT_DOCS, skip_research: bool = False) -> Path:
    if not skip_research:
        research.run(output=data_path)

    data = load(data_path)
    ok, errors = validate.validate(data)
    if not ok:
        formatted = "\n".join(f"- {error}" for error in errors)
        raise RuntimeError(f"Prediction data failed validation:\n{formatted}")

    return render.write_site(data, output_dir=docs_dir, source_data=data_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the daily World Cup prediction publish pipeline.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--docs", type=Path, default=DEFAULT_DOCS)
    parser.add_argument("--skip-research", action="store_true", help="Render from an existing data/latest.json")
    parser.add_argument("--date", help="UTC date override for research, YYYY-MM-DD")
    parser.add_argument("--days", type=int, help="Fixture window length in days")
    args = parser.parse_args()

    if args.date or args.days is not None:
        start = dt.date.fromisoformat(args.date) if args.date else None
        days = args.days if args.days is not None else research.DEFAULT_DAYS
        research.run(output=args.data, start=start, days=days)
        skip_research = True
    else:
        skip_research = args.skip_research

    index_path = publish(data_path=args.data, docs_dir=args.docs, skip_research=skip_research)
    print(f"Published {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
