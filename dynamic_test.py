#!/usr/bin/env python3
"""
Dynamic test: does the matcher's root selection depend on cosmic state?

Splits all turns by Kp regime and compares:
  - root distributions
  - CoG means
  - position enrichment
  - which roots win in each regime
"""
import json
from collections import Counter
import statistics
from ml_lib.datasets import load_engine_turns, root_to_features


def bucket_by_kp(turns, threshold=2.0):
    calm, active = [], []
    for t in turns:
        kp = (t.get("cosmic") or {}).get("kp_value")
        if kp is None:
            continue
        if kp < threshold:
            calm.append(t)
        else:
            active.append(t)
    return calm, active


def cog_stats(turns):
    cogs = []
    for t in turns:
        f = root_to_features(t.get("root"))
        if f and "mean_CoG" in f:
            cogs.append(f["mean_CoG"])
    if not cogs:
        return None
    return {
        "n": len(cogs),
        "mean": statistics.mean(cogs),
        "std": statistics.stdev(cogs) if len(cogs) > 1 else 0,
    }


def emph_pos1(turns, letter="ض"):
    roots = [t["root"] for t in turns if t.get("root") and len(t["root"]) == 3]
    if not roots:
        return None
    n1 = sum(1 for r in roots if r[0] == letter)
    return {"n": len(roots), "pos1_count": n1, "rate": 100 * n1 / len(roots)}


def main():
    turns = load_engine_turns()
    print(f">> {len(turns)} total turns")

    calm, active = bucket_by_kp(turns, threshold=2.0)
    print(f"\n  calm   (Kp < 2.0): {len(calm)} turns")
    print(f"  active (Kp >= 2.0): {len(active)} turns")

    if len(calm) < 10 or len(active) < 10:
        print("\n!! one bucket is too small for analysis")
        return

    # ---- 1. CoG comparison ----
    print("\n" + "=" * 60)
    print("1. CoG COMPARISON")
    print("=" * 60)
    cs = cog_stats(calm)
    as_ = cog_stats(active)
    print(f"  calm   n={cs['n']}  mean={cs['mean']:.4f}  std={cs['std']:.4f}")
    print(f"  active n={as_['n']}  mean={as_['mean']:.4f}  std={as_['std']:.4f}")
    print(f"  difference: {as_['mean'] - cs['mean']:+.4f}")

    # ---- 2. ض position 1 ----
    print("\n" + "=" * 60)
    print("2. ض AT POSITION 1")
    print("=" * 60)
    ce = emph_pos1(calm, "ض")
    ae = emph_pos1(active, "ض")
    print(f"  calm:   {ce['pos1_count']}/{ce['n']}  ({ce['rate']:.2f}%)")
    print(f"  active: {ae['pos1_count']}/{ae['n']}  ({ae['rate']:.2f}%)")

    # ---- 3. Root distribution overlap ----
    print("\n" + "=" * 60)
    print("3. ROOT DISTRIBUTION")
    print("=" * 60)
    calm_roots = Counter(t["root"] for t in calm if t.get("root"))
    active_roots = Counter(t["root"] for t in active if t.get("root"))
    calm_set = set(calm_roots.keys())
    active_set = set(active_roots.keys())
    overlap = calm_set & active_set
    print(f"  calm distinct:   {len(calm_set)}")
    print(f"  active distinct: {len(active_set)}")
    print(f"  overlap:         {len(overlap)}")
    print(f"  overlap pct:     {100*len(overlap)/max(len(calm_set|active_set), 1):.1f}%")

    print(f"\n  Top 10 in calm:   {[r for r,_ in calm_roots.most_common(10)]}")
    print(f"  Top 10 in active: {[r for r,_ in active_roots.most_common(10)]}")

    # ---- 4. Roots unique to each regime ----
    calm_only = calm_set - active_set
    active_only = active_set - calm_set
    print(f"\n  Roots ONLY in calm:   {sorted(calm_only)[:15]}")
    print(f"  Roots ONLY in active: {sorted(active_only)[:15]}")

    # ---- 5. Direction of the finding ----
    print("\n" + "=" * 60)
    print("INTERPRETATION")
    print("=" * 60)
    cog_diff = abs(as_['mean'] - cs['mean'])
    if cog_diff < 0.02:
        print(f"  CoG difference {cog_diff:.4f} — negligible.")
        print("  >> The matcher's output is INDEPENDENT of cosmic state.")
        print("  >> The dynamic claim does not survive.")
    elif cog_diff < 0.05:
        print(f"  CoG difference {cog_diff:.4f} — small but present.")
        print("  >> Weak cosmic dependence.")
    else:
        print(f"  CoG difference {cog_diff:.4f} — substantial.")
        print("  >> The matcher's output DOES depend on cosmic state.")

    if len(overlap) < 0.5 * min(len(calm_set), len(active_set)):
        print("  >> Large portion of roots are regime-specific.")
        print("  >> Selection is input-driven.")
    else:
        print("  >> Most roots appear in both regimes.")
        print("  >> Selection is dominated by the matcher's own geometry.")


if __name__ == "__main__":
    main()
