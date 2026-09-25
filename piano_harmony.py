import sys, numpy as np
from scipy.signal import butter, lfilter

SR      = 44100
CHUNK   = 4096          # ~93 ms per buffer
rng     = np.random.default_rng(42)

# ============================================================
# COMPONENT 1 — CHAOS ENGINE (root note selector)
# 4D hyper-chaotic Lorenz-Rössler hybrid from the reference.
# x → root MIDI note, y → chord quality, z → octave, w → velocity
# ============================================================
class ChaosRoot:
    def __init__(self):
        self.state = np.array([0.1, 0.0, 0.1, 0.5], dtype=np.float64)
        self.scale = np.array([0, 2, 3, 5, 7, 8, 10])  # natural minor
        self.root_midi = 48   # C3

    def step(self, dt=0.0005):
        x, y, z, w = self.state
        dx = 10.0 * (y - x) + w
        dy = x * (28.0 - z) - y
        dz = x * y - (8.0 / 3.0) * z
        dw = -0.5 * x - 0.1 * w
        self.state += np.array([dx, dy, dz, dw]) * dt

    def pick_root(self):
        """Map chaotic state to a MIDI root note in the minor scale."""
        x, y, z, w = self.state
        idx = int(abs(x) * 3.7) % len(self.scale)
        octave_shift = int(abs(z) * 0.6) % 2
        midi = 48 + self.scale[idx] + 12 * octave_shift
        return int(np.clip(midi, 36, 84))

    def pick_quality(self):
        """y decides major / minor / sus / 7th."""
        y = self.state[1]
        if y < -5:
            return [0, 3, 7]          # minor
        elif y < 0:
            return [0, 4, 7]          # major
        elif y < 8:
            return [0, 3, 7, 10]      # minor 7
        else:
            return [0, 5, 7]          # sus4

# ============================================================
# COMPONENT 2 — KURAMOTO SWARM (voice synchronization)
# 3 oscillators = root, third, fifth. Coupling decides how
# tightly the three voices strike together.
# ============================================================
class KuramotoVoices:
    def __init__(self, n=3):
        self.n = n
        self.phases = rng.uniform(0, 2*np.pi, n)
        self.native = np.array([0.5, 0.7, 1.0])   # different rhythms
        self.coupling = 0.8

    def step(self, dt):
        diffs = self.phases[:, None] - self.phases[None, :]
        interact = np.sum(np.sin(diffs), axis=1)
        dphase = 2*np.pi*self.native + (self.coupling/self.n)*interact
        self.phases = np.mod(self.phases + dphase*dt, 2*np.pi)

    def strikes(self, threshold=0.98):
        """Return boolean array: which voices strike this chunk."""
        return np.sin(self.phases) > threshold

# ============================================================
# COMPONENT 3 — SIREN NETWORK (piano timbre)
# 8→16→16→1 sinusoidal MLP generates inharmonic partials.
# ============================================================
class SirenPiano:
    def __init__(self, seed=7):
        r = np.random.default_rng(seed)
        self.W1 = r.uniform(-0.1, 0.1, (8, 16))
        self.W2 = r.uniform(-0.1, 0.1, (16, 16))
        self.Wo = r.uniform(-0.2, 0.2, (16, 1))
        self.omega = 30.0
        self.B = 0.0004          # piano inharmonicity coefficient

    def partials(self, f0, n_partials=8):
        """Return (freqs, amps) for one piano note."""
        latent = np.linspace(0, 1, 8)
        h1 = np.sin(self.omega * (latent @ self.W1))
        h2 = np.sin(self.omega * 1.2 * (h1 @ self.W2))
        raw = np.tanh(h2 @ self.Wo).flatten()
        amps = np.abs(raw) / (np.max(np.abs(raw)) + 1e-9)
        # natural piano rolloff baked in
        base = np.array([1.0, 0.55, 0.35, 0.22, 0.14, 0.08, 0.05, 0.03])
        amps = amps * base
        partials = np.arange(1, n_partials+1)
        freqs = f0 * partials * np.sqrt(1 + self.B * partials**2)
        return freqs, amps

# ============================================================
# PIANO NOTE RENDERER
# ============================================================
def midi_to_hz(m):
    return 440.0 * 2**((m - 69) / 12)

