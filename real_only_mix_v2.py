#!/usr/bin/env python3
"""
Real Disaster Mix v2 — seamless loop, enhanced dynamics, wider stereo.

Adds:
- Crossfade loop so the end blends into the beginning
- Dual-scale Haas widening
- Sub-harmonic layer extracted from lows
- Slow dynamic compression
- Auto-gain
"""
import sys, wave, glob, subprocess
from pathlib import Path
import numpy as np

SR = 44100
OUTPUT = Path("real_disasters_mix_v2.wav")
SAMPLES_DIR = Path("real_samples")


def ensure_samples():
    if not SAMPLES_DIR.exists() or not any(SAMPLES_DIR.glob("*.wav")):
        print(">> No samples found. Running fetch_real_samples.py...")
        r = subprocess.run([sys.executable, "fetch_real_samples.py"])
        if r.returncode != 0:
            print("!! Fetch failed", file=sys.stderr)
            return False
    return True


def load_all_samples():
    categories = {}
    for path in sorted(SAMPLES_DIR.glob("*.wav")):
        cat = path.stem.rsplit("_", 1)[0]
        try:
            with wave.open(str(path), "rb") as wf:
                n = wf.getnframes()
                ch = wf.getnchannels()
                data = np.frombuffer(wf.readframes(n), dtype=np.int16)
            if ch == 2:
                data = data.reshape(-1, 2).mean(axis=1).astype(np.int16)
            audio = data.astype(np.float32) / 32768.0
            if len(audio) < SR:
                continue
            categories.setdefault(cat, []).append(audio)
        except Exception as e:
            print(f"!! could not load {path}: {e}", file=sys.stderr)
    return categories


def loop_to_length(audio, length):
    out = np.zeros(length, dtype=np.float32)
    pos = 0
    while pos < length:
        take = min(len(audio), length - pos)
        out[pos:pos+take] = audio[:take]
        pos += take
    return out


def sub_harmonic_layer(audio, factor=8):
    """Extract a low-pass filtered version to add as a sub layer."""
    # Simple moving-average low-pass at ~SR/factor
    win = max(2, factor * 4)
    kernel = np.ones(win, dtype=np.float32) / win
    low = np.convolve(audio, kernel, mode="same")
    # Scale down and slow it further
    return low.astype(np.float32) * 0.5


def slow_compress(audio, threshold=0.3, ratio=3.0, attack_ms=20, release_ms=400):
    """Slow dynamic compression — reduce peaks, lift quiet parts."""
    env = np.abs(audio)
    # Envelope follower
    attack = np.exp(-1.0 / (SR * attack_ms / 1000.0))
    release = np.exp(-1.0 / (SR * release_ms / 1000.0))
    smooth = np.zeros_like(env)
    prev = 0.0
    for i in range(len(env)):
        coef = attack if env[i] > prev else release
        prev = coef * prev + (1 - coef) * env[i]
        smooth[i] = prev
    # Compute gain reduction
    over = np.maximum(smooth - threshold, 0.0)
    gain_reduction = 1.0 - over / (over + (threshold * (ratio - 1.0) / ratio + 1e-9))
    # Add makeup gain
    return audio * gain_reduction * 1.4


