"""Root sequence loaders."""
import json, glob, os
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_engine_turns(max_files=None):
    """Load all engine dialogue turns from telemetry/*.jsonl.

    Returns list of dicts: {root, cosmic, features, session}.
    """
    files = sorted(glob.glob(str(PROJECT_ROOT / "telemetry" / "session_*_dialogue.jsonl")))
    if max_files:
        files = files[-max_files:]

    turns = []
    for f in files:
        session = os.path.basename(f).replace(".jsonl", "")
        with open(f, encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("type") != "turn":
                    continue
                turns.append({
                    "root": r.get("root"),
                    "similarity": r.get("similarity"),
                    "cosmic": r.get("cosmic_raw") or {},
                    "triad": r.get("triad"),
                    "prosody": r.get("prosody"),
                    "session": session,
                    "chunk": r.get("chunk"),
                    "ts": r.get("ts"),
                })
    return turns


def load_quran_roots(path=None):
    """Load the extracted root sequence from the Quran."""
    if path is None:
        path = PROJECT_ROOT / "experiments" / "quran" / "analysis.json"
    if not Path(path).exists():
        return []
    data = json.loads(Path(path).read_text())
    # top_roots is [[root, count], ...]
    return [(r, n) for r, n in data.get("top_roots", [])]


def load_poem_roots():
    """Load all poem root files."""
    files = sorted(glob.glob(str(PROJECT_ROOT / "poem_roots*.json")))
    poems = []
    for f in files:
        try:
            data = json.loads(Path(f).read_text())
            poems.append({
                "title": data.get("title"),
                "roots": [e["root"] for e in data.get("sequence", [])],
                "file": os.path.basename(f),
            })
        except Exception:
            continue
    return poems
