#!/usr/bin/env python3
"""
Binary TV Space — FAST version.
Pre-generates one noise buffer per band and mixes with envelopes.
"""
import wave, time
from pathlib import Path
import numpy as np

SR = 44100
DURATION_SEC = 2 * 60
LETTER_PERIOD = 1.2
LETTER_SIGMA = 0.45

VOICED_SET = set("بج دذرزضظعغلمنوي".replace(" ", ""))
EMPHATIC_SET = set("صضطظ")
FRICATIVE_SET = set("ثذزسشصضظفخغحعه")
ALPHABET = "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"

BAND_RANGES = {
    "SUB":  (28, 80),
    "LOW":  (80, 250),
    "MID":  (250, 800),
    "HIGH": (2500, 7000),
    "AIR":  (7000, 15000),
}

BAND_RULES = {
    (0, 0, 0): ["SUB"],
    (0, 0, 1): ["SUB", "MID"],
    (0, 1, 0): ["LOW", "HIGH"],
    (0, 1, 1): ["HIGH"],
    (1, 0, 0): ["SUB", "MID"],
    (1, 0, 1): ["MID"],
    (1, 1, 0): ["MID", "HIGH"],
    (1, 1, 1): ["HIGH", "AIR"],
}


def letter_code(letter):
    V = 1 if letter in VOICED_SET else 0
    M = 1 if letter in FRICATIVE_SET else 0
    E = 1 if letter in EMPHATIC_SET else 0
    return (V, M, E)


def build_band_pool():
    """Pre-generate one 2-second noise buffer per band."""
    n = int(SR * 2.0)
    pool = {}
    for name, (lo, hi) in BAND_RANGES.items():
        w = np.random.randn(n)
        spec = np.fft.rfft(w)
        f = np.fft.rfftfreq(n, 1/SR)
        bc = np.sqrt(lo * hi)
        bw = max((hi - lo) / 2, 3.0)
        mask = np.exp(-0.5 * ((f - bc) / bw) ** 2) + 0.02
        out = np.fft.irfft(spec * mask, n=n)
        peak = np.max(np.abs(out)) + 1e-9
        pool[name] = (out / peak).astype(np.float32)
    return pool


def main():
    print("=" * 60)
    print("BINARY TV SPACE — FAST")
    print(f"  Duration: {DURATION_SEC/60:.1f} min")
    print(f"  Letters: ~{int(DURATION_SEC / LETTER_PERIOD)}")
    print("=" * 60)

    t_start = time.time()

    np.random.seed(2026)

    n_total = int(SR * DURATION_SEC)
    out = np.zeros(n_total, dtype=np.float32)

    print(">> Pre-generating band pool...")
    pool = build_band_pool()
    print(f"   pool ready in {time.time()-t_start:.1f}s")

    # Build letter sequence: forward + reverse + random walk
    letters = list(ALPHABET) + list(reversed(ALPHABET))
    slots = int(DURATION_SEC / LETTER_PERIOD)
    idx = 0
    while len(letters) < slots:
        step = int(np.random.choice([-7, -5, -3, -1, 1, 3, 5, 7]))
        idx = (idx + step) % 28
        letters.append(ALPHABET[idx])
    letters = letters[:slots]

    print(f">> {len(letters)} letters")

    # Envelope
    burst_n = int(SR * LETTER_PERIOD * 3)
    local_t = np.linspace(-LETTER_PERIOD * 1.5,
                          LETTER_PERIOD * 1.5, burst_n)
    env = np.exp(-0.5 * (local_t / LETTER_SIGMA) ** 2).astype(np.float32)

    # Build the piece
    print(">> Mixing letters...")
    for i, letter in enumerate(letters):
        code = letter_code(letter)
        bands = BAND_RULES.get(code, ["MID"])

        # Build burst by mixing pre-computed band noise
        local = np.zeros(burst_n, dtype=np.float32)
        for band in bands:
            src = pool[band]
            # random offset
            off = np.random.randint(0, len(src) - burst_n) if len(src) > burst_n else 0
            chunk = src[off:off+burst_n]
            if len(chunk) < burst_n:
                chunk = np.pad(chunk, (0, burst_n - len(chunk)))
            local += chunk

        local = local / (np.max(np.abs(local)) + 1e-9)
        local = local * env

        center = int((i + 0.5) * LETTER_PERIOD * SR)
        start = center - burst_n // 2
        end = start + burst_n

        s0 = max(0, -start)
        e0 = burst_n - max(0, end - n_total)
        d0 = max(0, start)
        d1 = d0 + (e0 - s0)
        if d1 > d0:
            out[d0:d1] += local[s0:e0]

        if i % 500 == 0 and i > 0:
            pct = 100 * i / len(letters)
            print(f"   {pct:.0f}%  ({time.time()-t_start:.0f}s)")

    print(f">> Mix done in {time.time()-t_start:.1f}s")

    # Baseline hiss — generate as a 5s loop, tile
    print(">> Adding baseline hiss...")
    loop_n = int(SR * 5.0)
    w = np.random.randn(loop_n)
    spec = np.fft.rfft(w)
    f = np.fft.rfftfreq(loop_n, 1/SR)
    mask = (f > 100) * (f < 16000) * (f / (f + 100.0))
    hiss_loop = np.fft.irfft(spec * mask, n=loop_n).astype(np.float32)
    hiss_loop = hiss_loop / (np.max(np.abs(hiss_loop)) + 1e-9)
    repeats = (n_total + loop_n - 1) // loop_n
    baseline = np.tile(hiss_loop, repeats)[:n_total] * 0.04
    out += baseline

    # Sub drone
    print(">> Adding sub drone...")
    t = np.arange(n_total) / SR
    out += (0.06 * np.sin(2 * np.pi * 30 * t)).astype(np.float32)

    # Slow swell
    out *= (0.85 + 0.15 * np.sin(2 * np.pi * 0.015 * t)).astype(np.float32)

    # Normalize
    print(">> Normalizing...")
    peak = np.max(np.abs(out)) + 1e-9
    out = out / peak * 0.94

    # Stereo
    print(">> Stereo widening...")
    pan = (0.5 + 0.5 * np.sin(2 * np.pi * 0.02 * t)).astype(np.float32)
    d1 = int(SR * 0.010)
    d2 = int(SR * 0.025)
    left = out * pan + np.concatenate([np.zeros(d1, np.float32), out[:-d1]]) * (1 - pan) * 0.3
    right = out * (1 - pan) + np.concatenate([np.zeros(d2, np.float32), out[:-d2]]) * pan * 0.3
    peak = max(np.max(np.abs(left)), np.max(np.abs(right))) + 1e-9
    left = left / peak * 0.94
    right = right / peak * 0.94

    # Write
    print(">> Writing WAV...")
    stereo = np.stack([left, right], axis=1)
    int16 = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
    out_path = Path("binary_tv_space.wav")
    with wave.open(str(out_path), "w") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes(int16.tobytes())

    print(f"\n>> wrote {out_path}  ({out_path.stat().st_size/1e6:.1f} MB)")
    print(f">> Total build time: {time.time()-t_start:.1f}s")


if __name__ == "__main__":
    main()
