"""Run with python3 -m opsbrief --input ... --as-of YYYY-MM-DD."""

import argparse
import json
from datetime import date
from pathlib import Path

from .planning import analyze
from .report import render


def main():
    parser = argparse.ArgumentParser(description="Build a local OpsBrief facts report")
    parser.add_argument("--input", type=Path, required=True, help="Normalized snapshot JSON")
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument("--output", type=Path, default=Path("reports/weekly.html"))
    args = parser.parse_args()
    try:
        snapshot = json.loads(args.input.read_text(encoding="utf-8"))
        report = analyze(snapshot, args.as_of)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render(report), encoding="utf-8")
        args.output.with_suffix(".json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Cannot generate report: {exc}\n")
    print(f"HTML: {args.output.resolve()}")
    print(f"JSON: {args.output.with_suffix('.json').resolve()}")


if __name__ == "__main__":
    main()
