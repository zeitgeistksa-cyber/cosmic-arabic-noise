#!/usr/bin/env python3
"""Evolutionary trainer with Arabic root diversity + universal rhythm scoring."""
import json, time, glob, numpy as np, os, shutil
from pathlib import Path
from universal_rhythm import rhythm_score

TELEMETRY_DIR = Path("telemetry"); BRAIN_DIR = Path("brains")
BRAIN_DIR.mkdir(exist_ok=True)
TOP_K, PERTURB_SIGMA, HYPER_NOISE = 5, 0.01, 0.15

def load_all_records():
    out = []
    for f in sorted(glob.glob(str(TELEMETRY_DIR / "session_*.jsonl"))):
        with open(f, encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line: continue
                try: out.append(json.loads(line))
                except json.JSONDecodeError: continue
    return out

def build_segments(records):
    records.sort(key=lambda r: (r.get("session",""), r.get("chunk",0)))
    segs, cm, cs = [], None, []
    for r in records:
        if r.get("type") == "mutation":
            if cm is not None: segs.append((cm, cs))
            cm, cs = r, []
        elif r.get("type") == "state" and cm is not None:
            cs.append(r)
    if cm is not None: segs.append((cm, cs))
    return segs

def score_segment(mut, states):
    if len(states) < 3: return 0.0
    e = np.array([s["entropy"] for s in states])
    me, se = float(np.mean(e)), float(np.std(e))
    dur = min(len(states), 40)/40.0
    evol = max(0.0, min(1.0, 1.0 - abs(se - 0.15)/0.35))
    roots = {s.get("current_root") for s in states}
    root_bonus = min(len(roots), 8)/8.0
    chunks = [s["chunk"] for s in states]
    if len(chunks) >= 2:
        span = (max(chunks)-min(chunks))*2048/44100
        rate = len(roots)/max(span, 1e-3)
        rhythm_bonus = rhythm_score(rate)
    else:
        rhythm_bonus = 0.0
    base = me*(0.5+0.5*evol)*(0.5+0.5*dur)*(0.7+0.3*root_bonus)
    return base*(0.8 + 0.2*rhythm_bonus)

def next_gen():
    gs = sorted(BRAIN_DIR.glob("gen_*.npz"),
                key=lambda p: int(p.stem.split("_")[1]))
    return 1 if not gs else int(gs[-1].stem.split("_")[1]) + 1

def wavg(brains, weights):
    w = np.array(weights, dtype=np.float64); w = w/(w.sum()+1e-12)
    out = {k: np.zeros_like(brains[0][k]) for k in ("W1","W2","W_out","theory_weights")}
    out["omega_0"] = out["coupling_k"] = 0.0
    for b, wi in zip(brains, w):
        for k in ("W1","W2","W_out","theory_weights"): out[k] += wi*b[k]
        out["omega_0"] += wi*b["omega_0"]; out["coupling_k"] += wi*b["coupling_k"]
    out["theory_weights"] /= (out["theory_weights"].sum()+1e-12)
    return out

def main():
    recs = load_all_records()
    print(f">> {len(recs)} records")
    segs = build_segments(recs)
    print(f">> {len(segs)} segments")
    scored = sorted(((score_segment(m,s), m, s) for m, s in segs if score_segment(m,s)>0),
                    key=lambda x: x[0], reverse=True)
    if not scored:
        print("!! No scored segments. Run engine longer."); return
    for i, (s, m, st) in enumerate(scored[:TOP_K]):
        roots = sorted({x.get("current_root") for x in st})
        print(f"   [{i+1}] score={s:.3f} chunk={m['chunk']} "
              f"omega0={m['omega_0']:.1f} k={m['coupling_k']:.2f} "
              f"roots={roots[:4]}{'...' if len(roots)>4 else ''}")
    winners = [x[1] for x in scored[:TOP_K]]
    scores = [x[0] for x in scored[:TOP_K]]
    brains = [{"W1": np.array(w["W1"]), "W2": np.array(w["W2"]),
               "W_out": np.array(w["W_out"]),
               "theory_weights": np.array(w["theory_weights"]),
               "omega_0": float(w["omega_0"]),
               "coupling_k": float(w["coupling_k"])} for w in winners]
    child = wavg(brains, scores)
    for k in ("W1","W2","W_out"): child[k] += np.random.randn(*child[k].shape)*PERTURB_SIGMA
    child["omega_0"] = float(np.clip(child["omega_0"]*(1+np.random.randn()*HYPER_NOISE), 15.0, 120.0))
    child["coupling_k"] = float(np.clip(child["coupling_k"]*(1+np.random.randn()*HYPER_NOISE), 0.05, 3.5))
    gen = next_gen()
    meta = {"generation": gen, "parent_generation": gen-1,
            "score": float(np.mean(scores)), "source": "telemetry_evolution",
            "num_parents": len(winners), "num_segments_analyzed": len(scored),
            "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    out = BRAIN_DIR / f"gen_{gen}.npz"
    np.savez_compressed(out, W1=child["W1"], W2=child["W2"], W_out=child["W_out"],
        theory_weights=child["theory_weights"],
        omega_0=np.float64(child["omega_0"]),
        coupling_k=np.float64(child["coupling_k"]), meta=json.dumps(meta))
    latest = BRAIN_DIR / "latest.npz"
    tmp = BRAIN_DIR / ".latest.tmp"
    try:
        if tmp.exists() or tmp.is_symlink(): tmp.unlink()
        os.symlink(out.name, tmp)
        os.replace(str(tmp), str(latest))
    except OSError:
        shutil.copyfile(out, latest)
    print(f">> Wrote {out} (gen {gen})  omega0={child['omega_0']:.2f}  k={child['coupling_k']:.2f}")

if __name__ == "__main__": main()
