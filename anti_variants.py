import sys, time, argparse, numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 44100
rng = np.random.default_rng()

# ---------- DSP helpers ----------
def bp(x, lo, hi, order=3):
    sos = butter(order, [lo/(SR/2), hi/(SR/2)], btype="band", output="sos")
    return sosfilt(sos, x)

def lp(x, hi, order=4):
    sos = butter(order, hi/(SR/2), btype="low", output="sos")
    return sosfilt(sos, x)

def hp(x, lo, order=4):
    sos = butter(order, lo/(SR/2), btype="high", output="sos")
    return sosfilt(sos, x)

def hann(n): return np.hanning(n)

def norm(x, g=1.0):
    return x / (np.max(np.abs(x)) + 1e-9) * g

def lorenz(n, dt=0.001):
    x, y, z = 0.1, 0.0, 0.0
    out = np.zeros(n)
    for i in range(n):
        dx = 10*(y-x); dy = x*(28-z)-y; dz = x*y - 8/3*z
        x += dx*dt; y += dy*dt; z += dz*dt
        out[i] = x
    return out

# ---------- 6 variant generators ----------
def variant_industrial(t, N):
    """Machine shop — grinders, hammers, hydraulic hiss."""
    out = np.zeros(N)
    # hydraulic hiss
    out += 0.25 * bp(rng.standard_normal(N), 200, 8000)
    # hammer strikes (irregular)
    pos = 0
    while pos < N:
        n = int(rng.uniform(0.004, 0.02)*SR)
        if pos+n >= N: break
        f = rng.uniform(80, 400)
        seg = np.sin(2*np.pi*f*t[pos:pos+n]) * hann(n) * rng.uniform(0.4, 1.0)
        out[pos:pos+n] += seg
        pos += int(rng.uniform(0.05, 0.4)*SR)
    # grinder whine
    out += 0.15 * np.sin(2*np.pi*7200*t) * (0.5+0.5*np.sin(2*np.pi*0.4*t))
    # sub pressure
    out += 0.5*np.sin(2*np.pi*41.2*t) + 0.4*np.sin(2*np.pi*55*t)
    return out

def variant_organic(t, N):
    """Wet, breathing, insectile — cicada chorus + heartbeat."""
    out = np.zeros(N)
    # cicada: dense AM'd high band
    carrier = bp(rng.standard_normal(N), 3000, 9000)
    am = 0.5 + 0.5*np.sin(2*np.pi*70*t) * np.sin(2*np.pi*0.3*t)
    out += 0.6 * carrier * am
    # heartbeat (two-thump cycle ~1 Hz)
    beat = np.zeros(N)
    for start in np.arange(0, N/SR, 1.0):
        i = int(start*SR)
        for offset, amp in [(0, 1.0), (0.18, 0.7)]:
            j = i + int(offset*SR)
            n = int(0.08*SR)
            if j+n >= N: break
            env = np.exp(-np.linspace(0, 5, n))
            beat[j:j+n] += amp * np.sin(2*np.pi*60*t[j:j+n]) * env
    out += 0.8 * beat
    # breathe LFO
    out *= 0.7 + 0.3*np.sin(2*np.pi*0.15*t)
    return out

