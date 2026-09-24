#!/usr/bin/env python3
"""Record 90s of audio + telemetry simultaneously, then correlate."""
import wave, subprocess, os, time, json, glob, sys
import numpy as np
from pathlib import Path
from phoneme_table import PHONEMES

SR = 44100
DURATION = 90
OUT_RAW = "correlate.raw"
OUT_WAV = "correlate.wav"

def root_cog(root):
    if not root or len(root) != 3: return None
    feats = [PHONEMES[c][3] for c in root if c in PHONEMES]
    return float(np.mean(feats)) if feats else None

# Record
print(f">> Recording {DURATION}s...")
start = time.time()
proc = subprocess.Popen(
    ["python", "-u", "dialogue_engine.py"],
    stdout=open(OUT_RAW, "wb"),
    stderr=subprocess.DEVNULL,
)
time.sleep(DURATION)
proc.terminate()
proc.wait()
end = time.time()
print(f">> Recording complete ({end-start:.1f}s)")

# Find the session started during this window
files = sorted(glob.glob("telemetry/session_*_dialogue.jsonl"),
               key=os.path.getmtime)
newest = files[-1]
print(f">> Session: {newest}")

# Read roots with timestamps
roots = []
with open(newest, encoding="utf-8") as fp:
    for line in fp:
        line = line.strip()
        if not line: continue
        try: r = json.loads(line)
        except: continue
        if r.get("type") == "turn" and r.get("ts", 0) >= start:
            roots.append(r["root"])
print(f">> Roots in window: {len(roots)}")

# Load audio
raw = Path(OUT_RAW).read_bytes()
audio = np.frombuffer(raw, dtype=np.int16)
if len(audio) % 2: audio = audio[:-1]
audio = audio.reshape(-1, 2)[:, 0].astype(np.float32)

# Write WAV
with wave.open(OUT_WAV, "wb") as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
    wf.writeframes(audio.astype(np.int16).tobytes())

# Compute centroid per window aligned to turn boundaries
turn_len_samples = int(SR * (end-start) / max(len(roots), 1))
print(f">> Samples per turn: {turn_len_samples} ({turn_len_samples/SR:.2f}s)")

centroids = []
for i in range(len(roots)):
    seg = audio[i*turn_len_samples : (i+1)*turn_len_samples]
    if len(seg) < 1024: continue
    spec = np.abs(np.fft.rfft(seg))
    freqs = np.fft.rfftfreq(len(seg), 1/SR)
    centroids.append(np.sum(freqs * spec) / (np.sum(spec) + 1e-9))

cogs = np.array([root_cog(r) for r in roots[:len(centroids)]])
cen = np.array(centroids)
valid = ~np.isnan(cogs)
print(f">> Valid pairs: {valid.sum()}")

if valid.sum() > 10:
    r = np.corrcoef(cogs[valid], cen[valid])[0, 1]
    print(f"\n>> Correlation root CoG vs audio centroid: {r:+.3f}")
    print(f"   root CoG range: [{cogs[valid].min():.3f}, {cogs[valid].max():.3f}]")
    print(f"   audio centroid: [{cen[valid].min():.0f}, {cen[valid].max():.0f}] Hz")
else:
    print("!! not enough valid pairs")
