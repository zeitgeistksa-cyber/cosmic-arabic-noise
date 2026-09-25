import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR   = 44100
DUR  = 60          # longer = more unsettling
rng  = np.random.default_rng()   # fresh randomness every run

t = np.linspace(0, DUR, int(SR * DUR), False)
N = len(t)

# ---------- helpers ----------
def env_hann(n):
    return np.hanning(n)

def smooth(x, w=2048):
    k = np.ones(w) / w
    return np.convolve(x, k, mode="same")

def bandpass(x, lo, hi, order=4):
    sos = butter(order, [lo/(SR/2), hi/(SR/2)], btype="band", output="sos")
    return sosfilt(sos, x)

# ---------- 1. DEEP DRONE (55 Hz + detuned saw-ish stack) ----------
def drone_stack(f0, detunes):
    out = np.zeros(N)
    for d in detunes:
        out += np.sin(2*np.pi*(f0 + d)*t)
    return out / len(detunes)

base     = drone_stack(55,  [0.0, +0.7, -0.5, +1.3])
sub      = 0.6*np.sin(2*np.pi*27.5*t)          # sub-octave rumble
tritone  = 0.35*np.sin(2*np.pi*(55*2**(6/12))*t)
cluster  = (0.22*np.sin(2*np.pi*110*t)
          + 0.22*np.sin(2*np.pi*(110*2**(1/12))*t)
          + 0.18*np.sin(2*np.pi*(110*2**(2/12))*t))

# slow cosmic breathing + slow pitch drift
lfo   = 0.5 + 0.5*np.sin(2*np.pi*0.07*t)
drift = 1 + 0.015*np.sin(2*np.pi*0.03*t)
drone = (base * drift * lfo) + sub

# ---------- 2. HIGH WHINE BURSTS (click-free, random) ----------
whine = np.zeros(N)
pos = 0
while pos < N:
    dur_s = rng.uniform(0.4, 2.5)
    n = int(dur_s * SR)
    if pos + n > N: n = N - pos
    f = rng.uniform(7000, 13000)
    seg = 0.07*np.sin(2*np.pi*f*t[pos:pos+n])
    seg *= env_hann(n)                      # no clicks
    whine[pos:pos+n] += seg
    pos += n + int(rng.uniform(0.3, 2.0) * SR)

# ---------- 3. RANDOM NOISE GRID (cosmic-ray crackle) ----------
noise = rng.standard_normal(N) * 0.08
gate  = (rng.random(N) < 0.18).astype(float)
noise = noise * smooth(gate, 4096)
noise = bandpass(noise, 300, 6000)

# ---------- 4. SHEPARD TONE (infinite rise, phase-based) ----------
shepard = np.zeros(N)
bands = 6
for k in range(bands):
    fk   = 80 * 2**k
    ph   = 2*np.pi*fk*t
    # amplitude window: fades in at low freq, out at high freq
    win  = 0.5 - 0.5*np.cos(2*np.pi * (np.log2(fk/80) % 1))
    shepard += 0.06 * win * np.sin(ph)
shepard *= 0.7 + 0.3*np.sin(2*np.pi*0.05*t)

# ---------- 5. RING-MODULATED SIZZLE (metallic, piercing) ----------
sizzle = 0.09 * np.sin(2*np.pi*9000*t) * np.sin(2*np.pi*7.3*t)
sizzle += 0.06 * np.sin(2*np.pi*11300*t) * np.sin(2*np.pi*3.1*t)

# ---------- 6. SELF-MUTATION (entropy-driven weight wobble) ----------
# break the mix into chunks, measure variance, wobble weights if too stable
chunk = SR * 2
weights = np.array([1.0, 0.7, 0.5, 0.4, 0.3])
hist = []
for i in range(0, N, chunk):
    seg = drone[i:i+chunk]
    if len(seg) < chunk: break
    v = np.var(seg)
    hist.append(v)
    if len(hist) > 4 and np.var(hist[-4:]) < 1e-4:
        weights += rng.normal(0, 0.15, size=weights.shape)
        weights = np.clip(weights, 0.1, 1.5)

# ---------- MIX ----------
mix = (weights[0]*drone
     + weights[1]*tritone
     + weights[2]*cluster
     + weights[3]*whine
     + weights[4]*shepard
     + noise + sizzle)

# ---------- ASYMMETRIC SATURATION (more harmonic grit) ----------
mix = np.sin(mix * 2.2)            # wavefold
mix = np.tanh(mix * 2.5)           # soft clip

# ---------- SAFETY + FADE ----------
peak = np.max(np.abs(mix)) + 1e-9
mix = mix / peak * 0.85
fade = np.minimum(1, t/3) * np.minimum(1, (DUR - t)/3)
mix *= fade

# ---------- STEREO with slight detune for width ----------
left  = mix
right = 0.97 * mix + 0.03 * np.roll(mix, int(0.004*SR))
stereo = np.stack([left, right], axis=-1)

# ---------- WRITE ----------
wavfile.write("cosmic_annoyance_v2.wav", SR, (stereo*32767).astype(np.int16))
print(f"peak={peak:.3f}  dur={DUR}s  weights={weights.round(2)}")
