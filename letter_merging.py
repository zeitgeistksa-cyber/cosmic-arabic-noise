#!/usr/bin/env python3
"""
Analyze how Arabic letters merge into 3-letter roots.
Three layers: phonotactic (corpus), articulatory (formant), acoustic (audio).
"""
import json, math, wave
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

from phoneme_table import PHONEMES, root_to_log_triad
from phoneme_grammar import VOICED, EMPHATIC, MANNER

SR = 44100


# ============================================================
# LAYER 1: Phonotactic merging (which pairs occur in real roots?)
# ============================================================
def load_source_roots():
    lines = open("arabic_db/roots.txt", encoding="utf-8").read().splitlines()
    return [ln.strip() for ln in lines
            if len(ln.strip()) == 3
            and all(c in PHONEMES for c in ln.strip())]


def bigram_matrix(roots):
    """Compute letter-pair counts at each position boundary (1-2 and 2-3)."""
    pairs_12 = Counter()
    pairs_23 = Counter()
    for r in roots:
        pairs_12[r[0] + r[1]] += 1
        pairs_23[r[1] + r[2]] += 1
    return pairs_12, pairs_23


def find_forbidden_pairs(pairs, all_letters):
    """Letter pairs that never occur even though both letters exist."""
    forbidden = []
    for a in all_letters:
        for b in all_letters:
            if a == b:
                continue
            if pairs[a + b] == 0:
                forbidden.append(a + b)
    return forbidden


def ocp_violations(roots):
    """
    Obligatory Contour Principle: identical adjacent consonants.
    Count how often real Arabic roots violate OCP at each boundary.
    """
    viol_12 = sum(1 for r in roots if r[0] == r[1])
    viol_23 = sum(1 for r in roots if r[1] == r[2])
    viol_all = sum(1 for r in roots if r[0] == r[1] == r[2])
    return {
        "roots": len(roots),
        "identical_1_2": viol_12,
        "identical_2_3": viol_23,
        "all_identical": viol_all,
        "pct_identical_any": 100 * (viol_12 + viol_23 - viol_all) / len(roots),
    }


# ============================================================
# LAYER 2: Articulatory merging (how do adjacent letters blend?)
# ============================================================
def articulatory_distance(a, b):
    """Distance between two letters' formant signatures."""
    if a not in PHONEMES or b not in PHONEMES:
        return None
    fa = np.array(PHONEMES[a], dtype=np.float64)
    fb = np.array(PHONEMES[b], dtype=np.float64)
    return float(np.linalg.norm(fa - fb))


def transition_cost(root):
    """
    Sum of articulatory distances between consecutive letters.
    High = the mouth has to move a lot between positions.
    Low = smooth transition.
    """
    if len(root) != 3:
        return None
    d12 = articulatory_distance(root[0], root[1])
    d23 = articulatory_distance(root[1], root[2])
    if d12 is None or d23 is None:
        return None
    return d12 + d23


# ============================================================
# LAYER 3: Acoustic merging (what does the audio actually do?)
# ============================================================
def spectral_overlap(root, dur=2.0):
    """
    Synthesize a root and measure how much the three tones overlap
    spectrally and temporally.
    """
    triad = root_to_log_triad(root)
    if triad is None:
        return None
    f1, f2, f3 = triad
    n = int(SR * dur)
    t = np.arange(n) / SR
    pos = np.linspace(0, 1, n)

    def env(start, end):
        c = 0.5 * (start + end)
        h = 0.5 * (end - start) + 1e-9
        return np.maximum(0.0, 1.0 - np.abs(pos - c) / h)

    # Frequency-dependent envelope widths: lower tones ring longer
    import math as _m
    def width_for(f):
        # Map log-frequency to width: 60 Hz -> 0.5, 8000 Hz -> 0.25
        if f < 20: return 0.42
        log_f = _m.log2(f)
        norm = max(0.0, min(1.0, (log_f - 6) / 7))  # 64 Hz=0, 8192 Hz=1
        return 0.50 - 0.25 * norm   # widest at low f, tightest at high f

    w1 = width_for(f1)
    w2 = width_for(f2)
    w3 = width_for(f3)
    # Three evenly-placed syllables with frequency-dependent widths
    centers = [0.20, 0.50, 0.80]
    e1 = env(centers[0] - w1/2, centers[0] + w1/2)
    e2 = env(centers[1] - w2/2, centers[1] + w2/2)
    e3 = env(centers[2] - w3/2, centers[2] + w3/2)

    # Temporal overlap: sum of pairwise overlap of envelopes
    overlap_12 = float(np.sum(e1 * e2))
    overlap_23 = float(np.sum(e2 * e3))
    overlap_13 = float(np.sum(e1 * e3))

    # Spectral overlap: distance between tones in log-frequency
    import math
    log_dist_12 = abs(math.log2(f2 / f1)) if f1 > 0 else 0
    log_dist_23 = abs(math.log2(f3 / f2)) if f2 > 0 else 0
    log_dist_13 = abs(math.log2(f3 / f1)) if f1 > 0 else 0

    return {
        "f1": f1, "f2": f2, "f3": f3,
        "time_overlap_12": overlap_12 / n,
        "time_overlap_23": overlap_23 / n,
        "time_overlap_13": overlap_13 / n,
        "log_dist_12": log_dist_12,
        "log_dist_23": log_dist_23,
        "log_dist_13": log_dist_13,
    }


