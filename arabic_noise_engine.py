#!/usr/bin/env python3
"""Arabic Phoneme Noise Engine v3.2
16-dim latent (12 cosmic + 4 Arabic), rhythm-modulated, telemetry-enabled."""
import sys, os, json, time, random
import numpy as np
from pathlib import Path
from phoneme_table import PHONEMES, PHONEME_LETTERS, root_to_log_triad
from universal_rhythm import universal_rhythm_lfo

SR, CHUNK = 44100, 2048
ENGINE_VERSION = "3.2"
np.random.seed(42)

TELEMETRY_DIR = Path("telemetry"); BRAIN_DIR = Path("brains")
TELEMETRY_DIR.mkdir(exist_ok=True); BRAIN_DIR.mkdir(exist_ok=True)

class TelemetryLogger:
    def __init__(self):
        self.session_id = time.strftime("%Y%m%d_%H%M%S")
        self.path = TELEMETRY_DIR / f"session_{self.session_id}.jsonl"
        self.fp = open(self.path, "a")
    def log(self, r):
        r["ts"] = time.time(); r["session"] = self.session_id
        r["engine_version"] = ENGINE_VERSION
        self.fp.write(json.dumps(r, ensure_ascii=False) + "\n"); self.fp.flush()
    def close(self):
        try: self.fp.close()
        except: pass

class BrainManager:
    @staticmethod
    def latest_path():
        gens = sorted(BRAIN_DIR.glob("gen_*.npz"),
                      key=lambda p: int(p.stem.split("_")[1]))
        return gens[-1] if gens else None
    @staticmethod
    def load():
        p = BrainManager.latest_path()
        if p is None: return None
        try:
            d = np.load(p, allow_pickle=False)
            return {"W1": d["W1"], "W2": d["W2"], "W_out": d["W_out"],
                    "theory_weights": d["theory_weights"],
                    "omega_0": float(d["omega_0"]),
                    "coupling_k": float(d["coupling_k"]),
                    "meta": json.loads(str(d["meta"]))}
        except Exception as e:
            print(f"[brain] load failed: {e}", file=sys.stderr); return None
    @staticmethod
    def save(gen, W1, W2, W_out, tw, o0, ck, meta):
        path = BRAIN_DIR / f"gen_{gen}.npz"
        np.savez_compressed(path, W1=W1, W2=W2, W_out=W_out,
                            theory_weights=tw, omega_0=np.float64(o0),
                            coupling_k=np.float64(ck), meta=json.dumps(meta))
        latest = BRAIN_DIR / "latest.npz"
        tmp = BRAIN_DIR / ".latest.tmp"
        try:
            if tmp.exists() or tmp.is_symlink(): tmp.unlink()
            os.symlink(path.name, tmp)
            os.replace(str(tmp), str(latest))
        except OSError:
            import shutil; shutil.copyfile(path, latest)
        return path

def load_roots():
    txt = Path("arabic_db/roots.txt")
    if txt.exists():
        lines = [ln.strip() for ln in txt.read_text(encoding="utf-8").splitlines()]
        valid = [r for r in lines if len(r) == 3 and all(c in PHONEME_LETTERS for c in r)]
        if valid:
            print(f"[arabic] loaded {len(valid)} roots from {txt}", file=sys.stderr)
            return valid
    print("[arabic] no roots.txt — using 8 demo roots", file=sys.stderr)
    return ["ابت", "عرب", "كتب", "علم", "نور", "صوت", "كون", "روح"]

