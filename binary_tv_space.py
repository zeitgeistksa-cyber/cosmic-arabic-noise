#!/usr/bin/env python3
"""
Binary TV Space — 20-minute continuous piece.

Each Arabic letter has a 3-bit code [Voicing, Manner, Emphasis].
The code selects which space bands are active in that letter's slot.
The sequence of codes drives the spectral envelope over time.

Bands:
  SUB   28-80 Hz
  LOW   80-250 Hz
  MID   250-800 Hz
  HIGH  2500-7000 Hz
  AIR   7000-15000 Hz
"""
import wave
from pathlib import Path
import numpy as np
import sys
sys.path.insert(0, str(Path(__file__).parent))
from phoneme_table import PHONEMES

SR = 44100
DURATION_SEC = 2 * 60          # 20 minutes
LETTER_PERIOD = 1.2              # seconds per letter
LETTER_SIGMA = 0.45              # envelope width

# ------------- Letter → binary code -------------
# From phoneme table analysis
VOICED = set("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")  # will filter below
# Real voicing classification
VOICED_SET = set("بج دذرزضظعغلمنوي".replace(" ", ""))
EMPHATIC_SET = set("صضطظ")
FRICATIVE_SET = set("ثذزسشصضظفخغحعه")

ALPHABET = "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"

def letter_code(letter):
    """Return [V, M, E] binary code for a letter."""
    V = 1 if letter in VOICED_SET else 0
    M = 1 if letter in FRICATIVE_SET else 0
    E = 1 if letter in EMPHATIC_SET else 0
    return (V, M, E)


# ------------- Band assignment from code -------------
# V=voiced → SUB band preferred
# M=fricative → HIGH band preferred
# E=emphatic → MID boost
BAND_RULES = {
    (0, 0, 0): ["SUB"],           # voiceless stop
    (0, 0, 1): ["SUB", "MID"],    # voiceless emphatic stop
    (0, 1, 0): ["LOW", "HIGH"],   # voiceless fricative (س ف ح خ)
    (0, 1, 1): ["HIGH"],          # voiceless emphatic fricative (ص)
    (1, 0, 0): ["SUB", "MID"],    # voiced stop / nasal (ب د م ن)
    (1, 0, 1): ["MID"],           # voiced emphatic stop (ض)
    (1, 1, 0): ["MID", "HIGH"],   # voiced fricative (ز ذ غ ع)
    (1, 1, 1): ["HIGH", "AIR"],   # voiced emphatic fricative (ظ)
}

BAND_RANGES = {
    "SUB":  (28, 80),
    "LOW":  (80, 250),
    "MID":  (250, 800),
    "HIGH": (2500, 7000),
    "AIR":  (7000, 15000),
}


# ------------- Fast band-shaped noise -------------
def shaped_burst(n, bands):
    """Return n samples of noise filtered to the given bands."""
    noise = np.random.randn(n)
    spec = np.fft.rfft(noise)
    f = np.fft.rfftfreq(n, 1 / SR)
    mask = np.zeros_like(f)
    for band_name in bands:
        lo, hi = BAND_RANGES[band_name]
        bc = np.sqrt(lo * hi)
        bw = max((hi - lo) / 2, 3.0)
        mask += np.exp(-0.5 * ((f - bc) / bw) ** 2)
    mask += 0.01
    out = np.fft.irfft(spec * mask, n=n)
    peak = np.max(np.abs(out)) + 1e-9
    return (out / peak).astype(np.float32)


# ------------- Build the binary sequence -------------
def binary_sequence(duration_sec):
    """
    Generate a letter sequence that walks through the binary codes.
    Uses a simple pattern: forward alphabet → backward alphabet →
    random walk through code space.
    """
    letters = []
    # Phase 1: forward alphabet (28 letters)
    letters.extend(list(ALPHABET))
    # Phase 2: reverse alphabet
    letters.extend(list(reversed(ALPHABET)))
    # Phase 3: random walk (fill remaining time)
    slots = int(duration_sec / LETTER_PERIOD)
    remaining = slots - len(letters)
    if remaining > 0:
        # Random walk that favors adjacent letters in the code space
        idx = 0
        for _ in range(remaining):
            # Step ±1, ±3, ±5, ±7 (prime steps = primes based shuffle)
            step = int(np.random.choice([-7, -5, -3, -1, 1, 3, 5, 7]))
            idx = (idx + step) % 28
            letters.append(ALPHABET[idx])
    return letters


