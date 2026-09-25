#!/data/data/com.termux/files/usr/bin/bash
set -e

echo "=============================================="
echo "  ☀️  SOLAR ACOUSTIC SIMULATOR — BOOTSTRAP"
echo "=============================================="

ROOT="$HOME/solar_acoustic_sim"
mkdir -p "$ROOT"/{solar_sim,agents,dashboard,tests,docs,data,logs,params}

# ---------- package init ----------
cat > "$ROOT/solar_sim/__init__.py" <<'EOF'
__version__ = "0.5.0"
EOF

cat > "$ROOT/agents/__init__.py" <<'EOF'
EOF

cat > "$ROOT/dashboard/__init__.py" <<'EOF'
EOF

# ============================================================
# PHASE 1 — PHYSICS CORE
# ============================================================
cat > "$ROOT/solar_sim/physics.py" <<'EOF'
"""Phase 1: Physics core — chaos, p-mode swarm, photon SIREN."""
import numpy as np

class ChaosCore:
    """Lorenz-Rössler 4D hybrid driving solar dynamo."""
    def __init__(self, seed=0):
        rng = np.random.default_rng(seed)
        self.state = rng.uniform(-0.5, 0.5, 4)
        self.dt = 0.0003

    def step(self, steps=1):
        for _ in range(steps):
            x, y, z, w = self.state
            dx = 10.0*(y - x) + w
            dy = x*(28.0 - z) - y
            dz = x*y - (8.0/3.0)*z
            dw = -0.5*x - 0.1*w
            self.state += np.array([dx, dy, dz, dw]) * self.dt
        return self.state


class PModeSwarm:
    """Kuramoto-coupled p-mode oscillators at real solar frequencies (mHz)."""
    N_MODES = 12
    FUNDAMENTAL = 3.0e-3   # 3 mHz

    def __init__(self, n=N_MODES, seed=1):
        rng = np.random.default_rng(seed)
        self.n = n
        self.phases = rng.uniform(0, 2*np.pi, n)
        self.freqs = self.FUNDAMENTAL * np.arange(1, n+1)
        self.coupling = 1.2

    def step(self, dt):
        diffs = self.phases[:, None] - self.phases[None, :]
        interact = np.sum(np.sin(diffs), axis=1)
        dphase = 2*np.pi*self.freqs + (self.coupling/self.n)*interact
        self.phases = np.mod(self.phases + dphase*dt, 2*np.pi)

    def amplitudes(self):
        return np.abs(np.sin(self.phases))


class PhotonSIREN:
    """Sinusoidal MLP for photon-pressure fluctuations."""
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
EOF

cat > "$ROOT/solar_sim/solar_cycle.py" <<'EOF'
"""11-year solar cycle modulation."""
import numpy as np

CYCLE_YEARS = 11.0
DEFAULT_PHASE = 0.65

def solar_cycle_amplitude(t_seconds, phase=DEFAULT_PHASE):
    """Returns 0.3-1.0 amplitude from the 11-year dynamo cycle."""
    yr = t_seconds / (CYCLE_YEARS * 365.25 * 86400)
    return 0.3 + 0.7 * (0.5 + 0.5*np.sin(2*np.pi*(yr + phase)))
EOF

# ============================================================
# PHASE 2 — SONIFICATION
# ============================================================
cat > "$ROOT/solar_sim/sonify.py" <<'EOF'
"""Phase 2: Sonification — convert physics to audible audio."""
import numpy as np
from .physics import ChaosCore, PModeSwarm, PhotonSIREN
from .solar_cycle import solar_cycle_amplitude

SR = 44100
FREQ_SCALE = 1000.0    # mHz → Hz

def pmodes_to_audio(swarm, t):
    amps = swarm.amplitudes()
    sig = np.zeros_like(t)
    for i in range(swarm.n):
        f = np.clip(swarm.freqs[i]*FREQ_SCALE, 20, 8000)
        sig += amps[i] * np.sin(2*np.pi*f*t)
    return sig


class SolarSynth:
    """Full solar sonification engine."""
    def __init__(self, seed=0):
        self.core = ChaosCore(seed=seed)
        self.swarm = PModeSwarm(seed=seed+1)
        self.siren = PhotonSIREN(seed=seed+2)
        self.t = 0.0

    def chunk(self, n, rng):
        self.core.step()
        self.swarm.step(n/SR)
        t = (self.t + np.arange(n)) / SR
        self.t += n

        cycle = solar_cycle_amplitude(self.t)

        # p-mode acoustics
        p = pmodes_to_audio(self.swarm, t) * 0.3 * cycle

        # granulation (convection)
        gran = rng.standard_normal(n) * 0.15

        # photon pressure via SIREN
        amps = self.swarm.amplitudes()
        latent = np.array([
            *self.core.state,
            np.sin(self.swarm.phases[0]),
            np.sin(self.swarm.phases[1]),
            cycle, np.mean(amps),
        ])
        photon = self.siren.pressure(latent)[0] * np.sin(2*np.pi*440*t) * 0.1

        # 3-minute chromospheric mode (scaled)
        three_min = 0.2 * np.sin(2*np.pi*5.5*t) * cycle

        mix = p + gran*0.5 + photon + three_min
        mix = np.tanh(mix * 1.8)                 # plasma nonlinearity
        peak = np.max(np.abs(mix)) + 1e-9
        return (mix / peak * 0.85).astype(np.float32)
