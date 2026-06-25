from __future__ import annotations

import argparse
import datetime as dt

import pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the 08:15 Agent research stage.")
    parser.add_argument("--start-date")
    parser.add_argument("--days", type=int, default=pipeline.DEFAULT_DAYS)
    args = parser.parse_args()

    start = dt.date.fromisoformat(args.start_date) if args.start_date else None
    payload = pipeline.run_research(start=start, days=args.days)
    print(f"research completed fixtures={payload['fixture_count']} odds={payload['odds_available_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
