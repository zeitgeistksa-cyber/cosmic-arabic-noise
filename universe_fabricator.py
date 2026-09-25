import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, lfilter

SR    = 44100
DUR   = 90
rng   = np.random.default_rng()

t = np.linspace(0, DUR, int(SR*DUR), False)
N = len(t)

# ---------------- utility ----------------
def bandpass(x, lo, hi, order=4):
    sos = butter(order, [lo/(SR/2), hi/(SR/2)], btype="band", output="sos")
    return sosfilt(sos, x)

def lowpass(x, hi, order=4):
    sos = butter(order, hi/(SR/2), btype="low", output="sos")
    return sosfilt(sos, x)

def highpass(x, lo, order=4):
    sos = butter(order, lo/(SR/2), btype="high", output="sos")
    return sosfilt(sos, x)

def hann(n): return np.hanning(n)

def norm(x, g=1.0):
    return x / (np.max(np.abs(x)) + 1e-9) * g

# ---------------- 1. COSMIC MICROWAVE BACKGROUND ----------------
# faint, isotropic, band-limited hiss
cmb = rng.standard_normal(N)
cmb = bandpass(cmb, 40, 4000, order=2)
cmb = norm(cmb, 0.18)

# ---------------- 2. SOLAR WIND (pink-ish drift) ----------------
# Voss-McCartney style pink noise
def pink(n, octaves=10):
    out = np.zeros(n)
    for k in range(octaves):
        step = 2**k
        hold = rng.standard_normal(n//step + 1)
        out += np.repeat(hold, step)[:n] / (k + 1)
    return out

solar = pink(N, 12)
solar = lowpass(solar, 3500)
solar = norm(solar, 0.30)

# ---------------- 3. DARK MATTER HUM (sub drone) ----------------
# avoided <20 Hz for safety; sits at 27.5 + 41.2 + 55 Hz
dm = (0.55*np.sin(2*np.pi*27.5*t)
    + 0.35*np.sin(2*np.pi*41.2*t)
    + 0.25*np.sin(2*np.pi*55.0*t))
dm *= 0.9 + 0.1*np.sin(2*np.pi*0.017*t)   # slow gravity-well breathing

# ---------------- 4. PULSAR RHYTHM ----------------
# periodic bursts at slowly varying rates
pulsar = np.zeros(N)
pos = 0
while pos < N:
    rate = rng.uniform(0.6, 3.5)          # bursts per second
    period = int(SR / rate)
    n = int(rng.uniform(0.002, 0.020) * SR)   # burst length
    if pos + n >= N: break
    f = rng.uniform(200, 1800)
    seg = 0.35*np.sin(2*np.pi*f*t[pos:pos+n]) * hann(n)
    pulsar[pos:pos+n] += seg
    pos += period

# ---------------- 5. MAGNETAR FLARES ----------------
# rare, huge, decaying noise bursts
magnetar = np.zeros(N)
for _ in range(rng.integers(6, 14)):
    start = rng.integers(0, N - SR)
    length = int(rng.uniform(0.4, 2.5) * SR)
    end = min(N, start + length)
    k = end - start
    env = np.exp(-np.linspace(0, 6, k))
    burst = bandpass(rng.standard_normal(k), 200, 9000, order=2)
    magnetar[start:end] += 0.9 * burst * env

# ---------------- 6. GRAVITATIONAL WAVE CHIRPS ----------------
# frequency sweep upward, brief
chirps = np.zeros(N)
for _ in range(rng.integers(10, 20)):
    start = rng.integers(0, N - SR)
    dur = int(rng.uniform(0.15, 0.8) * SR)
    end = min(N, start + dur)
    k = end - start
    f0, f1 = rng.uniform(60, 200), rng.uniform(600, 1800)
    freqs = np.linspace(f0, f1, k)
    phase = 2*np.pi*np.cumsum(freqs)/SR
    env = hann(k)
    chirps[start:end] += 0.35*np.sin(phase) * env

# ---------------- 7. NEBULA PADS ----------------
# slow evolving detuned stack with cosmic intervals
def pad(f0, detunes, seconds):
    n = int(seconds*SR)
    tt = np.arange(n)/SR
    out = np.zeros(n)
    for d in detunes:
        out += np.sin(2*np.pi*(f0 + d)*tt)
    return out / len(detunes)

pad_a = pad(110, [0.0, 0.6, -0.4, 1.1], DUR)
pad_b = pad(110*2**(6/12), [0.0, 0.5, -0.6], DUR)     # tritone
pad_c = pad(110*2**(1/12), [0.0, 0.4], DUR)           # minor 2nd
pad_mix = 0.7*pad_a + 0.55*pad_b + 0.45*pad_c
pad_mix *= 0.6 + 0.4*np.sin(2*np.pi*0.04*t)

# ---------------- 8. QUASAR JET SIZZLE ----------------
qjet = (0.10*np.sin(2*np.pi*9200*t) * np.sin(2*np.pi*5.7*t)
      + 0.08*np.sin(2*np.pi*11700*t) * np.sin(2*np.pi*3.3*t))

# ---------------- 9. HAWKING SHIMMER ----------------
# sparse ultra-high tick noise
hawk = np.zeros(N)
idx = rng.choice(N, size=int(N*0.0015), replace=False)
hawk[idx] = rng.standard_normal(len(idx)) * 0.4
hawk = bandpass(hawk, 6000, 15000, order=2)

# ---------------- 10. SHEPARD INFINITE RISE ----------------
shep = np.zeros(N)
for k in range(6):
    fk = 80 * 2**k
    ph = 2*np.pi*fk*t
    win = 0.5 - 0.5*np.cos(2*np.pi*(k % 6)/6)
    shep += 0.06 * win * np.sin(ph)

# ---------------- 11. GALACTIC ROTATION LFO ----------------
gal = 0.85 + 0.15*np.sin(2*np.pi*0.012*t)

# ---------------- MIX ----------------
mix = (dm * 1.20
     + pad_mix * 0.70
     + solar * 0.55 * gal
     + cmb * 0.50
     + pulsar * 0.60
     + magnetar * 0.75
     + chirps * 0.55
     + qjet * 0.55
     + hawk * 0.40
     + shep * 0.35)

# ---------------- SELF-MUTATION (multi-timescale) ----------------
chunk = int(SR * 2.5)
w = np.array([1.0, 0.85, 0.7, 0.55, 0.4, 0.25, 0.15])
hist = []
for i in range(0, N, chunk):
    end = min(N, i + chunk)
    seg = mix[i:end]
    if len(seg) < chunk: break
    hist.append(float(np.var(seg)))
    if len(hist) > 6 and np.var(hist[-6:]) < 5e-5:
        # decay into randomness — force divergence
        w += rng.normal(0, 0.25, size=w.shape)
        w = np.clip(w, 0.05, 1.8)
        mix[i:end] *= w[0]
        mix[i:end] += (w[1]*pulsar[i:end]
                     + w[2]*magnetar[i:end]
                     + w[3]*chirps[i:end])

# ---------------- SATURATION CHAIN ----------------
stage = mix.copy()
stage = np.sin(stage * 2.6)             # wavefold
stage = np.tanh(stage * 3.2)            # soft clip
stage = np.sign(stage) * np.abs(stage)**0.85   # asymm curve
# subtle bit-reduction flavor (stays clean, just grit)
q = 0.0008
stage = np.round(stage / q) * q
stage = np.tanh(stage * 1.4)

# ---------------- SAFETY + FADE ----------------
peak = float(np.max(np.abs(stage)) + 1e-9)
stage = stage / peak * 0.88
fade = np.minimum(1, t/3) * np.minimum(1, (DUR - t)/3)
stage *= fade

# ---------------- STEREO WIDTH (Haas + decorrelated) ----------------
mid  = stage
side = 0.035 * np.roll(stage, int(0.006*SR))
left  = mid + side
right = mid - side
stereo = np.stack([left, right], axis=-1)
stereo = norm(stereo, 0.88)

# ---------------- WRITE ----------------
wavfile.write("universe_fabricator.wav", SR,
              (stereo*32767).astype(np.int16))
print(f"peak={peak:.3f}  dur={DUR}s  frames={N}")
