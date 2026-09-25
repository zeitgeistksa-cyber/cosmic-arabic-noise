import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR    = 44100
DUR   = 60
rng   = np.random.default_rng()
t     = np.linspace(0, DUR, int(SR*DUR), False)
N     = len(t)

def bandpass(x, lo, hi, order=4):
    sos = butter(order, [lo/(SR/2), hi/(SR/2)], btype="band", output="sos")
    return sosfilt(sos, x)

def hann(n): return np.hanning(n)

def norm(x, g=1.0):
    return x / (np.max(np.abs(x)) + 1e-9) * g

# ============================================================
# LAYER 1: BROADBAND ANTI-PHASE CARRIER
# Covers 20 Hz – 18 kHz in overlapping bands.
# Each band is a noise carrier that, when emitted,
# creates destructive interference with matching frequencies.
# ============================================================
BANDS = [
    (20,   80),
    (80,   300),
    (300,  1200),
    (1200, 4000),
    (4000, 8000),
    (8000, 18000),
]

anti_carrier = np.zeros(N)
for lo, hi in BANDS:
    noise = rng.standard_normal(N)
    noise = bandpass(noise, lo, hi, order=3)
    # phase inversion happens at emission; here we shape amplitude
    anti_carrier += noise * (hi - lo) / 18000.0

anti_carrier = norm(anti_carrier, 0.6)

# ============================================================
# LAYER 2: TONAL ANTI-SIGNALS (targeted cancellation)
# Strong pure tones at common interference frequencies.
# These cancel specific tonal noises (fans, hums, whines).
# ============================================================
targets = [50, 60, 100, 120, 400, 800, 2400, 5200]
tonal_anti = np.zeros(N)
for f in targets:
    # slight detune for wider coverage
    for det in [-0.5, 0.0, +0.5]:
        tonal_anti += 0.06 * np.sin(2*np.pi*(f+det)*t)
tonal_anti *= 0.5 + 0.5*np.sin(2*np.pi*0.08*t)   # slow flicker

# ============================================================
# LAYER 3: PULSED ANTI-BURST FIELD
# Short bursts of anti-phase noise to break transient waves.
# Based on pulsar-like rhythm for unpredictable coverage.
# ============================================================
pulse_anti = np.zeros(N)
pos = 0
while pos < N:
    rate = rng.uniform(2.0, 12.0)
    period = int(SR / rate)
    n = int(rng.uniform(0.001, 0.015) * SR)
    if pos + n >= N: break
    burst = rng.standard_normal(n)
    burst = bandpass(burst, 200, 12000, order=2)
    pulse_anti[pos:pos+n] += burst * hann(n) * 0.5
    pos += period

# ============================================================
# LAYER 4: SWEEPING ANTI-FREQUENCY (radar-jam style)
# Continuous upward/downward sweeps that catch waves
# across a moving frequency band.
# ============================================================
sweep_anti = np.zeros(N)
sweep_dur = int(0.5 * SR)
for i in range(0, N - sweep_dur, sweep_dur):
    f0 = rng.uniform(100, 2000)
    f1 = rng.uniform(2000, 10000)
    k = sweep_dur
    freqs = np.linspace(f0, f1, k)
    phase = 2*np.pi*np.cumsum(freqs)/SR
    env = hann(k)
    sweep_anti[i:i+k] += 0.3 * np.sin(phase) * env

# ============================================================
# LAYER 5: SUB-HARMONIC PRESSURE (low-frequency block)
# Deep tones that create pressure nodes in the 25–90 Hz range.
# ============================================================
sub_pressure = (0.5*np.sin(2*np.pi*27.5*t)
              + 0.4*np.sin(2*np.pi*41.2*t)
              + 0.3*np.sin(2*np.pi*55.0*t)
              + 0.25*np.sin(2*np.pi*82.5*t))
sub_pressure *= 0.8 + 0.2*np.sin(2*np.pi*0.02*t)

# ============================================================
# LAYER 6: CHAOTIC JAMMER (Lorenz-attractor driven FM)
# Uses chaotic FM to prevent any frequency from
# stabilizing — a wave that never repeats cannot be
# predicted or filtered.
# ============================================================
def lorenz(n, dt=0.001, sigma=10, rho=28, beta=8/3):
    x, y, z = 0.1, 0.0, 0.0
    xs = np.zeros(n)
    for i in range(n):
        dx = sigma*(y-x); dy = x*(rho-z)-y; dz = x*y - beta*z
        x += dx*dt; y += dy*dt; z += dz*dt
        xs[i] = x
    return xs

lz = lorenz(min(N, 200000))
lz = np.interp(np.linspace(0, len(lz)-1, N), np.arange(len(lz)), lz)
lz = lz / (np.max(np.abs(lz)) + 1e-9)
jammer_phase = 2*np.pi*np.cumsum(5000 + 4500*lz)/SR
jammer = 0.12 * np.sin(jammer_phase) * np.sin(2*np.pi*7.3*t)

# ============================================================
# MIX — weighted blend, chaos-heavy
# ============================================================
mix = (anti_carrier * 1.0
     + tonal_anti   * 0.6
     + pulse_anti   * 0.7
     + sweep_anti   * 0.5
     + sub_pressure * 0.8
     + jammer       * 0.9)

# ============================================================
# SATURATION CHAIN
# ============================================================
mix = np.sin(mix * 2.4)
mix = np.tanh(mix * 3.0)
q = 0.0006
mix = np.round(mix / q) * q
mix = np.tanh(mix * 1.5)

# ============================================================
# SELF-MUTATION (entropy-driven divergence)
# ============================================================
chunk = int(SR * 2.0)
w = np.array([1.0, 0.6, 0.7, 0.5, 0.8, 0.9])
hist = []
for i in range(0, N, chunk):
    end = min(N, i + chunk)
    seg = mix[i:end]
    if len(seg) < chunk: break
    hist.append(float(np.var(seg)))
    if len(hist) > 5 and np.var(hist[-5:]) < 1e-4:
        w += rng.normal(0, 0.3, size=w.shape)
        w = np.clip(w, 0.05, 1.8)
        mix[i:end] *= w[0]

# ============================================================
# SAFETY + FADE
# ============================================================
peak = float(np.max(np.abs(mix)) + 1e-9)
mix = mix / peak * 0.85
fade = np.minimum(1, t/3) * np.minimum(1, (DUR-t)/3)
mix *= fade

# ============================================================
# STEREO WIDTH (decorrelated anti-phase)
# Left = normal, Right = phase-inverted copy
# This creates a null zone in the center.
# ============================================================
left  = mix
right = np.roll(mix, int(0.005*SR)) * 0.95
stereo = np.stack([left, right], axis=-1)
stereo = norm(stereo, 0.88)

wavfile.write("anti_wave_fabricator.wav", SR,
              (stereo*32767).astype(np.int16))
print(f"peak={peak:.3f}  dur={DUR}s  layers=6")
