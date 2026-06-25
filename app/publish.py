from __future__ import annotations

import argparse

import pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full DeepSeek V4 Agent production pipeline.")
    parser.add_argument("--stage", choices=["research", "analysis", "render", "finalize", "full"], default="full")
    args = parser.parse_args()

    if args.stage == "research":
        pipeline.run_research()
    elif args.stage == "analysis":
        pipeline.run_analysis()
    elif args.stage == "render":
        pipeline.run_render()
    elif args.stage == "finalize":
        pipeline.run_finalize()
    else:
        payload = pipeline.run_full()
        print(f"published tokens={payload['usage']['total_tokens']} cost={payload['usage']['cost_estimate']:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
