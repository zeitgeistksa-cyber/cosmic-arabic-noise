#!/usr/bin/env python3
"""
Quantify the acoustic properties that predict pleasantness.
Reads the current cosmic attractor's top roots and analyzes them.
"""
import numpy as np
from phoneme_table import PHONEMES, root_to_log_triad
from phoneme_grammar import VOICED, EMPHATIC, MANNER


SR = 44100


# ---------- 1. Plomp-Levelt roughness ----------
def plomp_levelt_roughness(freqs):
    """
    Roughness between simultaneous tones (Plomp & Levelt 1965).
    Lower = more consonant. Sum of pairwise roughness.
    """
    total = 0.0
    for i in range(len(freqs)):
        for j in range(i + 1, len(freqs)):
            f1, f2 = sorted([freqs[i], freqs[j]])
            if f1 <= 0 or f2 <= 0:
                continue
            # Critical bandwidth approximation
            s = 0.24 / (0.0207 * f1 + 18.96)
            df = f2 - f1
            x = s * df
            # Plomp-Levelt curve
            rough = np.exp(-3.5 * x) - np.exp(-5.75 * x)
            total += rough
    return total


# ---------- 2. Missing fundamental detection ----------
def find_common_subharmonic(freqs, tolerance=0.05):
    """
    Search for a low fundamental whose integer multiples fit the given freqs.
    Returns (f0, fit_quality) or (None, 0).
    """
    best_f0, best_fit = None, 0.0
    # Search f0 from 20 Hz to the lowest tone
    f_min = min(freqs)
    for f0 in np.linspace(20, f_min, 500):
        fit = 0.0
        for f in freqs:
            n = f / f0
            nearest = round(n)
            if nearest < 1:
                continue
            err = abs(n - nearest) / nearest
            if err < tolerance:
                fit += 1.0
        fit /= len(freqs)
        if fit > best_fit:
            best_fit, best_f0 = fit, f0
    return best_f0, best_fit


# ---------- 3. Harmonic balance after wavefolding ----------
def harmonic_balance(freq_hz, dur=0.5, sr=SR):
    """
    Synthesize a single tone, wavefold it, and measure odd/even harmonic ratio.
    """
    n = int(sr * dur)
    t = np.arange(n) / sr
    tone = np.sin(2 * np.pi * freq_hz * t)
    folded = np.tanh(np.sin(tone * 2.2) * 2.8)
    # FFT
    spec = np.abs(np.fft.rfft(folded))
    freqs = np.fft.rfftfreq(n, 1 / sr)
    # Find harmonics of freq_hz up to 20 kHz
    odd_energy = 0.0
    even_energy = 0.0
    for h in range(2, 20):
        target = freq_hz * h
        if target > 20000:
            break
        # Take ±5% band around target
        mask = (freqs > target * 0.95) & (freqs < target * 1.05)
        e = np.sum(spec[mask] ** 2)
        if h % 2 == 1:
            odd_energy += e
        else:
            even_energy += e
    total = odd_energy + even_energy + 1e-9
    return odd_energy / total, even_energy / total


# ---------- 4. Spectral centroid stability ----------
def spectral_centroid(audio, sr=SR):
    spec = np.abs(np.fft.rfft(audio))
    freqs = np.fft.rfftfreq(len(audio), 1 / sr)
    return float(np.sum(freqs * spec) / (np.sum(spec) + 1e-9))


# ---------- 5. Amplitude modulation spectrum ----------
def am_spectrum(audio, sr=SR):
    """
    Compute power spectrum of the amplitude envelope.
    Look for energy near 2 Hz (universal communication tempo).
    """
    # Envelope
    env = np.abs(audio)
    # Smooth with a moving average to remove audio-rate content
    win = int(sr * 0.01)
    kernel = np.ones(win) / win
    env = np.convolve(env, kernel, mode="same")
    # FFT of envelope
    spec = np.abs(np.fft.rfft(env - env.mean()))
    freqs = np.fft.rfftfreq(len(env), 1 / sr)
    # Power in the 0.5-4 Hz band (universal rhythm band)
    band = (freqs >= 0.5) & (freqs <= 4.0)
    band_power = np.sum(spec[band] ** 2)
    total_power = np.sum(spec ** 2) + 1e-9
    return band_power / total_power