def variant_digital(t, N):
    """Data center — fan, disk seek, modem handshake."""
    out = np.zeros(N)
    # fan hum stack
    for f in [50, 100, 150, 200, 250]:
        out += 0.08*np.sin(2*np.pi*f*t)
    # disk seek clicks
    pos = 0
    while pos < N:
        n = int(rng.uniform(0.002, 0.008)*SR)
        if pos+n >= N: break
        out[pos:pos+n] += 0.4 * rng.standard_normal(n) * hann(n)
        pos += int(rng.uniform(0.02, 0.25)*SR)
    # modem handshake (frequency steps)
    for _ in range(rng.integers(8, 16)):
        start = rng.integers(0, N-SR//2)
        dur = int(rng.uniform(0.1, 0.5)*SR)
        k = min(dur, N-start)
        f = rng.choice([300, 800, 1200, 2100, 2400])
        out[start:start+k] += 0.2*np.sin(2*np.pi*f*t[start:start+k])
    return out

def variant_void(t, N):
    """Deep space — sub drone + Hawking shimmer + slow wails."""
    out = np.zeros(N)
    # sub layers
    out += 0.6*np.sin(2*np.pi*27.5*t)
    out += 0.5*np.sin(2*np.pi*41.2*t)
    out += 0.4*np.sin(2*np.pi*55.0*t)
    # shimmer ticks
    idx = rng.choice(N, size=int(N*0.001), replace=False)
    tick = np.zeros(N)
    tick[idx] = rng.standard_normal(len(idx)) * 0.5
    out += bp(tick, 6000, 15000)
    # slow wails (magnetar)
    for _ in range(rng.integers(6, 12)):
        start = rng.integers(0, N-SR)
        dur = int(rng.uniform(0.5, 2.0)*SR)
        k = min(dur, N-start)
        f = rng.uniform(200, 800)
        env = np.exp(-np.linspace(0, 4, k))
        out[start:start+k] += 0.4*np.sin(2*np.pi*f*t[start:start+k]) * env
    return out

def variant_metal(t, N):
    """Metal — FM bell tones + feedback squeal + distortion."""
    out = np.zeros(N)
    # FM bell bed
    for _ in range(rng.integers(20, 40)):
        f0 = rng.uniform(400, 2500)
        idx = rng.uniform(1, 5)
        ph_c = 2*np.pi*f0*t
        ph_m = 2*np.pi*f0*1.5*t
        out += 0.05 * np.sin(ph_c + idx*np.sin(ph_m))
    # feedback squeal
    out += 0.2 * np.sin(2*np.pi*4800*t) * (0.3+0.7*np.abs(np.sin(2*np.pi*2.1*t)))
    # chaotic distortion
    lz = lorenz(min(N, 100000)); lz = np.interp(np.linspace(0, len(lz)-1, N),
                                                np.arange(len(lz)), lz)
    lz = lz / (np.max(np.abs(lz)) + 1e-9)
    out += 0.15 * np.sin(2*np.pi*800*t + 6*lz)
    return out

def variant_choir(t, N):
    """Dissonant choir — many detuned voices, chant-like."""
    out = np.zeros(N)
    base = 110.0
    intervals = [0, 1, 3, 5, 6, 8, 10]  # cluster
    for iv in intervals:
        for det in [-0.4, 0.0, 0.4]:
            f = base * 2**(iv/12) + det
            out += 0.06 * np.sin(2*np.pi*f*t)
    # formant sweep
    out *= 0.7 + 0.3*np.sin(2*np.pi*0.08*t)
    # whisper noise
    out += 0.1 * bp(rng.standard_normal(N), 2000, 6000) * (0.5+0.5*np.sin(2*np.pi*0.5*t))
    # sub anchor
    out += 0.4*np.sin(2*np.pi*41.2*t)
    return out

VARIANTS = {
    "industrial": variant_industrial,
    "organic":    variant_organic,
    "digital":    variant_digital,
    "void":       variant_void,
    "metal":      variant_metal,
    "choir":      variant_choir,
}

# ---------- main pipeline ----------
def build(name, duration, gain=0.95):
    N = int(SR*duration)
    t = np.linspace(0, duration, N, False)
    gen = VARIANTS[name]
    print(f"[*] building variant '{name}' for {duration}s")
    mix = gen(t, N)

    # saturation chain
    mix = np.sin(mix * 2.3)
    mix = np.tanh(mix * 3.0)
    q = 0.0006
    mix = np.round(mix / q) * q
    mix = np.tanh(mix * 1.4)

    # peak + fade
    mix = norm(mix, gain)
    fade = np.minimum(1, t/2) * np.minimum(1, (duration-t)/2)
    mix *= fade

    # stereo decorrelation
    left = mix
    right = np.roll(mix, int(0.005*SR)) * 0.96
    stereo = np.stack([left, right], axis=-1)
    stereo = norm(stereo, gain)

    fname = f"anti_{name}_{int(time.time())}.wav"
    wavfile.write(fname, SR, (stereo*32767).astype(np.int16))
    print(f"[*] wrote {fname}")
    return fname

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--variant", default="all",
                   help="one of: " + ", ".join(VARIANTS) + " | all")
    p.add_argument("--duration", type=int, default=45)
    p.add_argument("--gain", type=float, default=0.95)
    args = p.parse_args()

    if args.variant == "all":
        for name in VARIANTS:
            build(name, args.duration, args.gain)
    else:
        build(args.variant, args.duration, args.gain)

if __name__ == "__main__":
    main()
