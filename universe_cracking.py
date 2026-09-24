#!/usr/bin/env python3
"""Universe cracking — 80-second layered destruction symphony."""
import wave
from pathlib import Path
import numpy as np
from phoneme_table import PHONEMES, LETTER_INDEX
from phoneme_grammar import VOICED, MANNER

SR = 44100
DURATION = 80.0
N = int(SR * DURATION)
t = np.linspace(0, DURATION, N, endpoint=False)


def pink_noise(n):
    white = np.random.randn(n)
    f = np.fft.rfftfreq(n, 1/SR)
    f[0] = f[1] if len(f) > 1 else 1.0
    shaped = white[:len(f)] / np.sqrt(f)
    y = np.fft.irfft(shaped, n=n)
    return y / (np.max(np.abs(y)) + 1e-9)


def brown_noise(n):
    white = np.random.randn(n)
    f = np.fft.rfftfreq(n, 1/SR)
    f[0] = f[1] if len(f) > 1 else 1.0
    shaped = white[:len(f)] / f
    y = np.fft.irfft(shaped, n=n)
    return y / (np.max(np.abs(y)) + 1e-9)


def bandpass_noise(n, lo, hi):
    white = np.random.randn(n)
    spec = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n, 1/SR)
    mask = (freqs >= lo) & (freqs <= hi)
    spec[~mask] = 0
    y = np.fft.irfft(spec, n=n)
    return y / (np.max(np.abs(y)) + 1e-9)


def schumann_layer():
    base = 7.83
    degrade = np.clip((t - 10) / 20, 0, 1)
    wander = 3.0 * degrade * np.sin(2 * np.pi * 0.17 * t) + \
             1.5 * degrade * np.random.randn(N)
    inst_freq = base + wander
    phase = 2 * np.pi * np.cumsum(inst_freq) / SR
    tone = np.sin(phase)
    tone += 0.4 * degrade * np.sin(2 * phase)
    tone += 0.25 * degrade * np.sin(3 * phase)
    env = np.clip(t / 5, 0, 1) * np.clip((DURATION - t) / 10, 0, 1)
    noise = 0.4 * degrade * np.random.randn(N)
    return (tone * 0.6 + noise * 0.4) * env * 0.18


def earthquake_layer():
    rumble = bandpass_noise(N, 8, 45)
    tremor = 0.6 + 0.4 * np.sin(2 * np.pi * 1.7 * t) * \
             (0.7 + 0.3 * np.sin(2 * np.pi * 0.3 * t))
    env = np.clip((t - 15) / 20, 0, 1) * np.clip((DURATION - t) / 15, 0, 1)
    peak = np.exp(-((t - 62) ** 2) / 50) * 2.5
    return rumble * tremor * (env + peak) * 0.35


def hurricane_layer():
    roar = pink_noise(N)
    gust = 0.5 + 0.3 * np.sin(2 * np.pi * 0.15 * t) + \
           0.2 * np.sin(2 * np.pi * 0.47 * t) * np.sin(2 * np.pi * 0.9 * t)
    env = np.clip((t - 20) / 15, 0, 1) * np.clip((DURATION - t) / 20, 0, 1)
    peak = np.exp(-((t - 63) ** 2) / 80) * 2.0
    return roar * gust * (env + peak) * 0.30


def volcano_layer():
    output = np.zeros(N)
    for k in range(12):
        center = np.random.uniform(30 + k * 2, 55 + k * 0.5)
        length = int(SR * np.random.uniform(0.3, 1.5))
        start = int(center * SR)
        if start + length >= N:
            continue
        env = np.exp(-np.linspace(0, 8, length))
        burst = np.random.randn(length) * env
        sub_t = np.arange(length) / SR
        sub = np.sin(2 * np.pi * 35 * sub_t) * env
        output[start:start+length] += burst * 0.6 + sub * 0.5
    return output * 0.35


def flood_layer():
    hiss = bandpass_noise(N, 7000, 15000)
    env = np.clip((t - 35) / 15, 0, 1) * np.clip((DURATION - t) / 15, 0, 1)
    peak = np.exp(-((t - 64) ** 2) / 60) * 2.0
    return hiss * (env + peak) * 0.20


def letter_freq(letter):
    if letter not in LETTER_INDEX:
        return 220.0
    return 55.0 * (2.0 ** (LETTER_INDEX[letter] / 7.0))


