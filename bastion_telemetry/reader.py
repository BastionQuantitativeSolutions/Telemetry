"""Readers for sanitized daily telemetry artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


def read_jsonl(path: str | Path) -> Iterator[dict[str, Any]]:
    """Yield JSONL rows from a sanitized telemetry file."""
    telemetry_path = Path(path)
    with telemetry_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)