# ------------- Build the piece -------------
def build(duration_sec, letter_period, output_path):
    n_total = int(SR * duration_sec)
    out = np.zeros(n_total, dtype=np.float32)

    letters = binary_sequence(duration_sec)
    print(f">> {len(letters)} letters over {duration_sec/60:.1f} min")

    burst_n = int(SR * letter_period * 3)
    local_t = np.linspace(-letter_period * 1.5, letter_period * 1.5, burst_n)
    env = np.exp(-0.5 * (local_t / LETTER_SIGMA) ** 2).astype(np.float32)

    # Track binary codes for the log
    code_log = []

    for i, letter in enumerate(letters):
        code = letter_code(letter)
        bands = BAND_RULES.get(code, ["MID"])
        code_log.append((letter, code, bands))

        local = shaped_burst(burst_n, bands) * env

        center = int((i + 0.5) * letter_period * SR)
        start = center - burst_n // 2
        end = start + burst_n

        s0 = max(0, -start)
        e0 = burst_n - max(0, end - n_total)
        d0 = max(0, start)
        d1 = d0 + (e0 - s0)
        if d1 > d0:
            out[d0:d1] += local[s0:e0]

        # progress print every 100 letters
        if i % 100 == 0 and i > 0:
            pct = 100 * i / len(letters)
            print(f"   {pct:.0f}%  letter {letters[i]}, code {code} → {bands}")

    # Baseline hiss (the continuous space bed)
    print(">> Adding baseline hiss...")
    baseline = shaped_burst(n_total, ["LOW", "HIGH", "AIR"]) * 0.04
    out += baseline

    # Deep 30 Hz sub drone
    print(">> Adding sub drone...")
    t = np.arange(n_total) / SR
    out += (0.06 * np.sin(2 * np.pi * 30 * t)).astype(np.float32)

    # Very slow swell
    out *= (0.85 + 0.15 * np.sin(2 * np.pi * 0.015 * t)).astype(np.float32)

    # Peak normalize
    peak = np.max(np.abs(out)) + 1e-9
    out = out / peak * 0.94

    return out, code_log


def write_wav(audio, path):
    # Mono → stereo with slow panning
    n = len(audio)
    t = np.arange(n) / SR
    pan = (0.5 + 0.5 * np.sin(2 * np.pi * 0.02 * t)).astype(np.float32)
    d1 = int(SR * 0.010)
    d2 = int(SR * 0.025)
    left = audio * pan + np.concatenate([np.zeros(d1, np.float32), audio[:-d1]]) * (1 - pan) * 0.3
    right = audio * (1 - pan) + np.concatenate([np.zeros(d2, np.float32), audio[:-d2]]) * pan * 0.3
    peak = max(np.max(np.abs(left)), np.max(np.abs(right))) + 1e-9
    left = left / peak * 0.94
    right = right / peak * 0.94
    stereo = np.stack([left, right], axis=1)
    int16 = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes(int16.tobytes())


def main():
    print("=" * 68)
    print("BINARY TV SPACE — 20-minute continuous piece")
    print("=" * 68)
    print(f"  Duration: {DURATION_SEC/60:.1f} minutes")
    print(f"  Letter period: {LETTER_PERIOD}s")
    print(f"  Expected letters: ~{int(DURATION_SEC/LETTER_PERIOD)}")

    np.random.seed(2026)

    t0 = __import__("time").time()
    audio, code_log = build(DURATION_SEC, LETTER_PERIOD,
                             Path("binary_tv_space.wav"))
    print(f">> Build time: {__import__('time').time() - t0:.1f}s")

    write_wav(audio, Path("binary_tv_space.wav"))
    size_mb = Path("binary_tv_space.wav").stat().st_size / 1e6
    print(f"\n>> wrote binary_tv_space.wav  ({size_mb:.1f} MB)")

    # Print code statistics
    from collections import Counter
    code_counts = Counter(tuple(c) for _, c, _ in code_log)
    print(f"\n>> Binary code distribution:")
    for code, count in code_counts.most_common():
        pct = 100 * count / len(code_log)
        print(f"   {code}  {count:>4}  ({pct:5.1f}%)  "
              f"V={code[0]} M={code[1]} E={code[2]}  "
              f"→ {BAND_RULES[code]}")


if __name__ == "__main__":
    main()
