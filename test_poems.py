#!/usr/bin/env python3
"""Batch test multiple poems vs cosmic vector."""
import json, os, random
import numpy as np
from phoneme_table import PHONEMES
from root_semantics import precompute, cosine
from cosmic_semantics import cosmic_semantic_vector

def load_corpus():
    lines = open("arabic_db/roots.txt", encoding="utf-8").read().splitlines()
    return sorted({ln.strip() for ln in lines
                   if len(ln.strip()) == 3 and all(c in PHONEMES for c in ln.strip())})

def load_poem_roots(path):
    if not os.path.exists(path): return []
    data = json.loads(open(path, encoding="utf-8").read())
    return [e["root"] for e in data["sequence"]]

corpus = load_corpus()
rv = precompute(corpus)
cosmic_vec, raw = cosmic_semantic_vector()
cosmic_vec = np.array(cosmic_vec)

random_scores = np.array([
    cosine(cosmic_vec, rv[random.choice(corpus)]) for _ in range(10000)
])

poems = [
    ("Imru' al-Qais — Mu'allaqa", "poem_roots.json"),
    ("Al-Mutanabbi", "poem_roots_2.json"),
    ("Nizar Qabbani", "poem_roots_3.json"),
    ("Mahmoud Darwish", "poem_roots_4.json"),
]
all_poem_scores = []
for name, path in poems:
    roots = load_poem_roots(path)
    if not roots: 
        print(f"  (skip {name}: no data)")
        continue
    scores = [cosine(cosmic_vec, rv[r]) for r in roots if r in rv]
    if not scores: continue
    arr = np.array(scores)
    z = (arr.mean() - random_scores.mean()) / (random_scores.std() / np.sqrt(len(arr)) + 1e-9)
    print(f"  {name:30s}  n={len(arr):3d}  mean={arr.mean():.4f}  z={z:+.3f}")
    all_poem_scores.extend(scores)

if all_poem_scores:
    all_arr = np.array(all_poem_scores)
    z_all = (all_arr.mean() - random_scores.mean()) / (random_scores.std() / np.sqrt(len(all_arr)) + 1e-9)
    print()
    print(f"  COMBINED  n={len(all_arr)}  mean={all_arr.mean():.4f}  z={z_all:+.3f}")
    if abs(z_all) > 1.96:
        print(f"  ** Significant at p<0.05 **")
