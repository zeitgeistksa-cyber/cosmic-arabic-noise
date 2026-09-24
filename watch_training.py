#!/usr/bin/env python3
"""Live terminal dashboard for the continuous trainer."""
import json, os, time, sys
from pathlib import Path
import numpy as np

LOG = Path("training_log.jsonl")
TELEMETRY_GLOB = "telemetry/session_*_dialogue.jsonl"


def read_log(n=200):
    if not LOG.exists():
        return []
    lines = LOG.read_text().splitlines()[-n:]
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


def latest_cosmic():
    import glob
    files = sorted(glob.glob(TELEMETRY_GLOB), key=os.path.getmtime)
    if not files:
        return None
    with open(files[-1], encoding="utf-8") as fp:
        for line in reversed(fp.readlines()):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("type") == "turn":
                return r.get("cosmic_raw")
    return None


def spark(values, width=40):
    """Render a sparkline using block characters."""
    if not values:
        return ""
    vals = np.array(values[-width:], dtype=float)
    lo, hi = vals.min(), vals.max()
    if hi - lo < 1e-9:
        return "." * len(vals)
    chars = "▁▂▃▄▅▆▇█"
    norm = (vals - lo) / (hi - lo)
    idx = np.clip((norm * (len(chars) - 1)).astype(int), 0, len(chars) - 1)
    return "".join(chars[i] for i in idx)


def render():
    os.system("clear")
    print("=" * 70)
    print("  CONTINUOUS TRAINING — live dashboard")
    print("=" * 70)

    log = read_log(400)
    trains = [r for r in log if r.get("event") == "train"]
    ckpts = [r for r in log if r.get("event") == "checkpoint"]

    if not trains:
        print("\n  waiting for first training step...")
    else:
        last = trains[-1]
        best_loss = min(r["loss"] for r in trains)
        best_mae = min(r["mae"] for r in trains)
        best_cos = max(r["cos_sim"] for r in trains)

        print(f"\n  STEP {last['step']}  ·  "
              f"elapsed {last['elapsed_s']/60:.1f} min")
        print(f"\n  CURRENT")
        print(f"    loss     {last['loss']:.5f}")
        print(f"    mae      {last['mae']:.4f}")
        print(f"    cos_sim  {last['cos_sim']:.4f}")
        print(f"    samples  {last['samples']}")
        print(f"\n  BEST")
        print(f"    loss     {best_loss:.5f}")
        print(f"    mae      {best_mae:.4f}")
        print(f"    cos_sim  {best_cos:.4f}")
        print(f"\n  TOTAL TRAINING STEPS: {len(trains)}")
        print(f"  CHECKPOINTS SAVED: {len(ckpts)}")

        # Loss sparkline
        losses = [r["loss"] for r in trains[-60:]]
        print(f"\n  LOSS TREND (last {len(losses)})")
        print(f"    {spark(losses, 60)}")
        print(f"    min {min(losses):.4f}  max {max(losses):.4f}")

        maes = [r["mae"] for r in trains[-60:]]
        print(f"\n  MAE TREND")
        print(f"    {spark(maes, 60)}")

        coss = [r["cos_sim"] for r in trains[-60:]]
        print(f"\n  COSINE SIMILARITY TREND")
        print(f"    {spark(coss, 60)}")

    # Live cosmic state
    c = latest_cosmic()
    if c:
        print(f"\n  LIVE COSMIC STATE")
        print(f"    schumann  {c.get('schumann_score')}")
        print(f"    kp        {c.get('kp_value')}")
        print(f"    wind      {c.get('wind_speed')} km/s")
        print(f"    bz        {c.get('bz')}")

    print("\n" + "=" * 70)
    print("  Ctrl+C to exit. Trainer keeps running in tmux.")
    print("=" * 70)


if __name__ == "__main__":
    try:
        while True:
            render()
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n")
        sys.exit(0)
