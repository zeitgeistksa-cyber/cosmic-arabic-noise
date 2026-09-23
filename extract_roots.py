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
    w = strip_diacritics(normalize_alif(word))
    w = "".join(c for c in w if c in PHONEME_LETTERS)
    if len(w) < 3: return None
    if len(w) == 3: return w
    pruned = "".join(c for c in w if c not in WEAK)
    if len(pruned) == 3: return pruned
    if len(pruned) > 3:
        return pruned[0] + pruned[len(pruned)//2] + pruned[-1]
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
