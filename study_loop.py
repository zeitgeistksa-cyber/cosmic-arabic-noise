#!/usr/bin/env python3
"""
Continuous study loop.
Every 30 minutes:
  1. Runs find_patterns.py
  2. Runs position + correlation controls
  3. Computes the current attractor's similarity to the last N hours
  4. Tracks whether findings are stable or drifting
  5. Appends to experiments/timeline.jsonl
"""
import subprocess, time, json, os, glob
from pathlib import Path
from datetime import datetime

TIMELINE = Path("experiments/timeline.jsonl")
TIMELINE.parent.mkdir(exist_ok=True)
REPORTS = Path("experiments/reports")
REPORTS.mkdir(exist_ok=True)

INTERVAL_SEC = 1800


def run(cmd):
    """Run a shell command and return stdout."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True,
                           text=True, timeout=120)
        return r.stdout
    except Exception as e:
        return f"!! error: {e}"


def parse_correlations(output):
    """Extract the top correlations from find_patterns output."""
    lines = output.splitlines()
    corrs = {}
    in_section = False
    for line in lines:
        if "Strong correlations" in line:
            in_section = True
            continue
        if in_section:
            if line.strip().startswith("==") or line.strip().startswith("==="):
                break
            if "↔" in line and "r =" in line:
                try:
                    left = line.split("↔")
                    pair = left[0].split()[-1] + "-" + left[1].split()[0]
                    r_str = line.split("r =")[1].split()[0]
                    corrs[pair] = float(r_str)
                except Exception:
                    pass
    return corrs


def parse_position(output):
    """Extract position enrichment from position_control output."""
    enrich = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 7 and parts[0] in "ضزذصطج":
            try:
                enrich[parts[0]] = float(parts[3])
            except ValueError:
                pass
    return enrich


def current_cosmic():
    out = run("python cosmic_data.py")
    try:
        return json.loads(out)
    except Exception:
        return {}


def count_turns():
    n = 0
    for f in glob.glob("telemetry/session_*_dialogue.jsonl"):
        with open(f, encoding="utf-8") as fp:
            for line in fp:
                if '"type": "turn"' in line:
                    n += 1
    return n


def main():
    print(f">> study loop started at {datetime.now().isoformat()}")
    while True:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"\n[{ts}] starting analysis cycle")

        # Current cosmic state
        cosmic = current_cosmic()
        print(f"[{ts}] cosmic: schumann={cosmic.get('schumann_score')} "
              f"kp={cosmic.get('kp_value')} wind={cosmic.get('wind_speed')}")

        # Run analyses
        patterns_out = run("python find_patterns.py")
        position_out = run("python position_control.py")
        english_out = run("python run_english_attractor.py")

        # Parse results
        corrs = parse_correlations(patterns_out)
        enrich = parse_position(position_out)
        turns = count_turns()

        # Save full reports
        (REPORTS / f"patterns_{ts}.txt").write_text(patterns_out)
        (REPORTS / f"position_{ts}.txt").write_text(position_out)
        (REPORTS / f"english_{ts}.txt").write_text(english_out)

        # Append to timeline
        record = {
            "timestamp": ts,
            "turns_total": turns,
            "cosmic": {
                "schumann": cosmic.get("schumann_score"),
                "kp": cosmic.get("kp_value"),
                "wind": cosmic.get("wind_speed"),
                "bz": cosmic.get("bz"),
            },
            "top_correlations": corrs,
            "position_enrichment": enrich,
        }
        with open(TIMELINE, "a", encoding="utf-8") as fp:
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")

        print(f"[{ts}] turns={turns}  correlations={len(corrs)}  "
              f"enrichment_letters={len(enrich)}")
        print(f"[{ts}] wrote experiments/timeline.jsonl")

        # Wait
        time.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n>> stopped")
