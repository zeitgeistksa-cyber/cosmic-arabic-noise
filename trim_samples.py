#!/usr/bin/env python3
"""
Trim all WAVs in real_samples/ to short loops.
- Skip silence at the start
- Cut to N seconds max
- RMS-normalize each to a common level
- Overwrite in place (backup kept briefly)
"""
import wave
from pathlib import Path
import numpy as np

SAMPLES_DIR = Path("real_samples")
MAX_SEC = 30          # keep at most 30 seconds
SKIP_SILENCE_SEC = 0.5
SILENCE_THRESHOLD = 0.005  # RMS below this = silence
TARGET_RMS = 0.15


def load_wav(p):
    with wave.open(str(p), "rb") as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        n = wf.getnframes()
        data = np.frombuffer(wf.readframes(n), dtype=np.int16)
    if ch == 2:
        data = data.reshape(-1, 2).mean(axis=1).astype(np.int16)
    return data.astype(np.float32) / 32768.0, sr


def trim_audio(audio, sr):
    # 1) skip silent head
    skip_n = int(sr * SKIP_SILENCE_SEC)
    start = 0
    for i in range(0, len(audio) - skip_n, skip_n):
        chunk = audio[i:i+skip_n]
        if np.sqrt(np.mean(chunk ** 2)) > SILENCE_THRESHOLD:
            start = i
            break
    trimmed = audio[start:]

    # 2) cap length
    max_n = int(sr * MAX_SEC)
    if len(trimmed) > max_n:
        # take from somewhere in the middle to avoid loud edges
        mid = len(trimmed) // 2
        half = max_n // 2
        trimmed = trimmed[mid-half : mid+half]

    # 3) fade in/out
    fade_n = int(sr * 0.3)
    if fade_n * 2 < len(trimmed):
        fi = np.linspace(0, 1, fade_n, dtype=np.float32)
        trimmed[:fade_n] *= fi
        trimmed[-fade_n:] *= fi[::-1]

    # 4) RMS-normalize
    rms = np.sqrt(np.mean(trimmed ** 2)) + 1e-9
    trimmed = trimmed / rms * TARGET_RMS

    # 5) soft clip
    trimmed = np.tanh(trimmed)

    return trimmed


def write_wav(p, audio, sr=44100):
    int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(p), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(int16.tobytes())


def main():
    print("=" * 60)
    print("TRIMMING SAMPLES")
    print("=" * 60)

    total_before = 0
    total_after = 0

    for p in sorted(SAMPLES_DIR.glob("*.wav")):
        size_before = p.stat().st_size
        total_before += size_before

        print(f"\n>> {p.name}")
        print(f"   before: {size_before // 1024} KB")

        try:
            audio, sr = load_wav(p)
            print(f"   source: {len(audio)/sr:.1f} s @ {sr} Hz")

            trimmed = trim_audio(audio, sr)
            write_wav(p, trimmed, sr)

            size_after = p.stat().st_size
            total_after += size_after
            print(f"   after:  {size_after // 1024} KB  "
                  f"({len(trimmed)/sr:.1f} s)")
        except Exception as e:
            print(f"   error: {e}")
            total_after += size_before

    print(f"\n>> Total: {total_before/1e6:.1f} MB -> "
          f"{total_after/1e6:.1f} MB "
          f"({100*total_after/max(total_before,1):.0f}% of original)")


if __name__ == "__main__":
    main()
