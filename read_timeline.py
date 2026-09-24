#!/usr/bin/env python3
"""Plot the evolution of findings over time."""
import json
import numpy as np
from pathlib import Path

records = []
with open("experiments/timeline.jsonl") as fp:
    for line in fp:
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except: pass

print(f"=== {len(records)} timeline entries ===\n")

if len(records) < 2:
    print("!! need at least 2 entries")
    raise SystemExit

# Turns growth
turns = [r["turns_total"] for r in records]
print(f"Turns: {turns[0]} → {turns[-1]}  (+{turns[-1]-turns[0]})")

# Cosmic states
for key in ("schumann", "kp", "wind"):
    vals = [r["cosmic"].get(key) for r in records if r["cosmic"].get(key) is not None]
    if vals:
        print(f"{key:10s}  min={min(vals):.1f}  max={max(vals):.1f}  "
              f"mean={np.mean(vals):.1f}  std={np.std(vals):.1f}")

# Correlation stability
print("\n=== Correlation stability ===")
corr_keys = set()
for r in records:
    corr_keys.update(r.get("top_correlations", {}).keys())

for key in sorted(corr_keys):
    vals = [r["top_correlations"][key] for r in records
            if key in r.get("top_correlations", {})]
    if len(vals) >= 2:
        print(f"  {key:35s}  "
              f"mean={np.mean(vals):+.3f}  std={np.std(vals):.3f}  "
              f"last={vals[-1]:+.3f}")

# Position enrichment stability
print("\n=== Position enrichment stability ===")
letters = set()
for r in records:
    letters.update(r.get("position_enrichment", {}).keys())

for letter in sorted(letters):
    vals = [r["position_enrichment"][letter] for r in records
            if letter in r.get("position_enrichment", {})]
    if len(vals) >= 2:
        print(f"  {letter}  mean={np.mean(vals):6.2f}  std={np.std(vals):5.2f}  "
              f"last={vals[-1]:6.2f}")
