from __future__ import annotations

import pipeline


def main() -> int:
    payload = pipeline.run_finalize()
    print(f"finalize completed matches={len(payload['matches'])} tokens={payload['usage']['total_tokens']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
