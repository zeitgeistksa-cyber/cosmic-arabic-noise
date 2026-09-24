#!/usr/bin/env python3
"""
Root Semantics — Pure Acoustic Version (v2)
============================================
No formulas. No named axes. Every dimension is a raw number taken
directly from the Arabic phoneme table.

Each root becomes a 4-dimensional vector:
    [mean_F1, mean_F2, mean_F3, mean_CoG]

where the mean is taken across the 3 letters of the root.
This is the simplest possible acoustic representation.
If a cosmic state prefers specific roots, it must prefer them
on the basis of these raw numbers alone — no voice formula, no
manner penalty, nothing but formant and noise measurements.
"""
import numpy as np
from phoneme_table import PHONEMES


def letter_vector(letter):
    """Return the 4 raw acoustic values for one letter. No transformation."""
    if letter not in PHONEMES:
        return np.zeros(4, dtype=np.float64)
    F1, F2, F3, CoG = PHONEMES[letter]
    return np.array([F1, F2, F3, CoG], dtype=np.float64)


def root_semantic(root):
    """Return the 4-dim raw acoustic vector for a 3-letter root."""
    if len(root) != 3:
        return np.zeros(4, dtype=np.float64)
    vs = [letter_vector(c) for c in root]
    return np.mean(vs, axis=0)


def precompute(roots):
    """Return {root: unit-normalized 4-dim vector}."""
    table = {}
    for r in roots:
        v = root_semantic(r)
        n = np.linalg.norm(v) + 1e-9
        table[r] = v / n
    return table


def cosine(a, b):
    """Plain cosine similarity, clipped to [-1, 1]."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if a.shape != b.shape:
        # Truncate to the shorter length rather than crash
        m = min(a.size, b.size)
        a = a[:m]
        b = b[:m]
    na = np.linalg.norm(a) + 1e-9
    nb = np.linalg.norm(b) + 1e-9
    return float(np.clip(np.dot(a, b) / (na * nb), -1.0, 1.0))


if __name__ == "__main__":
    for r in ["ضدد", "زبد", "ذبب", "ردد", "بدر", "طرد", "نور", "علم"]:
        v = root_semantic(r)
        print(f"{r}  F1={v[0]:.2f}  F2={v[1]:.2f}  F3={v[2]:.2f}  CoG={v[3]:.2f}")
