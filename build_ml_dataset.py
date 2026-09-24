#!/usr/bin/env python3
"""Run all experiments and export to standard ML formats."""
import json
from pathlib import Path
from collections import Counter
import numpy as np

from ml_lib.datasets import (
    load_engine_turns, load_quran_roots, load_poem_roots,
    root_to_features, load_cosmic_series,
)

OUT = Path("ml_lib/data")
OUT.mkdir(parents=True, exist_ok=True)


def build_engine_dataset():
    """Every engine turn with features + cosmic state."""
    turns = load_engine_turns()
    print(f">> {len(turns)} engine turns")

    rows = []
    for t in turns:
        feats = root_to_features(t["root"])
        if not feats:
            continue
        cosmic = t["cosmic"] or {}
        row = dict(feats)
        row.update({
            "cosmic_schumann": cosmic.get("schumann_score"),
            "cosmic_kp": cosmic.get("kp_value"),
            "cosmic_wind": cosmic.get("wind_speed"),
            "similarity": t.get("similarity"),
            "session": t.get("session"),
        })
        rows.append(row)

    # Save as JSONL (always works)
    out_jsonl = OUT / "engine_turns.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as fp:
        for r in rows:
            fp.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f">> wrote {out_jsonl}")

    # Save as CSV if pandas available
    try:
        import pandas as pd
        df = pd.DataFrame(rows)
        out_csv = OUT / "engine_turns.csv"
        df.to_csv(out_csv, index=False)
        print(f">> wrote {out_csv}  ({df.shape})")
        # Also save as numpy arrays for easy loading
        num_cols = [c for c in df.columns if df[c].dtype in (np.float64, np.int64)]
        np.save(OUT / "engine_features.npy", df[num_cols].values.astype(np.float32))
        (OUT / "engine_feature_names.txt").write_text("\n".join(num_cols))
        print(f">> wrote {OUT/'engine_features.npy'}  ({len(num_cols)} features)")
    except ImportError:
        print("!! pandas not installed — skipping CSV export")


def build_corpus_comparison():
    """Quran vs poems vs engine — the key comparative dataset."""
    quran = load_quran_roots()
    poems = load_poem_roots()
    turns = load_engine_turns()

    def stats_for_root_list(roots):
        if not roots:
            return None
        emph = set("صضطظ")
        pos1_emph = sum(1 for r in roots if len(r) == 3 and r[0] in emph)
        pos3_emph = sum(1 for r in roots if len(r) == 3 and r[2] in emph)
        return {
            "n": len(roots),
            "emph_pos1_pct": 100 * pos1_emph / len(roots),
            "emph_pos3_pct": 100 * pos3_emph / len(roots),
        }

    engine_roots = [t["root"] for t in turns if t.get("root")]
    quran_roots = [r for r, _ in quran]  # only top ones
    poem_roots = []
    for p in poems:
        poem_roots.extend(p["roots"])

    comparison = {
        "engine": stats_for_root_list(engine_roots),
        "quran_top20": stats_for_root_list(quran_roots),
        "poems_combined": stats_for_root_list(poem_roots),
    }

    out = OUT / "corpus_comparison.json"
    out.write_text(json.dumps(comparison, ensure_ascii=False, indent=2))
    print(f">> wrote {out}")
    print(json.dumps(comparison, indent=2))


def build_cosmic_time_series():
    """Timeline as clean time series."""
    entries = load_cosmic_series()
    rows = []
    for e in entries:
        c = e.get("cosmic", {})
        rows.append({
            "ts": e.get("timestamp"),
            "schumann": c.get("schumann"),
            "kp": c.get("kp"),
            "wind": c.get("wind"),
            "turns_total": e.get("turns_total"),
        })
    out = OUT / "cosmic_series.jsonl"
    with open(out, "w", encoding="utf-8") as fp:
        for r in rows:
            fp.write(json.dumps(r) + "\n")
    print(f">> wrote {out}  ({len(rows)} entries)")

    try:
        import pandas as pd
        df = pd.DataFrame(rows)
        df.to_csv(OUT / "cosmic_series.csv", index=False)
        print(f">> wrote {OUT/'cosmic_series.csv'}")
    except ImportError:
        pass


def main():
    print("=" * 60)
    print("BUILDING ML DATASET")
    print("=" * 60)
    print()
    build_engine_dataset()
    print()
    build_corpus_comparison()
    print()
    build_cosmic_time_series()
    print()
    print("=" * 60)
    print(f"DONE — files in {OUT}")
    print("=" * 60)


if __name__ == "__main__":
    main()
