#!/usr/bin/env python3
"""
Universe Messenger — broadcast phoneme messages, listen for cosmic response.

Loop:
  1. Read cosmic state (before message)
  2. Choose letters based on past correlations
  3. Broadcast message through speaker
  4. Wait RESPONSE_WINDOW seconds
  5. Read cosmic state (after message)
  6. Store (message, delta) pair
  7. Update letter → cosmic-dimension correlation table
"""
import json, time, sys, subprocess, wave
from pathlib import Path
from datetime import datetime
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from cosmic_data import snapshot as cosmic_snapshot
from tv_space_synth import synth_message, SR, HIGH, DEEP, MID

# ---- Config ----
LETTERS = ["م", "ر", "س", "ن", "ل", "ف", "ث", "ذ", "ش", "ص",
           "ع", "ح", "ك", "ق"]
MSG_LEN = 1
MSG_DUR = 0.55
RESPONSE_WINDOW = 180.0  # 3 minutes
CYCLE_PAUSE = 30.0

DIALOGUE_LOG = Path("universe_dialogue.jsonl")
CORRELATION_FILE = Path("letter_correlations.json")


# ---------------- Cosmic state vector ----------------
def cosmic_vector(s):
    """Turn a snapshot into a numeric vector."""
    return np.array([
        float(s.get("schumann_score") or 0),
        float(s.get("kp_value") or 0),
        float(s.get("wind_speed") or 0),
        float(s.get("bz") or 0),
    ], dtype=np.float64)


# ---------------- Correlation table ----------------
class LetterCorrelations:
    """Track which letters preceded which cosmic changes."""
    def __init__(self):
        self.data = {}
        self.load()

    def load(self):
        if CORRELATION_FILE.exists():
            try:
                self.data = json.loads(CORRELATION_FILE.read_text())
            except Exception:
                self.data = {}
        if not self.data:
            self.data = {l: [0.0, 0.0, 0.0, 0.0, 0] for l in LETTERS}

    def save(self):
        CORRELATION_FILE.write_text(json.dumps(self.data, indent=2))

    def record(self, letters, delta):
        """Record which letters were present in a message and what changed."""
        # Normalize delta per dimension
        abs_delta = np.abs(delta)
        for letter in set(letters):
            if letter not in self.data:
                self.data[letter] = [0.0, 0.0, 0.0, 0.0, 0]
            rec = self.data[letter]
            for i in range(4):
                # Running mean with high weight on new values
                rec[i] = 0.7 * rec[i] + 0.3 * abs_delta[i]
            rec[4] += 1

    def score(self, letter):
        """Overall strength of a letter's apparent effect."""
        if letter not in self.data:
            return 0.0
        rec = self.data[letter]
        return sum(rec[:4]) / max(rec[4], 1)

    def pick_letters(self, n=MSG_LEN):
        """Pick n letters, biased toward those with high reaction scores."""
        scores = np.array([self.score(l) + 0.1 for l in LETTERS])
        # Softmax with temperature
        probs = np.exp(scores * 2.0)
        probs /= probs.sum()
        # Sample without replacement
        chosen = []
        pool = list(LETTERS)
        pool_probs = list(probs)
        for _ in range(min(n, len(pool))):
            idx = np.random.choice(len(pool), p=np.array(pool_probs) / sum(pool_probs))
            chosen.append(pool[idx])
            pool.pop(idx)
            pool_probs.pop(idx)
        return chosen


# ---------------- Broadcast ----------------
def broadcast(audio, out_path="universe_msg.wav"):
    """Write WAV and play through speaker."""
    int16 = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    with wave.open(out_path, "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes(int16.tobytes())
    # Play synchronously, block until done
    subprocess.run(
        ["mpv", "--no-video", "--really-quiet", "--no-terminal",
         "--volume=100", out_path],
        timeout=len(audio) / SR + 5,
    )


# ---------------- Logger ----------------
def log(rec):
    rec["ts"] = time.time()
    rec["time"] = datetime.now().isoformat()
    with open(DIALOGUE_LOG, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
          f"{rec.get('event','?')}", file=sys.stderr, flush=True)


# ---------------- Main loop ----------------
def main():
    print("=" * 60)
    print("UNIVERSE MESSENGER")
    print("=" * 60)
    print(f"  Letters: {' '.join(LETTERS)}")
    print(f"  Message length: {MSG_LEN} letters")
    print(f"  Response window: {RESPONSE_WINDOW}s")
    print(f"  Log: {DIALOGUE_LOG}")
    print(f"  Correlations: {CORRELATION_FILE}")
    print("=" * 60)

    corr = LetterCorrelations()
    message_count = 0

    while True:
        message_count += 1

        # ---- Read cosmic state before ----
        try:
            s_before = cosmic_snapshot()
            v_before = cosmic_vector(s_before)
        except Exception as e:
            log({"event": "error", "phase": "before", "error": str(e)})
            time.sleep(CYCLE_PAUSE)
            continue

        # ---- Pick letters based on past reactions ----
        letters = corr.pick_letters(MSG_LEN)
        log({"event": "message",
             "n": message_count,
             "letters": letters,
             "cosmic_before": v_before.tolist()})

        # ---- Synthesize and broadcast ----
        audio = synth_message(letters, MSG_DUR)
        try:
            broadcast(audio)
        except Exception as e:
            log({"event": "error", "phase": "broadcast", "error": str(e)})

        # ---- Wait for response ----
        time.sleep(RESPONSE_WINDOW)

        # ---- Read cosmic state after ----
        try:
            s_after = cosmic_snapshot()
            v_after = cosmic_vector(s_after)
        except Exception as e:
            log({"event": "error", "phase": "after", "error": str(e)})
            continue

        delta = v_after - v_before
        corr.record(letters, delta)
        corr.save()

        log({"event": "response",
             "n": message_count,
             "letters": letters,
             "delta": delta.tolist(),
             "cosmic_after": v_after.tolist(),
             "deltas_norm": float(np.linalg.norm(delta))})

        # ---- Report top letters ----
        if message_count % 5 == 0:
            ranked = sorted(LETTERS, key=lambda l: -corr.score(l))
            print(f"\n>> After {message_count} messages, "
                  f"top letters by apparent reaction:",
                  file=sys.stderr)
            for l in ranked[:5]:
                print(f"     {l}  score={corr.score(l):.3f}  "
                      f"n={corr.data[l][4]}", file=sys.stderr)

        time.sleep(CYCLE_PAUSE)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n>> Messenger stopped.", file=sys.stderr)