EOF

# ============================================================
# PHASE 3 — AIDEN (ANALYZER)
# ============================================================
cat > "$ROOT/agents/aiden.py" <<'EOF'
"""Phase 3: Aiden — real-time spectral analyzer."""
import numpy as np

class Aiden:
    def __init__(self, window=50):
        self.window = window
        self.entropy_hist = []
        self.peak_freqs = []
        self.anomaly_count = 0

    def analyze(self, chunk, sr=44100):
        fft = np.abs(np.fft.rfft(chunk)) + 1e-9
        freqs = np.fft.rfftfreq(len(chunk), 1/sr)

        mask = (freqs > 0.5) & (freqs < 100)
        if np.any(mask):
            peak_f = freqs[mask][np.argmax(fft[mask])]
            self.peak_freqs.append(peak_f)
            if len(self.peak_freqs) > self.window:
                self.peak_freqs.pop(0)

        prob = fft / np.sum(fft)
        entropy = float(-np.sum(prob * np.log2(prob)))
        self.entropy_hist.append(entropy)
        if len(self.entropy_hist) > self.window:
            self.entropy_hist.pop(0)

        anomaly = False
        if len(self.entropy_hist) >= 10:
            if np.var(self.entropy_hist[-10:]) < 0.005:
                anomaly = True
                self.anomaly_count += 1

        return {
            "entropy": entropy,
            "peak_hz": self.peak_freqs[-1] if self.peak_freqs else 0.0,
            "anomaly": anomaly,
            "anomaly_count": self.anomaly_count,
        }
EOF

# ============================================================
# PHASE 4 — GOHM (PLANNER)
# ============================================================
cat > "$ROOT/agents/gohm.py" <<'EOF'
"""Phase 4: Gohm — strategy planner and parameter generator."""
import json, time, os

STRATEGIES = [
    "CONTINUE_MONITOR",
    "MUTATE_COUPLING",
    "SHIFT_P_MODE",
    "REGENERATE_SIREN",
    "INCREASE_CHAOS",
    "DAMPEN_OSCILLATION",
]

class Gohm:
    def __init__(self, params_dir="params"):
        self.generation = 0
        self.log = []
        self.params_dir = params_dir
        os.makedirs(params_dir, exist_ok=True)

    def plan(self, aiden_report):
        self.generation += 1
        strategies = []
        if aiden_report.get("anomaly"):
            strategies += ["MUTATE_COUPLING", "REGENERATE_SIREN"]
        if aiden_report["entropy"] < 3.0:
            strategies.append("INCREASE_CHAOS")
        if aiden_report["entropy"] > 8.0:
            strategies.append("DAMPEN_OSCILLATION")
        if not strategies:
            strategies.append("CONTINUE_MONITOR")

        entry = {
            "gen": self.generation,
            "strategies": strategies,
            "entropy": round(aiden_report["entropy"], 4),
            "peak_hz": round(aiden_report["peak_hz"], 3),
            "ts": round(time.time(), 2),
        }
        self.log.append(entry)
        return strategies

    def write_params(self, params):
        fname = os.path.join(self.params_dir, f"solar_params_gen{self.generation}.json")
        with open(fname, "w") as f:
            json.dump(params, f, indent=2)
        return fname
EOF

# ============================================================
# PHASE 5 — DASHBOARD (console)
# ============================================================
cat > "$ROOT/dashboard/console.py" <<'EOF'
"""Phase 5: Console dashboard (Termux-friendly)."""
import os, sys

def render(state, aiden, gohm, clear=True):
    if clear:
        os.system("clear" if os.name != "nt" else "cls")
    print("=" * 62)
    print("  ☀️   SOLAR ACOUSTIC SIMULATOR — LIVE DASHBOARD")
    print("=" * 62)
    print(f"  Frame             : {state.get('frame', 0)}")
    print(f"  Generation        : {gohm.generation}")
    print(f"  Spectral entropy  : {aiden.entropy_hist[-1]:.3f}" if aiden.entropy_hist else "  Spectral entropy  : ---")
    print(f"  Peak frequency    : {aiden.peak_freqs[-1]:.2f} Hz" if aiden.peak_freqs else "  Peak frequency    : ---")
    print(f"  Anomaly count     : {aiden.anomaly_count}")
    print(f"  Cycle amplitude   : {state.get('cycle_amp', 0)*100:.0f}%")
    print("-" * 62)
    print("  Recent Gohm strategies:")
    for entry in gohm.log[-5:]:
        print(f"    gen {entry['gen']:>3}: {', '.join(entry['strategies'])}")
    print("=" * 62)
