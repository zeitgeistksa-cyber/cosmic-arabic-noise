#!/usr/bin/env python3
"""
Speak an Arabic poem through the phoneme engine.
Extracts triliteral roots from each word and synthesizes them in order.
"""
import sys, wave, re
import numpy as np
from pathlib import Path
from phoneme_table import PHONEMES, root_to_log_triad
from phoneme_grammar import VOICED, EMPHATIC, MANNER
from extract_roots import triliteral_skeleton

SR = 44100
ROOT_DUR = 1.6      # seconds per root
GAP_DUR = 0.15      # silence between roots

# ---------------- The Poem ----------------
# Opening of Imru' al-Qais's Mu'allaqa — the most famous line in Arabic poetry.
import argparse
import json as _json

def _load_poem_args():
    p = argparse.ArgumentParser()
    p.add_argument("--title", required=True, help="Poem title")
    p.add_argument("--lines-file", required=True,
                   help="Text file with one poem line per line")
    p.add_argument("--out", required=True, help="Output WAV path")
    p.add_argument("--roots-out", required=True,
                   help="Output roots JSON path")
    return p.parse_args()

_args = _load_poem_args()
POEM_TITLE = _args.title
POEM_LINES = [ln.strip() for ln in
              Path(_args.lines_file).read_text(encoding="utf-8").splitlines()
              if ln.strip()]
OUT_WAV = Path(_args.out)
OUT_ROOTS = Path(_args.roots_out)

# ---------------- Synthesis ----------------
def char(c):
    """Per-letter character: (sub_gain, hiss_gain)."""
    if c not in PHONEMES:
        return 0.0, 0.0
    voice = 1.0 if c in VOICED else 0.0
    emph = 1.0 if c in EMPHATIC else 0.0
    manner = MANNER.get(c, 0.5)
    return (voice * (1.0 - manner) * 0.5 + emph * 0.3, manner * 0.4)


def synth_root(root, sr=SR, dur=ROOT_DUR):
    """Return a mono float array for one root, 3 syllables with per-letter character."""
    if len(root) != 3 or root_to_log_triad(root) is None:
        return np.zeros(int(sr * dur), dtype=np.float32)
    f1, f2, f3 = root_to_log_triad(root)
    letters = list(root)
    n = int(sr * dur)
    t = np.arange(n) / sr
    pos = np.linspace(0.0, 1.0, n)   # position within the root's timeline

    def env(start, end):
        c = 0.5 * (start + end)
        h = 0.5 * (end - start) + 1e-9
        return np.maximum(0.0, 1.0 - np.abs(pos - c) / h)

    e1 = env(0.00, 0.42)
    e2 = env(0.29, 0.71)
    e3 = env(0.58, 1.00)

    triad = (e1 * np.sin(2*np.pi*f1*t)
             + e2 * np.sin(2*np.pi*f2*t)
             + e3 * np.sin(2*np.pi*f3*t))

    # per-letter sub thump / hiss
    s0, h0 = char(letters[0])
    s1, h1 = char(letters[1])
    s2, h2 = char(letters[2])

    sub_lfo = np.sin(2*np.pi*35.0*t)
    noise = np.random.randn(n)

    sub = (s0*e1 + s1*e2 + s2*e3) * sub_lfo
    hiss = (h0*e1 + h1*e2 + h2*e3) * noise

    mixed = triad * 0.62 + sub * 0.18 + hiss * 0.12
    sat = np.tanh(np.sin(mixed * 2.2) * 2.8)

    # gentle fade in/out
    fade_n = int(sr * 0.03)
    if fade_n > 0:
        fade = np.linspace(0, 1, fade_n)
        sat[:fade_n] *= fade
        sat[-fade_n:] *= fade[::-1]

    peak = np.max(np.abs(sat)) + 1e-9
    return (sat / peak * 0.95).astype(np.float32)


def word_to_root(word):
    """Try to extract a 3-letter root from a word. Returns None if impossible."""
    return triliteral_skeleton(word)


# ---------------- Main ----------------
def main():
    print(f">> Poem: {POEM_TITLE}")
    print(f">> Lines: {len(POEM_LINES)}")

    samples = []
    timeline = []

    for line_idx, line in enumerate(POEM_LINES):
        words = line.split()
        print(f"\n  Line {line_idx + 1}: {line}")
        for w in words:
            root = word_to_root(w)
            if root and len(root) == 3 and all(c in PHONEMES for c in root):
                samples.append(synth_root(root))
                # inter-root silence
                samples.append(np.zeros(int(SR * GAP_DUR), dtype=np.float32))
                timeline.append((w, root))
                triad = root_to_log_triad(root)
                print(f"    {w:8s} -> {root}  f1={triad[0]:6.1f}  "
                      f"f2={triad[1]:6.1f}  f3={triad[2]:6.1f}")
            else:
                print(f"    {w:8s} -> (skipped, no valid triliteral root)")

    if not samples:
        print("!! no roots extracted from poem")
        return

    audio = np.concatenate(samples)
    total_sec = len(audio) / SR
    print(f"\n>> Total: {len(timeline)} roots, {total_sec:.1f} seconds")

    # stereo with slight stereo width
    delay = int(SR * 0.004)
    left = audio
    right = np.concatenate([np.zeros(delay, dtype=np.float32), audio[:-delay]])
    stereo = np.stack([left, right], axis=1)

    int16 = (np.clip(stereo, -1.0, 1.0) * 32767).astype(np.int16)
    out = OUT_WAV
    with wave.open(str(out), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(int16.tobytes())

    print(f">> wrote {out}")

    # Save the root sequence for later analysis
    import json
    seq = [{"word": w, "root": r, "line": i}
           for i, (w, r) in enumerate(timeline)]
    OUT_ROOTS.write_text(
        json.dumps({"title": POEM_TITLE, "sequence": seq},
                   ensure_ascii=False, indent=2))
    print(f">> wrote poem_roots.json")


if __name__ == "__main__":
    main()
