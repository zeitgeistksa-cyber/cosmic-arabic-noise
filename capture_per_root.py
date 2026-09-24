"""Capture 3 seconds of engine output per root and save as separate WAVs."""
import subprocess, wave, time, os
from pathlib import Path

CAPTURE_DIR = Path("audio_samples")
CAPTURE_DIR.mkdir(exist_ok=True)
SR, CHUNK = 44100, 2048
SAMPLES_PER_ROOT = int(SR * 3)  # 3 seconds

print(">> Run this in a second terminal: ./start_dialogue.sh")
print(">> Then press Enter here to start capturing")
input()

# Read raw PCM from a shell pipe to the engine
p = subprocess.Popen(
    ["python", "dialogue_engine.py"],
    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
)
buf = b""
for i in range(6):  # capture 6 chunks of 3 sec = 18 sec
    chunk = p.stdout.read(SAMPLES_PER_ROOT * 4)  # 2ch * 2bytes
    path = CAPTURE_DIR / f"capture_{i:02d}.wav"
    with wave.open(str(path), "w") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(chunk)
    print(f">> wrote {path}")
p.terminate()
