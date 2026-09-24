#!/usr/bin/env python3
"""Information-theoretic measures of the audio."""
import wave, sys, zlib
import numpy as np

def load_wav(path):
    with wave.open(path, "rb") as wf:
        n = wf.getnframes()
        data = np.frombuffer(wf.readframes(n), dtype=np.int16)
        return data, wf.getframerate()

def spectral_entropy(audio, sr):
    spec = np.abs(np.fft.rfft(audio))
    p = spec / (spec.sum() + 1e-9)
    return -np.sum(p * np.log2(p + 1e-9))

def main(path):
    data, sr = load_wav(path)
    print(f">> {path}")

    # Raw bytes
    raw_bytes = data.tobytes()

    # Compressed size
    compressed = zlib.compress(raw_bytes, level=9)
    ratio = len(compressed) / len(raw_bytes)

    print(f"\n>> Information content:")
    print(f"   raw size:         {len(raw_bytes)/1e6:.2f} MB")
    print(f"   compressed size:  {len(compressed)/1e6:.2f} MB")
    print(f"   compression ratio: {ratio:.4f}")
    print(f"   (1.0 = pure noise, 0.0 = silence)")

    # Spectral entropy
    audio_mono = data.reshape(-1, 2)[:, 0].astype(np.float32)
    n_bits = len(audio_mono) * 8 * ratio
    print(f"   effective bits/sample: {8 * ratio:.2f}")

    # Spectral entropy per 1-second window
    win_n = sr
    n_windows = len(audio_mono) // win_n
    ents = []
    for i in range(n_windows):
        seg = audio_mono[i*win_n:(i+1)*win_n]
        if len(seg) < 512: continue
        ents.append(spectral_entropy(seg, sr))
    print(f"\n>> Spectral entropy per 1-second window:")
    print(f"   mean: {np.mean(ents):.3f}  std: {np.std(ents):.3f}")
    print(f"   range: [{min(ents):.2f}, {max(ents):.2f}]")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "active_patched.wav")