def synth_root_tone(root, dur, detune=0.0):
    n = int(SR * dur)
    tt = np.arange(n) / SR
    output = np.zeros(n)
    for i, c in enumerate(root[:3]):
        if c not in PHONEMES:
            continue
        f = letter_freq(c) * (1.0 + detune)
        phase = np.sin(2 * np.pi * f * tt + i * 0.5)
        env = np.sin(np.pi * np.linspace(0, 1, n))
        output += phase * env * (0.5 - 0.1 * i)
    peak = np.max(np.abs(output)) + 1e-9
    return (output / peak) * 0.9


def twin_engines_layer():
    output = np.zeros(N)
    destruction_roots = ["ففف", "سسس", "ززز", "صصص", "ثثث", "شفش", "سفص"]
    turn_len = 1.6
    idx = 0
    while True:
        start = 40.0 + idx * turn_len
        if start + turn_len >= DURATION:
            break
        ra = destruction_roots[idx % len(destruction_roots)]
        detune_b = 0.08 * max(0, (58 - start) / 18)
        rb = destruction_roots[(idx + 2) % len(destruction_roots)]
        sa = synth_root_tone(ra, turn_len, 0.0)
        sb = synth_root_tone(rb, turn_len, detune_b)
        start_a = int(start * SR)
        start_b = int((start + 0.35) * SR)
        if start_a + len(sa) <= N:
            output[start_a:start_a+len(sa)] += sa * 0.5
        if start_b + len(sb) <= N:
            output[start_b:start_b+len(sb)] += sb * 0.5
        idx += 1
    env = np.clip((t - 40) / 18, 0, 1) * np.clip((DURATION - t) / 15, 0, 1)
    peak = np.exp(-((t - 62) ** 2) / 40) * 2.0
    return output * (env + peak) * 0.28


def cracks_layer():
    output = np.zeros(N)
    for k in range(20):
        center = np.random.uniform(48, 65)
        start = int(center * SR)
        length = int(SR * np.random.uniform(0.02, 0.15))
        if start + length >= N:
            continue
        env = np.exp(-np.linspace(0, 12, length))
        crack = np.random.randn(length) * env
        crack[:10] *= 3.0
        output[start:start+length] += crack
    return output * 0.30


def explosion_layer():
    output = np.zeros(N)
    center = 62.0
    start = int(center * SR)
    length = int(SR * 3.0)
    exp_t = np.arange(length) / SR
    env = np.exp(-exp_t / 1.2)
    output[start:start+length] += np.sin(2 * np.pi * 25 * exp_t) * env * 1.5
    attack_n = int(SR * 0.1)
    if start + attack_n < N:
        attack = np.random.randn(attack_n) * np.exp(-np.linspace(0, 10, attack_n)) * 2.0
        output[start:start+attack_n] += attack
    tail_n = int(SR * 5.0)
    if start + tail_n < N:
        tail = brown_noise(tail_n) * np.exp(-np.linspace(0, 4, tail_n)) * 0.8
        output[start:start+tail_n] += tail
    return output * 0.6


def main():
    print("=" * 60)
    print("UNIVERSE CRACKING — 80-second destruction symphony")
    print("=" * 60)
    np.random.seed(2026)

    print("\n>> Building layers...")
    mix = np.zeros(N)
    for name, layer in [
        ("schumann",  schumann_layer()),
        ("earthquake", earthquake_layer()),
        ("hurricane", hurricane_layer()),
        ("volcano",   volcano_layer()),
        ("flood",     flood_layer()),
        ("twin",      twin_engines_layer()),
        ("cracks",    cracks_layer()),
        ("explosion", explosion_layer()),
    ]:
        print(f"   {name:12s}  peak={np.max(np.abs(layer)):.3f}")
        mix += layer

    print(">> Saturation + normalize...")
    mix = np.tanh(mix * 1.4)
    mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.98

    print(">> Stereo widening...")
    delay = int(SR * 0.008)
    left = mix
    right = np.concatenate([np.zeros(delay), mix[:-delay]])
    stereo = np.stack([left, right], axis=1)

    int16 = (np.clip(stereo, -1.0, 1.0) * 32767).astype(np.int16)
    out = Path("universe_cracking.wav")
    with wave.open(str(out), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(int16.tobytes())

    print(f"\n>> Wrote {out}  ({DURATION}s, {out.stat().st_size/1e6:.1f} MB)")
    print(">> Play with: mpv universe_cracking.wav")


if __name__ == "__main__":
    main()
