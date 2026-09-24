#!/usr/bin/env python3
"""Temporal structure: envelope, autocorrelation, onset detection."""
import wave, sys
import numpy as np

def load_wav(path):
    with wave.open(path, "rb") as wf:
        n = wf.getnframes()
        data = np.frombuffer(wf.readframes(n), dtype=np.int16)
        if len(data) % 2: data = data[:-1]
        return data.reshape(-1, 2)[:, 0].astype(np.float32), wf.getframerate()

def envelope(audio, sr, win_ms=20):
    win = int(sr * win_ms / 1000)
    env = np.abs(audio)
    # Downsample to envelope rate
    n = len(env) // win
    return np.array([env[i*win:(i+1)*win].mean() for i in range(n)]), sr/win

def autocorr_envelope(env):
    env = env - env.mean()
    n = len(env)
    ac = np.correlate(env, env, mode='full')[n-1:]
    ac = ac / (ac[0] + 1e-9)
    return ac

def find_periods(ac, sr_env, min_hz=0.2, max_hz=20):
    """Find peaks in autocorrelation → rhythmic periods."""
    n = len(ac)
    min_lag = int(sr_env / max_hz)
    max_lag = int(sr_env / min_hz)
    max_lag = min(max_lag, n-1)
    if max_lag <= min_lag: return []
    segment = ac[min_lag:max_lag]
    peaks = []
    for i in range(1, len(segment)-1):
        if segment[i] > segment[i-1] and segment[i] > segment[i+1] and segment[i] > 0.1:
            peaks.append((min_lag+i, segment[i]))
    peaks.sort(key=lambda x: -x[1])
    return [(lag / sr_env, strength) for lag, strength in peaks[:5]]

def main(path):
    audio, sr = load_wav(path)
    print(f">> {path}  ({len(audio)/sr:.1f} s)")
    env, sr_env = envelope(audio, sr)
    print(f">> envelope: {len(env)} samples at {sr_env:.0f} Hz")
    ac = autocorr_envelope(env)
    periods = find_periods(ac, sr_env)
    print(f"\n>> Dominant periods (autocorrelation peaks):")
    for period, strength in periods:
        freq = 1.0 / period
        print(f"   period = {period:6.3f} s  →  {freq:5.2f} Hz  "
              f"(strength {strength:+.3f})")
    # Check the 2 Hz universal tempo specifically
    for hz in [0.5, 1.0, 2.0, 4.0]:
        lag = int(sr_env / hz)
        if lag < len(ac):
            print(f"   {hz} Hz autocorr: {ac[lag]:+.3f}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "active_patched.wav")
