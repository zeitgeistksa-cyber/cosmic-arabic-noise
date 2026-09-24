#!/usr/bin/env python3
"""
Dialogue Engine
===============
Speaks to the universe by choosing Arabic roots whose phoneme-derived
semantic vectors best match the current cosmic state.
"""
import sys, os, json, time, random
import numpy as np
from pathlib import Path
from phoneme_table import root_to_log_triad, PHONEMES
from phoneme_grammar import root_grammar, prosody
from cosmic_semantics import cosmic_semantic_vector
from root_semantics import root_semantic, precompute, cosine
from cosmic_driver import CosmicDriver
from universal_rhythm import universal_rhythm_lfo

SR, CHUNK = 44100, 2048
ENGINE_VERSION = "4.0-dialogue"

TELEMETRY_DIR = Path("telemetry"); BRAIN_DIR = Path("brains")
TELEMETRY_DIR.mkdir(exist_ok=True); BRAIN_DIR.mkdir(exist_ok=True)

# ---------- Load roots ----------
def load_roots():
    txt = Path("arabic_db/roots.txt")
    if txt.exists():
        lines = [ln.strip() for ln in txt.read_text(encoding="utf-8").splitlines()]
        valid = [r for r in lines if len(r) == 3 and all(c in PHONEMES for c in r)]
        if valid:
            print(f"[dialogue] loaded {len(valid)} roots", file=sys.stderr, flush=True)
            return valid
    print("[dialogue] fallback demo roots", file=sys.stderr, flush=True)
    return ["ابت", "عرب", "كتب", "علم", "نور", "صوت", "كون", "روح"]

# ---------- Spectrum decoder: what does the current output sound like? ----------
def decode_letter(spectrum_peak_hz):
    """Map a spectral peak to the closest Arabic letter by formant proximity."""
    best = "ا"; best_d = 1e9
    for c, (F1, F2, F3, CoG) in PHONEMES.items():
        d = abs(spectrum_peak_hz - F3 * 1000)
        if d < best_d:
            best_d = d; best = c
    return best

def acoustic_fingerprint(audio_chunk):
    """Report what the sound IS (spectral properties), not what letters it resembles."""
    mono = audio_chunk[:, 0].astype(np.float32)
    spec = np.abs(np.fft.rfft(mono)) + 1e-9
    freqs = np.fft.rfftfreq(len(mono), 1/SR)
    # Spectral centroid (Hz) -- where the "weight" of the sound sits
    centroid = float(np.sum(freqs * spec) / np.sum(spec))
    # Rolloff -- 85% of energy below this frequency
    cum = np.cumsum(spec) / np.sum(spec)
    rolloff = float(freqs[np.searchsorted(cum, 0.85)])
    # Roughness -- variance of the short-time envelope (0-1)
    env = np.abs(mono)
    rough = float(np.std(env) / (np.mean(env) + 1e-9))
    # Band label from centroid
    if centroid < 400:   band = "SUB"
    elif centroid < 1500: band = "LOW"
    elif centroid < 4000: band = "MID"
    elif centroid < 8000: band = "HIGH"
    else:                 band = "AIR"
    return f"{band}|c={centroid:.0f}Hz|r={rolloff:.0f}Hz|rough={rough:.2f}"

# Keep old name for compatibility
def acoustic_fingerprint(audio_chunk):
    """Report what the sound IS: band, centroid, rolloff, roughness."""
    mono = audio_chunk[:, 0].astype(np.float32)
    spec = np.abs(np.fft.rfft(mono)) + 1e-9
    freqs = np.fft.rfftfreq(len(mono), 1/SR)
    centroid = float(np.sum(freqs * spec) / np.sum(spec))
    cum = np.cumsum(spec) / np.sum(spec)
    rolloff = float(freqs[np.searchsorted(cum, 0.85)])
    env = np.abs(mono)
    rough = float(np.std(env) / (np.mean(env) + 1e-9))
    if centroid < 400:   band = "SUB"
    elif centroid < 1500: band = "LOW"
    elif centroid < 4000: band = "MID"
    elif centroid < 8000: band = "HIGH"
    else:                 band = "AIR"
    return f"{band}|c={centroid:.0f}Hz|r={rolloff:.0f}Hz|rough={rough:.2f}"

