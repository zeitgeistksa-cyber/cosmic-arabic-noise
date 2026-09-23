#!/usr/bin/env python3
"""
Autonomous Developer Loop
=========================
Every N seconds:
  1. Reads the latest telemetry summary
  2. Asks aichat for a code improvement suggestion
  3. Extracts any code block from the response
  4. Writes it to a proposals/ folder for review
  5. Logs everything to logs/autonomous.jsonl

The developer (you) reviews proposals and applies them manually,
or the loop can be extended to auto-apply with git commit.
"""
import json, time, subprocess, glob, os, re
from pathlib import Path
from datetime import datetime

PROPOSALS = Path("proposals"); PROPOSALS.mkdir(exist_ok=True)
LOGS = Path("logs"); LOGS.mkdir(exist_ok=True)
LOG_FILE = LOGS / "autonomous.jsonl"
INTERVAL = 120  # seconds between AI suggestions

def log(record):
    record["ts"] = time.time()
    record["time"] = datetime.now().isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(record, ensure_ascii=False) + "\n")

def latest_telemetry():
    files = sorted(glob.glob("telemetry/session_*.jsonl"), key=os.path.getmtime)
    if not files:
        return None
    return files[-1]

def telemetry_summary(path):
    """Read the last 200 lines and summarize."""
    lines = []
    with open(path, encoding="utf-8") as fp:
        for line in fp:
            lines.append(line)
    recent = lines[-200:]
    muts = 0; roots = set(); avg_ent = 0; n = 0
    for line in recent:
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("type") == "mutation":
            muts += 1
        elif r.get("type") == "state":
            avg_ent += r.get("entropy", 0)
            n += 1
            if r.get("current_root"):
                roots.add(r["current_root"])
    return {
        "recent_mutations": muts,
        "recent_states": n,
        "avg_entropy": avg_ent / n if n else 0,
        "distinct_roots": len(roots),
        "sample_roots": sorted(roots)[:10],
    }

def ask_ai(prompt, files=None):
    """Call aichat with the prompt and optional files."""
    cmd = ["aichat"]
    if files:
        for f in files:
            cmd.extend(["-f", f])
    cmd.append(prompt)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "!! aichat timed out"
    except Exception as e:
        return f"!! aichat error: {e}"

def extract_code_blocks(text):
    """Extract fenced code blocks from markdown."""
    return re.findall(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL)

def main():
    log({"event": "start", "interval": INTERVAL})
    print(f">> Autonomous developer loop running (interval={INTERVAL}s)")
    print(f">> Logs: {LOG_FILE}")
    print(f">> Proposals: {PROPOSALS}/")
    print(">> Ctrl+C to stop")
    iteration = 0
    while True:
        iteration += 1
        tel = latest_telemetry()
        if tel is None:
            print(">> No telemetry yet. Waiting...")
            time.sleep(INTERVAL)
            continue
        summary = telemetry_summary(tel)
        print(f"\n[{iteration}] Telemetry: {summary}")
        prompt = (
            f"You are an AI sound engineering assistant working on a live "
            f"neural noise engine driven by Arabic phoneme acoustics and cosmic data. "
            f"\n\nLatest telemetry summary:\n{json.dumps(summary, indent=2)}"
            f"\n\nSuggest ONE concrete code improvement to arabic_noise_engine.py "
            f"or train_gen.py. Be specific — name the function and the change. "
            f"Format: a short explanation, then a single fenced python code block "
            f"containing ONLY the new version of the function or block to replace."
        )
        response = ask_ai(prompt, files=["arabic_noise_engine.py", "train_gen.py"])
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        proposal_path = PROPOSALS / f"proposal_{ts}.md"
        proposal_path.write_text(
            f"# Proposal {ts}\n\n"
            f"## Telemetry\n\n```json\n{json.dumps(summary, indent=2)}\n```\n\n"
            f"## AI Response\n\n{response}\n",
            encoding="utf-8",
        )
        log({"event": "proposal", "iteration": iteration,
             "path": str(proposal_path), "summary": summary})
        print(f">> Proposal written: {proposal_path}")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log({"event": "stop"})
        print("\n>> Autonomous loop stopped.")
