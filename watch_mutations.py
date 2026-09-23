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
        if r.get("type") == "mutation":
            w = r["theory_weights"]
            print(f"MUT #{r['mutation_index']:3d}  chunk={r['chunk']:6d}  "
                  f"root={r.get('current_root','??')}  "
                  f"omega0={r['omega_0']:5.1f}  k={r['coupling_k']:4.2f}  "
                  f"theory=[{w[0]:.2f},{w[1]:.2f},{w[2]:.2f},{w[3]:.2f}]")
