#!/usr/bin/env python3
"""Map each Arabic root to an 8-dim semantic vector derived from its phonemes."""
import numpy as np
from phoneme_table import PHONEMES
from phoneme_grammar import MAKHRAJ, VOICED, EMPHATIC, MANNER

def letter_semantic(letter):
    """Per-letter contribution to the 8 cosmic semantic axes."""
    if letter not in PHONEMES:
        return np.zeros(8)
    F1, F2, F3, CoG = PHONEMES[letter]
    back = 1.0 - MAKHRAJ.get(letter, 0.5)               # 1 = deep, 0 = front
    voice = 1.0 if letter in VOICED else 0.0
    emph = 1.0 if letter in EMPHATIC else 0.0
    manner = MANNER.get(letter, 0.5)

    # 8 semantic axes
    intensity   = 0.5 * emph + 0.5 * CoG                 # fricatives hiss
    coherence   = voice * (1.0 - manner)                 # stops are crisp
    expansion   = back                                   # deep = outward
    contraction = manner * (1.0 - back)                  # frontal fricatives
    harmony     = voice * (1.0 - abs(F2 - 1.5))          # centered formant
    turbulence  = CoG                                    # high CoG = hiss
    density     = 1.0 - manner                           # stops feel dense
    luminosity  = F3 / 3.0                               # bright formants
    return np.array([intensity, coherence, expansion,
                     contraction, harmony, turbulence,
                     density, luminosity])

def root_semantic(root):
    """Average the 3 letters' semantic vectors."""
    if len(root) != 3:
        return np.zeros(8)
    vs = [letter_semantic(c) for c in root]
    return np.mean(vs, axis=0)

def precompute(roots):
    """Return {root: vector} for a list of roots, normalized."""
    table = {}
    for r in roots:
        v = root_semantic(r)
        n = np.linalg.norm(v) + 1e-9
        table[r] = v / n
    return table

def cosine(a, b):
    a = np.asarray(a, dtype=np.float64); b = np.asarray(b, dtype=np.float64)
    na = np.linalg.norm(a) + 1e-9; nb = np.linalg.norm(b) + 1e-9
    return float(np.dot(a, b) / (na * nb))

if __name__ == "__main__":
    for r in ["ابت", "عرب", "كتب", "صبر", "نور", "صدق", "علم", "كون"]:
        v = root_semantic(r)
        print(f"{r}  " + " ".join(f"{x:.2f}" for x in v))
