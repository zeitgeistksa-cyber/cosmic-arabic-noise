#!/usr/bin/env python3
"""
Real Disaster Mix — one WAV built only from recorded disaster samples.

Loads everything in real_samples/*.wav and mixes it all into a single
continuous piece. No synthesis. No phonemes. No physics drivers.

If real_samples/ is empty, fetches from Wikimedia Commons first.
"""
import sys, wave, json, glob, subprocess
from pathlib import Path
import numpy as np

SR = 44100
OUTPUT = Path("real_disasters_mix.wav")
SAMPLES_DIR = Path("real_samples")


def ensure_samples():
    """Run the fetcher if no samples exist."""
    if not SAMPLES_DIR.exists() or not any(SAMPLES_DIR.glob("*.wav")):
        print(">> No samples found. Running fetch_real_samples.py...")
        r = subprocess.run([sys.executable, "fetch_real_samples.py"])
        if r.returncode != 0:
            print("!! Fetch failed", file=sys.stderr)
            return False
    return True


def load_all_samples():
    """Return dict category -> list of mono float32 arrays."""
    categories = {}
    for path in sorted(SAMPLES_DIR.glob("*.wav")):
        # filename is like "earthquake_0.wav" → category = "earthquake"
        cat = path.stem.rsplit("_", 1)[0]
        try:
            with wave.open(str(path), "rb") as wf:
                n = wf.getnframes()
                ch = wf.getnchannels()
                data = np.frombuffer(wf.readframes(n), dtype=np.int16)
            if ch == 2:
                data = data.reshape(-1, 2).mean(axis=1).astype(np.int16)
            audio = data.astype(np.float32) / 32768.0
            if len(audio) < SR:  # skip clips under 1 second
                continue
            categories.setdefault(cat, []).append(audio)
        except Exception as e:
            print(f"!! could not load {path}: {e}", file=sys.stderr)
    return categories


def loop_to_length(audio, length):
    """Loop an audio clip to fill the target length."""
    out = np.zeros(length, dtype=np.float32)
    pos = 0
    while pos < length:
        remaining = length - pos
        take = min(len(audio), remaining)
        out[pos:pos+take] = audio[:take]
        pos += take
    return out


def build_mix(target_sec=180.0):
    """Build the combined mix from all real samples."""
    if not ensure_samples():
        return None

    categories = load_all_samples()
    if not categories:
        print("!! No samples loaded", file=sys.stderr)
        return None

    print(f"\n>> Loaded {sum(len(v) for v in categories.values())} "
          f"samples across {len(categories)} categories:")
    for cat, samples in sorted(categories.items()):
        total_sec = sum(len(s) for s in samples) / SR
        print(f"   {cat:12s}  {len(samples)} samples  "
              f"({total_sec:.1f} s of source)")

    # Target length
    N = int(SR * target_sec)

    # Build a master timeline
    master = np.zeros(N, dtype=np.float32)

    # Per-category gains — earthquake is bass, flood is high, etc.
    gains = {
        "earthquake": 0.45,
        "tremor":     0.35,
        "volcano":    0.40,
        "explosion":  0.30,
        "storm":      0.35,
        "wind":       0.30,
        "wave":       0.30,
        "fire":       0.15,
    }

    # Envelope per category — they enter at staggered times
    entries = {
        "earthquake": (0.0,  0.20),
        "tremor":     (0.05, 0.25),
        "wind":       (0.10, 0.30),
        "storm":      (0.15, 0.35),
        "volcano":    (0.25, 0.45),
        "wave":       (0.30, 0.50),
        "fire":       (0.40, 0.55),
        "explosion":  (0.55, 0.75),
    }

    t = np.arange(N) / SR

    for cat, samples in categories.items():
        gain = gains.get(cat, 0.25)
        entry_start_frac, entry_end_frac = entries.get(cat, (0.0, 0.3))
        entry_start = entry_start_frac * target_sec
        entry_end = entry_end_frac * target_sec

        # Envelope: linear ramp from entry_start to entry_end, hold, fade
        env = np.ones(N, dtype=np.float32)
        # Ramp in
        ramp_in = np.clip((t - entry_start) / max(entry_end - entry_start, 0.1),
                          0, 1)
        env *= ramp_in
        # Fade out at the end
        fade_out_start = target_sec - 15.0
        fade_out = np.clip((target_sec - t) / 15.0, 0, 1)
        env *= fade_out

        # For each sample in category, place it starting at a different
        # offset so they layer
        for i, s in enumerate(samples):
            offset = int((entry_start + i * 2.0) * SR) % N
            looped = loop_to_length(s, N - offset)
            master[offset:offset + len(looped)] += looped * gain * env[offset:offset + len(looped)]

    # Global envelope — swell
    global_env = np.ones(N, dtype=np.float32)
    # fade in first 3 seconds
    fi = int(3 * SR)
    global_env[:fi] = np.linspace(0, 1, fi)
    # fade out last 15 seconds
    fo = int(15 * SR)
    global_env[-fo:] = np.linspace(1, 0, fo)
    master *= global_env

    # RMS-normalize with soft ceiling
    rms = np.sqrt(np.mean(master ** 2)) + 1e-9
    master = master / rms * 0.15

    # Soft-clip
    master = np.tanh(master)

    # Peak-normalize to -0.5 dBFS
    peak = np.max(np.abs(master)) + 1e-9
    master = master / peak * 0.94

    return master


def write_stereo(audio, path):
    """Write as stereo WAV with slight Haas widening."""
    delay = int(SR * 0.010)  # 10 ms
    left = audio
    right = np.concatenate([np.zeros(delay, dtype=np.float32),
                            audio[:-delay]])
    stereo = np.stack([left, right], axis=1)
    int16 = (np.clip(stereo, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(int16.tobytes())


def main():
    print("=" * 60)
    print("REAL DISASTER MIX")
    print("=" * 60)

    mix = build_mix(target_sec=180.0)
    if mix is None:
        sys.exit(1)

    write_stereo(mix, OUTPUT)
    size_mb = OUTPUT.stat().st_size / 1e6
    duration = len(mix) / SR
    print(f"\n>> Wrote {OUTPUT}  ({duration:.1f}s, {size_mb:.1f} MB)")
    print(">> Play with: mpv real_disasters_mix.wav")


if __name__ == "__main__":
    main()
