#!/usr/bin/env python3
import sys, json, glob, os, time
files = sorted(glob.glob("telemetry/session_*_dialogue.jsonl"), key=os.path.getmtime)
if not files:
    print("!! No dialogue log yet. Run ./start_dialogue.sh"); sys.exit(1)
latest = files[-1]
print(f">> Following {latest}\n")
print(f"{'turn':>4}  {'root':>4}  {'sim':>5}  {'prosody':>10}  "
      f"{'schumann':>8}  {'kp':>4}  {'wind':>5}  heard")
print("-" * 90)
with open(latest) as fp:
    fp.seek(0, os.SEEK_END)
    pending = {}
    while True:
        line = fp.readline()
        if not line: time.sleep(0.1); continue
        line = line.strip()
        if not line: continue
        try: r = json.loads(line)
        except: continue
        t = r.get("type")
        if t == "turn":
            pending[r["turn"]] = r
            raw = r.get("cosmic_raw", {})
            print(f"{r['turn']:>4}  {r['root']:>4}  {r['similarity']:5.3f}  "
                  f"{str(r['prosody']['weights']):>10}  "
                  f"{raw.get('schumann_score','?'):>8}  "
                  f"{raw.get('kp_value','?'):>4}  "
                  f"{raw.get('wind_speed','?'):>5}  ...")
        elif t == "decode":
            intended = r.get("intended_root", "?")
            heard = r.get("heard", "?")
            print(f"      >> decoded: intended={intended}  heard_as={heard}")