# ---------- Main analysis ----------
def analyze_root(root):
    if root_to_log_triad(root) is None:
        return None
    f1, f2, f3 = root_to_log_triad(root)
    freqs = [f1, f2, f3]

    print(f"\n  {root}  f1={f1:.1f}  f2={f2:.1f}  f3={f3:.1f}")

    # 1. Roughness
    r = plomp_levelt_roughness(freqs)
    print(f"    Roughness:      {r:.4f}  (lower = more consonant)")

    # 2. Missing fundamental
    f0, fit = find_common_subharmonic(freqs)
    if f0 and fit > 0.5:
        print(f"    Missing f0:     {f0:.1f} Hz  (fit={fit*100:.0f}%)")
    else:
        print(f"    Missing f0:     none strong")

    # 3. Harmonic balance (use f1 as base)
    odd, even = harmonic_balance(f1)
    print(f"    Harmonics:      odd={odd*100:.0f}%  even={even*100:.0f}%")

    # 4. Interval ratios
    ratios = [f2/f1, f3/f1, f3/f2]
    print(f"    Ratios:         {ratios[0]:.3f}  {ratios[1]:.3f}  {ratios[2]:.3f}")

    return r, fit, odd, even


def main():
    # Get the current top roots from the engine (whatever the attractor prefers now)
    top_roots = ["صفف", "زفف", "حفف", "خفف", "حسس", "سفه", "خصف", "فظظ"]

    print("=" * 65)
    print("ACOUSTIC QUALITY ANALYSIS OF THE CURRENT ATTRACTOR")
    print("=" * 65)

    results = []
    for root in top_roots:
        r = analyze_root(root)
        if r:
            results.append(r)

    print("\n" + "=" * 65)
    print("SUMMARY — why these sound as a group")
    print("=" * 65)

    roughness = [r[0] for r in results]
    fits = [r[1] for r in results]
    odds = [r[2] for r in results]

    print(f"\n  Mean roughness:    {np.mean(roughness):.4f}")
    print(f"  Mean f0 fit:       {np.mean(fits)*100:.0f}%")
    print(f"  Mean odd harmonic: {np.mean(odds)*100:.0f}%")
    print(f"  Mean even harmonic:{np.mean([r[3] for r in results])*100:.0f}%")

    # Roughness comparison
    print(f"\n  Reference roughness values:")
    print(f"    Octave (2.00):   {plomp_levelt_roughness([200, 400]):.4f}")
    print(f"    Fifth (1.50):    {plomp_levelt_roughness([200, 300]):.4f}")
    print(f"    Third (1.25):    {plomp_levelt_roughness([200, 250]):.4f}")
    print(f"    Whole (1.125):   {plomp_levelt_roughness([200, 225]):.4f}")
    print(f"    Semitone (1.06): {plomp_levelt_roughness([200, 212]):.4f}")

    # 5. Analyze a full turn of engine output
    print("\n" + "=" * 65)
    print("AMPLITUDE MODULATION ANALYSIS")
    print("=" * 65)
    print("(checking for 2 Hz power — the universal acoustic communication tempo)")

    # Synthesize a 10-second sample of engine output
    from channel import synth_root
    samples = []
    for root in top_roots[:4]:
        s = synth_root(root, dur=2.5)
        if s is not None:
            samples.append(s)
            # silence gap
            samples.append(np.zeros(int(SR * 0.1), dtype=np.float32))
    if samples:
        audio = np.concatenate(samples)
        am_power = am_spectrum(audio)
        print(f"  0.5-4 Hz power fraction: {am_power*100:.2f}%")
        if am_power > 0.02:
            print(f"  ** Strong 2 Hz band presence — matches universal tempo **")
        else:
            print(f"  (weak 2 Hz content)")


if __name__ == "__main__":
    main()
