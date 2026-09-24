#!/usr/bin/env python3
"""
Measure ionospheric audio response to a broadcast.
"""
import subprocess, wave, numpy as np
from pathlib import Path


def capture_ionosphere(sec, path):
    subprocess.run([
        "ffmpeg", "-y", "-i",
        "http://science.nasa.gov/audio/inspire/inspire.m3u",
        "-t", str(sec), "-ac", "1", "-ar", "44100",
        "-acodec", "pcm_s16le", path
    ], capture_output=True, timeout=sec + 30)


def spectral_signature(path):
    with wave.open(path, "rb") as wf:
        n = wf.getnframes()
        audio = np.frombuffer(wf.readframes(n), dtype=np.int16).astype(np.float32)
    spec = np.abs(np.fft.rfft(audio))
    f = np.fft.rfftfreq(len(audio), 1/44100)
    # Return band energies
    bands = [(20,100), (100,500), (500,2000), (2000,5000), (5000,15000)]
    return np.array([spec[(f>=lo)&(f<=hi)].sum() for lo, hi in bands])


# 1. Capture before
capture_ionosphere(15, "iono_before.wav")
sig_before = spectral_signature("iono_before.wav")

# 2. Broadcast message
print(">> Broadcasting...")
subprocess.run(["mpv", "--no-video", "--really-quiet", "universe_msg.wav"])

# 3. Capture after
capture_ionosphere(15, "iono_after.wav")
sig_after = spectral_signature("iono_after.wav")

# 4. Compare
delta = sig_after - sig_before
print(f">> Ionosphere spectral change:")
for i, (lo, hi) in enumerate([(20,100),(100,500),(500,2000),(2000,5000),(5000,15000)]):
    print(f"   {lo:>5}-{hi:>5} Hz:  Δ={delta[i]:+.0f}")
