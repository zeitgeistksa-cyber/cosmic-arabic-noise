#!/usr/bin/env python3
"""Run the same cosine-based selection with English phoneme table."""
import numpy as np
from english_phoneme_table import ENGLISH_PHONEMES, root_to_log_triad
from cosmic_semantics import cosmic_semantic_vector

# Generate synthetic English "roots" (all 3-consonant combinations)
letters = list(ENGLISH_PHONEMES.keys())
english_roots = [a + b + c for a in letters for b in letters for c in letters]
print(f">> {len(english_roots)} synthetic English roots")

def root_vector(root):
    feats = []
    for c in root:
        feats.extend(ENGLISH_PHONEMES.get(c, (0, 0, 0, 0)))
    if not feats:
        return np.zeros(12)
    return np.array(feats[:12], dtype=np.float64)

def cosine(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    n = min(a.size, b.size)
    a, b = a[:n], b[:n]
    return float(np.dot(a, b) / ((np.linalg.norm(a) + 1e-9) * (np.linalg.norm(b) + 1e-9)))

# Build English root vectors and pad to 12-dim to match the new cosmic vector
# Actually the new cosmic vector is 4-dim. So we need 4-dim English vectors too.
def root_vector_4d(root):
    feats = []
    for c in root:
        F1, F2, F3, CoG = ENGLISH_PHONEMES.get(c, (0, 0, 0, 0))
        feats.extend([F1, F2, F3, CoG])
    v = np.array(feats, dtype=np.float64)
    return v / (np.linalg.norm(v) + 1e-9)

vec_full, raw = cosmic_semantic_vector()
print(f">> Cosmic vector: {[round(x,3) for x in vec_full]}")

# Wait — the new cosmic vector is 4-dim but English root vectors are 12-dim
# We need to reduce English to 4-dim by taking mean across the 3 letters
def root_vector_mean(root):
    per_letter = []
    for c in root:
        F1, F2, F3, CoG = ENGLISH_PHONEMES.get(c, (0, 0, 0, 0))
        per_letter.append([F1, F2, F3, CoG])
    v = np.mean(per_letter, axis=0)
    return v / (np.linalg.norm(v) + 1e-9)

scored = sorted(((cosine(vec_full, root_vector_mean(r)), r)
                 for r in english_roots), reverse=True)

print("\n=== Top 15 English roots under same cosmic vector ===")
for sim, root in scored[:15]:
    print(f"  {root}  sim={sim:.4f}")

print("\n=== Top 15 Arabic roots under same cosmic vector (for comparison) ===")
# Load Arabic roots and same-format vectors
from phoneme_table import PHONEMES
arabic_roots = [ln.strip() for ln in
                open("arabic_db/roots.txt", encoding="utf-8").read().splitlines()
                if len(ln.strip()) == 3 and all(c in PHONEMES for c in ln.strip())]
def arabic_vec(root):
    per_letter = []
    for c in root:
        F1, F2, F3, CoG = PHONEMES.get(c, (0, 0, 0, 0))
        per_letter.append([F1, F2, F3, CoG])
    v = np.mean(per_letter, axis=0)
    return v / (np.linalg.norm(v) + 1e-9)
scored_ar = sorted(((cosine(vec_full, arabic_vec(r)), r)
                    for r in arabic_roots), reverse=True)
for sim, root in scored_ar[:15]:
    print(f"  {root}  sim={sim:.4f}")

# Compare phoneme classes in top 10 of each
print("\n=== Letter class composition ===")
print("English top 10:", [r for _, r in scored[:10]])
print("Arabic  top 10:", [r for _, r in scored_ar[:10]])
