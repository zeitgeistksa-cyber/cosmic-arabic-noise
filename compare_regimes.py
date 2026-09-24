#!/usr/bin/env python3
import json, glob, os
import numpy as np
from collections import Counter

buckets = {}
for f in glob.glob("telemetry/session_*_dialogue.jsonl"):
    with open(f, encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line: continue
            try: r = json.loads(line)
            except: continue
            if r.get("type") != "turn": continue
            kp = (r.get("cosmic_raw") or {}).get("kp_value")
            if kp is None: continue
            kp_bucket = f"Kp_{int(kp)}"
            buckets.setdefault(kp_bucket, Counter())[r["root"]] += 1

for regime in sorted(buckets):
    c = buckets[regime]
    total = sum(c.values())
    print(f"\n{regime}  (n={total})")
    for root, n in c.most_common(10):
        pct = 100 * n / total
        bar = "█" * int(pct)
        print(f"  {root}  {n:4d}  {pct:5.1f}%  {bar}")
