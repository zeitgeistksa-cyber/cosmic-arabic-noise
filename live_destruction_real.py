#!/usr/bin/env python3
"""
Live Destruction Engine — Real Samples Edition.

Layers:
  A) Real recorded disasters (loaded from real_samples/)
  B) Synthetic physics layers (Lorenz, Rossler, Schumann, phonemes)

AI-controlled parameters adjust both real and synth layer levels.
"""
import sys, json, time, wave, glob
from pathlib import Path
import numpy as np

SR = 44100
CHUNK = 2048
STATE_FILE = Path("destruction_state.json")
PARAMS_FILE = Path("destruction_params.json")
SAMPLES_DIR = Path("real_samples")


# ---------- Parameter defaults ----------
DEFAULT_PARAMS = {
    "schumann_gain": 0.12,
    "seismic_gain": 0.20,
    "turbulence_gain": 0.15,
    "volcanic_rate": 0.10,
    "flood_gain": 0.15,
    "twin_gain": 0.18,
    "crack_rate": 0.30,
    "swell_depth": 0.4,
    "saturation": 1.3,
    "chaos_rate": 1.0,
    "real_earthquake": 0.35,
    "real_volcano": 0.30,
    "real_storm": 0.25,
    "real_wind": 0.20,
    "real_fire": 0.10,
    "real_wave": 0.20,
    "real_tremor": 0.25,
    "real_explosion": 0.15,
}


def load_params():
    if PARAMS_FILE.exists():
        try:
            return {**DEFAULT_PARAMS, **json.loads(PARAMS_FILE.read_text())}
        except Exception:
            pass
    PARAMS_FILE.write_text(json.dumps(DEFAULT_PARAMS, indent=2))
    return DEFAULT_PARAMS.copy()


# ---------- Physics drivers ----------
class Lorenz:
    def __init__(self):
        self.s = np.array([0.1, 0.0, 0.1])
    def step(self, dt):
        x, y, z = self.s
        self.s += np.array([10*(y-x), x*(28-z)-y, x*y-(8/3)*z]) * dt
        return self.s
    def norm(self):
        return np.tanh(self.s / 20.0)


class Rossler:
    def __init__(self):
        self.s = np.array([0.1, 0.0, 0.1])
    def step(self, dt):
        x, y, z = self.s
        self.s += np.array([-y-z, x+0.2*y, 0.2+z*(x-5.7)]) * dt
        return self.s
    def norm(self):
        return np.tanh(self.s / 5.0)


# ---------- Noise generators ----------
def pink(n):
    w = np.random.randn(n)
    spec = np.fft.rfft(w)
    f = np.fft.rfftfreq(n, 1/SR)
    f[0] = f[1] if len(f) > 1 else 1.0
    return np.fft.irfft(spec / np.sqrt(f), n=n)


def bandpass(n, lo, hi):
    w = np.random.randn(n)
    spec = np.fft.rfft(w)
    f = np.fft.rfftfreq(n, 1/SR)
    mask = (f >= lo) & (f <= hi)
    spec[~mask] = 0
    return np.fft.irfft(spec, n=n)


