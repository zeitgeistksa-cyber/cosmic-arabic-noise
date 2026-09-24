"""Sanity tests for the ML library, including the empirical enrichment claim."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ml_lib.datasets import (
    load_engine_turns, load_quran_roots, load_poem_roots,
    root_to_features, load_cosmic_series,
)


def test_engine_turns():
    turns = load_engine_turns()
    print(f"  engine turns: {len(turns)}")
    assert len(turns) > 0, "no engine turns loaded"
    return turns


def test_quran_roots():
    roots = load_quran_roots()
    print(f"  quran top roots: {len(roots)}")
    return roots


def test_poem_roots():
    poems = load_poem_roots()
    print(f"  poems: {len(poems)}")
    for p in poems:
        print(f"    {p['title']}: {len(p['roots'])} roots")
    return poems


def test_features():
    feats = root_to_features("ضدد")
    print(f"  features for ضدد: {len(feats)} keys")
    assert "voice_count" in feats
    assert feats["emph_count"] == 1
    return feats


def test_cosmic_series():
    entries = load_cosmic_series()
    print(f"  cosmic entries: {len(entries)}")
    return entries


def test_enrichment():
    """
    Verify the empirical finding: the engine over-selects specific
    voiced consonants at position 1 far more than the source distribution.

    Two claims are tested:
      1. The letter ض (emphatic voiced alveolar) is massively enriched.
      2. The aggregate of all emphatics (صضطظ) is moderately enriched.
    """
    EMPH = set("صضطظ")

    source_lines = open("arabic_db/roots.txt", encoding="utf-8").read().splitlines()
    source_roots = [ln.strip() for ln in source_lines
                    if len(ln.strip()) == 3
                    and all(c in "ابتثجحخدذرزسشصضطظعغفقكلمنهوي" for c in ln.strip())]
    n_src = len(source_roots)

    turns = load_engine_turns()
    engine_roots = [t["root"] for t in turns
                    if t.get("root") and len(t["root"]) == 3]
    n_eng = len(engine_roots)

    # ---- Claim 1: ض alone ----
    src_dad = sum(1 for r in source_roots if r[0] == "ض") / n_src
    eng_dad = sum(1 for r in engine_roots if r[0] == "ض") / n_eng
    dad_enrich = eng_dad / src_dad if src_dad > 0 else 0

    print(f"  ض  source: {src_dad*100:6.2f}%   engine: {eng_dad*100:6.2f}%   "
          f"enrichment: {dad_enrich:5.2f}x")

    # ---- Claim 2: all emphatics ----
    src_emph = sum(1 for r in source_roots if r[0] in EMPH) / n_src
    eng_emph = sum(1 for r in engine_roots if r[0] in EMPH) / n_eng
    emph_enrich = eng_emph / src_emph if src_emph > 0 else 0

    print(f"  صضطظ source: {src_emph*100:6.2f}%   engine: {eng_emph*100:6.2f}%   "
          f"enrichment: {emph_enrich:5.2f}x")

    # ---- Assertions ----
    assert dad_enrich > 5, (
        f"ض position-1 enrichment is only {dad_enrich:.2f}x; expected > 5x"
    )
    assert emph_enrich > 2, (
        f"aggregate emphatic enrichment is only {emph_enrich:.2f}x; expected > 2x"
    )



def main():
    print("=" * 60)
    print("ML LIBRARY TESTS")
    print("=" * 60)
    for name, fn in [
        ("engine turns", test_engine_turns),
        ("quran roots", test_quran_roots),
        ("poem roots", test_poem_roots),
        ("feature extraction", test_features),
        ("cosmic series", test_cosmic_series),
        ("emphatic enrichment", test_enrichment),
    ]:
        print(f"\n[{name}]")
        fn()
    print("\n>> all tests passed")


if __name__ == "__main__":
    main()
