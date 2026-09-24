#!/usr/bin/env python3
"""Poem vs cosmic state analysis."""
import json, glob, os, random
from collections import Counter
import numpy as np
from phoneme_table import PHONEMES, root_to_log_triad
from phoneme_grammar import VOICED, EMPHATIC, MANNER
from root_semantics import precompute, cosine, root_semantic
from cosmic_semantics import cosmic_semantic_vector


def load_corpus_roots():
    lines = open("arabic_db/roots.txt", encoding="utf-8").read().splitlines()
    return sorted({ln.strip() for ln in lines
                   if len(ln.strip()) == 3 and all(c in PHONEMES for c in ln.strip())})


def load_poem():
    p = "poem_roots.json"
    if not os.path.exists(p):
        print("!! poem_roots.json missing. Run: python play_poem.py")
        return []
    data = json.loads(open(p, encoding="utf-8").read())
    return [entry["root"] for entry in data["sequence"]]


def current_cosmic():
    vec, raw = cosmic_semantic_vector()
    return np.array(vec, dtype=np.float64), raw


def fingerprint(root):
    """Return (mean_F1, mean_F2, mean_F3, mean_CoG) for a root."""
    feats = []
    for c in root:
        if c in PHONEMES:
            feats.append(PHONEMES[c])
    if not feats:
        return np.zeros(4)
    return np.mean(feats, axis=0)


def main():
    poem = load_poem()
    corpus = load_corpus_roots()
    if not poem or not corpus:
        return

    print(f">> Poem roots: {len(poem)}")
    print(f">> Corpus roots: {len(corpus)}")

    cosmic_vec, cosmic_raw = current_cosmic()
    print(f">> Cosmic vector: {[round(float(x), 3) for x in cosmic_vec]}")
    print(f">> Cosmic raw: schumann={cosmic_raw.get('schumann_score')} "
          f"kp={cosmic_raw.get('kp_value')} wind={cosmic_raw.get('wind_speed')}")
    print()

    # Precompute corpus vectors
    corpus_rv = precompute(corpus)

    # ---- 1. Poem vs random scoring ----
    print("=" * 60)
    print("1. POEM ROOTS vs RANDOM ROOTS (cosine to cosmic vector)")
    print("=" * 60)
    poem_scores = []
    for r in poem:
        if r in corpus_rv:
            poem_scores.append(cosine(cosmic_vec, corpus_rv[r]))

    # Random samples from corpus
    random_scores = []
    for _ in range(5000):
        r = random.choice(corpus)
        random_scores.append(cosine(cosmic_vec, corpus_rv[r]))

    poem_arr = np.array(poem_scores)
    rand_arr = np.array(random_scores)
    print(f"  Poem  mean={poem_arr.mean():.4f}  std={poem_arr.std():.4f}  n={len(poem_arr)}")
    print(f"  Random mean={rand_arr.mean():.4f}  std={rand_arr.std():.4f}  n={len(rand_arr)}")
    z = (poem_arr.mean() - rand_arr.mean()) / (rand_arr.std() / np.sqrt(len(poem_arr)) + 1e-9)
    print(f"  z-score of poem mean vs random: {z:+.3f}")
    if abs(z) > 1.96:
        print("  ** Significant at p < 0.05 **")
    else:
        print("  (no significant difference)")

    # ---- 2. Position asymmetry in poem ----
    print()
    print("=" * 60)
    print("2. POSITION ASYMMETRY IN POEM")
    print("=" * 60)
    pos1 = Counter(); pos2 = Counter(); pos3 = Counter()
    for r in poem:
        pos1[r[0]] += 1; pos2[r[1]] += 1; pos3[r[2]] += 1
    print(f"  position 1: {dict(pos1)}")
    print(f"  position 2: {dict(pos2)}")
    print(f"  position 3: {dict(pos3)}")
    emph = set("صضطظ")
    poem_emph_pos1 = sum(1 for r in poem if r[0] in emph)
    poem_emph_pos3 = sum(1 for r in poem if r[2] in emph)
    print(f"  Emphatic at pos1: {poem_emph_pos1}/{len(poem)} "
          f"({100*poem_emph_pos1/max(len(poem),1):.1f}%)")
    print(f"  Emphatic at pos3: {poem_emph_pos3}/{len(poem)} "
          f"({100*poem_emph_pos3/max(len(poem),1):.1f}%)")

    # ---- 3. Fingerprint distance ----
    print()
    print("=" * 60)
    print("3. ACOUSTIC FINGERPRINT (poem vs corpus mean)")
    print("=" * 60)
    poem_fp = np.mean([fingerprint(r) for r in poem], axis=0)
    corpus_fp = np.mean([fingerprint(r) for r in corpus], axis=0)
    labels = ["F1", "F2", "F3", "CoG"]
    print(f"  {'dim':>4}  {'poem':>8}  {'corpus':>8}  {'diff':>8}")
    for i, lab in enumerate(labels):
        print(f"  {lab:>4}  {poem_fp[i]:8.3f}  {corpus_fp[i]:8.3f}  "
              f"{poem_fp[i]-corpus_fp[i]:+8.3f}")

    # ---- 4. Simulate poem under different cosmic states ----
    print()
    print("=" * 60)
    print("4. SIMULATED COSMIC STATES (does poem output change?)")
    print("=" * 60)
    # Fake three representative states
    states = {
        "calm":    [0.35, 0.10, 0.15, 0.50],
        "active":  [0.55, 0.40, 0.35, 0.50],
        "storm":   [0.85, 0.80, 0.60, 0.50],
    }
    for name, vec in states.items():
        v = np.array(vec)
        scores = [cosine(v, corpus_rv[r]) for r in poem if r in corpus_rv]
        print(f"  {name:8s}  poem_cos_mean={np.mean(scores):.4f}  "
              f"std={np.std(scores):.4f}")

    # Which poem roots would be picked as #1 under each state?
    print()
    print("  Top poem root under each simulated state:")
    for name, vec in states.items():
        v = np.array(vec)
        scored = sorted(((cosine(v, corpus_rv[r]), r) for r in poem if r in corpus_rv),
                        reverse=True)
        if scored:
            print(f"    {name:8s} -> {scored[0][1]}  sim={scored[0][0]:.4f}")

    # ---- 5. Save report ----
    report = {
        "poem_length": len(poem),
        "cosmic_vec": [float(x) for x in cosmic_vec],
        "cosmic_raw": {k: cosmic_raw.get(k) for k in
                       ("schumann_score", "kp_value", "wind_speed")},
        "poem_cos_mean": float(poem_arr.mean()),
        "random_cos_mean": float(rand_arr.mean()),
        "z_score": float(z),
        "emph_pos1_pct": 100*poem_emph_pos1/max(len(poem), 1),
        "emph_pos3_pct": 100*poem_emph_pos3/max(len(poem), 1),
    }
    os.makedirs("experiments/poem", exist_ok=True)
    with open("experiments/poem/analysis.json", "w", encoding="utf-8") as fp:
        json.dump(report, fp, indent=2, ensure_ascii=False)
    print()
    print(">> wrote experiments/poem/analysis.json")


if __name__ == "__main__":
    main()
