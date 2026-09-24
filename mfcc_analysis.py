#!/usr/bin/env python3
"""MFCC analysis — manual DCT implementation."""
import wave, sys
import numpy as np

def load_wav(path):
    with wave.open(path, "rb") as wf:
        n = wf.getnframes()
        data = np.frombuffer(wf.readframes(n), dtype=np.int16)
        if len(data) % 2: data = data[:-1]
        return data.reshape(-1, 2)[:, 0].astype(np.float32), wf.getframerate()

def dct_ii(x, norm='ortho'):
    """Manual DCT-II."""
    N = len(x)
    n = np.arange(N).reshape(-1, 1)
    k = np.arange(N).reshape(1, -1)
    basis = np.cos(np.pi * (n + 0.5) * k / N)
    out = basis.T @ x
    if norm == 'ortho':
        out[0] *= np.sqrt(1.0 / N)
        out[1:] *= np.sqrt(2.0 / N)
    return out

def mel_filterbank(sr, n_fft, n_mels=26, f_min=20, f_max=8000):
    def hz_to_mel(f): return 2595 * np.log10(1 + f/700)
    def mel_to_hz(m): return 700 * (10**(m/2595) - 1)
    mel_points = np.linspace(hz_to_mel(f_min), hz_to_mel(f_max), n_mels + 2)
    hz_points = mel_to_hz(mel_points)
    bin_points = np.floor((n_fft + 1) * hz_points / sr).astype(int)
    filters = np.zeros((n_mels, n_fft // 2 + 1))
    for i in range(1, n_mels + 1):
        lo, mid, hi = bin_points[i-1], bin_points[i], bin_points[i+1]
        for k in range(lo, mid):
            filters[i-1, k] = (k - lo) / max(mid - lo, 1)
        for k in range(mid, hi):
            filters[i-1, k] = (hi - k) / max(hi - mid, 1)
    return filters

def compute_mfcc(audio, sr, n_fft=2048, hop=1024, n_mels=26, n_mfcc=13):
    filters = mel_filterbank(sr, n_fft, n_mels)
    n_frames = (len(audio) - n_fft) // hop + 1
    mfccs = []
    for i in range(n_frames):
        frame = audio[i*hop : i*hop + n_fft]
        frame = frame * np.hanning(n_fft)
        spec = np.abs(np.fft.rfft(frame))**2
        mel_energy = filters @ spec
        log_mel = np.log(mel_energy + 1e-9)
        mfcc = dct_ii(log_mel)[:n_mfcc]
        mfccs.append(mfcc)
    return np.array(mfccs)

def main(path):
    audio, sr = load_wav(path)
    print(f">> {path}  ({len(audio)/sr:.1f} s)")
    mfccs = compute_mfcc(audio, sr)
    print(f"\n>> MFCC matrix shape: {mfccs.shape}")
    print(f"\n>> Per-coefficient statistics:")
    print(f"   {'idx':>4}  {'mean':>8}  {'std':>8}")
    for i in range(mfccs.shape[1]):
        col = mfccs[:, i]
        print(f"   {i:>4}  {col.mean():8.3f}  {col.std():8.3f}")
    print(f"\n>> MFCC[0] (loudness envelope):")
    n_bars = 60
    bin_n = max(1, len(mfccs) // n_bars)
    mn, mx = mfccs[:, 0].min(), mfccs[:, 0].max()
    for i in range(0, len(mfccs), bin_n):
        chunk = mfccs[i:i+bin_n, 0]
        if len(chunk) == 0: continue
        vn = (chunk.mean() - mn) / (mx - mn + 1e-9)
        bar = "#" * int(vn * 40)
        print(f"  {bar}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "active_patched.wav")