class ArabicNoiseEngine:
    def __init__(self, sr=SR):
        self.sr = sr
        self.sample_clock = 0
        self.chunk_counter = 0
        self.mutation_counter = 0
        self.last_mutation_chunk = 0
        self.session_start = time.time()
        self.logger = TelemetryLogger()

        self.chaos_state = np.array([0.1, 0.0, 0.1, 0.5], dtype=np.float64)
        self.n_oscillators = 8
        self.phases = np.random.uniform(0, 2 * np.pi, self.n_oscillators)
        self.native_freqs = np.array([27.5, 55.0, 110.0, 220.0, 440.0, 880.0, 1760.0, 3520.0])
        self.coupling_k = 0.5

        self.in_dim = 16
        self.hidden_dim = 32
        self.W1 = np.random.uniform(-0.1, 0.1, (self.in_dim, self.hidden_dim))
        self.W2 = np.random.uniform(-0.2, 0.2, (self.hidden_dim, self.hidden_dim))
        self.W_out = np.random.uniform(-0.2, 0.2, (self.hidden_dim, 2))

        self.theory_weights = np.array([0.25, 0.25, 0.25, 0.25])
        self.entropy_history = []
        self.omega_0 = 45.0

        self.roots = load_roots()
        self.current_root = random.choice(self.roots)
        self.root_period_chunks = int(SR * 2.5 / CHUNK)
        self.root_triad = root_to_log_triad(self.current_root)
        self.root_history = []

        brain = BrainManager.load()
        if brain is not None and brain["W1"].shape == (self.in_dim, self.hidden_dim):
            self.W1 = brain["W1"].astype(np.float64)
            self.W2 = brain["W2"].astype(np.float64)
            self.W_out = brain["W_out"].astype(np.float64)
            self.theory_weights = brain["theory_weights"].astype(np.float64)
            self.omega_0 = brain["omega_0"]
            self.coupling_k = brain["coupling_k"]
            self.inherited_gen = brain["meta"].get("generation", 0)
            print(f"[brain] inherited gen {self.inherited_gen}", file=sys.stderr)
        elif brain is not None:
            print(f"[brain] skip gen {brain['meta'].get('generation')} "
                  f"(shape mismatch)", file=sys.stderr)
            self.inherited_gen = 0
        else:
            self.inherited_gen = 0

        self.logger.log({"type": "session_start", "inherited_gen": self.inherited_gen,
                         "sr": self.sr, "chunk": CHUNK, "n_roots": len(self.roots),
                         "first_root": self.current_root})

    def _step_physics(self, dt=0.0005):
        x, y, z, w = self.chaos_state
        dx = 10.0*(y-x)+w; dy = x*(28.0-z)-y
        dz = x*y-(8.0/3.0)*z; dw = -0.5*x-0.1*w
        self.chaos_state += np.array([dx, dy, dz, dw])*dt
        pd = self.phases[:, None] - self.phases[None, :]
        inter = np.sum(np.sin(pd), axis=1)
        dp = 2*np.pi*self.native_freqs + (self.coupling_k/self.n_oscillators)*inter
        self.phases = np.mod(self.phases + dp*(CHUNK/self.sr), 2*np.pi)

    def _rotate_root(self):
        rhythm = universal_rhythm_lfo(
            np.array([self.chunk_counter * CHUNK / self.sr]))[0]
        period = max(8, int(self.root_period_chunks * (1.0 - 0.4 * rhythm)))
        if self.chunk_counter > 0 and self.chunk_counter % period == 0:
            self.current_root = random.choice(self.roots)
            self.root_triad = root_to_log_triad(self.current_root)
            self.root_history.append(self.current_root)
            self.logger.log({"type": "root_change", "chunk": self.chunk_counter,
                             "root": self.current_root,
                             "triad": list(self.root_triad) if self.root_triad else None})

    def _root_latent(self, cs, t):
        if self.root_triad is None:
            return np.zeros((cs, 4))
        f1, f2, f3 = self.root_triad
        rhythm_env = 0.7 + 0.3 * universal_rhythm_lfo(t)
        e1 = np.sin(2*np.pi*f1*t) * rhythm_env
        e2 = np.sin(2*np.pi*f2*t) * rhythm_env
        e3 = np.sin(2*np.pi*f3*t) * rhythm_env
        gm = np.cbrt(np.abs(e1*e2*e3) + 1e-9) * np.sign(e1*e2*e3)
        return np.stack([e1, e2, e3, gm], axis=-1)

    def _study(self, chunk, root):
        fm = np.abs(np.fft.rfft(chunk[:, 0])) + 1e-9
        pr = fm/np.sum(fm)
        ent = float(-np.sum(pr*np.log2(pr)))
        self.entropy_history.append(ent)
        if len(self.entropy_history) > 50: self.entropy_history.pop(0)
        if self.chunk_counter % 50 == 0:
            self.logger.log({"type": "state", "chunk": self.chunk_counter,
                "mutation_index": self.mutation_counter,
                "last_mutation_chunk": self.last_mutation_chunk,
                "entropy": ent, "entropy_var": float(np.var(self.entropy_history)),
                "chaos": self.chaos_state.tolist(),
                "theory_weights": self.theory_weights.tolist(),
                "omega_0": float(self.omega_0), "coupling_k": float(self.coupling_k),
                "current_root": root,
                "root_triad": list(self.root_triad) if self.root_triad else None,
                "W1_norm": float(np.linalg.norm(self.W1)),
                "W2_norm": float(np.linalg.norm(self.W2)),
                "Wout_norm": float(np.linalg.norm(self.W_out))})
        if len(self.entropy_history) >= 50 and np.var(self.entropy_history) < 0.01 \
                and (self.chunk_counter - self.last_mutation_chunk) > 400:
            self.logger.log({"type": "mutation", "chunk": self.chunk_counter,
                "mutation_index": self.mutation_counter,
                "entropy_before": float(np.mean(self.entropy_history)),
                "current_root": root,
                "W1": self.W1.tolist(), "W2": self.W2.tolist(),
                "W_out": self.W_out.tolist(),
                "theory_weights": self.theory_weights.tolist(),
                "omega_0": float(self.omega_0), "coupling_k": float(self.coupling_k)})
            self.W1 += np.random.randn(*self.W1.shape)*0.02
            self.W2 += np.random.randn(*self.W2.shape)*0.02
            self.theory_weights = np.random.dirichlet(np.ones(4))
            self.coupling_k = np.random.uniform(0.1, 2.5)
            self.omega_0 = np.random.uniform(20.0, 90.0)
            self.mutation_counter += 1
            self.last_mutation_chunk = self.chunk_counter

    def generate_chunk(self, cs):
        self._step_physics()
        self._rotate_root()
        t = (self.sample_clock + np.arange(cs))/self.sr
        self.sample_clock += cs; self.chunk_counter += 1
        cx, cy, cz, cw = self.chaos_state
        sub = np.sin(2*np.pi*(30.0+5.0*np.sin(0.1*t))*t)
        fm  = np.sin(2*np.pi*140.0*t + 4.0*np.sin(2*np.pi*63.3*t))
        sw  = np.sin(2*np.pi*(200.0+3000.0*(0.5+0.5*np.sin(0.05*t)))*t)
        pn  = np.random.randn(cs)*(0.5+0.5*np.sin(0.3*t))
        cosmic = np.stack([np.sin(2*np.pi*0.05*t),
            np.full(cs, cx/30.0), np.full(cs, cy/30.0), np.full(cs, cz/30.0),
            np.full(cs, np.sin(self.phases[0])),
            np.full(cs, np.sin(self.phases[2])),
            np.full(cs, np.sin(self.phases[4])),
            sub, fm, sw, pn,
            np.cos(2*np.pi*7.83*t)], axis=-1)
        arabic = self._root_latent(cs, t)
        latent = np.concatenate([cosmic, arabic], axis=-1)
        h1 = np.sin(self.omega_0*(latent @ self.W1))
        h2 = np.sin(self.omega_0*1.2*(h1 @ self.W2))
        ar = np.tanh(h2 @ self.W_out)
        ts = sub[:, None]*self.theory_weights[0]
        tf = fm[:, None]*self.theory_weights[1]
        tw = sw[:, None]*self.theory_weights[2]
        tn = pn[:, None]*self.theory_weights[3]*0.3
        ta = arabic[:, :3].mean(axis=-1, keepdims=True)*0.4*self.theory_weights[1]
        mixed = ar + (ts+tf+tw+tn+ta)
        sat = np.tanh(np.sin(mixed*2.5)*3.0)
        self._study(sat, self.current_root)
        mv = np.max(np.abs(sat)) + 1e-9
        fs = (sat/mv)*0.98
        return (np.clip(fs, -1.0, 1.0)*32767).astype(np.int16)

    def shutdown(self):
        self.logger.log({"type": "session_end", "chunk": self.chunk_counter,
                         "mutations": self.mutation_counter,
                         "runtime_sec": time.time()-self.session_start,
                         "roots_used": len(set(self.root_history))})
        self.logger.close()

def main():
    e = ArabicNoiseEngine()
    print(f"[engine {ENGINE_VERSION}] online :: gen {e.inherited_gen} "
          f":: roots={len(e.roots)} :: log={e.logger.path}", file=sys.stderr)
    try:
        while True:
            sys.stdout.buffer.write(e.generate_chunk(CHUNK).tobytes())
            sys.stdout.buffer.flush()
    except (KeyboardInterrupt, BrokenPipeError): pass
    finally: e.shutdown(); sys.exit(0)

if __name__ == "__main__": main()
