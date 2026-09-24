#!/usr/bin/env python3
"""
Live Destruction Engine.
Real-time layered destruction symphony driven by mathematical wave physics.

Streams raw PCM (16-bit stereo, 44.1 kHz) to stdout.

Layers (all continuously active):
  1. Schumann cavity      — 7.83 Hz fundamental, chaos-modulated
  2. Seismic P-wave       — bandpassed noise, tremor-modulated
  3. Cyclone turbulence   — pink noise, multi-harmonic gust AM
  4. Volcanic events      — Poisson-process bursts
  5. Flood hiss           — high-frequency filtered noise
  6. Twin phoneme engines — two cosine matchers detuning toward lock
  7. Cracks               — random impulsive transients
  8. Global swell         — the slow tide that all layers ride

Physics drivers (never stop, always changing):
  - Lorenz chaos attractor (sigma=10, beta=8/3, rho=28)
  - Rössler attractor (a=0.2, b=0.2, c=5.7)
  - Schumann 7.83 Hz + 14, 20, 26, 33 Hz harmonics
  - Poisson statistics for volcanic events
  - 1/f^alpha spectral shaping for turbulence
"""
import sys, json, time
import numpy as np
from pathlib import Path

SR = 44100
CHUNK = 2048
STATE_FILE = Path("destruction_state.json")
PARAMS_FILE = Path("destruction_params.json")

DEFAULT_PARAMS = {
    "schumann_gain": 0.18,
    "seismic_gain": 0.32,
    "turbulence_gain": 0.28,
    "volcanic_rate": 0.15,     # events per second
    "flood_gain": 0.22,
    "twin_gain": 0.30,
    "crack_rate": 0.40,        # cracks per second
    "swell_depth": 0.5,        # global envelope modulation depth
    "saturation": 1.4,         # tanh drive
    "chaos_rate": 1.0,         # how fast chaos state evolves
}

def load_params():
    if PARAMS_FILE.exists():
        try:
            return {**DEFAULT_PARAMS, **json.loads(PARAMS_FILE.read_text())}
        except Exception:
            pass
    PARAMS_FILE.write_text(json.dumps(DEFAULT_PARAMS, indent=2))
    return DEFAULT_PARAMS.copy()

def save_params(p):
    PARAMS_FILE.write_text(json.dumps(p, indent=2))


# =================================================================
# PHYSICS DRIVERS
# =================================================================
class Lorenz:
    def __init__(self, sigma=10.0, beta=8/3, rho=28.0):
        self.state = np.array([0.1, 0.0, 0.1])
        self.sigma = sigma; self.beta = beta; self.rho = rho
    def step(self, dt):
        x, y, z = self.state
        dx = self.sigma * (y - x)
        dy = x * (self.rho - z) - y
        dz = x * y - self.beta * z
        self.state += np.array([dx, dy, dz]) * dt
        return self.state
    def normalized(self):
        return np.tanh(self.state / 20.0)

class Rossler:
    def __init__(self, a=0.2, b=0.2, c=5.7):
        self.state = np.array([0.1, 0.0, 0.1])
        self.a = a; self.b = b; self.c = c
    def step(self, dt):
        x, y, z = self.state
        dx = -y - z
        dy = x + self.a * y
        dz = self.b + z * (x - self.c)
        self.state += np.array([dx, dy, dz]) * dt
        return self.state
    def normalized(self):
        return np.tanh(self.state / 5.0)


# =================================================================
# COLORED NOISE
# =================================================================
def pink_chunk(n):
    white = np.random.randn(n)
    spec = np.fft.rfft(white)
    f = np.fft.rfftfreq(n, 1/SR)
    f[0] = f[1] if len(f) > 1 else 1.0
    return np.fft.irfft(spec / np.sqrt(f), n=n)

def brown_chunk(n):
    white = np.random.randn(n)
    spec = np.fft.rfft(white)
    f = np.fft.rfftfreq(n, 1/SR)
    f[0] = f[1] if len(f) > 1 else 1.0
    return np.fft.irfft(spec / f, n=n)

