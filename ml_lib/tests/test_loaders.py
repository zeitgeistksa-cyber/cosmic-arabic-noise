"""Sanity tests for the ML library."""
import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ml_lib.datasets import (
    load_engine_turns, load_quran_roots, load_poem_roots,
    root_to_features, load_cosmic_series,
)


def test_engine_turns():
    turns = load_engine_turns()
    print(f"  engine turns: {len(turns)}")
    assert len(turns) > 0, "no engine turns loaded"
    assert "root" in turns[0]
    assert "cosmic" in turns[0]
    return turns


def test_quran_roots():
    roots = load_quran_roots()
    print(f"  quran top roots: {len(roots)}")
    assert len(roots) > 0, "no quran roots loaded"
    return roots


def test_poem_roots():
    poems = load_poem_roots()
    print(f"  poems: {len(poems)}")
    for p in poems:
        print(f"    {p['title']}: {len(p['roots'])} roots")
    assert len(poems) >= 1, "no poems loaded"
    return poems


def test_features():
    feats = root_to_features("ضدد")
    print(f"  features for ضدد: {len(feats)} keys")
    assert "voice_count" in feats
    assert "triad_f1" in feats
    assert feats["emph_count"] == 1
    return feats


def test_cosmic_series():
    entries = load_cosmic_series()
    print(f"  cosmic entries: {len(entries)}")
    return entries


def main():
    print("=" * 60)
    print("ML LIBRARY TESTS")
    print("=" * 60)
    print("\n[1] engine turns")
    test_engine_turns()
    print("\n[2] quran roots")
    test_quran_roots()
    print("\n[3] poem roots")
    test_poem_roots()
    print("\n[4] feature extraction")
    test_features()
    print("\n[5] cosmic series")
    test_cosmic_series()
    print("\n>> all tests passed")


if __name__ == "__main__":
    main()
