"""Cosmic time series loader."""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_cosmic_series():
    """Load the timeline as a time series."""
    path = PROJECT_ROOT / "experiments" / "timeline.jsonl"
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except Exception:
            continue
    return entries
