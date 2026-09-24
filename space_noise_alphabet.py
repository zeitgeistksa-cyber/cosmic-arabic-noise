#!/usr/bin/env python3
"""
Space White Noise — Arabic Alphabet Order.
Fast version: 5-second windows per letter, single FFT per letter.
"""
import wave, time
from pathlib import Path
import numpy as np
import sys

sys.path.insert(0, str(Path(__file__).parent))
from phoneme_table import PHONEMES, LETTER_INDEX

SR = 44100
DURATION = 100.0
ARABIC = "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"
assert len(ARABIC) == 28

F_LOW, F_HIGH = 30.0, 16000.0
band_centers = np.logspace(np.log10(F_LOW), np.log10(F_HIGH), 28)
LETTER_PERIOD = 3.5
BURST_SEC = 2.5       # each side of the letter peak
ENV_SIGMA = 0.7


def build_sequence(letters, duration, letter_period):
    n = int(SR * duration)
    out = np.zeros(n, dtype=np.float32)

    burst_n = int(SR * BURST_SEC)
    total_len = 2 * burst_n - 1
    win_t = np.linspace(-BURST_SEC, BURST_SEC, total_len)
    env = np.exp(-0.5 * (win_t / ENV_SIGMA) ** 2).astype(np.float32)

    for i, letter in enumerate(letters):
        pos_idx = LETTER_INDEX.get(letter, i + 1) - 1
        center_f = band_centers[pos_idx % len(band_centers)]
        lo, hi = center_f * 0.75, center_f * 1.35

        # --- generate noise, filter in ONE FFT ---
        noise = np.random.randn(total_len)
        spec = np.fft.rfft(noise)
        f = np.fft.rfftfreq(total_len, 1 / SR)

        # Band mask
        bc = np.sqrt(lo * hi)
        bw = max((hi - lo) / 2, 5.0)
        mask = np.exp(-0.5 * ((f - bc) / bw) ** 2)

        # Formant peaks from phoneme table
        if letter in PHONEMES:
            F1, F2, F3, CoG = PHONEMES[letter]
            for fc in (F1 * 1000, F2 * 1000, F3 * 1000):
                fw = max(fc * 0.15, 50.0)
                mask += 0.5 * np.exp(-0.5 * ((f - fc) / fw) ** 2)
            cog_hz = CoG * 8000
            if cog_hz > 100:
                mask += 0.4 * np.exp(-0.5 * ((f - cog_hz) / (cog_hz * 0.3)) ** 2)

        mask += 0.02
        filtered = np.fft.irfft(spec * mask, n=total_len).astype(np.float32)

        peak = np.max(np.abs(filtered)) + 1e-9
        filtered = filtered / peak

        local = filtered * env

        # Place in output
        center_sample = int((i + 0.5) * letter_period * SR)
        start = center_sample - burst_n + 1
        end = start + total_len

        s0 = max(0, -start)
        e0 = total_len - max(0, end - n)
        d0 = max(0, start)
        d1 = d0 + (e0 - s0)

        if d1 > d0:
            out[d0:d1] += local[s0:e0]

    return out


def add_baseline(body):
    n = len(body)
    w = np.random.randn(n)
    spec = np.fft.rfft(w)
    f = np.fft.rfftfreq(n, 1 / SR)
    # gentle highpass
    hpf = f / (f + 25.0)
    baseline = np.fft.irfft(spec * hpf, n=n).astype(np.float32)
    baseline = baseline / (np.max(np.abs(baseline)) + 1e-9)
    body = body + baseline * 0.05

    t = np.arange(n) / SR
    body += (0.08 * np.sin(2 * np.pi * 30 * t)).astype(np.float32)
    body *= (1.0 + 0.25 * np.sin(2 * np.pi * 0.04 * t)).astype(np.float32)
    return body


def write_stereo(body, path):
    peak = np.max(np.abs(body)) + 1e-9
    body = body / peak * 0.94
    n = len(body)
    t = np.arange(n) / SR
    pan = (0.5 + 0.5 * np.sin(2 * np.pi * 0.06 * t)).astype(np.float32)
    d1, d2 = int(SR * 0.012), int(SR * 0.032)
    left = body * pan + np.concatenate([np.zeros(d1, np.float32), body[:-d1]]) * (1 - pan) * 0.35
    right = body * (1 - pan) + np.concatenate([np.zeros(d2, np.float32), body[:-d2]]) * pan * 0.35
    peak = max(np.max(np.abs(left)), np.max(np.abs(right))) + 1e-9
    left = left / peak * 0.94
    right = right / peak * 0.94
    stereo = np.stack([left, right], axis=1)
    int16 = (np.clip(stereo, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes(int16.tobytes())


def make_variant(name, letters, duration, letter_period, path):
    t0 = time.time()
    print(f"\n>> {name}  ({duration}s)")
    body = build_sequence(letters, duration, letter_period)
    print(f"   sequence done in {time.time()-t0:.1f}s")
    body = add_baseline(body)
    print(f"   baseline done in {time.time()-t0:.1f}s")
    write_stereo(body, path)
    sz = path.stat().st_size / 1e6
    print(f"   wrote {path.name}  ({sz:.1f} MB)  total {time.time()-t0:.1f}s")


def main():
    print("=" * 68)
    print("SPACE WHITE NOISE — Arabic Alphabet Order (fast)")
    print("=" * 68)
    np.random.seed(2026)

    make_variant("forward", list(ARABIC), DURATION, LETTER_PERIOD,
                 Path("space_noise_forward.wav"))
    make_variant("reverse", list(reversed(ARABIC)), DURATION, LETTER_PERIOD,
                 Path("space_noise_reverse.wav"))

    # Palindrome
    print(f"\n>> palindrome")
    t0 = time.time()
    pal_period = 1.75
    fwd = build_sequence(list(ARABIC), DURATION / 2, pal_period)
    rev = build_sequence(list(reversed(ARABIC)), DURATION / 2, pal_period)
    pal = np.concatenate([fwd, rev]).astype(np.float32)
    pal = add_baseline(pal)
    xf = int(SR * 3.0)
    fi = np.linspace(0, 1, xf, dtype=np.float32)
    pal[:xf] = pal[:xf] * fi + pal[-xf:] * (1 - fi)
    pal = pal[:-xf]
    write_stereo(pal, Path("space_noise_palindrome.wav"))
    sz = Path("space_noise_palindrome.wav").stat().st_size / 1e6
    print(f"   wrote space_noise_palindrome.wav  ({sz:.1f} MB)  total {time.time()-t0:.1f}s")

    print("\n>> Done. Play with:")
    print("   mpv --loop=inf space_noise_forward.wav")


if __name__ == "__main__":
    main()
