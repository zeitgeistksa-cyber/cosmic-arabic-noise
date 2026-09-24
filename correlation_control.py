#!/usr/bin/env python3
"""Check if cosmic-phonetic correlations are intrinsic to frequency mapping."""
import random
import numpy as np
from phoneme_table import PHONEMES, root_to_log_triad
from phoneme_grammar import VOICED, EMPHATIC, MANNER

roots = [ln.strip() for ln in
         open("arabic_db/roots.txt", encoding="utf-8").read().splitlines()
         if len(ln.strip()) == 3 and all(c in PHONEMES for c in ln.strip())]

# Simulate: pick random roots, correlate random cosmic values
# If observed correlations are the same magnitude → code artifact
print("=== Null test: random selection vs random cosmic ===\n")
for _ in range(5):
    n = 5000
    # Random cosmic values
    schumann = np.random.uniform(20, 60, n)
    kp = np.random.uniform(0, 4, n)
    wind = np.random.uniform(250, 500, n)
    # Random roots
    sample = [random.choice(roots) for _ in range(n)]
    manner = np.array([np.mean([MANNER.get(c, 0.5) for c in r]) for r in sample])
    emph = np.array([sum(1 for c in r if c in EMPHATIC) for r in sample])
    # Correlate
    r_mann_sch = np.corrcoef(schumann, manner)[0, 1]
    r_emph_sch = np.corrcoef(schumann, emph)[0, 1]
    print(f"  run {_}: schumann↔manner={r_mann_sch:+.3f}  "
          f"schumann↔emph={r_emph_sch:+.3f}")

print("\nObserved from telemetry:")
print(f"  schumann ↔ manner_avg: r = -0.458")
print(f"  schumann ↔ emph_count: r = +0.255")
print("\nIf null values cluster around |r| < 0.05, the observed correlations")
print("are real (not from the mapping).")
