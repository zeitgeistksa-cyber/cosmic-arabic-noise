#!/usr/bin/env python3
"""
Continuous Trainer — learns the cosmic → phoneme spectrum mapping.

Reads telemetry in a rolling window, trains a small MLP with SGD,
checkpoints every N steps, logs every step to training_log.jsonl.

No TensorFlow. Pure NumPy, fast enough for real-time on Android.
"""
import json, os, time, glob, sys, math
from pathlib import Path
from datetime import datetime
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from phoneme_table import PHONEMES, root_to_log_triad

# --- Hyperparameters ---
INPUT_DIM = 4            # schumann, kp, wind, bz
HIDDEN_DIM = 32
OUTPUT_DIM = 7           # CoG, f1, f2, f3, voice_count, emph_count, manner_avg
LR = 0.002
BATCH = 32
POLL_SEC = 3.0
CHECKPOINT_EVERY = 200
LOG = Path("training_log.jsonl")
CHECKPOINT = Path("trainer_checkpoint.npz")
TELEMETRY_GLOB = "telemetry/session_*_dialogue.jsonl"


# ---------------------------------------------------------------------
# Model: 4 → 32 → 32 → 7, tanh activation
# ---------------------------------------------------------------------
class TinyMLP:
    def __init__(self, in_dim=INPUT_DIM, hidden=HIDDEN_DIM, out_dim=OUTPUT_DIM):
        rng = np.random.default_rng(42)
        self.W1 = rng.normal(0, 0.3, (in_dim, hidden))
        self.b1 = np.zeros(hidden)
        self.W2 = rng.normal(0, 0.3, (hidden, hidden))
        self.b2 = np.zeros(hidden)
        self.W3 = rng.normal(0, 0.3, (hidden, out_dim))
        self.b3 = np.zeros(out_dim)
        self.step = 0

    def forward(self, X):
        self.z1 = X @ self.W1 + self.b1
        self.h1 = np.tanh(self.z1)
        self.z2 = self.h1 @ self.W2 + self.b2
        self.h2 = np.tanh(self.z2)
        self.z3 = self.h2 @ self.W3 + self.b3
        return self.z3

    def backward(self, X, y_pred, y_true):
        n = X.shape[0]
        # MSE gradient
        dz3 = (y_pred - y_true) * 2.0 / n
        self.dW3 = self.h2.T @ dz3
        self.db3 = dz3.sum(axis=0)
        dh2 = dz3 @ self.W3.T
        dz2 = dh2 * (1 - self.h2 ** 2)
        self.dW2 = self.h1.T @ dz2
        self.db2 = dz2.sum(axis=0)
        dh1 = dz2 @ self.W2.T
        dz1 = dh1 * (1 - self.h1 ** 2)
        self.dW1 = X.T @ dz1
        self.db1 = dz1.sum(axis=0)

    def update(self, lr=LR):
        self.W3 -= lr * self.dW3
        self.b3 -= lr * self.db3
        self.W2 -= lr * self.dW2
        self.b2 -= lr * self.db2
        self.W1 -= lr * self.dW1
        self.b1 -= lr * self.db1
        self.step += 1

    def save(self, path):
        np.savez(path, W1=self.W1, b1=self.b1, W2=self.W2, b2=self.b2,
                 W3=self.W3, b3=self.b3, step=self.step)

    def load(self, path):
        if not Path(path).exists():
            return False
        d = np.load(path)
        self.W1, self.b1 = d["W1"], d["b1"]
        self.W2, self.b2 = d["W2"], d["b2"]
        self.W3, self.b3 = d["W3"], d["b3"]
        self.step = int(d["step"])
        return True


