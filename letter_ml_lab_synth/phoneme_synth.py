"""Formant synthesis with real 2nd-order IIR resonators."""
import numpy as np
from scipy.signal import lfilter

SR = 22050

FORMANTS = {
    "a":  (730, 1090, 2440, 1.0, 0.0),
    "e":  (530, 1840, 2480, 1.0, 0.0),
    "i":  (270, 2290, 3010, 1.0, 0.0),
    "o":  (570,  840, 2410, 1.0, 0.0),
    "u":  (300,  870, 2240, 1.0, 0.0),
    "p":  (400, 1100, 2200, 0.2, 0.8),
    "t":  (400, 1600, 2600, 0.2, 0.8),
    "k":  (400, 1800, 2400, 0.2, 0.8),
    "b":  (400, 1100, 2200, 0.95, 0.05),
    "d":  (400, 1600, 2600, 0.95, 0.05),
    "g":  (400, 1800, 2400, 0.95, 0.05),
    "s":  (500, 4000, 6500, 0.0, 1.0),
    "sh": (500, 2500, 4000, 0.0, 1.0),
    "f":  (500, 3500, 6000, 0.0, 1.0),
    "th": (500, 2500, 5500, 0.0, 1.0),
    "z":  (500, 4000, 6500, 0.4, 0.6),
    "v":  (500, 3500, 6000, 0.4, 0.6),
    "m":  (250,  900, 2200, 1.0, 0.0),
    "n":  (250, 1700, 2600, 1.0, 0.0),
    "ng": (250, 2300, 2750, 1.0, 0.0),
    "l":  (350, 1100, 2600, 1.0, 0.0),
    "r":  (310, 1060, 1380, 1.0, 0.0),
    "w":  (300,  610, 2200, 1.0, 0.0),
    "y":  (270, 2290, 3010, 1.0, 0.0),
}

# Glides: approximants move from start-formant → end-formant
GLIDES = {
    "y": ((270, 2290, 3010), (500, 1500, 2500)),   # /j/: i → schwa
    "w": ((300,  870, 2240), (500,  900, 2400)),   # /w/: u → schwa
    "l": ((350, 1100, 2600), (500,  900, 2400)),   # /l/: lateral → schwa
    "r": ((310, 1060, 1380), (500, 1200, 1600)),   # /r/: rhotic → schwa
}
# Nasal anti-formant (zero) at ~1000 Hz — real feature of m/n/ng
NASAL_ZERO_HZ = {"m": 1000, "n": 1500, "ng": 2000}

def _resonator(freq, bw, sr=SR):
    """2nd-order IIR resonator (Klatt-style)."""
    r = np.exp(-np.pi * bw / sr)
    theta = 2 * np.pi * freq / sr
    a1 = -2 * r * np.cos(theta)
    a2 = r * r
    b0 = 1 - r            # crude but stable gain
    return np.array([b0]), np.array([1.0, a1, a2])

def _glottal(n, f0_curve, sr=SR, jitter=0.0, seed=0):
    """Pulse train + harmonics for voiced excitation."""
    rng = np.random.default_rng(seed)
    phase = 2 * np.pi * np.cumsum(f0_curve) / sr
    if jitter > 0:
        phase += rng.normal(0, jitter, n)
    src = np.zeros(n)
    for k in range(1, 30):
        if k * f0_curve.mean() > sr * 0.45:
            break
        src += np.sin(k * phase) / k
    return src

def synthesize(phoneme, duration=0.35, f0=120.0, jitter=0.0,
               formant_shift=1.0, contour="flat", seed=0):
    rng = np.random.default_rng(seed)
    n = int(duration * SR)
    t = np.arange(n) / SR

    if phoneme not in FORMANTS:
        raise ValueError(f"unknown phoneme {phoneme}")
    F1, F2, F3, voicing, noise_mix = FORMANTS[phoneme]
    F1, F2, F3 = F1*formant_shift, F2*formant_shift, F3*formant_shift

    # pitch contour
    if contour == "rise":
        f0c = f0 * (1 + 0.5 * t / duration)
    elif contour == "fall":
        f0c = f0 * (1.5 - 0.5 * t / duration)
    elif contour == "wave":
        f0c = f0 * (1 + 0.2 * np.sin(2 * np.pi * 3 * t))
    else:
        f0c = np.full(n, f0)

    # sources
    voiced_src = _glottal(n, f0c, SR, jitter, seed)
    noise_src = rng.standard_normal(n)

    # formant targets: glide if approximant, else static
    if phoneme in GLIDES:
        (sF1, sF2, sF3), (eF1, eF2, eF3) = GLIDES[phoneme]
        sF1*=formant_shift; sF2*=formant_shift; sF3*=formant_shift
        eF1*=formant_shift; eF2*=formant_shift; eF3*=formant_shift
        prog = np.linspace(0, 1, n)
        F1c = sF1 + (eF1 - sF1) * prog
        F2c = sF2 + (eF2 - sF2) * prog
        F3c = sF3 + (eF3 - sF3) * prog
    else:
        F1c = np.full(n, F1); F2c = np.full(n, F2); F3c = np.full(n, F3)

    # time-varying resonators: chunk into 20ms frames
    frame = int(0.020 * SR)
    def apply_resonators(sig):
        out = np.zeros_like(sig)
        for i in range(0, n, frame):
            end = min(n, i + frame)
            for target, gain in [(F1c, 1.0), (F2c, 0.7), (F3c, 0.4)]:
                f = float(np.mean(target[i:end]))
                bw = 80 if f < 1000 else 120
                b, a = _resonator(f, bw)
                out[i:end] += gain * lfilter(b, a, sig[i:end])
        return out

    voiced = apply_resonators(voiced_src)
    unvoiced = apply_resonators(noise_src)

    sig = voicing * voiced + noise_mix * unvoiced * 0.5
    if phoneme in ("p","t","k","b","d","g"):
        # plosives: burst decays fast, don't let noise dominate
        burst = int(0.04 * n)
        fade = np.ones(n)
        fade[burst:] = np.linspace(1, 0.2, n - burst)
        sig *= fade

    # nasal zero: notch filter at zero_hz
    if phoneme in NASAL_ZERO_HZ:
        z = NASAL_ZERO_HZ[phoneme]
        r = 0.98
        theta = 2 * np.pi * z / SR
        b = np.array([1.0, -2*r*np.cos(theta), r*r])
        a = np.array([1.0, -1.6*r*np.cos(theta), 0.85*r*r])
        sig = lfilter(b, a, sig)

    # attack/decay envelope
    atk = int(0.02 * SR); rel = int(0.08 * SR)
    env = np.ones(n)
    env[:atk] = np.linspace(0, 1, atk)
    env[-rel:] = np.linspace(1, 0, rel)
    sig *= env

    peak = np.max(np.abs(sig)) + 1e-9
    return (sig / peak * 0.9).astype(np.float32)
