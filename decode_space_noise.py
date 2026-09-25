#!/usr/bin/env python3
"""
Read the phonetic content of a space-noise WAV.
For each frequency band, find which Arabic letters match best.
"""
import sys, wave
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from phoneme_table import PHONEMES


# The three TV-space bands
BANDS = {
    "SUB":    (20, 80),
    "LOW":    (80, 250),
    "MID":    (250, 800),
    "UPPER":  (800, 2500),
    "HIGH":   (2500, 7000),
    "AIR":    (7000, 16000),
}


def load_mono(path):
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        n = wf.getnframes()
        data = np.frombuffer(wf.readframes(n), dtype=np.int16)
    if ch == 2:
        data = data.reshape(-1, 2).mean(axis=1).astype(np.int16)
    return data.astype(np.float32) / 32768.0, sr


def band_energy(audio, sr):
    """Return energy in each band as a fraction of total."""
    spec = np.abs(np.fft.rfft(audio)) ** 2
    f = np.fft.rfftfreq(len(audio), 1 / sr)
    total = spec.sum() + 1e-9
    out = {}
    for name, (lo, hi) in BANDS.items():
        mask = (f >= lo) & (f <= hi)
        out[name] = spec[mask].sum() / total
    return out


def letter_fits_band(letter, band_name):
    """Return a score 0-1 for how well a letter's fingerprint sits in a band."""
    if letter not in PHONEMES:
        return 0.0
    F1, F2, F3, CoG = PHONEMES[letter]
    # Convert to Hz
    f1, f2, f3 = F1 * 1000, F2 * 1000, F3 * 1000
    cog = CoG * 8000
    lo, hi = BANDS[band_name]
    score = 0.0
    # Formant peaks inside band
    for f in (f1, f2, f3):
        if lo <= f <= hi:
            score += 0.33
    # CoG inside band (for fricatives)
    if lo <= cog <= hi:
        score += 0.5
    return min(1.0, score)


def rank_letters_by_band():
    """Build a table: for each band, which letters score highest."""
    table = {}
    for band in BANDS:
        scores = [(l, letter_fits_band(l, band)) for l in PHONEMES]
        scores.sort(key=lambda x: -x[1])
        table[band] = [l for l, s in scores if s > 0.3][:8]
    return table


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "space_noise_forward.wav"
    p = Path(path)
    if not p.exists():
        print(f"!! {p} not found")
        sys.exit(1)

    print("=" * 68)
    print(f"PHONETIC READING OF {p.name}")
    print("=" * 68)

    audio, sr = load_mono(p)
    print(f"\n>> {len(audio)/sr:.1f} s, {sr} Hz, mono")

    # Global energy distribution
    energies = band_energy(audio, sr)
    print(f"\n>> Band energy distribution")
    print(f"   {'band':>6}  {'Hz range':>12}  {'share':>8}  bar")
    for name in BANDS:
        e = energies[name]
        lo, hi = BANDS[name]
        bar = "#" * int(e * 200)
        print(f"   {name:>6}  {lo:>5}-{hi:>5}  {e*100:>6.1f}%  {bar}")

    # Match letters to bands
    table = rank_letters_by_band()
    print(f"\n>> Letters by frequency band")
    for name in BANDS:
        lo, hi = BANDS[name]
        letters = table[name]
        if letters:
            print(f"   {name:>6} ({lo:>5}-{hi:>5} Hz)  {' '.join(letters)}")

    # Time-resolved reading — sample windows
    print(f"\n>> Phonetic reading over time")
    win_n = int(sr * 5.0)
    n_windows = len(audio) // win_n
    for i in range(n_windows):
        seg = audio[i*win_n:(i+1)*win_n]
        e = band_energy(seg, sr)
        # find top 2 bands
        top = sorted(e.items(), key=lambda x: -x[1])[:2]
        t = i * 5.0
        # for each top band, take first letter
        reading = ""
        for band_name, _ in top:
            letters = table.get(band_name, [])
            if letters:
                reading += letters[0]
        print(f"   t={t:5.0f}s  {reading}  "
              f"({', '.join(f'{b}:{v*100:.0f}%' for b, v in top)})")


if __name__ == "__main__":
    main()