# ============================================================
# Main analysis
# ============================================================
def main():
    print("=" * 68)
    print("HOW LETTERS MERGE INTO WORDS")
    print("=" * 68)

    all_letters = list(PHONEMES.keys())
    source_roots = load_source_roots()
    print(f"\n>> {len(source_roots)} source roots (from arabic_db)")

    # ---------- LAYER 1: Phonotactic ----------
    print("\n" + "=" * 68)
    print("LAYER 1: PHONOTACTIC MERGING (which pairs occur?)")
    print("=" * 68)

    pairs_12, pairs_23 = bigram_matrix(source_roots)
    print(f"\n  Distinct letter pairs at boundary 1-2: {len(pairs_12)}")
    print(f"  Distinct letter pairs at boundary 2-3: {len(pairs_23)}")
    print(f"  Total possible pairs: {28*28}")

    forbidden_12 = find_forbidden_pairs(pairs_12, all_letters)
    forbidden_23 = find_forbidden_pairs(pairs_23, all_letters)
    print(f"\n  Forbidden pairs at 1-2: {len(forbidden_12)}")
    print(f"  Forbidden pairs at 2-3: {len(forbidden_23)}")

    print(f"\n  Top 15 pairs at 1-2:")
    for pair, n in pairs_12.most_common(15):
        a, b = pair[0], pair[1]
        dist = articulatory_distance(a, b)
        print(f"    {a}{b}  x{n:5d}  articulatory_dist={dist:.3f}")

    print(f"\n  Top 15 pairs at 2-3:")
    for pair, n in pairs_23.most_common(15):
        a, b = pair[0], pair[1]
        dist = articulatory_distance(a, b)
        print(f"    {a}{b}  x{n:5d}  articulatory_dist={dist:.3f}")

    # OCP analysis
    ocp = ocp_violations(source_roots)
    print(f"\n  OCP (identical adjacent) analysis:")
    print(f"    Roots with identical 1-2: {ocp['identical_1_2']:5d}  "
          f"({100*ocp['identical_1_2']/ocp['roots']:.2f}%)")
    print(f"    Roots with identical 2-3: {ocp['identical_2_3']:5d}  "
          f"({100*ocp['identical_2_3']/ocp['roots']:.2f}%)")
    print(f"    Roots with all three identical: {ocp['all_identical']}")
    print(f"    Random expectation: {(1/28)*100:.2f}% per boundary")

    # ---------- LAYER 2: Articulatory ----------
    print("\n" + "=" * 68)
    print("LAYER 2: ARTICULATORY MERGING (how far must the mouth move?)")
    print("=" * 68)

    # Distance distribution in real roots
    real_dists = [transition_cost(r) for r in source_roots]
    real_dists = [d for d in real_dists if d is not None]
    real_mean = np.mean(real_dists)
    real_std = np.std(real_dists)

    # Random 3-letter combinations
    import random
    random.seed(42)
    random_dists = []
    for _ in range(5000):
        r = "".join(random.choices(all_letters, k=3))
        d = transition_cost(r)
        if d is not None:
            random_dists.append(d)
    random_mean = np.mean(random_dists)
    random_std = np.std(random_dists)

    print(f"\n  Real roots     mean transition cost: {real_mean:.3f}  (std {real_std:.3f})")
    print(f"  Random triples mean transition cost: {random_mean:.3f}  (std {random_std:.3f})")
    print(f"  Difference: {real_mean - random_mean:+.3f}")

    if real_mean < random_mean:
        print(f"  >> Real Arabic prefers SMOOTHER articulatory transitions")
    else:
        print(f"  >> Real Arabic prefers LARGER articulatory movements")

    # ---------- LAYER 3: Acoustic ----------
    print("\n" + "=" * 68)
    print("LAYER 3: ACOUSTIC MERGING (how do the three tones overlap?)")
    print("=" * 68)

    # Compare example roots
    examples = ["ضدد", "بدر", "طرد", "نور", "صفف", "زفف", "كتب", "علم"]
    print(f"\n  {'root':6s}  {'overlap12':>10s}  {'overlap23':>10s}  "
          f"{'log_dist12':>11s}  {'log_dist23':>11s}")
    for r in examples:
        s = spectral_overlap(r)
        if s:
            print(f"  {r}  {s['time_overlap_12']:10.3f}  {s['time_overlap_23']:10.3f}  "
                  f"{s['log_dist_12']:11.2f}  {s['log_dist_23']:11.2f}")

    # What does "merging" mean in engine terms?
    print("\n  Interpretation:")
    print("    overlap12/23 near 1.0  → the three tones blend into a chord")
    print("    overlap12/23 near 0.0  → the three tones are separate syllables")
    print("    log_dist    near 0     → adjacent tones are acoustically similar")
    print("    log_dist    near 5+    → adjacent tones are in different octaves")


if __name__ == "__main__":
    main()