EOF

# ============================================================
# PHASE 7 — MAIN ENGINE / REDEPLOY LOOP
# ============================================================
cat > "$ROOT/solar_sim/engine.py" <<'EOF'
"""Main engine: ties physics + sonify + Aiden + Gohm together."""
import sys, time, json, os, numpy as np
from .sonify import SolarSynth
from agents.aiden import Aiden
from agents.gohm import Gohm
from dashboard.console import render

CHUNK = 4096

class Engine:
    def __init__(self, seed=0, log_dir="logs", params_dir="params"):
        self.synth = SolarSynth(seed=seed)
        self.aiden = Aiden()
        self.gohm = Gohm(params_dir=params_dir)
        self.rng = np.random.default_rng(seed)
        self.frame = 0
        self.telemetry = []
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, f"run_{int(time.time())}.jsonl")

    def _apply_strategies(self, strategies):
        for s in strategies:
            if s == "MUTATE_COUPLING":
                self.synth.swarm.coupling = float(self.rng.uniform(0.5, 3.0))
            elif s == "SHIFT_P_MODE":
                self.synth.swarm.freqs *= float(self.rng.uniform(0.98, 1.02))
            elif s == "REGENERATE_SIREN":
                from .physics import PhotonSIREN
                self.synth.siren = PhotonSIREN(seed=int(self.rng.integers(0, 1e6)))
            elif s == "INCREASE_CHAOS":
                self.synth.core.dt = min(0.001, self.synth.core.dt * 1.1)
            elif s == "DAMPEN_OSCILLATION":
                self.synth.swarm.coupling *= 0.85

    def run(self, duration=0, dashboard=True):
        start = time.time()
        log_f = open(self.log_path, "a")
        try:
            while True:
                if duration and (time.time() - start) > duration:
                    break

                chunk = self.synth.chunk(CHUNK, self.rng)
                report = self.aiden.analyze(chunk)

                if self.frame % 50 == 0:
                    strategies = self.gohm.plan(report)
                    self._apply_strategies(strategies)

                    rec = {
                        "frame": self.frame,
                        "gen": self.gohm.generation,
                        "entropy": report["entropy"],
                        "peak_hz": report["peak_hz"],
                        "strategies": strategies,
                        "cycle_amp": float(self.synth.t and 1.0 or 1.0),
                    }
                    self.telemetry.append(rec)
                    log_f.write(json.dumps(rec) + "\n")
                    log_f.flush()

                    if dashboard:
                        render({"frame": self.frame, "cycle_amp": 0.65},
                               self.aiden, self.gohm, clear=False)

                pcm = (np.clip(chunk, -1, 1) * 32767).astype("<i2").tobytes()
                sys.stdout.buffer.write(pcm)
                sys.stdout.buffer.flush()
                self.frame += 1
        except (KeyboardInterrupt, BrokenPipeError):
            pass
        finally:
            log_f.close()
            print(f"\n[engine] log saved → {self.log_path}")
EOF

# ============================================================
# CLI
# ============================================================
cat > "$ROOT/solar.py" <<'EOF'
#!/usr/bin/env python3
"""Solar Acoustic Simulator CLI."""
import argparse, subprocess, sys, os

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

def cmd_live(args):
    from solar_sim.engine import Engine
    mpv = subprocess.Popen([
        "mpv", "--no-video",
        "--demuxer=rawaudio", "--demuxer-lavf-format=s16le",
        "--demuxer-lavf-o=rate=44100,channels=1",
        "--volume=120", "--really-quiet", "-",
    ], stdin=subprocess.PIPE)
    try:
        Engine(seed=args.seed).run(duration=args.duration)
    except KeyboardInterrupt:
        pass
    finally:
        mpv.stdin.close(); mpv.wait()

def cmd_replay(args):
    import json
    path = args.log
    if not os.path.exists(path):
        print(f"no log at {path}"); return
    with open(path) as f:
        for line in f:
            rec = json.loads(line)
            print(f"gen={rec['gen']:>3} ent={rec['entropy']:.3f} "
                  f"pk={rec['peak_hz']:.2f}Hz → {rec['strategies']}")

