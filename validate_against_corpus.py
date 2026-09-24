#!/usr/bin/env python3
"""Check if engine's top roots match real Arabic corpus frequency."""
import json, glob
from collections import Counter

# Load Quran root frequencies (the JSON you downloaded has 'count' per word)
quran = json.load(open("arabic_db/quranRoots.json", encoding="utf-8"))
# Aggregate by skeleton — approximate by stripping vowels from each name
from extract_roots import triliteral_skeleton
corpus_freq = Counter()
for item in quran:
    skel = triliteral_skeleton(item.get("name", ""))
    if skel:
        corpus_freq[skel] += int(item.get("count", 1))

# Load engine's actual selections
engine_freq = Counter()
for f in glob.glob("telemetry/session_*_dialogue.jsonl"):
    for line in open(f, encoding="utf-8"):
        line = line.strip()
        if not line: continue
        try: r = json.loads(line)
        except: continue
        if r.get("type") == "turn":
            engine_freq[r["root"]] += 1

# Rank correlation between engine and corpus
common = set(engine_freq) & set(corpus_freq)
if len(common) < 10:
    print("!! too few overlapping roots for comparison"); raise SystemExit

import numpy as np
e_ranks = {r: i for i, (r, _) in enumerate(engine_freq.most_common())}
c_ranks = {r: i for i, (r, _) in enumerate(corpus_freq.most_common())}
shared = sorted(common, key=lambda r: e_ranks[r])[:100]

xs = np.array([e_ranks[r] for r in shared])
ys = np.array([c_ranks.get(r, 9999) for r in shared])
rho = float(np.corrcoef(xs, ys)[0, 1])

print(f"Spearman rank correlation: {rho:+.3f}")
print(f"Common roots: {len(common)}")
print(f"\nTop 20 engine choices vs their corpus rank:")
for r in shared[:20]:
    print(f"  {r}  engine_rank={e_ranks[r]:4d}  corpus_rank={c_ranks.get(r, 'N/A')}")
