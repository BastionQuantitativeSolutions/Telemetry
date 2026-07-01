#!/usr/bin/env python3
"""Build aggregated signal and execution files from by_date data.

Run this after cloning the repo to generate the concatenated files locally.
"""

from pathlib import Path
import sys

def main():
    repo = Path(__file__).parent.parent
    by_date = repo / "by_date"
    agg = repo / "aggregated"
    agg.mkdir(exist_ok=True)

    for fname in ("signals.jsonl", "execution.jsonl"):
        out_path = agg / fname.replace(".jsonl", "_all.jsonl")
        count = 0
        with open(out_path, "w", encoding="utf-8") as out_f:
            for date_dir in sorted(by_date.iterdir()):
                src = date_dir / fname
                if src.exists():
                    with open(src, "r", encoding="utf-8") as in_f:
                        for line in in_f:
                            out_f.write(line)
                            count += 1
        print(f"Built {out_path} ({count} lines)")

    return 0

if __name__ == "__main__":
    sys.exit(main())