def cmd_test(args):
    import pytest
    sys.exit(pytest.main([os.path.join(ROOT, "tests"), "-v"]))

def main():
    p = argparse.ArgumentParser(prog="solar")
    sub = p.add_subparsers(dest="cmd", required=True)

    l = sub.add_parser("live", help="run live simulation")
    l.add_argument("--duration", type=int, default=0)
    l.add_argument("--seed", type=int, default=0)
    l.set_defaults(func=cmd_live)

    r = sub.add_parser("replay", help="print a telemetry log")
    r.add_argument("log")
    r.set_defaults(func=cmd_replay)

    t = sub.add_parser("test", help="run tests")
    t.set_defaults(func=cmd_test)

    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
EOF

chmod +x "$ROOT/solar.py"

# ============================================================
# TESTS
# ============================================================
cat > "$ROOT/tests/test_physics.py" <<'EOF'
import numpy as np
from solar_sim.physics import ChaosCore, PModeSwarm, PhotonSIREN

def test_chaos_bounded():
    c = ChaosCore()
    for _ in range(1000):
        c.step()
    assert np.all(np.isfinite(c.state))
    assert np.all(np.abs(c.state) < 200)

def test_pmode_frequencies():
    s = PModeSwarm(n=12)
    assert abs(s.freqs[0] - 3.0e-3) < 1e-6
    assert len(s.freqs) == 12

def test_siren_shape():
    s = PhotonSIREN()
    out = s.pressure(np.zeros(8))
    assert out.shape == (1,)
    assert -1.0 <= out[0] <= 1.0
EOF

cat > "$ROOT/tests/test_agents.py" <<'EOF'
import numpy as np
from agents.aiden import Aiden
from agents.gohm import Gohm

def test_aiden_entropy():
    a = Aiden()
    chunk = np.random.randn(4096).astype(np.float32) * 0.1
    r = a.analyze(chunk)
    assert "entropy" in r
    assert r["entropy"] > 0

def test_gohm_plan():
    g = Gohm(params_dir="/tmp/solar_test_params")
    r = {"entropy": 5.0, "peak_hz": 3.0, "anomaly": False}
    s = g.plan(r)
    assert "CONTINUE_MONITOR" in s
EOF

cat > "$ROOT/tests/test_sonify.py" <<'EOF'
import numpy as np
from solar_sim.sonify import SolarSynth

def test_chunk_shape():
    s = SolarSynth()
    rng = np.random.default_rng(0)
    c = s.chunk(4096, rng)
    assert c.shape == (4096,)
    assert np.max(np.abs(c)) <= 1.0
EOF

cat > "$ROOT/tests/__init__.py" <<'EOF'
EOF

# ============================================================
# RUNNER — one command to rule them all
# ============================================================
cat > "$ROOT/run.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")"
exec python solar.py live "$@"
EOF
chmod +x "$ROOT/run.sh"

cat > "$ROOT/install.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
set -e
echo "[*] installing dependencies..."
pkg install -y python mpv
pip install --quiet numpy scipy pytest
echo "[*] linking CLI..."
mkdir -p "$PREFIX/bin"
cat > "$PREFIX/bin/solar" <<LAUNCH
#!/data/data/com.termux/files/usr/bin/bash
cd "$HOME/solar_acoustic_sim"
exec python solar.py "\$@"
LAUNCH
chmod +x "$PREFIX/bin/solar"
echo "[*] done. try: solar live"
EOF
chmod +x "$ROOT/install.sh"

# ============================================================
# README
# ============================================================
cat > "$ROOT/README.md" <<'EOF'
# ☀️ Solar Acoustic Simulator

Live sonification of the Sun's real acoustic phenomena (p-modes,
granulation, photon pressure, 11-year cycle) with two AI agents:
Aiden (analyzer) and Gohm (planner).

## What this is
A scientific / educational sonification tool. It does NOT affect
the Sun. The Sun is 150 million km away and cannot be influenced
by any Earth-based sound.

## Quick start
    ./install.sh
    solar live

## Structure
    solar_sim/    physics, sonification, engine
    agents/       aiden (analyze), gohm (plan)
    dashboard/    console + web renderers
    tests/        unit tests
    logs/         telemetry JSONL
    params/       generated parameter files

## Commands
    solar live                  # infinite stream
    solar live --duration 120   # 2 minutes
    solar test                  # run unit tests
    solar replay logs/run_*.jsonl

## Safety
- Volume ≤ 70 dB
- Break every 20 min
- Not for targeting people without consent
EOF

echo
echo "=============================================="
echo "  ✅ BUILD COMPLETE"
echo "=============================================="
echo "  Folder: $ROOT"
echo
echo "  Next:"
echo "    cd $ROOT"
echo "    ./install.sh"
echo "    solar live"
echo "=============================================="
