#!/usr/bin/env python3
"""Write the latest telemetry + cosmic state to a small JSON for the web viewer."""
import json, glob, os, time
from collections import Counter
from pathlib import Path

OUT = Path("snapshot.json")
OUT.parent.mkdir(exist_ok=True)

def latest_dialogue():
    files = sorted(glob.glob("telemetry/session_*_dialogue.jsonl"),
                   key=os.path.getmtime)
    return files[-1] if files else None

def summarize(path, tail_n=200):
    if path is None:
        return {"turns": 0}
    turns, decodes = [], []
    with open(path, encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("type") == "turn":
                turns.append(r)
            elif r.get("type") == "decode":
                decodes.append(r)
    recent = turns[-tail_n:]
    root_counts = Counter(t["root"] for t in recent)
    return {
        "session": os.path.basename(path),
        "turns_total": len(turns),
        "turns_recent": len(recent),
        "distinct_roots": len(root_counts),
        "top_roots": root_counts.most_common(15),
        "last_cosmic": (recent[-1].get("cosmic_raw") if recent else None),
        "last_triad": (recent[-1].get("triad") if recent else None),
        "recent_turns": [
            {"turn": t["turn"], "root": t["root"],
             "sim": round(t.get("similarity", 0), 3),
             "cosmic": t.get("cosmic_raw")}
            for t in recent[-25:]
        ],
        "recent_decodes": [
            {"intended": d.get("intended_root"), "heard": d.get("heard")}
            for d in decodes[-25:]
        ],
    }

def main():
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "engine_version": "4.1",
        "latest": summarize(latest_dialogue()),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f">> wrote {OUT}")

if __name__ == "__main__":
    main()
