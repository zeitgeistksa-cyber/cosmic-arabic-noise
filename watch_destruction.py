#!/usr/bin/env python3
"""Live terminal dashboard for the destruction engine."""
import json, os, sys, time
from pathlib import Path

STATE = Path("destruction_state.json")
PARAMS = Path("destruction_params.json")
LOG = Path("destruction_ai_log.jsonl")

def load(p):
    try:
        return json.loads(p.read_text())
    except Exception:
        return None

def read_last_log(n=5):
    if not LOG.exists():
        return []
    lines = LOG.read_text().splitlines()[-n:]
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out

def clear():
    os.system("clear")

def render():
    clear()
    print("=" * 70)
    print("  LIVE DESTRUCTION ENGINE — terminal monitor")
    print("=" * 70)

    state = load(STATE)
    params = load(PARAMS)

    print(f"\n  [{time.strftime('%H:%M:%S')}]")

    if state:
        L = state.get("lorenz", [0,0,0])
        R = state.get("rossler", [0,0,0])
        print(f"\n  PHYSICS")
        print(f"    Lorenz:      [{L[0]:+.3f}, {L[1]:+.3f}, {L[2]:+.3f}]")
        print(f"    Rossler:     [{R[0]:+.3f}, {R[1]:+.3f}, {R[2]:+.3f}]")
        lock = state.get("twin_lock", 0)
        bar = "#" * int(lock * 30)
        print(f"    Twin lock:   {lock:.3f}  {bar}")
    else:
        print("\n  (no state — engine not running)")

    if params:
        print(f"\n  PARAMETERS")
        for k in sorted(params):
            v = params[k]
            print(f"    {k:18s}  {v:.4f}")

    log = read_last_log(8)
    if log:
        print(f"\n  RECENT AI ACTIONS")
        for entry in log:
            t = entry.get("time", "")[11:19]
            ev = entry.get("event", "?")
            if ev == "applied":
                print(f"    {t}  APPLIED  {entry['param']}: "
                      f"{entry['old']:.3f} -> {entry['new']:.3f}  "
                      f"({entry.get('reason','')[:40]})")
            elif ev == "ask":
                print(f"    {t}  ASK      lock={entry.get('twin_lock', 0):.3f}")
            elif ev == "reject":
                print(f"    {t}  REJECT   {entry.get('reason','')}")
            elif ev == "skip":
                print(f"    {t}  SKIP     {entry.get('reason','')}")
            else:
                print(f"    {t}  {ev.upper()}")

    print("\n" + "=" * 70)
    print("  Ctrl+C to exit. Engine keeps running in tmux.")
    print("=" * 70)


if __name__ == "__main__":
    try:
        while True:
            render()
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n")
        sys.exit(0)