# ---------- Real sample loader ----------
class SampleBank:
    """Loads WAV files and streams them with looping."""
    def __init__(self):
        self.categories = {}
        if not SAMPLES_DIR.exists():
            print(">> No samples directory. Running synth-only.", file=sys.stderr)
            return
        manifest_path = SAMPLES_DIR / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
        else:
            # Discover WAVs by name
            manifest = {}
            for f in glob.glob(str(SAMPLES_DIR / "*.wav")):
                name = Path(f).stem.rsplit("_", 1)[0]
                manifest.setdefault(name, []).append(f)

        for cat, paths in manifest.items():
            loaded = []
            for p in paths:
                try:
                    with wave.open(p, "rb") as wf:
                        n = wf.getnframes()
                        data = np.frombuffer(wf.readframes(n), dtype=np.int16)
                        mono = data.astype(np.float32) / 32768.0
                    if len(mono) < SR:
                        continue
                    loaded.append(mono)
                except Exception as e:
                    print(f"   skip {p}: {e}", file=sys.stderr)
            if loaded:
                self.categories[cat] = loaded
                print(f">> loaded {len(loaded)} samples for '{cat}'",
                      file=sys.stderr)

        # Per-category playback state
        self.positions = {cat: {"sample": 0, "offset": 0}
                          for cat in self.categories}

    def read(self, category, n):
        """Return n samples from a looping sample in the category."""
        if category not in self.categories:
            return np.zeros(n, dtype=np.float32)
        pool = self.categories[category]
        state = self.positions[category]
        if state["sample"] >= len(pool):
            state["sample"] = 0
        src = pool[state["sample"]]
        out = np.zeros(n, dtype=np.float32)
        written = 0
        while written < n:
            remaining = len(src) - state["offset"]
            take = min(remaining, n - written)
            out[written:written+take] = src[state["offset"]:state["offset"]+take]
            written += take
            state["offset"] += take
            if state["offset"] >= len(src):
                # pick next sample in pool
                state["sample"] = (state["sample"] + 1) % len(pool)
                state["offset"] = 0
                src = pool[state["sample"]]
        return out


# ---------- Phoneme engine (compressed) ----------
from phoneme_table import PHONEMES, LETTER_INDEX

DESTRUCTION_ROOTS = ["ففف", "سسس", "ززز", "صصص", "ثثث", "شفش", "سفص", "فظظ"]


