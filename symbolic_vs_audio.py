#!/usr/bin/env python3
"""Correlate symbolic root features with audio spectral features."""
import json, glob, os, sys
import wave
import numpy as np
from phoneme_table import PHONEMES

def load_wav(path):
    with wave.open(path, "rb") as wf:
        n = wf.getnframes()
        data = np.frombuffer(wf.readframes(n), dtype=np.int16)
        if len(data) % 2: data = data[:-1]
        return data.reshape(-1, 2)[:, 0].astype(np.float32), wf.getframerate()

def telemetry_roots_since(ts_start):
    """Return root sequence from the newest session."""
    files = sorted(glob.glob("telemetry/session_*_dialogue.jsonl"), key=os.path.getmtime)
    if not files: return []
    roots = []
    with open(files[-1], encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line: continue
            try: r = json.loads(line)
            except: continue
            if r.get("type") == "turn" and r.get("ts", 0) >= ts_start:
                roots.append(r["root"])
    return roots

def root_cog(root):
    if not root or len(root) != 3: return None
    feats = [PHONEMES[c][3] for c in root if c in PHONEMES]
    if not feats: return None
    return float(np.mean(feats))

def main():
    # Load audio (only the last N seconds, to align with recent telemetry)
    audio_path = sys.argv[1] if len(sys.argv) > 1 else "active_patched.wav"
    audio, sr = load_wav(audio_path)
    print(f">> audio: {audio_path}  ({len(audio)/sr:.1f} s)")

    # Compute spectral centroid per 1-second window
    win_n = sr
    n_windows = len(audio) // win_n
    centroids = []
    for i in range(n_windows):
        seg = audio[i*win_n:(i+1)*win_n]
        spec = np.abs(np.fft.rfft(seg))
        freqs = np.fft.rfftfreq(len(seg), 1/sr)
        centroids.append(np.sum(freqs * spec) / (np.sum(spec) + 1e-9))
    centroids = np.array(centroids)

    # Load roots (last N from newest session)
    roots = telemetry_roots_since(0)[-n_windows:]
    print(f">> telemetry roots loaded: {len(roots)}")
    if len(roots) < n_windows:
        print("!! not enough telemetry roots to align")
        return

    root_cogs = np.array([root_cog(r) for r in roots[:n_windows]])
    valid = ~np.isnan(root_cogs)
    if valid.sum() < 10:
        print("!! not enough valid roots")
        return

    # Correlation
    r = np.corrcoef(root_cogs[valid], centroids[valid])[0, 1]
    print(f"\n>> Symbolic CoG vs Audio Centroid:")
    print(f"   correlation: {r:+.3f}")
    print(f"   root CoG range:   [{root_cogs[valid].min():.3f}, {root_cogs[valid].max():.3f}]")
    print(f"   audio centroid:   [{centroids[valid].min():.0f}, {centroids[valid].max():.0f}] Hz")

    # Time series comparison
    print(f"\n>> First 20 seconds side-by-side:")
    print(f"   {'sec':>4}  {'root_cog':>9}  {'centroid':>10}")
    for i in range(min(20, n_windows)):
        print(f"   {i:>4}  {root_cogs[i]:>9.3f}  {centroids[i]:>10.0f}")

if __name__ == "__main__":
    main()
