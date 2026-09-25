import sys, os, json, time, numpy as np
from scipy.signal import butter, sosfilt

SR    = 44100
CHUNK = 4096
rng   = np.random.default_rng()

# ============================================================
# SOLAR PHYSICS CONSTANTS
# ============================================================
P_MODE_FREQ     = 3.0e-3        # 3 mHz fundamental
P_MODE_HARMONICS = 12            # observed p-mode ridges
CUTOFF_FREQ     = 5.3e-3        # acoustic cutoff (5.3 mHz)
SOLAR_CYCLE_YEARS = 11.0
SOLAR_CYCLE_PHASE = 0.65         # current cycle 25 phase

# ============================================================
# SOLAR PHYSICS ENGINE (three components)
# ============================================================
class SolarCore:
    """Lorenz-Rössler hybrid drives the solar dynamo / p-mode excitation."""
    def __init__(self):
        self.state = np.array([0.1, 0.0, 0.1, 0.3])
        self.dt = 0.0003

    def step(self):
        x, y, z, w = self.state
        dx = 10.0*(y-x) + w
        dy = x*(28.0-z) - y
        dz = x*y - (8.0/3.0)*z
        dw = -0.5*x - 0.1*w
        self.state += np.array([dx,dy,dz,dw]) * self.dt

class PModeSwarm:
    """Kuramoto swarm models coupled p-mode oscillators."""
    def __init__(self, n=12):
        self.n = n
        self.phases = rng.uniform(0, 2*np.pi, n)
        self.freqs = P_MODE_FREQ * (np.arange(1, n+1))
        self.coupling = 1.2

    def step(self, dt):
        diffs = self.phases[:,None] - self.phases[None,:]
        interact = np.sum(np.sin(diffs), axis=1)
        dphase = 2*np.pi*self.freqs + (self.coupling/self.n)*interact
        self.phases = np.mod(self.phases + dphase*dt, 2*np.pi)

    def amplitudes(self):
        return np.abs(np.sin(self.phases))

class PhotonSIREN:
    """SIREN MLP models photon pressure fluctuations."""
    def __init__(self, seed=13):
        r = np.random.default_rng(seed)
        self.W1 = r.normal(0, 0.3, (8, 16))
        self.W2 = r.normal(0, 0.3, (16, 16))
        self.Wo = r.normal(0, 0.3, (16, 1))
        self.omega = 45.0

    def pressure(self, latent):
        h1 = np.sin(self.omega * (latent @ self.W1))
        h2 = np.sin(self.omega * 1.2 * (h1 @ self.W2))
        return np.tanh(h2 @ self.Wo).flatten()

# ============================================================
# SOLAR CYCLE ENVELOPE (11-year modulation)
# ============================================================
def solar_cycle(t_seconds):
    """Returns amplitude 0.3-1.0 based on 11-year cycle."""
    phase = (t_seconds / (SOLAR_CYCLE_YEARS * 365.25 * 86400)) + SOLAR_CYCLE_PHASE
    return 0.3 + 0.7 * (0.5 + 0.5*np.sin(2*np.pi*phase))

# ============================================================
# AIDEN — Real-time spectral analyzer
# ============================================================
class Aiden:
    def __init__(self):
        self.entropy_hist = []
        self.peak_freqs = []
        self.anomaly_count = 0

    def analyze(self, chunk):
        fft = np.abs(np.fft.rfft(chunk))
        freqs = np.fft.rfftfreq(len(chunk), 1/SR)
        # find p-mode peaks (0-10 Hz range)
        mask = (freqs > 0.001) & (freqs < 10)
        if np.any(mask):
            peak_idx = np.argmax(fft[mask])
            peak_f = freqs[mask][peak_idx]
            self.peak_freqs.append(peak_f)
            if len(self.peak_freqs) > 20:
                self.peak_freqs.pop(0)
        # spectral entropy
        mag = fft + 1e-9
        prob = mag / np.sum(mag)
        entropy = float(-np.sum(prob * np.log2(prob)))
        self.entropy_hist.append(entropy)
        if len(self.entropy_hist) > 50:
            self.entropy_hist.pop(0)
        # anomaly detection
        if len(self.entropy_hist) > 10:
            if np.var(self.entropy_hist[-10:]) < 0.005:
                self.anomaly_count += 1
                return {"status": "STABLE", "entropy": entropy,
                        "peak_hz": self.peak_freqs[-1] if self.peak_freqs else 0,
                        "anomaly": True}
        return {"status": "ANALYZING", "entropy": entropy,
                "peak_hz": self.peak_freqs[-1] if self.peak_freqs else 0,
                "anomaly": False}