# ---------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------
def load_examples(max_files=5):
    """Read telemetry and produce (cosmic_vec, root_features) pairs."""
    files = sorted(glob.glob(TELEMETRY_GLOB), key=os.path.getmtime)[-max_files:]
    if not files:
        return None, None
    X, Y = [], []
    for f in files:
        with open(f, encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("type") != "turn":
                    continue
                cosmic = r.get("cosmic_raw") or {}
                sch = cosmic.get("schumann_score")
                kp = cosmic.get("kp_value")
                wind = cosmic.get("wind_speed")
                bz = cosmic.get("bz")
                if sch is None or kp is None or wind is None:
                    continue
                bz = 0.0 if bz is None else bz
                # Cosmic vector (normalized)
                x = np.array([sch / 100.0, kp / 9.0,
                              (wind - 200) / 600.0, (bz + 20) / 40.0])
                # Root features
                root = r.get("root")
                if not root or len(root) != 3:
                    continue
                feats = [PHONEMES[c] for c in root if c in PHONEMES]
                if len(feats) < 3:
                    continue
                feats = np.array(feats)
                cog = feats[:, 3].mean()
                triad = root_to_log_triad(root)
                if triad is None:
                    continue
                f1, f2, f3 = triad
                # voicing / emphatic / manner counts
                from phoneme_grammar import VOICED, EMPHATIC, MANNER
                vc = sum(1 for c in root if c in VOICED) / 3.0
                ec = sum(1 for c in root if c in EMPHATIC) / 3.0
                mc = np.mean([MANNER.get(c, 0.5) for c in root])
                y = np.array([cog, f1 / 4000.0, f2 / 4000.0, f3 / 4000.0,
                              vc, ec, mc])
                X.append(x); Y.append(y)
    if not X:
        return None, None
    return np.array(X), np.array(Y)


# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------
def log_record(rec):
    rec["ts"] = time.time()
    rec["time"] = datetime.now().isoformat(timespec="seconds")
    with open(LOG, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(rec) + "\n")


# ---------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------
def main():
    print("=" * 62)
    print("CONTINUOUS TRAINER — pure NumPy")
    print("=" * 62)
    print(f"  Model: {INPUT_DIM} -> {HIDDEN_DIM} -> {HIDDEN_DIM} -> {OUTPUT_DIM}")
    print(f"  Learning rate: {LR}   Batch: {BATCH}")
    print(f"  Log: {LOG}")
    print(f"  Checkpoint: {CHECKPOINT}")
    print("=" * 62)

    model = TinyMLP()
    if model.load(CHECKPOINT):
        print(f">> Resumed from checkpoint at step {model.step}")

    best_loss = float("inf")
    last_size = 0
    t_start = time.time()

    while True:
        try:
            X, Y = load_examples()
            if X is None or len(X) < BATCH:
                time.sleep(POLL_SEC)
                continue

            # Sample a batch
            idx = np.random.choice(len(X), size=BATCH, replace=False)
            xb, yb = X[idx], Y[idx]

            # Forward / backward
            pred = model.forward(xb)
            loss = float(np.mean((pred - yb) ** 2))
            model.backward(xb, pred, yb)
            model.update(LR)

            # Metrics
            mae = float(np.mean(np.abs(pred - yb)))
            # Cosine similarity per row, then averaged
            a = pred / (np.linalg.norm(pred, axis=1, keepdims=True) + 1e-9)
            b = yb / (np.linalg.norm(yb, axis=1, keepdims=True) + 1e-9)
            cos_sim = float(np.mean(np.sum(a * b, axis=1)))

            rec = {
                "event": "train",
                "step": model.step,
                "loss": loss,
                "mae": mae,
                "cos_sim": cos_sim,
                "samples": len(X),
                "elapsed_s": time.time() - t_start,
            }
            log_record(rec)

            # Print status every step (dashboard reads this log too)
            if model.step % 5 == 0:
                marker = " *" if loss < best_loss else ""
                print(f"  step={model.step:5d}  loss={loss:.5f}  "
                      f"mae={mae:.4f}  cos={cos_sim:.3f}  "
                      f"samples={len(X)}{marker}", flush=True)

            if loss < best_loss:
                best_loss = loss

            if model.step % CHECKPOINT_EVERY == 0:
                model.save(CHECKPOINT)
                print(f"  [checkpoint saved at step {model.step}]", flush=True)
                log_record({"event": "checkpoint",
                            "step": model.step,
                            "loss": loss,
                            "best_loss": best_loss})

            time.sleep(POLL_SEC)

        except KeyboardInterrupt:
            print("\n>> Trainer stopped.", flush=True)
            model.save(CHECKPOINT)
            break
        except Exception as e:
            print(f"!! trainer error: {e}", flush=True)
            time.sleep(POLL_SEC)


if __name__ == "__main__":
    main()