def render_piano_note(midi, duration, velocity, siren):
    """Additive inharmonic piano with per-partial decay + hammer strike."""
    n = int(duration * SR)
    t = np.arange(n) / SR
    f0 = midi_to_hz(midi)
    freqs, amps = siren.partials(f0)
    out = np.zeros(n, dtype=np.float32)

    for k, (f, a) in enumerate(zip(freqs, amps)):
        if f > SR * 0.45:
            break
        # higher partials decay faster
        decay_t = duration * (1.0 - 0.11 * k)
        decay = np.exp(-t / max(decay_t, 0.05))
        # two-string detune shimmer
        detune = 1.0 + rng.normal(0, 0.0004) if k == 0 else 1.0
        out += a * decay * np.sin(2*np.pi*f*detune*t)

    # hammer strike — 12 ms lowpassed noise
    atk = min(int(0.012 * SR), n)
    strike = rng.standard_normal(atk) * 0.18
    b, a_lp = butter(2, 2500/(SR/2), btype="low")
    strike = lfilter(b, a_lp, strike)
    env = np.exp(-np.arange(atk)/(SR*0.005))
    out[:atk] += strike * env

    # velocity curve
    out *= velocity
    return out.astype(np.float32)

# ============================================================
# MAIN ENGINE
# ============================================================
class PianoHarmonyEngine:
    def __init__(self):
        self.sr = SR
        self.clock = 0
        self.chaos = ChaosRoot()
        self.voices = KuramotoVoices()
        self.siren = SirenPiano()

        # current chord state
        self.root_midi = 48
        self.quality = [0, 3, 7]
        self.note_buffers = []      # active (buffer, offset)
        self.next_chord_in = 0

        # self-study loop from the reference engine
        self.entropy_hist = []
        self.bpm = 70

    def _mutate(self):
        """Entropy-driven mutation — same idea as reference engine."""
        self.siren.W1 += rng.normal(0, 0.02, self.siren.W1.shape)
        self.siren.W2 += rng.normal(0, 0.02, self.siren.W2.shape)
        self.voices.coupling = rng.uniform(0.1, 2.5)
        self.siren.omega = rng.uniform(20.0, 90.0)
        self.bpm = int(rng.uniform(50, 110))

    def _entropy(self, chunk):
        mag = np.abs(np.fft.rfft(chunk)) + 1e-9
        prob = mag / np.sum(mag)
        return float(-np.sum(prob * np.log2(prob)))

    def generate_chunk(self, n):
        # advance physics
        self.chaos.step()
        self.voices.step(n / SR)

        # schedule new chord on strike
        if self.next_chord_in <= 0:
            self.root_midi = self.chaos.pick_root()
            self.quality = self.chaos.pick_quality()
            strikes = self.voices.strikes()
            for i, hit in enumerate(strikes):
                if hit:
                    midi = self.root_midi + self.quality[i % len(self.quality)]
                    dur = rng.uniform(1.5, 3.5)
                    vel = rng.uniform(0.5, 0.95)
                    buf = render_piano_note(midi, dur, vel, self.siren)
                    self.note_buffers.append([buf, 0])
            beat = 60.0 / self.bpm
            self.next_chord_in = int(beat * SR)

        # mix active notes
        out = np.zeros(n, dtype=np.float32)
        alive = []
        for buf, off in self.note_buffers:
            k = min(n, len(buf) - off)
            if k > 0:
                out[:k] += buf[off:off+k]
                off += k
            if off < len(buf):
                alive.append([buf, off])
        self.note_buffers = alive
        self.next_chord_in -= n

        # gentle saturation
        out = np.tanh(out * 1.4) * 0.85

        # self-study
        e = self._entropy(out)
        self.entropy_hist.append(e)
        if len(self.entropy_hist) > 50:
            self.entropy_hist.pop(0)
        if len(self.entropy_hist) > 10 and np.var(self.entropy_hist) < 0.01:
            self._mutate()
            self.entropy_hist.clear()

        peak = np.max(np.abs(out)) + 1e-9
        return (out / peak * 0.95).astype(np.float32)

# ============================================================
# STREAM TO STDOUT (pipes to mpv)
# ============================================================
def main():
    eng = PianoHarmonyEngine()
    try:
        while True:
            chunk = eng.generate_chunk(CHUNK)
            pcm = (np.clip(chunk, -1, 1) * 32767).astype("<i2").tobytes()
            sys.stdout.buffer.write(pcm)
            sys.stdout.buffer.flush()
    except (KeyboardInterrupt, BrokenPipeError):
        sys.exit(0)

if __name__ == "__main__":
    main()
