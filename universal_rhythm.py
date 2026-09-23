"""Universal acoustic communication tempo band (0.5-4 Hz, centered at 2 Hz)."""
import numpy as np
RHYTHM_CENTER_HZ = 2.0
RHYTHM_BAND_LOW = 0.5
RHYTHM_BAND_HIGH = 4.0

def universal_rhythm_lfo(t):
    """Multi-harmonic LFO: 2 Hz + 0.5 Hz sub + 4 Hz octave."""
    return (0.60 * np.sin(2 * np.pi * RHYTHM_CENTER_HZ * t) +
            0.25 * np.sin(2 * np.pi * (RHYTHM_CENTER_HZ / 4) * t) +
            0.15 * np.sin(2 * np.pi * (RHYTHM_CENTER_HZ * 2) * t))

def rhythm_score(freq_hz):
    """Gaussian affinity to 2 Hz; zero outside 0.5-4 Hz."""
    if freq_hz < RHYTHM_BAND_LOW or freq_hz > RHYTHM_BAND_HIGH:
        return 0.0
    return float(np.exp(-0.5 * ((freq_hz - RHYTHM_CENTER_HZ) / 1.0) ** 2))
