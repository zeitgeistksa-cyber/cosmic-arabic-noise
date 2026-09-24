#!/usr/bin/env python3
"""Extract triliteral Arabic roots from quranRoots.json (vocabulary format)."""
import json, sys
from pathlib import Path
from phoneme_table import PHONEME_LETTERS

DIACRITICS = "\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652\u0653\u0654\u0655\u0670"
WEAK = set("اوي")
ALIF_FORMS = set("آأإٱ")

def strip_diacritics(s):
    return "".join(c for c in s if c not in DIACRITICS)

def normalize_alif(s):
    return "".join("ا" if c in ALIF_FORMS else c for c in s)

def triliteral_skeleton(word):
    """Extract a 3-letter root more conservatively.

    Rules:
    - Strip diacritics and normalize alif forms
    - Only strip internal long vowels (ا و ي) that sit between consonants
    - Preserve initial/final letters
    - If the result is not exactly 3 letters, return None
    """
    w = strip_diacritics(normalize_alif(word))
    w = "".join(c for c in w if c in PHONEME_LETTERS)
    if len(w) < 3:
        return None
    if len(w) == 3:
        return w
    # Strip ONLY internal weak letters
    if len(w) >= 4:
        first, middle, last = w[0], w[1:-1], w[-1]
        middle_clean = "".join(c for c in middle if c not in WEAK)
        candidate = first + middle_clean + last
        if len(candidate) == 3:
            return candidate
    return None

def main():
    src = Path("arabic_db/quranRoots.json")
    dst = Path("arabic_db/roots.txt")
    if not src.exists():
        print(f"!! {src} missing. Run setup.sh first."); sys.exit(1)
    data = json.loads(src.read_text(encoding="utf-8"))
    roots = set()
    for item in data:
        name = item.get("name") if isinstance(item, dict) else (item if isinstance(item, str) else None)
        if not name: continue
        s = triliteral_skeleton(name)
        if s and len(s) == 3 and all(c in PHONEME_LETTERS for c in s):
            roots.add(s)
    roots = sorted(roots)
    dst.write_text("\n".join(roots), encoding="utf-8")
    print(f">> {len(roots)} unique roots -> {dst}")
    print(f">> sample: {roots[:20]}")

if __name__ == "__main__":
    main()
