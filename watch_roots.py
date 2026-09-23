#!/usr/bin/env python3
import sys, json, glob, os, time
files = sorted(glob.glob("telemetry/session_*.jsonl"), key=os.path.getmtime)
if not files: print("!! No telemetry."); sys.exit(1)
latest = files[-1]; print(f">> Following {latest}\n")
with open(latest) as fp:
    fp.seek(0, os.SEEK_END)
    while True:
        line = fp.readline()
        if not line: time.sleep(0.1); continue
        line = line.strip()
        if not line: continue
        try: r = json.loads(line)
        except: continue
        if r.get("type") == "root_change":
            t = r.get("triad") or [0,0,0]
            print(f"ROOT >>> {r.get('root','???')}   "
                  f"f1={t[0]:8.1f}  f2={t[1]:8.1f}  f3={t[2]:9.1f} Hz   "
                  f"chunk={r.get('chunk',0):6d}")
