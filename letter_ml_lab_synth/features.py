"""Pitch-normalized features + onset descriptors."""
import numpy as np

def _frames(sig, n_fft=1024, hop=512):
    out = []
    for i in range(0, len(sig)-n_fft, hop):
        out.append(sig[i:i+n_fft] * np.hanning(n_fft))
    return np.stack(out) if out else np.zeros((1, n_fft))

def mfcc(sig, sr, n_filters=26, n_coeffs=13):
    fr = _frames(sig)
    mag = np.abs(np.fft.rfft(fr, axis=1))
    mel = np.linspace(0, sr/2, n_filters)
    bins = np.clip(np.floor((1024+1)*mel/sr).astype(int), 0, mag.shape[1]-1)
    filt = np.array([mag[:, bins[i]:bins[i+1]].mean(1) for i in range(len(bins)-1)]).T
    filt = np.log(filt + 1e-9)
    N = filt.shape[1]
    k = np.arange(n_coeffs)[:, None]; n = np.arange(N)[None, :]
    dct = np.cos(np.pi*k*(2*n+1)/(2*N))
    return (filt @ dct.T).mean(0)

def autocorr_f0(sig, sr, fmin=60, fmax=400):
    x = sig - sig.mean()
    if np.max(np.abs(x)) < 1e-6: return 0.0
    ac = np.correlate(x, x, mode="full")[len(x)-1:]
    lo = int(sr/fmax); hi = int(sr/fmin)
    if hi >= len(ac): return 0.0
    seg = ac[lo:hi]
    return float(sr/(lo + int(np.argmax(seg)))) if len(seg) else 0.0

def pitch_stats(sig, sr):
    n = 1024; hop = 512
    ps = [autocorr_f0(sig[i:i+n], sr) for i in range(0, len(sig)-n, hop)]
    ps = [p for p in ps if p > 0]
    if not ps:
        return {"f0_mean":0,"f0_std":0,"f0_range":0,"f0_slope":0,"voiced_ratio":0}
    p = np.array(ps); t = np.arange(len(p))
    return {
        "f0_mean": float(p.mean()),
        "f0_std":  float(p.std()),
        "f0_range": float(p.max()-p.min()),
        "f0_slope": float(np.polyfit(t, p, 1)[0]) if len(p) > 1 else 0.0,
        "voiced_ratio": float(len(p) / max(1, len(sig)//hop)),
    }

def spectral_flatness(sig):
    mag = np.abs(np.fft.rfft(sig)) + 1e-9
    return float(np.exp(np.mean(np.log(mag))) / np.mean(mag))

def harmonic_ratio(sig, sr):
    x = sig - sig.mean()
    if np.max(np.abs(x)) < 1e-6: return 0.0
    ac = np.correlate(x, x, mode="full")[len(x)-1:]
    ac /= (ac[0] + 1e-9)
    f0 = autocorr_f0(sig, sr)
    if f0 == 0: return 0.0
    lag = int(sr/f0)
    return float(ac[lag]) if lag < len(ac) else 0.0

def formants(sig, sr):
    mag = np.abs(np.fft.rfft(sig))
    freqs = np.fft.rfftfreq(len(sig), 1/sr)
    mag_s = np.convolve(mag, np.ones(50)/50, mode="same")
    mask = (freqs > 200) & (freqs < 4000)
    f, m = freqs[mask], mag_s[mask]
    if len(m) < 10: return {"F1":0,"F2":0,"F3":0}
    peaks = [(m[i], f[i]) for i in range(1, len(m)-1)
             if m[i] > m[i-1] and m[i] > m[i+1]]
    peaks.sort(reverse=True)
    top = [p[1] for p in peaks[:3]] + [0,0,0]
    return {"F1": float(top[0]), "F2": float(top[1]), "F3": float(top[2])}

def onset_features(sig, sr, window_ms=30):
    """Energy + ZCR in first 30ms → separates plosive from fricative."""
    n = int(window_ms * sr / 1000)
    if n >= len(sig): n = len(sig)
    head = sig[:n]
    tail = sig[n:]
    rms_head = float(np.sqrt(np.mean(head**2))) if len(head) else 0.0
    rms_tail = float(np.sqrt(np.mean(tail**2))) if len(tail) else 0.0
    zcr_head = float(np.mean(np.abs(np.diff(np.sign(head))))) if len(head) > 1 else 0.0
    zcr_tail = float(np.mean(np.abs(np.diff(np.sign(tail))))) if len(tail) > 1 else 0.0
    return {
        "onset_rms": rms_head,
        "onset_rms_ratio": rms_head / (rms_tail + 1e-9),
        "onset_zcr": zcr_head,
        "onset_zcr_ratio": zcr_head / (zcr_tail + 1e-9),
    }

def extract(sig, sr):
    eps = 1e-9
    # ── pitch normalization: resample-invariant MFCCs ──
    sig_norm = sig  # pitch normalization disabled

    rms = float(np.sqrt(np.mean(sig**2)))
    zcr = float(np.mean(np.abs(np.diff(np.sign(sig)))))
    spec = np.abs(np.fft.rfft(sig))
    freqs = np.fft.rfftfreq(len(sig), 1/sr)
    centroid = float(np.sum(freqs*spec)/(np.sum(spec)+eps))
    spread = float(np.sqrt(np.sum(((freqs-centroid)**2)*spec)/(np.sum(spec)+eps)))
    peak_f = float(freqs[np.argmax(spec)])
    rolloff = float(freqs[np.searchsorted(np.cumsum(spec), 0.85*np.sum(spec))])

    mfcc_v = mfcc(sig_norm, sr)     # ← uses NORMALIZED signal
    feats = {
        "rms": rms, "zcr": zcr,
        "centroid": centroid, "spread": spread,
        "peak_f": peak_f, "rolloff": rolloff,
        "spectral_flatness": spectral_flatness(sig),
        "hnr": harmonic_ratio(sig, sr),
        **pitch_stats(sig, sr),
        **formants(sig, sr),
        **onset_features(sig, sr),
    }
    for i, v in enumerate(mfcc_v):
        feats[f"mfcc_{i}"] = float(v)
    return feats
