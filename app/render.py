from __future__ import annotations

import pipeline


def main() -> int:
    payload = pipeline.run_render()
    print(f"render completed model={payload['render_model']} tokens={payload['usage']['total_tokens']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
