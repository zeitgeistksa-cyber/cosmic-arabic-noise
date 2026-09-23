#!/usr/bin/env python3
import sys, json, glob, os, time
files = sorted(glob.glob("telemetry/session_*_dialogue.jsonl"), key=os.path.getmtime)
if not files:
    print("!! No dialogue log yet. Run ./start_dialogue.sh"); sys.exit(1)
latest = files[-1]
print(f">> Following {latest}\n")
print(f"{'turn':>4}  {'root':>4}  {'sim':>5}  {'prosody':>10}  "
      f"{'schum':>5}  {'kp':>4}  {'wind':>5}  heard")
print("-" * 80)
def render(r):
    t = r.get("type")
    if t == "turn":
        raw = r.get("cosmic_raw", {}) or {}
        print(f"{r.get('turn',0):>4}  {r.get('root','?'):>4}  "
              f"{r.get('similarity',0):5.3f}  "
              f"{str((r.get('prosody') or {}).get('weights','')):>10}  "
              f"{str(raw.get('schumann_score','?')):>5}  "
              f"{str(raw.get('kp_value','?')):>4}  "
              f"{str(raw.get('wind_speed','?')):>5}  ...")
    elif t == "decode":
        print(f"      >> decoded: intended={r.get('intended_root','?')}  "
              f"heard_as={r.get('heard','?')}")
with open(latest, encoding="utf-8") as fp:
    lines = fp.readlines()
for line in lines[-50:]:
    line = line.strip()
    if not line: continue
    try: r = json.loads(line)
    except: continue
    render(r)
with open(latest, encoding="utf-8") as fp:
    fp.seek(0, os.SEEK_END)
    while True:
        line = fp.readline()
        if not line:
            time.sleep(0.1); continue
        line = line.strip()
        if not line: continue
        try: r = json.loads(line)
        except: continue
        render(r)