def bandpass_chunk(n, lo, hi):
    white = np.random.randn(n)
    spec = np.fft.rfft(white)
    f = np.fft.rfftfreq(n, 1/SR)
    mask = (f >= lo) & (f <= hi)
    spec[~mask] = 0
    return np.fft.irfft(spec, n=n)


# =================================================================
# PHONEME ENGINE (twin cosine matchers)
# =================================================================
from phoneme_table import PHONEMES, LETTER_INDEX

DESTRUCTION_ROOTS = ["ففف", "سسس", "ززز", "صصص", "ثثث", "شفش", "سفص", "فظظ"]

def root_to_freqs(root):
    out = []
    for c in root[:3]:
        if c in LETTER_INDEX:
            idx = LETTER_INDEX[c]
            out.append(55.0 * (2.0 ** (idx / 7.0)))
    return out


# =================================================================
# MAIN ENGINE
# =================================================================
class LiveDestruction:
    def __init__(self):
        self.params = load_params()
        self.lorenz = Lorenz()
        self.rossler = Rossler()
        self.sample_clock = 0
        self.twin_root_idx = 0
        self.twin_lock = 0.0  # 0 = detuned, 1 = locked
        self.next_volcanic = 0.0
        self.next_crack = 0.0
        self.volcanic_queue = []   # (samples_remaining, energy)
        self.crack_queue = []
        self.schumann_phase = 0.0
        self.twin_phase = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    def _step_physics(self):
        dt = 0.0005 * self.params["chaos_rate"]
        for _ in range(4):
            self.lorenz.step(dt)
            self.rossler.step(dt)

    def _render(self, n):
        p = self.params
        t = (self.sample_clock + np.arange(n)) / SR
        self.sample_clock += n

        # --- physics ---
        L = self.lorenz.normalized()
        R = self.rossler.normalized()

        # --- 1. Schumann ---
        # 7.83 Hz fundamental, chaos-modulated frequency
        sch_freq = 7.83 + 2.5 * L[0] + 1.2 * R[1]
        sch_phase_inc = 2 * np.pi * sch_freq / SR
        self.schumann_phase += sch_phase_inc * n
        sch_phase = self.schumann_phase + 2 * np.pi * sch_freq * np.arange(n) / SR
        schumann = np.sin(sch_phase)
        schumann += 0.4 * np.sin(2 * sch_phase)
        schumann += 0.25 * np.sin(3 * sch_phase)
        schumann += 0.15 * np.sin(4 * sch_phase)
        # add noise that grows with chaos
        schumann += 0.3 * abs(L[2]) * np.random.randn(n)
        schumann *= p["schumann_gain"]

        # --- 2. Seismic ---
        seismic = bandpass_chunk(n, 8, 45)
        tremor = 0.6 + 0.4 * np.sin(2 * np.pi * (1.5 + L[0]) * t) * \
                 (0.7 + 0.3 * np.sin(2 * np.pi * (0.3 + 0.1 * R[0]) * t))
        seismic *= tremor * p["seismic_gain"]

        # --- 3. Turbulence (hurricane) ---
        turb = pink_chunk(n)
        gust = 0.5 + 0.3 * np.sin(2 * np.pi * (0.15 + 0.05 * L[1]) * t) + \
               0.2 * np.sin(2 * np.pi * (0.47 + 0.1 * R[2]) * t)
        turb *= gust * p["turbulence_gain"]

        # --- 4. Volcanic (Poisson) ---
        volcanic = np.zeros(n)
        # spawn new events
        expected = p["volcanic_rate"] * n / SR
        n_new = np.random.poisson(expected)
        for _ in range(n_new):
            pos = np.random.randint(0, n)
            energy = np.random.uniform(0.5, 1.5)
            length = int(SR * np.random.uniform(0.3, 1.5))
            if pos + length > n:
                length = n - pos
            env = np.exp(-np.linspace(0, 8, length))
            burst = np.random.randn(length) * env * energy
            sub = np.sin(2 * np.pi * 35 * np.arange(length) / SR) * env * energy * 0.7
            volcanic[pos:pos+length] += burst + sub

        # --- 5. Flood hiss ---
        flood = bandpass_chunk(n, 7000, 15000) * p["flood_gain"]

        # --- 6. Twin phoneme engines ---
        # update twin lock: increases when chaos is low
        chaos_mag = abs(L[0]) + abs(L[1]) + abs(L[2])
        self.twin_lock = 0.7 * self.twin_lock + 0.3 * max(0.0, 1.0 - chaos_mag / 2.0)
        twin = np.zeros(n)
        tt = np.arange(n) / SR
        for k, c in enumerate(DESTRUCTION_ROOTS[self.twin_root_idx % len(DESTRUCTION_ROOTS)][:3]):
            if c not in LETTER_INDEX:
                continue
            fA = 55.0 * (2.0 ** (LETTER_INDEX[c] / 7.0))
            # B detunes less as lock increases
            detune = 0.08 * (1.0 - self.twin_lock)
            fB = fA * (1.0 + detune)
            phaseA = 2 * np.pi * fA * t + self.twin_phase[k]
            phaseB = 2 * np.pi * fB * t + self.twin_phase[k + 3]
            envA = 0.5 + 0.5 * np.sin(2 * np.pi * 0.5 * t + k)
            envB = 0.5 + 0.5 * np.sin(2 * np.pi * 0.5 * t + k + 1.5)
            twin += (np.sin(phaseA) * envA + np.sin(phaseB) * envB) * 0.3
        twin *= p["twin_gain"]
        # rotate root
        if self.sample_clock % (SR * 3) < n:
            self.twin_root_idx += 1
        for k in range(6):
            self.twin_phase[k] += 2 * np.pi * 200 * n / SR

        # --- 7. Cracks (Poisson) ---
        cracks = np.zeros(n)
        n_cracks = np.random.poisson(p["crack_rate"] * n / SR)
        for _ in range(n_cracks):
            pos = np.random.randint(0, n)
            length = int(SR * np.random.uniform(0.02, 0.15))
            if pos + length > n:
                length = n - pos
            env = np.exp(-np.linspace(0, 12, length))
            crack = np.random.randn(length) * env
            crack[:min(10, length)] *= 3.0
            cracks[pos:pos+length] += crack

        # --- 8. Global swell ---
        swell = 1.0 - p["swell_depth"] * 0.5 * (1.0 + np.sin(2 * np.pi * 0.02 * t))

        # --- mix ---
        mix = (schumann + seismic + turb + volcanic + flood + twin + cracks)
        mix *= swell

        # saturation
        mix = np.tanh(mix * p["saturation"])

        # normalize smoothly (running peak)
        peak = np.max(np.abs(mix)) + 1e-6
        mix = mix / max(peak, 0.5) * 0.95

        return mix

    def state_snapshot(self):
        L = self.lorenz.normalized()
        R = self.rossler.normalized()
        return {
            "sample_clock": self.sample_clock,
            "lorenz": L.tolist(),
            "rossler": R.tolist(),
            "twin_lock": float(self.twin_lock),
            "params": self.params,
        }

    def run(self):
        print(">> Live Destruction Engine online", file=sys.stderr, flush=True)
        last_state = time.time()
        try:
            while True:
                chunk = self._render(CHUNK)
                int16 = (np.clip(chunk, -1.0, 1.0) * 32767).astype(np.int16)
                stereo = np.stack([int16, int16], axis=1)
                sys.stdout.buffer.write(stereo.tobytes())
                sys.stdout.buffer.flush()

                # write state every second for the AI advisor
                if time.time() - last_state > 1.0:
                    STATE_FILE.write_text(json.dumps(self.state_snapshot(), indent=2))
                    last_state = time.time()
                    # reload params if the AI changed them
                    self.params = load_params()

                self._step_physics()
        except (KeyboardInterrupt, BrokenPipeError):
            sys.exit(0)


if __name__ == "__main__":
    LiveDestruction().run()
