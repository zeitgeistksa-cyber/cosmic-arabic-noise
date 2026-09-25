#!/usr/bin/env python3
"""
Deep study of زلزال (earthquake).
Morphology, phonetics, cross-linguistic comparison, synthesis.
"""
import wave
from pathlib import Path
import numpy as np
from phoneme_table import PHONEMES, LETTER_INDEX
from phoneme_grammar import VOICED, EMPHATIC, MANNER

SR = 44100

WORD = "زلزال"
ROOT = "زل"  # the primitive biliteral base

def letter_freq(letter):
    if letter not in LETTER_INDEX:
        return 220.0
    return 55.0 * (2.0 ** (LETTER_INDEX[letter] / 7.0))

def letter_character(c):
    if c not in PHONEMES:
        return 0.0, 0.0
    voice = 1.0 if c in VOICED else 0.0
    emph = 1.0 if c in EMPHATIC else 0.0
    manner = MANNER.get(c, 0.5)
    sub = voice * (1.0 - manner) * 0.6 + emph * 0.35
    hiss = manner * 0.5
    return sub, hiss

def synth_letter(c, dur=0.45):
    n = int(SR * dur)
    t = np.arange(n) / SR
    pos = np.linspace(0.0, 1.0, n)
    f = letter_freq(c)
    if c == "ا":
        f = 220.0  # open vowel
    center, half = 0.5, 0.45
    env = np.maximum(0.0, 1.0 - np.abs(pos - center) / half)
    sub_g, hiss_g = letter_character(c)
    tone = env * np.sin(2 * np.pi * f * t)
    tone += 0.3 * env * np.sin(2 * np.pi * 2 * f * t)
    sub = sub_g * env * np.sin(2 * np.pi * 40.0 * t)
    hiss = hiss_g * env * np.random.randn(n) * 0.6
    mixed = tone * 0.7 + sub * 0.25 + hiss * 0.25
    sat = np.tanh(np.sin(mixed * 2.5) * 3.0)
    fade_n = int(SR * 0.03)
    fade = np.linspace(0, 1, fade_n)
    sat[:fade_n] *= fade
    sat[-fade_n:] *= fade[::-1]
    peak = np.max(np.abs(sat)) + 1e-9
    return (sat / peak * 0.9).astype(np.float32)

def synth_word(word, dur=0.45):
    samples = []
    for c in word:
        if c in PHONEMES:
            samples.append(synth_letter(c, dur))
    return np.concatenate(samples) if samples else np.zeros(SR, dtype=np.float32)

def centroid_over_time(audio, win_sec=0.05):
    win = int(SR * win_sec)
    cs = []
    for i in range(0, len(audio) - win, win):
        seg = audio[i : i + win]
        spec = np.abs(np.fft.rfft(seg))
        freqs = np.fft.rfftfreq(len(seg), 1/SR)
        cs.append(np.sum(freqs * spec) / (np.sum(spec) + 1e-9))
    return np.array(cs)

def main():
    print("=" * 65)
    print("  زلزال — EARTHQUAKE STUDY")
    print("=" * 65)

    # Morphology
    print("\n[1] MORPHOLOGY")
    print("  Pattern:  فَعْلَال  (faʿlāl)")
    print("  Base:     ز-ل  (biliteral primitive)")
    print("  Redup:    ز-ل-ز-ل  (reduplicated quadriliteral)")
    print("  Noun:     زلزال  (repeated shaking)")
    print("  Siblings: وسواس, صلصال, قهقهة — all pattern-for-repetition")

    # Phoneme details
    print("\n[2] PHONEME SEQUENCE")
    print(f"  {'pos':>3}  {'letter':>6}  {'idx':>3}  {'F1':>5}  "
          f"{'F2':>5}  {'F3':>5}  {'CoG':>5}  {'f(Hz)':>7}  class")
    for i, c in enumerate(WORD):
        if c not in PHONEMES:
            continue
        F1, F2, F3, CoG = PHONEMES[c]
        idx = LETTER_INDEX.get(c, 0)
        f = letter_freq(c)
        cls = "fricative" if MANNER.get(c, 0.5) == 1.0 else (
              "sonorant" if MANNER.get(c, 0.5) == 0.5 else "vowel/stop")
        print(f"  {i:>3}  {c:>6}  {idx:>3}  {F1:>5.2f}  {F2:>5.2f}  "
              f"{F3:>5.2f}  {CoG:>5.2f}  {f:>7.1f}  {cls}")

    # Noise flip-flop
    print("\n[3] NOISE FLIP-FLOP (CoG sequence)")
    cogs = [PHONEMES[c][3] for c in WORD if c in PHONEMES]
    bars = "".join("#" if c > 0.4 else "." for c in cogs)
    vals = "  ".join(f"{c:.2f}" for c in cogs)
    print(f"  {vals}")
    print(f"  {bars}")
    alternations = sum(1 for i in range(1, len(cogs)) if cogs[i] != cogs[i-1])
    print(f"  {alternations} transitions across {len(cogs)} phonemes")

    # Synthesis
    print("\n[4] SYNTHESIS")
    audio = synth_word(WORD)
    int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    out = Path("zilzal.wav")
    with wave.open(str(out), "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes(int16.tobytes())
    print(f"  wrote {out}  ({len(audio)/SR:.2f}s)")

    # Spectral centroid over time
    cs = centroid_over_time(audio)
    print(f"\n[5] SPECTRAL CENTROID OVER TIME (50 ms windows)")
    print(f"  mean = {cs.mean():.0f} Hz  std = {cs.std():.0f} Hz")
    print(f"  min  = {cs.min():.0f} Hz  max = {cs.max():.0f} Hz")
    # Show as ascii
    n_bars = 60
    step = max(1, len(cs) // n_bars)
    for i in range(0, len(cs), step):
        v = cs[i:i+step].mean()
        vn = (v - cs.min()) / (cs.max() - cs.min() + 1e-9)
        bar = "#" * int(vn * 50)
        t = i / SR
        print(f"  t={t:4.2f}s  {bar}")

    # Zero-crossings = perceived vibration rate
    print(f"\n[6] VIBRATION RATE")
    zc = np.sum(np.abs(np.diff(np.sign(audio)))) / (len(audio) / SR)
    print(f"  zero-crossings per second: {zc:.0f} Hz")
    print(f"  syllables per second: {len(WORD)/(len(audio)/SR):.2f}")

    # Comparison
    print("\n[7] CROSS-LINGUISTIC COMPARISON")
    print("  Arabic  زلزال     — reduplicated, performs the shake")
    print("  Hebrew רעידת אדמה — 'trembling of the ground', no redup")
    print("  English earthquake — compound noun, no redup")
    print("  Japanese 地震      — 'earth + shake', no redup")
    print("  Greek σεισμός      — from σείω (agitate), no redup")
    print()
    print("  Arabic is unique among major disaster words in that the")
    print("  phoneme sequence performs the phenomenon it names.")

if __name__ == "__main__":
    main()