def build_mix(target_sec=240.0):
    if not ensure_samples():
        return None

    categories = load_all_samples()
    if not categories:
        print("!! No samples loaded", file=sys.stderr)
        return None

    print(f"\n>> {sum(len(v) for v in categories.values())} samples, "
          f"{len(categories)} categories")
    for cat, samples in sorted(categories.items()):
        total_sec = sum(len(s) for s in samples) / SR
        print(f"   {cat:12s}  {len(samples)}  ({total_sec:.1f}s)")

    N = int(SR * target_sec)
    master = np.zeros(N, dtype=np.float32)
    t = np.arange(N) / SR

    # Entry fractions — stagger across 55% of the piece
    entries = {
        "earthquake": (0.00, 0.15),
        "tremor":     (0.05, 0.20),
        "wind":       (0.10, 0.25),
        "storm":      (0.15, 0.30),
        "volcano":    (0.25, 0.40),
        "wave":       (0.30, 0.45),
        "fire":       (0.40, 0.50),
        "explosion":  (0.50, 0.65),
    }
    gains = {
        "earthquake": 0.50, "tremor": 0.38, "volcano": 0.42,
        "explosion": 0.32, "storm": 0.36, "wind": 0.32,
        "wave": 0.30, "fire": 0.14,
    }

    for cat, samples in categories.items():
        gain = gains.get(cat, 0.25)
        start_frac, end_frac = entries.get(cat, (0.0, 0.3))
        s0 = start_frac * target_sec
        s1 = end_frac * target_sec

        # Envelope: ramp in with a curve, stay full, subtle breathing
        ramp = np.clip((t - s0) / max(s1 - s0, 0.1), 0, 1)
        ramp = ramp ** 1.5  # slower start
        breathe = 1.0 + 0.08 * np.sin(2 * np.pi * (0.05 + 0.03 * cat.__hash__() % 0.1) * t)
        env = ramp * breathe

        for i, s in enumerate(samples):
            offset = int((s0 + i * 2.5) * SR) % N
            looped = loop_to_length(s, N - offset)
            master[offset:offset+len(looped)] += looped * gain * env[offset:offset+len(looped)]

    # Sub-harmonic layer
    print(">> Extracting sub layer...")
    sub = sub_harmonic_layer(master, factor=10)
    master += sub * 0.18

    # Compression
    print(">> Slow compression...")
    master = slow_compress(master, threshold=0.35, ratio=3.0)

    # Normalize to RMS 0.15
    rms = np.sqrt(np.mean(master ** 2)) + 1e-9
    master = master / rms * 0.15

    # Soft clip
    master = np.tanh(master * 1.1)

    # Peak-normalize
    peak = np.max(np.abs(master)) + 1e-9
    master = master / peak * 0.94

    # ===== SEAMLESS LOOP =====
    # Take the last 8 seconds and crossfade them over the first 8 seconds
    print(">> Crossfading for seamless loop...")
    xf = int(SR * 8.0)
    fade_in = np.linspace(0, 1, xf, dtype=np.float32)
    fade_out = 1.0 - fade_in
    tail = master[-xf:]
    # Overwrite first `xf` samples with a blend of the tail and the head
    master[:xf] = master[:xf] * fade_in + tail * fade_out
    # Trim the tail so the file ends where the crossfade begins
    master = master[:-xf]

    return master


def write_stereo(audio, path):
    """Stereo with dual-scale Haas widening."""
    delay1 = int(SR * 0.010)  # 10 ms
    delay2 = int(SR * 0.035)  # 35 ms

    left = audio + np.concatenate([np.zeros(delay1, dtype=np.float32), audio[:-delay1]]) * 0.3
    right = audio + np.concatenate([np.zeros(delay2, dtype=np.float32), audio[:-delay2]]) * 0.3

    peak = max(np.max(np.abs(left)), np.max(np.abs(right))) + 1e-9
    left = left / peak * 0.94
    right = right / peak * 0.94

    stereo = np.stack([left, right], axis=1)
    int16 = (np.clip(stereo, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(int16.tobytes())


def main():
    print("=" * 60)
    print("REAL DISASTER MIX v2 — ENHANCED")
    print("=" * 60)
    mix = build_mix(target_sec=240.0)
    if mix is None:
        sys.exit(1)
    write_stereo(mix, OUTPUT)
    size_mb = OUTPUT.stat().st_size / 1e6
    duration = len(mix) / SR
    print(f"\n>> Wrote {OUTPUT}  ({duration:.1f}s, {size_mb:.1f} MB)")
    print(">> Seamless loop — the end blends into the beginning")
    print(">> Play with: mpv --loop=inf real_disasters_mix_v2.wav")


if __name__ == "__main__":
    main()
