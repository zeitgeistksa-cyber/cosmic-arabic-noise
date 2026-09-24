#!/usr/bin/env python3
"""Quran corpus vs cosmic attractor. Same tests as poem_vs_cosmos.py."""
import json, os, random
from collections import Counter
import numpy as np
from phoneme_table import PHONEMES, root_to_log_triad
from phoneme_grammar import VOICED, EMPHATIC, MANNER
from root_semantics import precompute, cosine
from cosmic_semantics import cosmic_semantic_vector
from extract_roots import triliteral_skeleton


def load_quran(path="books/quran_simple.txt"):
    """Return list of ayah lines from Quran file."""
    lines = []
    with open(path, encoding="utf-8") as fp:
        for ln in fp:
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            lines.append(ln)
    return lines


def load_corpus():
    lines = open("arabic_db/roots.txt", encoding="utf-8").read().splitlines()
    return sorted({ln.strip() for ln in lines
                   if len(ln.strip()) == 3 and all(c in PHONEMES for c in ln.strip())})


def fingerprint(root):
    feats = [PHONEMES[c] for c in root if c in PHONEMES]
    if not feats:
        return np.zeros(4)
    return np.mean(feats, axis=0)


def main():
    print("=" * 60)
    print("QURAN CORPUS vs COSMIC ATTRACTOR")
    print("=" * 60)

    ayat = load_quran()
    print(f">> {len(ayat)} ayah lines")

    # ---- Extract all roots ----
    all_roots = []
    for ayah in ayat:
        for word in ayah.split():
            r = triliteral_skeleton(word)
            if r and len(r) == 3 and all(c in PHONEMES for c in r):
                all_roots.append(r)

    if not all_roots:
        print("!! no roots extracted — check extract_roots")
        return

    c = Counter(all_roots)
    print(f">> {len(all_roots)} root instances")
    print(f">> {len(c)} distinct roots")

    # ---- Cosmic vector ----
    vec, raw = cosmic_semantic_vector()
    vec = np.array(vec)
    print(f">> cosmic vector: {[round(float(x), 3) for x in vec]}")
    print(f">> cosmic raw: schumann={raw.get('schumann_score')} "
          f"kp={raw.get('kp_value')} wind={raw.get('wind_speed')}")
    print()

    corpus = load_corpus()
    rv = precompute(corpus)

    # ---- 1. Quran vs random cosine scores ----
    print("=" * 60)
    print("1. QURAN ROOTS vs RANDOM (cosine to cosmic vector)")
    print("=" * 60)
    quran_scores = [cosine(vec, rv[r]) for r in all_roots if r in rv]
    random_scores = np.array([cosine(vec, rv[random.choice(corpus)])
                              for _ in range(10000)])
    q_arr = np.array(quran_scores)
    z = (q_arr.mean() - random_scores.mean()) / (
        random_scores.std() / np.sqrt(len(q_arr)) + 1e-9)
    print(f"  Quran:  mean={q_arr.mean():.4f}  std={q_arr.std():.4f}  n={len(q_arr)}")
    print(f"  Random: mean={random_scores.mean():.4f}  std={random_scores.std():.4f}")
    print(f"  z-score: {z:+.3f}")
    if abs(z) > 1.96:
        print(f"  ** SIGNIFICANT at p<0.05 **")

    # ---- 2. Position asymmetry ----
    print()
    print("=" * 60)
    print("2. POSITION ASYMMETRY")
    print("=" * 60)
    pos1 = Counter(); pos3 = Counter()
    for r in all_roots:
        pos1[r[0]] += 1
        pos3[r[2]] += 1
    emph = set("صضطظ")
    q1 = sum(1 for r in all_roots if r[0] in emph)
    q3 = sum(1 for r in all_roots if r[2] in emph)
    total = len(all_roots)
    print(f"  Emphatic at pos1: {q1}/{total}  ({100*q1/total:.2f}%)")
    print(f"  Emphatic at pos3: {q3}/{total}  ({100*q3/total:.2f}%)")
    print(f"  Ratio pos1/pos3: {q1/max(q3,1):.2f}")

    # Compare with engine ratio (from earlier findings)
    print(f"  Engine ratio:     6.20  (from 6,150 turns)")

    # ---- 3. Top 20 roots ----
    print()
    print("=" * 60)
    print("3. TOP 20 ROOTS")
    print("=" * 60)
    for r, n in c.most_common(20):
        triad = root_to_log_triad(r)
        print(f"  {r}  x{n:5d}  f1={triad[0]:6.1f} f2={triad[1]:6.1f} f3={triad[2]:7.1f}")

    # ---- 4. Fingerprint ----
    print()
    print("=" * 60)
    print("4. ACOUSTIC FINGERPRINT (Quran vs corpus)")
    print("=" * 60)
    quran_fp = np.mean([fingerprint(r) for r in all_roots], axis=0)
    corpus_fp = np.mean([fingerprint(r) for r in corpus], axis=0)
    labels = ["F1", "F2", "F3", "CoG"]
    print(f"  {'dim':>4}  {'quran':>8}  {'corpus':>8}  {'diff':>8}")
    for i, lab in enumerate(labels):
        print(f"  {lab:>4}  {quran_fp[i]:8.3f}  {corpus_fp[i]:8.3f}  "
              f"{quran_fp[i]-corpus_fp[i]:+8.3f}")

    # ---- 5. Compare to poems ----
    print()
    print("=" * 60)
    print("5. COMPARISON WITH PREVIOUS RESULTS")
    print("=" * 60)
    print(f"  {'Corpus':<20}  {'n':>6}  {'z-score':>8}  {'emph_pos1%':>10}")
    print(f"  {'-'*20}  {'-'*6}  {'-'*8}  {'-'*10}")
    print(f"  {'Quran':<20}  {total:>6}  {z:>+8.3f}  {100*q1/total:>10.2f}")
    # Poem values from batch_test3
    print(f"  {'Poems (combined)':<20}  {' 19':>6}  {'-2.43':>8}  {'0.00':>10}")
    print(f"  {'Engine attractor':<20}  {'6150':>6}  {'+0.00':>8}  {'27.50':>10}")

    # ---- Save ----
    os.makedirs("experiments/quran", exist_ok=True)
    report = {
        "ayah_lines": len(ayat),
        "root_instances": len(all_roots),
        "distinct_roots": len(c),
        "cosmic_vector": [float(x) for x in vec],
        "z_score_vs_random": float(z),
        "emphatic_pos1_pct": 100 * q1 / total,
        "emphatic_pos3_pct": 100 * q3 / total,
        "ratio": float(q1 / max(q3, 1)),
        "top_roots": c.most_common(30),
        "fingerprint": {
            "F1": float(quran_fp[0]), "F2": float(quran_fp[1]),
            "F3": float(quran_fp[2]), "CoG": float(quran_fp[3]),
        },
    }
    with open("experiments/quran/analysis.json", "w", encoding="utf-8") as fp:
        json.dump(report, fp, ensure_ascii=False, indent=2)
    print()
    print(">> wrote experiments/quran/analysis.json")


if __name__ == "__main__":
    main()
