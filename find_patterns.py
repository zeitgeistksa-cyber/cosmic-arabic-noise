#!/usr/bin/env python3
"""
Find new patterns in the dialogue telemetry.
Correlates cosmic state with phonetic features, position, sequence structure.
"""
import json, glob, os
from collections import Counter, defaultdict
import numpy as np
from phoneme_table import PHONEMES, root_to_log_triad
from phoneme_grammar import VOICED, EMPHATIC, MANNER


# ---------- Load telemetry ----------
def load_turns():
    turns = []
    for f in sorted(glob.glob("telemetry/session_*_dialogue.jsonl")):
        with open(f, encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line: continue
                try: r = json.loads(line)
                except: continue
                if r.get("type") == "turn":
                    turns.append(r)
    return turns


def extract_features(t):
    raw = t.get("cosmic_raw") or {}
    root = t.get("root", "")
    if not root or len(root) != 3: return None
    sch = raw.get("schumann_score")
    kp = raw.get("kp_value")
    wind = raw.get("wind_speed")
    if sch is None or kp is None or wind is None: return None

    letters = list(root)
    triad = root_to_log_triad(root) or (0, 0, 0)

    return {
        "root": root, "letters": letters,
        "schumann": sch, "kp": kp, "wind": wind,
        "voice_count": sum(1 for c in letters if c in VOICED),
        "emph_count": sum(1 for c in letters if c in EMPHATIC),
        "manner_avg": float(np.mean([MANNER.get(c, 0.5) for c in letters])),
        "c0": letters[0], "c1": letters[1], "c2": letters[2],
        "c0_voice": 1 if letters[0] in VOICED else 0,
        "c1_voice": 1 if letters[1] in VOICED else 0,
        "c2_voice": 1 if letters[2] in VOICED else 0,
        "c0_emph": 1 if letters[0] in EMPHATIC else 0,
        "c2_emph": 1 if letters[2] in EMPHATIC else 0,
        "f1": triad[0], "f2": triad[1], "f3": triad[2],
        "f_mean": (triad[0] + triad[1] + triad[2]) / 3.0,
        "f_spread": max(triad) - min(triad),
    }


turns = load_turns()
records = [f for f in (extract_features(t) for t in turns) if f is not None]
print(f"=== {len(records)} turns with full data ===\n")


# ---------- 1. Correlation table ----------
print("=== 1. Cosmic ↔ phonetic correlations ===")
cosmic_dims = ["schumann", "kp", "wind"]
phonetic_dims = ["voice_count", "emph_count", "manner_avg",
                 "c0_voice", "c1_voice", "c2_voice",
                 "f_mean", "f_spread"]

print(f"  {'cosmic':>10}  {'phonetic':>14}  {'r':>7}  {'|r|':>6}")
strong = []
for cd in cosmic_dims:
    cvals = np.array([r[cd] for r in records], dtype=np.float64)
    for pd in phonetic_dims:
        pvals = np.array([r[pd] for r in records], dtype=np.float64)
        if pvals.std() < 1e-6: continue
        r = float(np.corrcoef(cvals, pvals)[0, 1])
        if abs(r) > 0.08:
            bar = "#" * int(abs(r) * 40)
            print(f"  {cd:>10}  {pd:>14}  {r:+7.3f}  {abs(r):6.3f}  {bar}")
            if abs(r) > 0.15:
                strong.append((cd, pd, r))

print(f"\n  Strong correlations (|r|>0.15): {len(strong)}")
for cd, pd, r in strong:
    print(f"    {cd} ↔ {pd}:  r = {r:+.3f}")


# ---------- 2. Letter position bias ----------
print("\n=== 2. Letter position bias ===")
pos1 = Counter(r["c0"] for r in records)
pos2 = Counter(r["c1"] for r in records)
pos3 = Counter(r["c2"] for r in records)
all_letters = set(pos1) | set(pos2) | set(pos3)
print(f"  {'letter':>6}  {'pos1':>6}  {'pos2':>6}  {'pos3':>6}  {'total':>6}")
for letter in sorted(all_letters,
                     key=lambda c: -(pos1[c] + pos2[c] + pos3[c]))[:20]:
    print(f"  {letter:>6}  {pos1[letter]:>6}  {pos2[letter]:>6}  "
          f"{pos3[letter]:>6}  {pos1[letter]+pos2[letter]+pos3[letter]:>6}")


# ---------- 3. Sequence structure ----------
print("\n=== 3. Sequence structure ===")
identical_pairs = 0
shared_letter_pairs = 0
overlap_dist = Counter()
for i in range(1, len(records)):
    prev = set(records[i-1]["letters"])
    cur = set(records[i]["letters"])
    if records[i]["root"] == records[i-1]["root"]:
        identical_pairs += 1
    shared = len(prev & cur)
    overlap_dist[shared] += 1
    shared_letter_pairs += shared
n = len(records) - 1
print(f"  Identical consecutive turns: {identical_pairs}/{n}  "
      f"({100*identical_pairs/max(n,1):.1f}%)")
print(f"  Mean shared letters (consecutive): "
      f"{shared_letter_pairs/max(n,1):.2f}")
print(f"  Overlap distribution:")
for k in sorted(overlap_dist):
    print(f"    {k} shared letters: {overlap_dist[k]:>5}  "
          f"({100*overlap_dist[k]/max(n,1):.1f}%)")


# ---------- 4. Triad frequency distribution ----------
print("\n=== 4. Triad frequency distribution ===")
f1 = np.array([r["f1"] for r in records])
f2 = np.array([r["f2"] for r in records])
f3 = np.array([r["f3"] for r in records])
print(f"  f1:  mean={f1.mean():7.1f}  std={f1.std():7.1f}  "
      f"range=[{f1.min():.0f}, {f1.max():.0f}]")
print(f"  f2:  mean={f2.mean():7.1f}  std={f2.std():7.1f}  "
      f"range=[{f2.min():.0f}, {f2.max():.0f}]")
print(f"  f3:  mean={f3.mean():7.1f}  std={f3.std():7.1f}  "
      f"range=[{f3.min():.0f}, {f3.max():.0f}]")

# Correlate cosmic with frequency
for cd in cosmic_dims:
    cvals = np.array([r[cd] for r in records], dtype=np.float64)
    for fd in ["f1", "f2", "f3", "f_mean"]:
        fvals = np.array([r[fd] for r in records], dtype=np.float64)
        r = float(np.corrcoef(cvals, fvals)[0, 1])
        if abs(r) > 0.08:
            print(f"    {cd:>10} ↔ {fd:>6}:  r={r:+.3f}")


# ---------- 5. Regime comparison with chi-square ----------
print("\n=== 5. Root distribution by Kp regime ===")
regimes = {"calm": [], "active": [], "storm": []}
for r in records:
    kp = r["kp"]
    if kp < 1: regimes["calm"].append(r["root"])
    elif kp < 4: regimes["active"].append(r["root"])
    else: regimes["storm"].append(r["root"])

for name, roots in regimes.items():
    if not roots: continue
    c = Counter(roots)
    total = len(roots)
    probs = [n/total for n in c.values()]
    H = -sum(p * np.log2(p) for p in probs)
    print(f"  {name:8s}  n={total:5d}  distinct={len(c):4d}  H={H:.2f} bits")
    print(f"           top5: {[r for r,_ in c.most_common(5)]}")


# ---------- 6. Lag analysis ----------
print("\n=== 6. Lag analysis (does cosmic today predict tomorrow?) ===")
for lag in [1, 5, 20, 100]:
    if len(records) <= lag: continue
    # Correlate schumann[t] with voice_count[t+lag]
    x = np.array([records[i]["schumann"] for i in range(len(records)-lag)])
    y = np.array([records[i+lag]["voice_count"] for i in range(len(records)-lag)])
    if x.std() < 1e-6 or y.std() < 1e-6: continue
    r = float(np.corrcoef(x, y)[0, 1])
    print(f"  schumann[t] ↔ voice_count[t+{lag:3d}]:  r = {r:+.3f}  (n={len(x)})")


# ---------- 7. First vs last letter asymmetry ----------
print("\n=== 7. Position asymmetry ===")
first_voiced = sum(r["c0_voice"] for r in records)
last_voiced = sum(r["c2_voice"] for r in records)
first_emph = sum(r["c0_emph"] for r in records)
last_emph = sum(r["c2_emph"] for r in records)
n = len(records)
print(f"  Voiced at position 1: {first_voiced}/{n}  ({100*first_voiced/n:.1f}%)")
print(f"  Voiced at position 3: {last_voiced}/{n}  ({100*last_voiced/n:.1f}%)")
print(f"  Emphatic at position 1: {first_emph}/{n}  ({100*first_emph/n:.1f}%)")
print(f"  Emphatic at position 3: {last_emph}/{n}  ({100*last_emph/n:.1f}%)")


# ---------- Summary ----------
print("\n" + "=" * 60)
print("SUMMARY — Top patterns found")
print("=" * 60)
if strong:
    print("\nTop correlations (|r|>0.15):")
    for cd, pd, r in sorted(strong, key=lambda x: -abs(x[2]))[:5]:
        print(f"  {cd} ↔ {pd}:  r = {r:+.3f}")
else:
    print("\nNo strong correlations found at |r|>0.15")
    print("This suggests either:")
    print("  - Cosmic state doesn't drive phoneme selection strongly")
    print("  - Or the effect requires a different feature representation")
print()
