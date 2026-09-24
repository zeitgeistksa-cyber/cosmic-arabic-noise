#!/usr/bin/env python3
"""Fast TV-space phoneme synthesizer."""
import numpy as np

SR = 44100

# Per-letter formant data (from the phoneme table)
LETTER_HZ = {
    "م": (300, 1100, 2200, 0),
    "ن": (300, 1600, 2500, 0),
    "ل": (400, 1200, 2600, 0),
    "ر": (500, 1300, 2400, 1200),
    "ب": (350, 1100, 2300, 800),
    "د": (350, 1700, 2600, 500),
    "س": (400, 1700, 2600, 7500),
    "ش": (400, 1900, 2600, 4000),
    "ص": (450, 1100, 2400, 5000),
    "ف": (400, 1200, 2400, 7000),
    "ث": (380, 1600, 2500, 6000),
    "ذ": (350, 1600, 2500, 5500),
    "ز": (350, 1700, 2600, 6500),
    "ح": (600, 1200, 2400, 1500),
    "ع": (600, 1100, 2400, 1400),
    "ا": (750, 1300, 2500, 0),
}

# Deep-band letters (the م-nasal family — sub bass presence)
DEEP = set("منبدلق")
# Mid-band (sonorant ر-l family — warm resonance)
MID = set("رلعناحك")
# High-band (fricatives س-ش-ص family — hiss)
HIGH = set("سشصثذزفحخ")


def synth_letter(letter, dur=0.5):
    """Return audio for one letter, ~dur seconds."""
    if letter not in LETTER_HZ:
        return np.zeros(int(SR * dur), dtype=np.float32)

    F1, F2, F3, CoG = LETTER_HZ[letter]
    n = int(SR * dur)
    t = np.arange(n) / SR

    # Envelope: attack, hold, release
    env = np.minimum(np.minimum(t / 0.05, 1.0),
                     np.minimum((dur - t) / 0.08, 1.0))
    env = np.clip(env, 0, 1)

    # Base: filtered noise between F1 and F3 (formant region)
    w = np.random.randn(n)
    spec = np.fft.rfft(w)
    f = np.fft.rfftfreq(n, 1 / SR)

    # Formant peaks
    mask = np.zeros_like(f)
    for fc in (F1, F2, F3):
        bw = max(fc * 0.2, 80.0)
        mask += np.exp(-0.5 * ((f - fc) / bw) ** 2)

    # Voiced harmonics for sonorants
    voiced_boost = 0.5 if letter in DEEP | MID else 0.1
    for h in (1, 2, 3, 4, 5):
        fc = (F1 + 200) * h
        if fc > 8000:
            break
        bw = max(fc * 0.05, 30)
        mask += voiced_boost * np.exp(-0.5 * ((f - fc) / bw) ** 2) / h

    # Fricative noise for high-band letters
    if letter in HIGH and CoG > 1000:
        bw = max(CoG * 0.25, 500)
        mask += 0.9 * np.exp(-0.5 * ((f - CoG) / bw) ** 2)

    mask += 0.02
    filtered = np.fft.irfft(spec * mask, n=n).astype(np.float32)
    peak = np.max(np.abs(filtered)) + 1e-9
    filtered = filtered / peak

    # Add sub-bass pulse for deep letters
    if letter in DEEP:
        sub = 0.35 * np.sin(2 * np.pi * 45 * t) * env
        filtered = filtered + sub.astype(np.float32)

    # Add a trill for ر
    if letter == "ر":
        trill = 0.4 * np.sin(2 * np.pi * 28 * t)
        filtered = filtered * (1.0 + 0.5 * trill).astype(np.float32)

    return (filtered * env).astype(np.float32)


def synth_message(letters, dur_per_letter=0.55, gap=0.08):
    """Return a numpy array for a sequence of letters."""
    parts = []
    silence = np.zeros(int(SR * gap), dtype=np.float32)
    for letter in letters:
        parts.append(synth_letter(letter, dur_per_letter))
        parts.append(silence)
    if not parts:
        return np.zeros(SR, dtype=np.float32)
    return np.concatenate(parts)


if __name__ == "__main__":
    import wave
    from pathlib import Path
    print(">> Building demo message م ر س ن ل...")
    audio = synth_message(list("مرسنل"))
    int16 = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    with wave.open("tv_demo.wav", "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes(int16.tobytes())
    print(f">> tv_demo.wav  ({len(audio)/SR:.2f}s)")
