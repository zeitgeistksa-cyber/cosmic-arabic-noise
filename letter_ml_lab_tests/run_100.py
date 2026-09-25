"""Run all 100 tests and log ML-ready verdicts."""
import sys, os, json, time
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset = os.path.join(root, "dataset", "letters_100.jsonl")
    log_path = os.path.join(root, "logs", "run_100_telemetry.jsonl")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    with open(dataset) as f:
        rows = [json.loads(l) for l in f]

    results = []
    start = time.time()
    for i, rec in enumerate(rows):
        feats = rec["features"]
        # cheap classifier rules for smoke testing
        verdict = "unknown"
        if feats["zcr"] > 0.3 and feats["centroid"] > 3000:
            verdict = "fricative"
        elif feats["rms"] > 0.15 and feats["zcr"] < 0.15:
            verdict = "voiced"
        elif feats["peak_f"] < 400:
            verdict = "low"
        else:
            verdict = "mid"

        results.append({
            "test_id": rec["test_id"],
            "category": rec["category"],
            "label": rec["label"],
            "verdict": verdict,
            "match": verdict in rec["category"] or rec["category"] in verdict,
            "features": feats,
        })
        if (i+1) % 20 == 0:
            print(f"[*] processed {i+1}/{len(rows)}")

    with open(log_path, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # summary
    matched = sum(1 for r in results if r["match"])
    print(f"\n[summary] {matched}/{len(results)} matched "
          f"({100*matched/len(results):.1f}%) in {time.time()-start:.1f}s")
    print(f"[summary] log → {log_path}")

if __name__ == "__main__":
    main()
