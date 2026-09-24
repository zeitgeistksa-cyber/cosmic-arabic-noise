#!/usr/bin/env python3
"""ASCII spectrogram + time-frequency features."""
import wave, sys
import numpy as np
from pathlib import Path

def load_wav(path):
    with wave.open(path, "rb") as wf:
        n = wf.getnframes()
        data = np.frombuffer(wf.readframes(n), dtype=np.int16)
        if len(data) % 2: data = data[:-1]
        data = data.reshape(-1, 2)
        return data[:, 0].astype(np.float32), wf.getframerate()

def ascii_spectrogram(audio, sr, n_rows=24, n_cols=80):
    """Render a coarse spectrogram as ASCII art."""
    # Split into n_cols time slices
    win_n = len(audio) // n_cols
    if win_n < 64:
        print("!! audio too short for spectrogram")
        return
    # Compute a magnitude spectrum per slice
    specs = []
    for i in range(n_cols):
        seg = audio[i*win_n : (i+1)*win_n]
        # Apply Hann window
        seg = seg * np.hanning(len(seg))
        spec = np.abs(np.fft.rfft(seg))
        specs.append(spec)
    # Truncate to n_rows frequency bands (log-spaced)
    n_bins = len(specs[0])
    # Log-spaced frequency bands
    band_edges = np.logspace(np.log10(1), np.log10(n_bins-1), n_rows+1).astype(int)
    band_edges = np.unique(band_edges)
    n_rows_actual = len(band_edges) - 1

    grid = np.zeros((n_rows_actual, n_cols))
    for i, spec in enumerate(specs):
        for j in range(n_rows_actual):
            lo, hi = band_edges[j], band_edges[j+1]
            grid[j, i] = np.mean(spec[lo:hi])
    # Normalize
    grid = grid / (grid.max() + 1e-9)
    # Character ramp
    chars = " .:-=+*#%@"
    print(f"\n>> ASCII spectrogram (top = high freq, bottom = low freq)")
    print(f"   {n_cols} time slices  ×  {n_rows_actual} freq bands\n")
    for j in range(n_rows_actual - 1, -1, -1):
        row = ""
        for i in range(n_cols):
            idx = int(grid[j, i] * (len(chars)-1))
            row += chars[idx]
        # Frequency label
        lo_hz = band_edges[j] * sr / (2 * (n_bins - 1))
        print(f"  {lo_hz:6.0f} Hz |{row}|")
    print(f"         |{'_' * n_cols}|")
    print(f"          time →")

def stats(audio, sr):
    spec = np.abs(np.fft.rfft(audio))
    freqs = np.fft.rfftfreq(len(audio), 1/sr)
    centroid = np.sum(freqs * spec) / (np.sum(spec) + 1e-9)
    cum = np.cumsum(spec) / (np.sum(spec) + 1e-9)
    rolloff = freqs[np.searchsorted(cum, 0.85)]
    flatness = np.exp(np.mean(np.log(spec + 1e-9))) / (np.mean(spec) + 1e-9)
    print(f"\n>> Overall spectral stats:")
    print(f"   centroid:  {centroid:8.0f} Hz")
    print(f"   rolloff:   {rolloff:8.0f} Hz")
    print(f"   flatness:  {flatness:8.4f}  (0=tonal, 1=noise)")
    return centroid, rolloff, flatness

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "active_patched.wav"
    audio, sr = load_wav(path)
    print(f">> {path}  ({len(audio)/sr:.1f} s)")
    stats(audio, sr)
    ascii_spectrogram(audio, sr)
