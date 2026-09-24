#!/usr/bin/env python3
"""Chromagram — how much energy in each pitch class."""
import wave, sys
import numpy as np

def load_wav(path):
    with wave.open(path, "rb") as wf:
        n = wf.getnframes()
        data = np.frombuffer(wf.readframes(n), dtype=np.int16)
        if len(data) % 2: data = data[:-1]
        return data.reshape(-1, 2)[:, 0].astype(np.float32), wf.getframerate()

def compute_chroma(audio, sr, hop=4096):
    """Return mean chroma vector (12 pitch classes)."""
    n_fft = hop * 2
    chroma = np.zeros(12)
    n_frames = (len(audio) - n_fft) // hop + 1
    for i in range(n_frames):
        frame = audio[i*hop : i*hop + n_fft] * np.hanning(n_fft)
        spec = np.abs(np.fft.rfft(frame))
        freqs = np.fft.rfftfreq(n_fft, 1/sr)
        # For each bin, compute pitch class
        for j, f in enumerate(freqs):
            if f < 40 or f > 5000: continue
            # MIDI note number, mod 12 = pitch class
            midi = 69 + 12 * np.log2(f / 440)
            pc = int(round(midi)) % 12
            chroma[pc] += spec[j]
    if chroma.sum() > 0:
        chroma /= chroma.sum()
    return chroma

def main(path):
    audio, sr = load_wav(path)
    print(f">> {path}  ({len(audio)/sr:.1f} s)")
    chroma = compute_chroma(audio, sr)
    notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    print(f"\n>> Chromagram (pitch class energy):")
    for i, (note, v) in enumerate(zip(notes, chroma)):
        bar = "#" * int(v * 100)
        print(f"   {note:>3}  {v:6.4f}  {bar}")
    # Measure concentration: entropy of the chroma vector
    ent = -np.sum(chroma * np.log2(chroma + 1e-9))
    print(f"\n>> Chroma entropy: {ent:.3f} bits (max 3.585)")
    print(f"   (low = tonal, high = noisy)")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "active_patched.wav")