def acoustic_fingerprint(audio_chunk):
    """Report what the sound IS: band, centroid, rolloff, roughness."""
    mono = audio_chunk[:, 0].astype(np.float32)
    spec = np.abs(np.fft.rfft(mono)) + 1e-9
    freqs = np.fft.rfftfreq(len(mono), 1/SR)
    centroid = float(np.sum(freqs * spec) / np.sum(spec))
    cum = np.cumsum(spec) / np.sum(spec)
    rolloff = float(freqs[np.searchsorted(cum, 0.85)])
    env = np.abs(mono)
    rough = float(np.std(env) / (np.mean(env) + 1e-9))
    if centroid < 400:   band = "SUB"
    elif centroid < 1500: band = "LOW"
    elif centroid < 4000: band = "MID"
    elif centroid < 8000: band = "HIGH"
    else:                 band = "AIR"
    return f"{band}|c={centroid:.0f}Hz|r={rolloff:.0f}Hz|rough={rough:.2f}"

def decode_output(audio_chunk):
    return acoustic_fingerprint(audio_chunk)

# ---------- Dialogue engine ----------
class DialogueEngine:
    def __init__(self, sr=SR):
        self.sr = sr
        self.sample_clock = 0
        self.chunk_counter = 0
        self.turn_counter = 0
        self.session_start = time.time()

        self.logger_path = TELEMETRY_DIR / (
            f"session_{time.strftime('%Y%m%d_%H%M%S')}_dialogue.jsonl")
        self.logger_fp = open(self.logger_path, "a")

        # Physics
        self.chaos_state = np.array([0.1, 0.0, 0.1, 0.5], dtype=np.float64)
        self.phases = np.random.uniform(0, 2 * np.pi, 8)
        self.native_freqs = np.array([27.5, 55.0, 110.0, 220.0,
                                      440.0, 880.0, 1760.0, 3520.0])
        self.coupling_k = 0.5

        # Neural
        self.in_dim = 16
        self.hidden_dim = 32
        self.W1 = np.random.uniform(-0.1, 0.1, (self.in_dim, self.hidden_dim))
        self.W2 = np.random.uniform(-0.2, 0.2, (self.hidden_dim, self.hidden_dim))
        self.W_out = np.random.uniform(-0.2, 0.2, (self.hidden_dim, 2))
        self.theory_weights = np.array([0.25, 0.25, 0.25, 0.25])
        self.omega_0 = 45.0

        # Semantic layer
        self.roots = load_roots()
        self.root_vectors = precompute(self.roots)
        self.root_list = list(self.root_vectors.keys())
        self.cosmic = CosmicDriver(poll_interval=15)

        # Dialogue state
        self.current_root = random.choice(self.root_list)
        self.current_triad = root_to_log_triad(self.current_root)
        self.turn_chunks = 100                 # ~4.6 s per turn
        self.turn_start_chunk = 0
        self.turn_history = []

        self.log({"type": "session_start", "engine": ENGINE_VERSION,
                  "roots": len(self.roots)})

    def log(self, r):
        r["ts"] = time.time()
        r["chunk"] = self.chunk_counter
        self.logger_fp.write(json.dumps(r, ensure_ascii=False) + "\n")
        self.logger_fp.flush()

    def _step_physics(self, dt=0.0005):
        x, y, z, w = self.chaos_state
        dx = 10.0*(y-x)+w; dy = x*(28.0-z)-y
        dz = x*y-(8.0/3.0)*z; dw = -0.5*x-0.1*w
        self.chaos_state += np.array([dx, dy, dz, dw])*dt
        pd = self.phases[:, None] - self.phases[None, :]
        inter = np.sum(np.sin(pd), axis=1)
        dp = 2*np.pi*self.native_freqs + (self.coupling_k/8)*inter
        self.phases = np.mod(self.phases + dp*(CHUNK/self.sr), 2*np.pi)

    def _new_turn(self, chunk):
        """Called at the start of each dialogue turn."""
        # 1) Listen to the universe
        cosmic_vec_full, raw_state = cosmic_semantic_vector(self.cosmic)
        cosmic_vec = cosmic_vec_full  # 4-dim raw vector, matched to 4-dim root vectors

        # 2) Find the root whose semantics best match
        scored = [(cosine(cosmic_vec, self.root_vectors[r]), r)
                  for r in self.root_list]
        scored.sort(reverse=True)
        # 2b) Z-score the top to spread selection weights
        top = scored[:40]
        sims = np.array([s for s, _ in top])
        mean_s, std_s = sims.mean(), sims.std() + 1e-9
        z = (sims - mean_s) / std_s
        # Convert z-scores to weights via softmax-like scaling
        weights = np.exp(1.2 * z)   # soften: 3.0 was too sharp
        weights /= weights.sum()
        idx = np.random.choice(len(top), p=weights)
        sim, chosen = top[idx]

        self.current_root = chosen
        self.current_triad = root_to_log_triad(chosen)

        # 3) Grammar & prosody
        grammar = root_grammar(chosen)
        pros = prosody(chosen)

        self.turn_counter += 1
        self.turn_start_chunk = chunk

        entry = {
            "type": "turn",
            "turn": self.turn_counter,
            "root": chosen,
            "triad": list(self.current_triad) if self.current_triad else None,
            "similarity": float(sim),
            "prosody": pros,
            "cosmic_vec": [float(x) for x in cosmic_vec],
            "cosmic_raw": {k: raw_state.get(k) for k in
                           ("schumann_score", "kp_value", "wind_speed", "bz")},
        }
        self.turn_history.append(entry)
        self.log(entry)
        print(f"\n[turn {self.turn_counter}] universe={cosmic_vec[:3]}  "
              f"-> root={chosen}  (sim={sim:.3f})  "
              f"prosody={pros['weights']}", file=sys.stderr, flush=True)

    def _phoneme_latent(self, cs, t):
        """Build the 4-dim latent from the current root's triad, shaped by prosody."""
        if self.current_triad is None:
            return np.zeros((cs, 4))
        f1, f2, f3 = self.current_triad
        p = prosody(self.current_root)
        # Weight each letter channel by its prosodic weight
        w1, w2, w3 = [x / 3.0 for x in p["weights"]]
        rhythm = 0.7 + 0.3 * universal_rhythm_lfo(t)
        e1 = np.sin(2*np.pi*f1*t) * w1 * rhythm
        e2 = np.sin(2*np.pi*f2*t) * w2 * rhythm
        e3 = np.sin(2*np.pi*f3*t) * w3 * rhythm
        gm = np.cbrt(np.abs(e1*e2*e3) + 1e-9) * np.sign(e1*e2*e3)
        return np.stack([e1, e2, e3, gm], axis=-1)

    def generate_chunk(self, cs):
        self._step_physics()
        if self.chunk_counter - self.turn_start_chunk >= self.turn_chunks:
            self._new_turn(self.chunk_counter)
        t = (self.sample_clock + np.arange(cs)) / self.sr
        self.sample_clock += cs
        self.chunk_counter += 1

        # Position within current turn (0..1), per-sample
        turn_start_s = self.turn_start_chunk * CHUNK / self.sr
        turn_dur_s = self.turn_chunks * CHUNK / self.sr
        turn_pos = np.clip((t - turn_start_s) / turn_dur_s, 0.0, 1.0)

        cx, cy, cz, cw = self.chaos_state
        sub = np.sin(2*np.pi*(30.0+5.0*np.sin(0.1*t))*t)
        fm  = np.sin(2*np.pi*140.0*t + 4.0*np.sin(2*np.pi*63.3*t))
        sw  = np.sin(2*np.pi*(200.0+3000.0*(0.5+0.5*np.sin(0.05*t)))*t)
        pn  = np.random.randn(cs)*(0.5+0.5*np.sin(0.3*t))

        cosmic = np.stack([
            np.sin(2*np.pi*0.05*t),
            np.full(cs, cx/30.0), np.full(cs, cy/30.0), np.full(cs, cz/30.0),
            np.full(cs, np.sin(self.phases[0])),
            np.full(cs, np.sin(self.phases[2])),
            np.full(cs, np.sin(self.phases[4])),
            sub, fm, sw, pn,
            np.cos(2*np.pi*7.83*t),
        ], axis=-1)

        arabic = self._phoneme_latent(cs, t)
        latent = np.concatenate([cosmic, arabic], axis=-1)

        h1 = np.sin(self.omega_0*(latent @ self.W1))
        h2 = np.sin(self.omega_0*1.2*(h1 @ self.W2))
        ar = np.tanh(h2 @ self.W_out)   # SIREN texture

        # ---- Direct triad with per-letter envelopes ----
        triad_direct = np.zeros(cs)
        sub_perletter = np.zeros(cs)
        hiss_perletter = np.zeros(cs)

        if self.current_triad is not None and len(self.current_root) == 3:
            f1, f2, f3 = self.current_triad
            letters = list(self.current_root)

            # Triangular envelopes for three overlapping syllables
            def env_seg(pos, start, end):
                center = 0.5 * (start + end)
                half = 0.5 * (end - start) + 1e-9
                return np.maximum(0.0, 1.0 - np.abs(pos - center) / half)

            env1 = env_seg(turn_pos, 0.00, 0.42)
            env2 = env_seg(turn_pos, 0.29, 0.71)
            env3 = env_seg(turn_pos, 0.58, 1.00)

            triad_direct = (env1 * np.sin(2*np.pi*f1*t)
                            + env2 * np.sin(2*np.pi*f2*t)
                            + env3 * np.sin(2*np.pi*f3*t))

            # Per-letter character
            from phoneme_grammar import VOICED, EMPHATIC, MANNER

            def char(c):
                if c not in PHONEMES:
                    return 0.0, 0.0
                voice = 1.0 if c in VOICED else 0.0
                emph = 1.0 if c in EMPHATIC else 0.0
                manner = MANNER.get(c, 0.5)
                sub_gain = voice * (1.0 - manner) * 0.5 + emph * 0.3
                hiss_gain = manner * 0.4
                return sub_gain, hiss_gain

            s0, h0 = char(letters[0])
            s1, h1c = char(letters[1])
            s2, h2c = char(letters[2])

            sub_perletter = (s0 * env1 + s1 * env2 + s2 * env3) * sub
            hiss_perletter = (h0 * env1 + h1c * env2 + h2c * env3) * pn

        # ---- Final mix ----
        mixed = (ar * 0.10                    # SIREN texture, subtle
                 + triad_direct[:, None] * 0.85        # the phoneme triads
                 + sub_perletter[:, None] * 0.15       # per-letter sub thump
                 + hiss_perletter[:, None] * 0.10)     # per-letter hiss

        sat = np.tanh(np.sin(mixed*2.2)*2.8)
        mv = np.max(np.abs(sat)) + 1e-9
        fs = (sat / mv) * 0.98

        # Acoustic fingerprint
        if self.chunk_counter % 100 == 0:
            int16 = (np.clip(fs, -1.0, 1.0) * 32767).astype(np.int16)
            heard = decode_output(int16)
            self.log({"type": "decode", "heard": heard,
                      "intended_root": self.current_root})
            print(f"[decode] intended={self.current_root}  "
                  f"heard_as={heard}", file=sys.stderr, flush=True)

        return (np.clip(fs, -1.0, 1.0) * 32767).astype(np.int16)


    def shutdown(self):
        self.log({"type": "session_end", "turns": self.turn_counter,
                  "runtime_sec": time.time()-self.session_start})
        self.logger_fp.close()

def main():
    e = DialogueEngine()
    print(f"[dialogue {ENGINE_VERSION}] online :: "
          f"roots={len(e.roots)} :: log={e.logger_path}", file=sys.stderr, flush=True)
    try:
        while True:
            sys.stdout.buffer.write(e.generate_chunk(CHUNK).tobytes())
            sys.stdout.buffer.flush()
    except (KeyboardInterrupt, BrokenPipeError):
        pass
    finally:
        e.shutdown(); sys.exit(0)

if __name__ == "__main__":
    main()