# ---------- Main engine ----------
class LiveDestructionReal:
    def __init__(self):
        self.params = load_params()
        self.lorenz = Lorenz()
        self.rossler = Rossler()
        self.clock = 0
        self.twin_idx = 0
        self.twin_lock = 0.0
        self.twin_phases = [0.0] * 6
        self.schumann_phase = 0.0
        self.bank = SampleBank()

    def step_physics(self):
        dt = 0.0005 * self.params["chaos_rate"]
        for _ in range(4):
            self.lorenz.step(dt)
            self.rossler.step(dt)

    def render(self, n):
        p = self.params
        t = (self.clock + np.arange(n)) / SR
        self.clock += n

        L = self.lorenz.norm()
        R = self.rossler.norm()

        # --- REAL SAMPLES ---
        real = np.zeros(n, dtype=np.float32)
        for cat in ["earthquake", "volcano", "storm", "wind",
                    "fire", "wave", "tremor", "explosion"]:
            gain_key = f"real_{cat}"
            gain = p.get(gain_key, 0.0)
            if gain <= 0:
                continue
            chunk = self.bank.read(cat, n) * gain
            real += chunk

        # --- SCHUMANN ---
        sch_freq = 7.83 + 2.5 * L[0] + 1.2 * R[1]
        sch_phase = self.schumann_phase + 2*np.pi*sch_freq*np.arange(n)/SR
        self.schumann_phase += 2*np.pi*sch_freq*n/SR
        schumann = np.sin(sch_phase) + 0.4*np.sin(2*sch_phase) + 0.25*np.sin(3*sch_phase)
        schumann += 0.3 * abs(L[2]) * np.random.randn(n)
        schumann *= p["schumann_gain"]

        # --- SEISMIC ---
        seismic = bandpass(n, 8, 45)
        tremor_mod = 0.6 + 0.4*np.sin(2*np.pi*(1.5+L[0])*t) * \
                     (0.7 + 0.3*np.sin(2*np.pi*(0.3+0.1*R[0])*t))
        seismic *= tremor_mod * p["seismic_gain"]

        # --- TURBULENCE ---
        turb = pink(n)
        gust = 0.5 + 0.3*np.sin(2*np.pi*(0.15+0.05*L[1])*t) + \
               0.2*np.sin(2*np.pi*(0.47+0.1*R[2])*t)
        turb *= gust * p["turbulence_gain"]

        # --- VOLCANIC (synth) ---
        volcanic = np.zeros(n)
        n_new = np.random.poisson(p["volcanic_rate"] * n / SR)
        for _ in range(n_new):
            pos = np.random.randint(0, n)
            energy = np.random.uniform(0.5, 1.5)
            length = int(SR * np.random.uniform(0.3, 1.5))
            if pos + length > n:
                length = n - pos
            env = np.exp(-np.linspace(0, 8, length))
            burst = np.random.randn(length) * env * energy
            sub = np.sin(2*np.pi*35*np.arange(length)/SR) * env * energy * 0.7
            volcanic[pos:pos+length] += burst + sub

        # --- FLOOD ---
        flood = bandpass(n, 7000, 15000) * p["flood_gain"]

        # --- TWIN ENGINES ---
        chaos_mag = np.linalg.norm(L) + np.linalg.norm(R)
        self.twin_lock = 0.7*self.twin_lock + 0.3*max(0.0, 1.0 - chaos_mag/4.0)
        twin = np.zeros(n)
        root = DESTRUCTION_ROOTS[self.twin_idx % len(DESTRUCTION_ROOTS)]
        for k, c in enumerate(root[:3]):
            if c not in LETTER_INDEX:
                continue
            fA = 55.0 * (2.0 ** (LETTER_INDEX[c] / 7.0))
            detune = 0.08 * (1.0 - self.twin_lock)
            fB = fA * (1.0 + detune)
            phaseA = 2*np.pi*fA*t + self.twin_phases[k]
            phaseB = 2*np.pi*fB*t + self.twin_phases[k+3]
            envA = 0.5 + 0.5*np.sin(2*np.pi*0.5*t + k)
            envB = 0.5 + 0.5*np.sin(2*np.pi*0.5*t + k + 1.5)
            twin += (np.sin(phaseA)*envA + np.sin(phaseB)*envB) * 0.3
        twin *= p["twin_gain"]
        if self.clock % (SR * 3) < n:
            self.twin_idx += 1
        for k in range(6):
            self.twin_phases[k] += 2*np.pi*200*n/SR

        # --- CRACKS ---
        cracks = np.zeros(n)
        for _ in range(np.random.poisson(p["crack_rate"] * n / SR)):
            pos = np.random.randint(0, n)
            length = int(SR * np.random.uniform(0.02, 0.15))
            if pos + length > n:
                length = n - pos
            env = np.exp(-np.linspace(0, 12, length))
            crack = np.random.randn(length) * env
            crack[:min(10, length)] *= 3.0
            cracks[pos:pos+length] += crack

        # --- GLOBAL SWELL ---
        swell = 1.0 - p["swell_depth"] * 0.5 * (1.0 + np.sin(2*np.pi*0.02*t))

        # --- MIX ---
        mix = real + schumann + seismic + turb + volcanic + flood + twin + cracks
        mix *= swell

        # Saturation
        mix = np.tanh(mix * p["saturation"])

        # Normalize
        peak = np.max(np.abs(mix)) + 1e-6
        mix = mix / max(peak, 0.5) * 0.95

        return mix

    def snapshot(self):
        L = self.lorenz.norm()
        R = self.rossler.norm()
        return {
            "sample_clock": self.clock,
            "lorenz": L.tolist(),
            "rossler": R.tolist(),
            "twin_lock": float(self.twin_lock),
            "params": self.params,
            "sample_categories": list(self.bank.categories.keys()),
        }

    def run(self):
        print(">> Live Destruction Engine (Real Samples) online", file=sys.stderr)
        last_state = time.time()
        try:
            while True:
                chunk = self.render(CHUNK)
                int16 = (np.clip(chunk, -1.0, 1.0) * 32767).astype(np.int16)
                stereo = np.stack([int16, int16], axis=1)
                sys.stdout.buffer.write(stereo.tobytes())
                sys.stdout.buffer.flush()

                if time.time() - last_state > 1.0:
                    STATE_FILE.write_text(json.dumps(self.snapshot(), indent=2))
                    last_state = time.time()
                    self.params = load_params()

                self.step_physics()
        except (KeyboardInterrupt, BrokenPipeError):
            sys.exit(0)


if __name__ == "__main__":
    LiveDestructionReal().run()
