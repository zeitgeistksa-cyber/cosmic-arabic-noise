#!/usr/bin/env python3
"""
Disaster Word Simulator.
Synthesizes Arabic disaster words letter-by-letter through the phoneme engine.
"""
import wave
from pathlib import Path
import numpy as np
from phoneme_table import PHONEMES, LETTER_INDEX
from phoneme_grammar import VOICED, EMPHATIC, MANNER

SR = 44100
SYLLABLE_DUR = 0.55
GAP_DUR = 0.08

WORDS = {
    "زلزال": ("Earthquake", "زلزال"),
    "اعصار": ("Hurricane", "اعصار"),
    "بركان": ("Volcano", "بركان"),
    "طوفان": ("Flood", "طوفان"),
}


def letter_freq(letter):
    """Frequency for a single letter, from its index."""
    if letter not in LETTER_INDEX:
        return 220.0
    i = LETTER_INDEX[letter]
    return 55.0 * (2.0 ** (i / 7.0))


def letter_character(c):
    """Return (sub_gain, hiss_gain, noise_gain) for one letter."""
    if c not in PHONEMES:
        return 0.0, 0.0, 0.0
    voice = 1.0 if c in VOICED else 0.0
    emph = 1.0 if c in EMPHATIC else 0.0
    manner = MANNER.get(c, 0.5)
    sub_gain = voice * (1.0 - manner) * 0.6 + emph * 0.35
    hiss_gain = manner * 0.5
    noise_gain = 0.15
    return sub_gain, hiss_gain, noise_gain


def synth_letter(c, dur=SYLLABLE_DUR):
    """Synthesize one letter as a syllable."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    pos = np.linspace(0.0, 1.0, n)

    # Frequency: for weak letters, use formant-derived base
    if c in "او":  # long vowels
        # Use a low formant-ish tone
        F1, F2, F3, CoG = PHONEMES.get(c, (0.5, 1.2, 2.4, 0))
        f = (F1 + F2 + F3) / 3.0 * 200.0  # scale to Hz
    else:
        f = letter_freq(c)

    # Envelope: triangular, medium
    center = 0.5
    half = 0.45
    env = np.maximum(0.0, 1.0 - np.abs(pos - center) / half)

    # Sub-thump for voiced stops
    s_gain, h_gain, n_gain = letter_character(c)

    tone = env * np.sin(2 * np.pi * f * t)
    # Add subtle harmonic
    tone += 0.3 * env * np.sin(2 * np.pi * 2 * f * t)
    # Add the sub / hiss character
    sub = s_gain * env * np.sin(2 * np.pi * 40.0 * t)
    hiss = h_gain * env * np.random.randn(n) * 0.6

    mixed = tone * 0.75 + sub * 0.25 + hiss * 0.2
    sat = np.tanh(np.sin(mixed * 2.5) * 3.0)

    # Fade in/out
    fade_n = int(SR * 0.03)
    if fade_n > 0:
        fade = np.linspace(0, 1, fade_n)
        sat[:fade_n] *= fade
        sat[-fade_n:] *= fade[::-1]

    peak = np.max(np.abs(sat)) + 1e-9
    return (sat / peak * 0.9).astype(np.float32)


def synth_word(word, dur_per_letter=SYLLABLE_DUR):
    """Synthesize an entire word."""
    samples = []
    for c in word:
        if c in PHONEMES:
            samples.append(synth_letter(c, dur_per_letter))
            samples.append(np.zeros(int(SR * GAP_DUR), dtype=np.float32))
    if not samples:
        return np.zeros(SR * 2, dtype=np.float32)
    return np.concatenate(samples)


def analyze(audio, label):
    """Return spectral properties of a word."""
    spec = np.abs(np.fft.rfft(audio))
    freqs = np.fft.rfftfreq(len(audio), 1/SR)
    centroid = np.sum(freqs * spec) / (np.sum(spec) + 1e-9)
    cum = np.cumsum(spec) / (np.sum(spec) + 1e-9)
    rolloff = freqs[np.searchsorted(cum, 0.85)]
    flat = np.exp(np.mean(np.log(spec + 1e-9))) / (np.mean(spec) + 1e-9)
    print(f"  {label:12s}  centroid={centroid:6.0f} Hz  "
          f"rolloff={rolloff:6.0f} Hz  flat={flat:.3f}")
    return centroid, rolloff, flat


def main():
    print("=" * 60)
    print("DISASTER WORD SIMULATION")
    print("=" * 60)

    all_audio = []
    print("\nSynthesizing each word:")

    for word, (label, _) in WORDS.items():
        # Print letter details
        print(f"\n  {label}  ({word})")
        for c in word:
            if c not in PHONEMES:
                continue
            idx = LETTER_INDEX.get(c, 0)
            f = letter_freq(c)
            print(f"    {c}  idx={idx:2d}  f={f:7.1f} Hz")

        audio = synth_word(word)
        all_audio.append(audio)
        all_audio.append(np.zeros(int(SR * 0.5), dtype=np.float32))  # pause

        # Save individual word
        out = Path(f"disaster_{label.lower()}.wav")
        int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
        with wave.open(str(out), "w") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
            wf.writeframes(int16.tobytes())
        print(f"    -> {out}")

    # Analysis
    print("\n" + "=" * 60)
    print("ACOUSTIC FINGERPRINTS")
    print("=" * 60)
    for word, (label, _) in WORDS.items():
        audio = synth_word(word)
        analyze(audio, label)

    # Save combined suite
    print("\n" + "=" * 60)
    print("DISASTER SUITE")
    print("=" * 60)
    combined = np.concatenate(all_audio)
    int16 = (np.clip(combined, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open("disaster_suite.wav", "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes(int16.tobytes())
    print(f"  Combined duration: {len(combined)/SR:.1f} s")
    print(f"  -> disaster_suite.wav")
    analyze(combined, "suite")


if __name__ == "__main__":
    main()
