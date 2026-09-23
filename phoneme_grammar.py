#!/usr/bin/env python3
"""
Arabic phoneme grammar.
Maps each letter to 4 structural axes:
  axis 0: makhraj position  (0 = glottal/back, 1 = labial/front)
  axis 1: voicing           (0 = voiceless, 1 = voiced)
  axis 2: emphasis          (0 = plain, 1 = pharyngealized)
  axis 3: manner            (0=stop, 1=fricative, 0.5=nasal/lateral/trill/glide)
"""
from phoneme_table import PHONEMES, LETTER_INDEX

# makhraj position from back (0) to front (1)
MAKHRAJ = {
    "ء": 0.00, "ه": 0.05, "ع": 0.10, "ح": 0.15,
    "ق": 0.25, "غ": 0.25, "خ": 0.28,
    "ك": 0.35,
    "ج": 0.45, "ش": 0.50, "ي": 0.55,
    "ت": 0.65, "د": 0.65, "ط": 0.65, "ض": 0.65,
    "س": 0.68, "ز": 0.68, "ص": 0.68, "ن": 0.68, "ل": 0.68, "ر": 0.68,
    "ث": 0.80, "ذ": 0.80, "ظ": 0.80,
    "ف": 0.90, "ب": 0.95, "م": 0.95, "و": 0.98,
}

VOICED = set("ابتثجحخدذرزسشصضطظعغفقكلمنهوي") - set("تثحخسشصكفهء")
EMPHATIC = set("صضطظ")

# manner: 0 = stop, 1 = fricative, 0.5 = sonorant
MANNER = {}
for c in "بتدطضكقء":
    MANNER[c] = 0.0      # stops
for c in "ج":
    MANNER[c] = 0.75     # affricate
for c in "ثذزسشصضظفخغحع":
    MANNER[c] = 1.0      # fricatives
for c in "منلروي":
    MANNER[c] = 0.5      # sonorants
MANNER["ه"] = 1.0

def letter_vector(letter):
    """Return the 4-axis structural vector for one letter."""
    if letter not in PHONEMES:
        return (0.5, 0.5, 0.0, 0.5)
    return (
        MAKHRAJ.get(letter, 0.5),
        1.0 if letter in VOICED else 0.0,
        1.0 if letter in EMPHATIC else 0.0,
        MANNER.get(letter, 0.5),
    )

def root_grammar(root):
    """Return a 12-dim vector: 3 letters × 4 axes."""
    if len(root) != 3:
        return [0.5] * 12
    out = []
    for c in root:
        out.extend(letter_vector(c))
    return out

def prosody(root):
    """Return prosodic descriptors: syllable weights and voicing rhythm."""
    if len(root) != 3:
        return {"weights": [], "voicing": [], "emphasis": 0}
    weights = []
    for c in root:
        m = MANNER.get(c, 0.5)
        # stop = light (1), fricative = heavy (2), sonorant = superheavy (3)
        w = 1 if m == 0.0 else (3 if m == 0.5 else 2)
        weights.append(w)
    voicing = [1 if c in VOICED else 0 for c in root]
    emph = sum(1 for c in root if c in EMPHATIC)
    return {"weights": weights, "voicing": voicing, "emphasis": emph}

if __name__ == "__main__":
    import sys
    for r in ["ابت", "عرب", "كتب", "صبر", "نور", "صدق"]:
        p = prosody(r)
        print(f"{r}  weights={p['weights']}  voicing={p['voicing']}  emph={p['emphasis']}")
