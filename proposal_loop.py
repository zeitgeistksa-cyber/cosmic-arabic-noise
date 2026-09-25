#!/usr/bin/env python3
"""
Proposal Loop — reads ACTIVE code, generates proposals.
Uses Groq by default. Writes to proposals_active/.
"""
import json, os, glob, time, subprocess, sys
from datetime import datetime
from pathlib import Path

MODEL = "groq:openai/gpt-oss-20b"
INTERVAL = 180          # 3 minutes
PROPOSALS = Path("proposals_active")
PROPOSALS.mkdir(exist_ok=True)
LOG = Path("proposal_loop.jsonl")

# Files the AI is allowed to read/analyze
SOURCE_FILES = [
    "dialogue_engine.py",
    "phoneme_table.py",
    "phoneme_grammar.py",
    "root_semantics.py",
    "cosmic_semantics.py",
    "tv_space_synth.py",
    "universe_messenger.py",
]


def latest_telemetry_summary():
    """Read recent dialogue turns and summarize."""
    files = sorted(glob.glob("telemetry/session_*_dialogue.jsonl"),
                   key=os.path.getmtime)
    if not files:
        return {"note": "no telemetry"}
    turns = []
    with open(files[-1], encoding="utf-8") as fp:
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
    turns = turns[-200:]
    if not turns:
        return {"note": "no turns in newest file"}
    from collections import Counter
    roots = Counter(t.get("root") for t in turns if t.get("root"))
    cosmics = [t.get("cosmic_raw") or {} for t in turns]
    return {
        "total_turns": len(turns),
        "distinct_roots": len(roots),
        "top_roots": roots.most_common(5),
        "last_cosmic": cosmics[-1] if cosmics else None,
    }


def read_source(name, max_chars=12000):
    p = Path(name)
    if not p.exists():
        return None
    s = p.read_text(encoding="utf-8")
    return s[:max_chars]


def ask(prompt, timeout=120):
    try:
        r = subprocess.run(
            ["aichat", "-m", MODEL],
            input=prompt, capture_output=True, text=True, timeout=timeout,
        )
        return (r.stdout or "").strip() or f"(err: {r.stderr[:200]})"
    except Exception as e:
        return f"(exception: {e})"


def build_prompt(file_name, file_src, telemetry):
    return f"""You are advising an autonomous audio engine that speaks
Arabic phoneme sequences in dialogue with live cosmic data.

CURRENT TELEMETRY (recent turns from the live engine):
{json.dumps(telemetry, indent=2, default=str)}

FILE UNDER REVIEW: {file_name}


Suggest ONE concrete improvement. Focus on:
- Making the sound more interesting
- Better cosmic-to-sound mapping
- More accurate pattern detection
- Cleaner code

Respond with EXACTLY these two sections:

## Reasoning
<one or two sentences>

## Suggested Change
<specific description of what to modify, referencing the function name and
the line or block>

Include a unified git diff in a code block labeled ```diff. The diff must apply with git apply."""


def log(rec):
    rec["ts"] = time.time()
    rec["time"] = datetime.now().isoformat(timespec="seconds")
    with open(LOG, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {rec.get('event')} "
          f"{rec.get('file', '')}", flush=True)


def main():
    print("=" * 62)
    print("PROPOSAL LOOP — active code focus")
    print(f"  Model: {MODEL}")
    print(f"  Every {INTERVAL}s")
    print(f"  Output: {PROPOSALS}/")
    print("=" * 62)

    cycle = 0
    while True:
        cycle += 1
        try:
            telemetry = latest_telemetry_summary()
            log({"event": "cycle", "n": cycle, "turns": telemetry.get("total_turns", 0)})

            # Rotate through the source files
            file_name = SOURCE_FILES[cycle % len(SOURCE_FILES)]
            src = read_source(file_name)
            if src is None:
                log({"event": "skip", "file": file_name, "reason": "not found"})
                time.sleep(INTERVAL)
                continue

            prompt = build_prompt(file_name, src, telemetry)
            response = ask(prompt)

            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prop = PROPOSALS / f"p_{cycle:04d}_{stamp}_{file_name}.md"
            prop.write_text(
                f"# Proposal {cycle}  ({stamp})\n\n"
                f"**File:** `{file_name}`\n\n"
                f"**Telemetry:**\n```json\n"
                f"{json.dumps(telemetry, indent=2, default=str)}\n```\n\n"
                f"**AI Response:**\n\n{response}\n",
                encoding="utf-8",
            )
            log({"event": "proposal", "file": file_name, "path": str(prop)})

        except Exception as e:
            log({"event": "error", "error": str(e)[:200]})

        time.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n>> stopped")