# ============================================================
# GOHM — Strategic planner / file generator
# ============================================================
class Gohm:
    def __init__(self):
        self.strategy_log = []
        self.generation = 0

    def plan(self, aiden_report):
        """Decide next strategy based on Aiden's analysis."""
        self.generation += 1
        strategies = []
        if aiden_report.get("anomaly"):
            strategies.append("MUTATE_COUPLING")
            strategies.append("SHIFT_P_MODE")
            strategies.append("REGENERATE_SIREN")
        if aiden_report["entropy"] < 3.0:
            strategies.append("INCREASE_CHAOS")
        if aiden_report["entropy"] > 8.0:
            strategies.append("DAMPEN_OSCILLATION")
        if not strategies:
            strategies.append("CONTINUE_MONITOR")
        entry = {"gen": self.generation, "strategies": strategies,
                 "entropy": aiden_report["entropy"],
                 "ts": round(time.time(), 2)}
        self.strategy_log.append(entry)
        return strategies

    def generate_file(self, gen, data):
        """Write a new parameter file for the next test."""
        fname = f"solar_params_gen{gen}.json"
        with open(fname, "w") as f:
            json.dump(data, f, indent=2)
        print(f"[GOHM] wrote {fname}")
        return fname

# ============================================================
# MAIN SOLAR SIMULATOR
# ============================================================
class SolarSimulator:
    def __init__(self):
        self.core = SolarCore()
        self.pmodes = PModeSwarm()
        self.siren = PhotonSIREN()
        self.aiden = Aiden()
        self.gohm = Gohm()
        self.t = 0
        self.telem = []

    def generate_chunk(self, n):
        # --- advance physics ---
        self.core.step()
        self.pmodes.step(n / SR)

        t = (self.t + np.arange(n)) / SR
        self.t += n

        # --- p-mode acoustic signal ---
        cycle_amp = solar_cycle(self.t)
        amps = self.pmodes.amplitudes()

        # each p-mode contributes a sine at its frequency
        p_signal = np.zeros(n)
        for i in range(self.pmodes.n):
            f = P_MODE_FREQ * (i+1) * 1000  # scale to audible
            f = np.clip(f, 20, 8000)
            p_signal += amps[i] * np.sin(2*np.pi*f*t)

        # --- granulation noise (convection) ---
        gran = rng.standard_normal(n) * 0.15

        # --- photon pressure from SIREN ---
        latent = np.array([self.core.state[0], self.core.state[1],
                           self.core.state[2], self.core.state[3],
                           np.sin(self.pmodes.phases[0]),
                           np.sin(self.pmodes.phases[1]),
                           cycle_amp, np.mean(amps)])
        photon = self.siren.pressure(latent)[0]
        photon_signal = photon * np.sin(2*np.pi*440*t) * 0.1

        # --- 3-minute oscillation component ---
        three_min_f = 5.5e-3 * 1000  # scale to audible ~5.5 Hz
        three_min = 0.2 * np.sin(2*np.pi*5.5*t) * cycle_amp

        # --- mix all solar components ---
        mix = (p_signal * 0.3 * cycle_amp
             + gran * 0.5
             + photon_signal
             + three_min)

        # --- saturation (solar plasma nonlinearity) ---
        mix = np.tanh(mix * 1.8)

        # --- normalize ---
        peak = np.max(np.abs(mix)) + 1e-9
        mix = mix / peak * 0.85

        return mix.astype(np.float32)

    def run(self, duration=0):
        """Main loop: generate, analyze, plan, regenerate."""
        start = time.time()
        frame = 0
        try:
            while True:
                if duration and (time.time() - start) > duration:
                    break

                chunk = self.generate_chunk(CHUNK)

                # AIDEN analyzes
                report = self.aiden.analyze(chunk)

                # GOHM plans every 50 chunks
                if frame % 50 == 0:
                    strategies = self.gohm.plan(report)

                    # execute strategies
                    if "MUTATE_COUPLING" in strategies:
                        self.pmodes.coupling = rng.uniform(0.5, 3.0)
                    if "SHIFT_P_MODE" in strategies:
                        self.pmodes.freqs *= rng.uniform(0.98, 1.02)
                    if "REGENERATE_SIREN" in strategies:
                        self.siren = PhotonSIREN(seed=int(time.time()) % 10000)
                    if "INCREASE_CHAOS" in strategies:
                        self.core.dt = min(0.001, self.core.dt * 1.1)
                    if "DAMPEN_OSCILLATION" in strategies:
                        self.pmodes.coupling *= 0.85

                    # log telemetry
                    telem = {
                        "frame": frame, "gen": self.gohm.generation,
                        "entropy": report["entropy"],
                        "peak_hz": report["peak_hz"],
                        "coupling": self.pmodes.coupling,
                        "cycle_amp": float(solar_cycle(self.t)),
                        "strategies": strategies,
                    }
                    self.telem.append(telem)
                    print(f"[AIDEN] ent={report['entropy']:.2f} "
                          f"pk={report['peak_hz']:.2f}Hz | "
                          f"[GOHM] {strategies}")

                # write PCM to stdout
                pcm = (np.clip(chunk, -1, 1)*32767).astype("<i2").tobytes()
                sys.stdout.buffer.write(pcm)
                sys.stdout.buffer.flush()
                frame += 1
        except (KeyboardInterrupt, BrokenPipeError):
            pass
        finally:
            # GOHM writes final report
            self.gohm.generate_file(
                self.gohm.generation,
                {"telem": self.telem[-10:] if self.telem else [],
                 "total_frames": frame})

if __name__ == "__main__":
    dur = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    SolarSimulator().run(dur)
