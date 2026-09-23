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
        if r.get("type") == "state":
            e = r.get("entropy", 0.0); root = r.get("current_root","??")
            bar = "#" * int(e * 6)
            print(f"chunk {r['chunk']:6d}  H={e:5.2f}  root={root}  {bar}")
