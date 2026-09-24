#!/usr/bin/env python3
"""
TV Space Sound — three layers, exactly the sci-fi cliché.
"""
import wave
from pathlib import Path
import numpy as np

SR = 44100
DURATION = 60.0
N = int(SR * DURATION)
t = np.arange(N) / SR


def shaped_noise(band_lo, band_hi, tilt=0.0):
    """Generate noise filtered to one band."""
    w = np.random.randn(N)
    spec = np.fft.rfft(w)
    f = np.fft.rfftfreq(N, 1 / SR)
    bc = np.sqrt(band_lo * band_hi)
    bw = max((band_hi - band_lo) / 2, 3.0)
    mask = np.exp(-0.5 * ((f - bc) / bw) ** 2)
    if tilt:
        mask *= (f / bc) ** tilt
    return np.fft.irfft(spec * mask, n=N)


print(">> Building TV space layers...")

# Layer 1 — the deep hum (nasal م-like)
sub = shaped_noise(28, 55, tilt=-0.3)
sub *= 1.0 + 0.15 * np.sin(2 * np.pi * 0.03 * t)  # slow swell
sub *= 0.7

# Layer 2 — the mid hum (sonorant ر-like)
mid = shaped_noise(120, 320, tilt=0.0)
mid *= 1.0 + 0.2 * np.sin(2 * np.pi * 0.07 * t)
mid *= 0.4

# Layer 3 — the high hiss (fricative س-like)
high = shaped_noise(6500, 14000, tilt=0.2)
high *= 1.0 + 0.1 * np.sin(2 * np.pi * 0.11 * t)
high *= 0.35

# Mix
mix = sub + mid + high

# Very slow global swell — breathing
mix *= 0.85 + 0.15 * np.sin(2 * np.pi * 0.02 * t)

# Normalize
mix /= (np.max(np.abs(mix)) + 1e-9)
mix *= 0.95

# Stereo with slow panning
pan = 0.5 + 0.5 * np.sin(2 * np.pi * 0.04 * t)
d = int(SR * 0.008)
left = mix * pan + np.concatenate([np.zeros(d, dtype=np.float32), mix[:-d]]) * (1 - pan) * 0.4
right = mix * (1 - pan) + np.concatenate([np.zeros(d, dtype=np.float32), mix[:-d]]) * pan * 0.4

peak = max(np.max(np.abs(left)), np.max(np.abs(right))) + 1e-9
left = left / peak * 0.94
right = right / peak * 0.94

stereo = np.stack([left, right], axis=1)
int16 = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
out = Path("tv_space_sound.wav")
with wave.open(str(out), "w") as wf:
    wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
    wf.writeframes(int16.tobytes())

print(f">> wrote {out}  ({out.stat().st_size/1e6:.1f} MB)")
print(">> Play with: mpv --loop=inf tv_space_sound.wav")
