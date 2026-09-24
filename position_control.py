#!/usr/bin/env python3
"""Compare engine selection to what's available in the source roots."""
import json, glob
from collections import Counter
from phoneme_table import PHONEMES

# 1) Source distribution
src = [ln.strip() for ln in
       open("arabic_db/roots.txt", encoding="utf-8").read().splitlines()
       if len(ln.strip()) == 3 and all(c in PHONEMES for c in ln.strip())]
src_pos1 = Counter(r[0] for r in src)
src_pos2 = Counter(r[1] for r in src)
src_pos3 = Counter(r[2] for r in src)
n_src = len(src)

# 2) Engine observed distribution
obs_pos1 = Counter(); obs_pos2 = Counter(); obs_pos3 = Counter()
turns = 0
for f in glob.glob("telemetry/session_*_dialogue.jsonl"):
    with open(f, encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line: continue
            try: r = json.loads(line)
            except: continue
            if r.get("type") != "turn": continue
            root = r.get("root", "")
            if len(root) != 3: continue
            obs_pos1[root[0]] += 1
            obs_pos2[root[1]] += 1
            obs_pos3[root[2]] += 1
            turns += 1

print(f"Source roots: {n_src}    Observed turns: {turns}\n")

print(f"  {'letter':>6}  {'src_p1':>7}  {'obs_p1':>7}  {'enrich':>7}  "
      f"{'src_p3':>7}  {'obs_p3':>7}  {'enrich':>7}")
for letter in "ضزذصطج":
    src1 = 100 * src_pos1[letter] / n_src
    obs1 = 100 * obs_pos1[letter] / max(turns, 1)
    src3 = 100 * src_pos3[letter] / n_src
    obs3 = 100 * obs_pos3[letter] / max(turns, 1)
    e1 = obs1 / max(src1, 0.001)
    e3 = obs3 / max(src3, 0.001)
    print(f"  {letter:>6}  {src1:7.2f}  {obs1:7.2f}  {e1:7.2f}  "
          f"{src3:7.2f}  {obs3:7.2f}  {e3:7.2f}")

print("\nIf enrichment > 1 → engine favors this letter more than source data")
print("If enrichment < 1 → engine avoids it")
print("If enrichment ≈ 1 → no position preference, just data")
