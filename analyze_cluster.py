#!/usr/bin/env python3
"""
Cluster reality test for the new pure-acoustic vectors.
Reports:
  1. Baseline top-10 under the current cosmic state
  2. Ablation: which cosmic dim actually drives selection
  3. Random baseline: top-10 under 500 random cosmic vectors
  4. Observed telemetry top-10 (all-time)
  5. Excess letter frequencies vs uniform
"""
import json, glob, os, random
from collections import Counter
import numpy as np

from phoneme_table import PHONEMES
from root_semantics import precompute, cosine
from cosmic_semantics import cosmic_semantic_vector


# ---------- Load roots ----------
def load_roots():
    lines = open("arabic_db/roots.txt", encoding="utf-8").read().splitlines()
    return sorted({ln.strip() for ln in lines
                   if len(ln.strip()) == 3 and all(c in PHONEMES for c in ln.strip())})


# ---------- Latest cosmic snapshot ----------
def latest_cosmic():
    files = sorted(glob.glob("telemetry/session_*_dialogue.jsonl"),
                   key=os.path.getmtime)
    if not files:
        return None
    with open(files[-1], encoding="utf-8") as fp:
        for line in reversed(fp.readlines()):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("type") == "turn":
                return r.get("cosmic_raw")
    return None


def top_roots_for(vec, rv, n=10):
    scored = [(cosine(vec, rv[r]), r) for r in rv]
    scored.sort(reverse=True)
    return [r for _, r in scored[:n]]


# ---------- Main ----------
roots = load_roots()
rv = precompute(roots)
print(f">> {len(roots)} roots loaded")

raw = latest_cosmic()
print(f">> Latest cosmic snapshot: {raw}")

vec_full, _ = cosmic_semantic_vector()
vec = vec_full  # now 4-dim
print(f">> Cosmic vector (4-dim): {[round(x,3) for x in vec]}")

names = ["schumann", "kp", "wind", "bz"]

# 1) Baseline
baseline = top_roots_for(vec, rv, 10)
print("\n=== BASELINE: top-10 under current cosmic state ===")
print("  " + "  ".join(baseline))

# 2) Ablation
print("\n=== ABLATION: zero one cosmic dim at a time ===")
for i, name in enumerate(names):
    ab = list(vec)
    ab[i] = 0.0
    top = top_roots_for(ab, rv, 10)
    overlap = len(set(top) & set(baseline))
    print(f"  drop {name:10s}  overlap={overlap:2d}/10   top5={top[:5]}")

# 3) Random baseline
print("\n=== RANDOM: 500 random cosmic vectors ===")
wins = Counter()
for _ in range(500):
    rnd = list(np.random.dirichlet(np.ones(4)))
    for r in top_roots_for(rnd, rv, 10):
        wins[r] += 1
print("  Most chosen under random vectors:")
for root, n in wins.most_common(15):
    print(f"    {root}  {n}")

# 4) Observed telemetry
print("\n=== OBSERVED: all-time telemetry top-10 ===")
observed = Counter()
for f in glob.glob("telemetry/session_*_dialogue.jsonl"):
    with open(f, encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("type") == "turn":
                observed[r["root"]] += 1
if observed:
    for root, n in observed.most_common(10):
        print(f"    {root}  {n}")
    top_observed = set(r for r, _ in observed.most_common(10))
    print(f"  Overlap baseline ∩ observed = {len(set(baseline) & top_observed)}/10")
    print(f"  Overlap random-top15 ∩ observed = "
          f"{len(set(r for r,_ in wins.most_common(15)) & top_observed)}/10")

# 5) Letter frequency excess
print("\n=== LETTER FREQUENCY (observed vs uniform) ===")
sample = random.sample(roots, min(1000, len(roots)))
uniform_counts = Counter("".join(sample))
recent = []
for f in glob.glob("telemetry/session_*_dialogue.jsonl"):
    with open(f, encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("type") == "turn":
                recent.append(r["root"])
recent = recent[-500:]
obs = Counter("".join(recent))
total_obs = sum(obs.values())
total_uniform = sum(uniform_counts.values())
print(f"  sample sizes: observed={total_obs} letters, uniform={total_uniform}")
print(f"  {'letter':>6}  {'obs%':>6}  {'unif%':>6}  {'ratio':>6}")
for letter, n in obs.most_common(15):
    obs_pct = 100.0 * n / total_obs
    unif_pct = 100.0 * uniform_counts.get(letter, 0) / total_uniform
    ratio = obs_pct / max(unif_pct, 0.01)
    bar = "#" * int(ratio * 4)
    print(f"  {letter:>6}  {obs_pct:6.2f}  {unif_pct:6.2f}  {ratio:6.2f}  {bar}")
