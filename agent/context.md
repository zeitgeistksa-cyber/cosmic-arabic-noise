# Project Brief

Repository: cosmic-arabic-noise

A self-evolving neural noise engine driven by Arabic phoneme acoustics, live cosmic data (Schumann resonance, solar wind, Kp index), and the universal 2 Hz communication rhythm. The engine speaks Arabic roots as structured noise in dialogue with live space-weather data.

## Files

- .gitignore  (179B)
- README.md  (1390B)
- agent/log.jsonl  (130B)
- agent_orchestrator.py  (15317B)
- arabic_noise_engine.py  (12589B)
- autonomous_dev.py  (4560B)
- cosmic_data.py  (3912B)
- cosmic_driver.py  (1937B)
- cosmic_semantics.py  (1901B)
- dashboard.sh  (1331B)
- dialogue_engine.py  (12247B)
- export.sh  (1171B)
- extract_roots.py  (1644B)
- import.sh  (628B)
- main  (0B)
- patch_cosmic_engine.py  (2018B)
- phoneme_grammar.py  (2614B)
- phoneme_table.py  (1611B)
- proposals/proposal_20260924_002539.md  (468B)
- proposals/proposal_20260924_003219.md  (467B)
- proposals/proposal_20260924_003419.md  (467B)
- proposals/proposal_20260924_003619.md  (467B)
- proposals/proposal_20260924_003819.md  (467B)
- proposals/proposal_20260924_004019.md  (467B)
- proposals/proposal_20260924_004219.md  (467B)
- proposals/proposal_20260924_004412.md  (466B)
- proposals/proposal_20260924_004421.md  (465B)
- proposals/proposal_20260924_004622.md  (467B)
- proposals/proposal_20260924_004823.md  (467B)
- proposals/proposal_20260924_005025.md  (467B)
- proposals/proposal_20260924_005652.md  (3474B)
- proposals/proposal_20260924_005854.md  (187B)
- proposals/proposal_20260924_010100.md  (187B)
- proposals/proposal_20260924_010302.md  (467B)
- proposals/proposal_20260924_010545.md  (3604B)
- proposals/proposal_20260924_010747.md  (187B)
- proposals/proposal_20260924_010948.md  (467B)
- proposals/proposal_20260924_011212.md  (3066B)
- proposals/proposal_20260924_011427.md  (3457B)
- proposals/proposal_20260924_011651.md  (2729B)

## Source Code

### dialogue_engine.py
```python
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
        cosmic_vec = cosmic_vec_full[:8]  # compare only first 8 dims to root vectors

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
            "turn": self.t
... (truncated)

```

### phoneme_table.py
```python
"""Arabic letter acoustic fingerprints.
Each letter maps to [F1/1000, F2/1000, F3/1000, NoiseCoG/8000] in Hz/1000."""
PHONEMES = {
    "ا": [0.75, 1.30, 2.50, 0.00],
    "ب": [0.35, 1.10, 2.30, 0.10],
    "ت": [0.40, 1.70, 2.60, 0.56],
    "ث": [0.38, 1.60, 2.50, 0.75],
    "ج": [0.35, 1.90, 2.60, 0.44],
    "ح": [0.60, 1.20, 2.40, 0.19],
    "خ": [0.50, 1.00, 2.30, 0.28],
    "د": [0.35, 1.70, 2.60, 0.06],
    "ذ": [0.35, 1.60, 2.50, 0.69],
    "ر": [0.50, 1.30, 2.40, 0.15],
    "ز": [0.35, 1.70, 2.60, 0.81],
    "س": [0.40, 1.70, 2.60, 0.94],
    "ش": [0.40, 1.90, 2.60, 0.50],
    "ص": [0.45, 1.10, 2.40, 0.63],
    "ض": [0.40, 1.10, 2.40, 0.38],
    "ط": [0.40, 1.10, 2.40, 0.25],
    "ظ": [0.40, 1.10, 2.40, 0.60],
    "ع": [0.60, 1.10, 2.40, 0.18],
    "غ": [0.50, 1.00, 2.30, 0.25],
    "ف": [0.40, 1.20, 2.40, 0.88],
    "ق": [0.45, 0.90, 2.20, 0.23],
    "ك": [0.40, 1.60, 2.50, 0.31],
    "ل": [0.40, 1.20, 2.60, 0.00],
    "م": [0.30, 1.10, 2.20, 0.00],
    "ن": [0.30, 1.60, 2.50, 0.00],
    "ه": [0.50, 1.40, 2.40, 0.38],
    "و": [0.35, 0.80, 2.20, 0.00],
    "ي": [0.30, 2.20, 2.90, 0.00],
}
LETTER_INDEX = {ch: i + 1 for i, ch in enumerate(PHONEMES.keys())}
PHONEME_LETTERS = set(PHONEMES.keys())

def root_to_log_triad(root):
    """Map 3-letter root to logarithmic frequency triad (Hz)."""
    if len(root) != 3:
        return None
    try:
        i1, i2, i3 = (LETTER_INDEX[c] for c in root)
    except KeyError:
        return None
    return (55.0 * (2.0 ** (i1 / 7.0)),
            110.0 * (3.0 ** (i2 / 9.0)),
            220.0 * (5.0 ** (i3 / 11.0)))

```

### phoneme_grammar.py
```python
#!/usr/bin/env python3
"""
Arabic phoneme grammar.
Maps each letter to 4 structural axes:
  axis 0: makhraj position  (0 = glottal/back, 1 = labial/front)
  axis 1: voicing           (0 = voiceless, 1 = voiced)
  axis 2: emphasis          (0 = plain, 1 = pharyngealized)
  axis 3: manner            (0=stop, 1=fricative, 0.5=nasal/lateral/trill/glide)
"""
from phoneme_table import PHONEMES, LETTER_INDEX

# makhraj position from back (0) to front (1)
MAKHRAJ = {
    "ء": 0.00, "ه": 0.05, "ع": 0.10, "ح": 0.15,
    "ق": 0.25, "غ": 0.25, "خ": 0.28,
    "ك": 0.35,
    "ج": 0.45, "ش": 0.50, "ي": 0.55,
    "ت": 0.65, "د": 0.65, "ط": 0.65, "ض": 0.65,
    "س": 0.68, "ز": 0.68, "ص": 0.68, "ن": 0.68, "ل": 0.68, "ر": 0.68,
    "ث": 0.80, "ذ": 0.80, "ظ": 0.80,
    "ف": 0.90, "ب": 0.95, "م": 0.95, "و": 0.98,
}

VOICED = set("بج دذرزضظعغلمنوي".replace(" ", ""))
EMPHATIC = set("صضطظ")

# manner: 0 = stop, 1 = fricative, 0.5 = sonorant
MANNER = {}
for c in "بتدطضكقء":
    MANNER[c] = 0.0      # stops
for c in "ج":
    MANNER[c] = 0.75     # affricate
for c in "ثذزسشصضظفخغحع":
    MANNER[c] = 1.0      # fricatives
for c in "منلروي":
    MANNER[c] = 0.5      # sonorants
MANNER["ه"] = 1.0

def letter_vector(letter):
    """Return the 4-axis structural vector for one letter."""
    if letter not in PHONEMES:
        return (0.5, 0.5, 0.0, 0.5)
    return (
        MAKHRAJ.get(letter, 0.5),
        1.0 if letter in VOICED else 0.0,
        1.0 if letter in EMPHATIC else 0.0,
        MANNER.get(letter, 0.5),
    )

def root_grammar(root):
    """Return a 12-dim vector: 3 letters × 4 axes."""
    if len(root) != 3:
        return [0.5] * 12
    out = []
    for c in root:
        out.extend(letter_vector(c))
    return out

def prosody(root):
    """Return prosodic descriptors: syllable weights and voicing rhythm."""
    if len(root) != 3:
        return {"weights": [], "voicing": [], "emphasis": 0}
    weights = []
    for c in root:
        m = MANNER.get(c, 0.5)
        # stop = light (1), fricative = heavy (2), sonorant = superheavy (3)
        w = 1 if m == 0.0 else (3 if m == 0.5 else 2)
        weights.append(w)
    voicing = [1 if c in VOICED else 0 for c in root]
    emph = sum(1 for c in root if c in EMPHATIC)
    return {"weights": weights, "voicing": voicing, "emphasis": emph}

if __name__ == "__main__":
    import sys
    for r in ["ابت", "عرب", "كتب", "صبر", "نور", "صدق"]:
        p = prosody(r)
        print(f"{r}  weights={p['weights']}  voicing={p['voicing']}  emph={p['emphasis']}")

```

### root_semantics.py
```python
#!/usr/bin/env python3
"""Map each Arabic root to an 8-dim semantic vector derived from its phonemes."""
import numpy as np
from phoneme_table import PHONEMES
from phoneme_grammar import MAKHRAJ, VOICED, EMPHATIC, MANNER

def letter_semantic(letter):
    """Per-letter contribution to the 8 cosmic semantic axes."""
    if letter not in PHONEMES:
        return np.zeros(8)
    F1, F2, F3, CoG = PHONEMES[letter]
    back = 1.0 - MAKHRAJ.get(letter, 0.5)               # 1 = deep, 0 = front
    voice = 1.0 if letter in VOICED else 0.0
    emph = 1.0 if letter in EMPHATIC else 0.0
    manner = MANNER.get(letter, 0.5)

    # 8 semantic axes
    intensity   = 0.5 * emph + 0.5 * CoG                 # fricatives hiss
    coherence   = voice * (1.0 - manner)                 # stops are crisp
    expansion   = back                                   # deep = outward
    contraction = manner * (1.0 - back)                  # frontal fricatives
    harmony     = voice * (1.0 - abs(F2 - 1.5))          # centered formant
    turbulence  = CoG                                    # high CoG = hiss
    density     = 1.0 - manner                           # stops feel dense
    luminosity  = F3 / 3.0                               # bright formants
    return np.array([intensity, coherence, expansion,
                     contraction, harmony, turbulence,
                     density, luminosity])

def root_semantic(root):
    """Average the 3 letters' semantic vectors."""
    if len(root) != 3:
        return np.zeros(8)
    vs = [letter_semantic(c) for c in root]
    return np.mean(vs, axis=0)

def precompute(roots):
    """Return {root: vector} for a list of roots, normalized."""
    table = {}
    for r in roots:
        v = root_semantic(r)
        n = np.linalg.norm(v) + 1e-9
        table[r] = v / n
    return table

def cosine(a, b):
    a = np.asarray(a, dtype=np.float64); b = np.asarray(b, dtype=np.float64)
    na = np.linalg.norm(a) + 1e-9; nb = np.linalg.norm(b) + 1e-9
    return float(np.dot(a, b) / (na * nb))

if __name__ == "__main__":
    for r in ["ابت", "عرب", "كتب", "صبر", "نور", "صدق", "علم", "كون"]:
        v = root_semantic(r)
        print(f"{r}  " + " ".join(f"{x:.2f}" for x in v))

```

### cosmic_semantics.py
```python
#!/usr/bin/env python3
import numpy as np
from cosmic_driver import CosmicDriver
_history = []
_HISTORY_LEN = 20
def _norm(x, lo, hi):
    if hi <= lo: return 0.5
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))
def _safe(x, default): return default if x is None else x
def cosmic_semantic_vector(driver=None):
    if driver is None: driver = CosmicDriver(poll_interval=0)
    s = driver.poll()
    sch = _safe(s.get("schumann_score"), 50)
    kp = _safe(s.get("kp_value"), 2.0)
    wind = _safe(s.get("wind_speed"), 400)
    bz = _safe(s.get("bz"), 0.0)
    intensity   = _norm(sch, 0, 100)
    coherence   = 1.0 - _norm(kp, 0, 9)
    expansion   = _norm(wind, 250, 800)
    contraction = _norm(-bz, 0, 20)
    harmony     = 1.0 - abs(_norm(sch, 0, 100) - 0.5) * 2
    turbulence  = _norm(kp, 0, 9)
    density     = _norm(wind**2 / 1000, 60, 640)
    luminosity  = _norm(kp, 0, 9) ** 2
    _history.append((sch, kp, wind, bz))
    if len(_history) > _HISTORY_LEN: _history.pop(0)
    if len(_history) >= 5:
        h = np.array(_history[-5:], dtype=np.float64)
        d_int = float(np.tanh((h[-1,0]-h[0,0]) / 20.0))
        d_turb = float(np.tanh((h[-1,1]-h[0,1]) / 3.0))
        d_exp = float(np.tanh((h[-1,2]-h[0,2]) / 100.0))
        d_con = float(np.tanh(-(h[-1,3]-h[0,3]) / 5.0))
    else:
        d_int = d_turb = d_exp = d_con = 0.0
    return [intensity, coherence, expansion, contraction,
            harmony, turbulence, density, luminosity,
            d_int, d_turb, d_exp, d_con], s
if __name__ == "__main__":
    vec, raw = cosmic_semantic_vector()
    names = ["intensity","coherence","expansion","contraction",
             "harmony","turbulence","density","luminosity",
             "d_int","d_turb","d_exp","d_con"]
    for n, v in zip(names, vec):
        bar = "#" * int(abs(v) * 30)
        sign = "+" if v >= 0 else "-"
        print(f"{n:12s}  {sign}{abs(v):.3f}  {bar}")

```

### cosmic_driver.py
```python
#!/usr/bin/env python3
"""Cosmic driver: maps live space data to sonic engine parameters."""
import time, json
from cosmic_data import snapshot

class CosmicDriver:
    def __init__(self, poll_interval=60):
        self.poll_interval = poll_interval
        self.last_poll = 0
        self.state = {
            "schumann_score": 50,
            "kp_value": 2.0,
            "wind_speed": 400,
            "bz": 0.0,
            "energy": 0.5,
            "chaos_boost": 0.0,
            "sub_boost": 0.5,
        }

    def poll(self):
        now = time.time()
        if now - self.last_poll < self.poll_interval:
            return self.state
        self.last_poll = now
        try:
            s = snapshot()
            sch = s.get("schumann_score", 50)
            kp = s.get("kp_value", 2.0)
            wind = s.get("wind_speed", 400)
            bz = s.get("bz", 0.0)
            # Energy: normalized 0-1 from Schumann score
            energy = min(1.0, max(0.0, sch / 100.0))
            # Chaos boost: Kp index 0-9 -> 0-1
            chaos_boost = min(1.0, kp / 9.0)
            # Sub boost: fast solar wind -> more low-end
            sub_boost = min(1.0, max(0.0, (wind - 300) / 500.0))
            self.state.update({
                "schumann_score": sch,
                "kp_value": kp,
                "wind_speed": wind,
                "bz": bz,
                "energy": energy,
                "chaos_boost": chaos_boost,
                "sub_boost": sub_boost,
            })
        except Exception:
            pass
        return self.state

    def modulation_factor(self):
        """Return a scalar in [0.5, 2.0] for overall intensity."""
        s = self.state
        return 0.5 + 1.5 * (0.5 * s["energy"] + 0.5 * s["chaos_boost"])

if __name__ == "__main__":
    d = CosmicDriver(poll_interval=0)
    print(json.dumps(d.poll(), indent=2))
    print(f"modulation_factor = {d.modulation_factor():.3f}")

```

### cosmic_data.py
```python
#!/usr/bin/env python3
"""
Cosmic Data Fetcher
===================
Pulls live data from:
  - SunGeo.net: Schumann resonance, Kp index, solar wind
  - NOAA SWPC: real-time solar wind, Kp, X-ray flux
  - NASA DONKI: solar flares, CMEs, geomagnetic storms

All sources are free, no API keys. Results cached for 60s.
"""
import json, time, urllib.request, urllib.error
from pathlib import Path

CACHE_DIR = Path("cosmic_cache")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL = 60  # seconds

def _fetch(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "cosmic-noise/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8")
    except Exception as e:
        return None

def _cached(name, url):
    path = CACHE_DIR / f"{name}.json"
    if path.exists() and (time.time() - path.stat().st_mtime) < CACHE_TTL:
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    raw = _fetch(url)
    if raw is None:
        return None
    try:
        data = json.loads(raw)
        path.write_text(json.dumps(data))
        return data
    except json.JSONDecodeError:
        return None

def get_schumann():
    """Live Schumann resonance + Kp index from SunGeo.net."""
    return _cached("sungeo_current", "https://sungeo.net/api/current")

def get_schumann_history(days=7):
    """Daily Schumann score averages."""
    return _cached(f"sungeo_history_{days}",
                   f"https://sungeo.net/api/history?days={days}")

def get_solar_wind():
    """Real-time solar wind plasma from NOAA SWPC."""
    return _cached("noaa_solar_wind_plasma",
                   "https://services.swpc.noaa.gov/products/solar-wind/plasma-7-day.json")

def get_solar_wind_mag():
    """Real-time solar wind magnetic field from NOAA SWPC."""
    return _cached("noaa_solar_wind_mag",
                   "https://services.swpc.noaa.gov/products/solar-wind/mag-7-day.json")

def get_kp_index():
    """Real-time planetary K-index from NOAA SWPC."""
    return _cached("noaa_kp",
                   "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json")

def get_goes_xray():
    """GOES X-ray flux (solar flare activity) from NOAA SWPC."""
    return _cached("noaa_goes_xray",
                   "https://services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json")

def get_donki_flares(days=7):
    """NASA DONKI solar flares from the last N days."""
    end = time.strftime("%Y-%m-%d")
    start = time.strftime("%Y-%m-%d", time.localtime(time.time() - days*86400))
    url = (f"https://api.nasa.gov/DONKI/FLR?startDate={start}&endDate={end}"
           f"&api_key=DEMO_KEY")
    return _cached(f"donki_flares_{days}", url)

def get_donki_cme(days=7):
    """NASA DONKI coronal mass ejections from the last N days."""
    end = time.strftime("%Y-%m-%d")
    start = time.strftime("%Y-%m-%d", time.localtime(time.time() - days*86400))
    url = (f"https://api.nasa.gov/DONKI/CME?startDate={start}&endDate={end}"
           f"&api_key=DEMO_KEY")
    return _cached(f"donki_cme_{days}", url)

def snapshot():
    """Return a compact dict of current cosmic state."""
    out = {"ts": time.time()}
    sch = get_schumann()
    if sch:
        out["schumann_status"] = sch.get("status")
        out["schumann_score"] = sch.get("score")
        out["kp_value"] = sch.get("kp_value")
        out["kp_text"] = sch.get("kp_text")
        solar = sch.get("solar", {})
        out["wind_speed"] = solar.get("wind_speed")
        out["bz"] = solar.get("bz")
    kp = get_kp_index()
    if kp and isinstance(kp, list) and len(kp) > 1:
        out["kp_latest"] = kp[-1]
    xray = get_goes_xray()
    if xray and isinstance(xray, list) and len(xray) > 0:
        out["xray_latest"] = xray[-1]
    return out

if __name__ == "__main__":
    s = snapshot()
    print(json.dumps(s, indent=2))

```

### universal_rhythm.py
```python
"""Universal acoustic communication tempo band (0.5-4 Hz, centered at 2 Hz)."""
import numpy as np
RHYTHM_CENTER_HZ = 2.0
RHYTHM_BAND_LOW = 0.5
RHYTHM_BAND_HIGH = 4.0

def universal_rhythm_lfo(t):
    """Multi-harmonic LFO: 2 Hz + 0.5 Hz sub + 4 Hz octave."""
    return (0.60 * np.sin(2 * np.pi * RHYTHM_CENTER_HZ * t) +
            0.25 * np.sin(2 * np.pi * (RHYTHM_CENTER_HZ / 4) * t) +
            0.15 * np.sin(2 * np.pi * (RHYTHM_CENTER_HZ * 2) * t))

def rhythm_score(freq_hz):
    """Gaussian affinity to 2 Hz; zero outside 0.5-4 Hz."""
    if freq_hz < RHYTHM_BAND_LOW or freq_hz > RHYTHM_BAND_HIGH:
        return 0.0
    return float(np.exp(-0.5 * ((freq_hz - RHYTHM_CENTER_HZ) / 1.0) ** 2))

```

### train_gen.py
```python
#!/usr/bin/env python3
"""Evolutionary trainer with Arabic root diversity + universal rhythm scoring."""
import json, time, glob, numpy as np, os, shutil
from pathlib import Path
from universal_rhythm import rhythm_score

TELEMETRY_DIR = Path("telemetry"); BRAIN_DIR = Path("brains")
BRAIN_DIR.mkdir(exist_ok=True)
TOP_K, PERTURB_SIGMA, HYPER_NOISE = 5, 0.01, 0.15

def load_all_records():
    out = []
    for f in sorted(glob.glob(str(TELEMETRY_DIR / "session_*.jsonl"))):
        with open(f, encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line: continue
                try: out.append(json.loads(line))
                except json.JSONDecodeError: continue
    return out

def build_segments(records):
    records.sort(key=lambda r: (r.get("session",""), r.get("chunk",0)))
    segs, cm, cs = [], None, []
    for r in records:
        if r.get("type") == "mutation":
            if cm is not None: segs.append((cm, cs))
            cm, cs = r, []
        elif r.get("type") == "state" and cm is not None:
            cs.append(r)
    if cm is not None: segs.append((cm, cs))
    return segs

def score_segment(mut, states):
    if len(states) < 3: return 0.0
    e = np.array([s["entropy"] for s in states])
    me, se = float(np.mean(e)), float(np.std(e))
    dur = min(len(states), 40)/40.0
    evol = max(0.0, min(1.0, 1.0 - abs(se - 0.15)/0.35))
    roots = {s.get("current_root") for s in states}
    root_bonus = min(len(roots), 8)/8.0
    chunks = [s["chunk"] for s in states]
    if len(chunks) >= 2:
        span = (max(chunks)-min(chunks))*2048/44100
        rate = len(roots)/max(span, 1e-3)
        rhythm_bonus = rhythm_score(rate)
    else:
        rhythm_bonus = 0.0
    base = me*(0.5+0.5*evol)*(0.5+0.5*dur)*(0.7+0.3*root_bonus)
    return base*(0.8 + 0.2*rhythm_bonus)

def next_gen():
    gs = sorted(BRAIN_DIR.glob("gen_*.npz"),
                key=lambda p: int(p.stem.split("_")[1]))
    return 1 if not gs else int(gs[-1].stem.split("_")[1]) + 1

def wavg(brains, weights):
    w = np.array(weights, dtype=np.float64); w = w/(w.sum()+1e-12)
    out = {k: np.zeros_like(brains[0][k]) for k in ("W1","W2","W_out","theory_weights")}
    out["omega_0"] = out["coupling_k"] = 0.0
    for b, wi in zip(brains, w):
        for k in ("W1","W2","W_out","theory_weights"): out[k] += wi*b[k]
        out["omega_0"] += wi*b["omega_0"]; out["coupling_k"] += wi*b["coupling_k"]
    out["theory_weights"] /= (out["theory_weights"].sum()+1e-12)
    return out

def main():
    recs = load_all_records()
    print(f">> {len(recs)} records")
    segs = build_segments(recs)
    print(f">> {len(segs)} segments")
    scored = sorted(((score_segment(m,s), m, s) for m, s in segs if score_segment(m,s)>0),
                    key=lambda x: x[0], reverse=True)
    if not scored:
        print("!! No scored segments. Run engine longer."); return
    for i, (s, m, st) in enumerate(scored[:TOP_K]):
        roots = sorted({x.get("current_root") for x in st})
        print(f"   [{i+1}] score={s:.3f} chunk={m['chunk']} "
              f"omega0={m['omega_0']:.1f} k={m['coupling_k']:.2f} "
              f"roots={roots[:4]}{'...' if len(roots)>4 else ''}")
    winners = [x[1] for x in scored[:TOP_K]]
    scores = [x[0] for x in scored[:TOP_K]]
    brains = [{"W1": np.array(w["W1"]), "W2": np.array(w["W2"]),
               "W_out": np.array(w["W_out"]),
               "theory_weights": np.array(w["theory_weights"]),
               "omega_0": float(w["omega_0"]),
               "coupling_k": float(w["coupling_k"])} for w in winners]
    child = wavg(brains, scores)
    for k in ("W1","W2","W_out"): child[k] += np.random.randn(*child[k].shape)*PERTURB_SIGMA
    child["omega_0"] = float(np.clip(child["omega_0"]*(1+np.random.randn()*HYPER_NOISE), 15.0, 120.0))
    child["coupling_k"] = float(np.clip(child["coupling_k"]*(1+np.random.randn()*HYPER_NOISE), 0.05, 3.5))
    gen = next_gen()
    meta = {"generation": gen, "parent_generation": gen-1,
            "score": float(np.mean(scores)), "source": "telemetry_evolution",
            "num_parents": len(winners), "num_segments_analyzed": len(scored),
            "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    out = BRAIN_DIR / f"gen_{gen}.npz"
    np.savez_compressed(out, W1=child["W1"], W2=child["W2"], W_out=child["W_out"],
        theory_weights=child["theory_weights"],
        omega_0=np.float64(child["omega_0"]),
        coupling_k=np.float64(child["coupling_k"]), meta=json.dumps(meta))
    latest = BRAIN_DIR / "latest.npz"
    tmp = BRAIN_DIR / ".latest.tmp"
    try:
        if tmp.exists() or tmp.is_symlink(): tmp.unlink()
        os.symlink(out.name, tmp)
        os.replace(str(tmp), str(latest))
    except OSError:
        shutil.copyfile(out, latest)
    print(f">> Wrote {out} (gen {gen})  omega0={child['omega_0']:.2f}  k={child['coupling_k']:.2f}")

if __name__ == "__main__": main()

```

### autonomous_dev.py
```python
#!/usr/bin/env python3
"""
Autonomous Developer Loop
=========================
Every N seconds:
  1. Reads the latest telemetry summary
  2. Asks aichat for a code improvement suggestion
  3. Extracts any code block from the response
  4. Writes it to a proposals/ folder for review
  5. Logs everything to logs/autonomous.jsonl

The developer (you) reviews proposals and applies them manually,
or the loop can be extended to auto-apply with git commit.
"""
import json, time, subprocess, glob, os, re
from pathlib import Path
from datetime import datetime

PROPOSALS = Path("proposals"); PROPOSALS.mkdir(exist_ok=True)
LOGS = Path("logs"); LOGS.mkdir(exist_ok=True)
LOG_FILE = LOGS / "autonomous.jsonl"
INTERVAL = 120  # seconds between AI suggestions

def log(record):
    record["ts"] = time.time()
    record["time"] = datetime.now().isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(record, ensure_ascii=False) + "\n")

def latest_telemetry():
    files = sorted(glob.glob("telemetry/session_*.jsonl"), key=os.path.getmtime)
    if not files:
        return None
    return files[-1]

def telemetry_summary(path):
    """Read the last 200 lines and summarize."""
    lines = []
    with open(path, encoding="utf-8") as fp:
        for line in fp:
            lines.append(line)
    recent = lines[-200:]
    muts = 0; roots = set(); avg_ent = 0; n = 0
    for line in recent:
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("type") == "mutation":
            muts += 1
        elif r.get("type") == "state":
            avg_ent += r.get("entropy", 0)
            n += 1
            if r.get("current_root"):
                roots.add(r["current_root"])
    return {
        "recent_mutations": muts,
        "recent_states": n,
        "avg_entropy": avg_ent / n if n else 0,
        "distinct_roots": len(roots),
        "sample_roots": sorted(roots)[:10],
    }

def ask_ai(prompt, files=None):
    """Call aichat with the prompt and optional files."""
    cmd = ["aichat"]
    if files:
        for f in files:
            cmd.extend(["-f", f])
    cmd.append(prompt)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "!! aichat timed out"
    except Exception as e:
        return f"!! aichat error: {e}"

def extract_code_blocks(text):
    """Extract fenced code blocks from markdown."""
    return re.findall(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL)

def main():
    log({"event": "start", "interval": INTERVAL})
    print(f">> Autonomous developer loop running (interval={INTERVAL}s)")
    print(f">> Logs: {LOG_FILE}")
    print(f">> Proposals: {PROPOSALS}/")
    print(">> Ctrl+C to stop")
    iteration = 0
    while True:
        iteration += 1
        tel = latest_telemetry()
        if tel is None:
            print(">> No telemetry yet. Waiting...")
            time.sleep(INTERVAL)
            continue
        summary = telemetry_summary(tel)
        print(f"\n[{iteration}] Telemetry: {summary}")
        prompt = (
            f"You are an AI sound engineering assistant working on a live "
            f"neural noise engine driven by Arabic phoneme acoustics and cosmic data. "
            f"\n\nLatest telemetry summary:\n{json.dumps(summary, indent=2)}"
            f"\n\nSuggest ONE concrete code improvement to arabic_noise_engine.py "
            f"or train_gen.py. Be specific — name the function and the change. "
            f"Format: a short explanation, then a single fenced python code block "
            f"containing ONLY the new version of the function or block to replace."
        )
        response = ask_ai(prompt, files=["arabic_noise_engine.py", "train_gen.py"])
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        proposal_path = PROPOSALS / f"proposal_{ts}.md"
        proposal_path.write_text(
            f"# Proposal {ts}\n\n"
            f"## Telemetry\n\n```json\n{json.dumps(summary, indent=2)}\n```\n\n"
            f"## AI Response\n\n{response}\n",
            encoding="utf-8",
        )
        log({"event": "proposal", "iteration": iteration,
             "path": str(proposal_path), "summary": summary})
        print(f">> Proposal written: {proposal_path}")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log({"event": "stop"})
        print("\n>> Autonomous loop stopped.")

```

## Telemetry Digest
```json

{
  "session": "session_20260924_005046_dialogue.jsonl",
  "turns": 577,
  "decodes": 578,
  "distinct_roots": 22,
  "top_roots": [
    [
      "مطر",
      39
    ],
    [
      "قنط",
      36
    ],
    [
      "طرد",
      36
    ],
    [
      "نطق",
      34
    ],
    [
      "طمن",
      34
    ],
    [
      "ربط",
      32
    ],
    [
      "رطب",
      30
    ],
    [
      "قطن",
      29
    ],
    [
      "طرق",
      28
    ],
    [
      "بطر",
      27
    ]
  ],
  "last_cosmic": {
    "schumann_score": 38,
    "kp_value": 1.67,
    "wind_speed": 309,
    "bz": null
  },
  "last_5_roots": [
    "ردد",
    "قنط",
    "بطن",
    "قطط",
    "قطن"
  ]
}

```

## Git State
```

7cff461 Fix ط voicing classification, soften selection softmax
290aced Dialogue v4.1: acoustic fingerprint decode, dynamic cosmic derivatives, spread similarity
d2f6e84 Fix: None-safe cosmic semantics, dialogue history replay, gemini-3.6-flash, flush prints
46fb0a1 Dialogue engine v4.0: cosmic semantic vector ↔ Arabic root semantics
9bca5c3 Untrack runtime dirs (logs, cache, proposals) — covered by .gitignore
cff7f82 Cosmic gen 3 trained
2c60468 test push
4462df4 Add cosmic data fetcher, driver, autonomous dev loop, tmux dashboard
---
?? agent/
?? agent_orchestrator.py
?? run_orchestrator.sh

```

## Recent AI Proposals

### proposal_20260924_011651.md
# Proposal 20260924_011651

## Telemetry

```json
{
  "recent_mutations": 0,
  "recent_states": 0,
  "avg_entropy": 0,
  "distinct_roots": 0,
  "sample_roots": []
}
```

## AI Response

To resolve the zero-mutation bottleneck (`recent_mutations: 0` in telemetry) caused by an overly strict entropy variance threshold, update `_study` in `arabic_noise_engine.py`. Increasing the entropy variance threshold from `< 0.01` to `< 0.12` allows the engine to properly detect audio stasis, triggering adaptive mutations and logging brain states to telemetry.

```python
    def _study(self, chunk, root):
   

### proposal_20260924_011853.md
# Proposal 20260924_011853

## Telemetry

```json
{
  "recent_mutations": 8,
  "recent_states": 65,
  "avg_entropy": 9.756995391934998,
  "distinct_roots": 41,
  "sample_roots": [
    "\u0627\u0644\u0644",
    "\u0628\u0647\u062c",
    "\u062a\u0644\u0643",
    "\u062a\u064a\u0647",
    "\u062c\u0644\u0628",
    "\u062c\u0648\u0631",
    "\u062d\u062f\u062b",
    "\u062d\u0632\u0628",
    "\u062e\u0632\u0646",
    "\u062f\u0628\u0628"
  ]
}
```

## AI Response




### proposal_20260924_012056.md
# Proposal 20260924_012056

## Telemetry

```json
{
  "recent_mutations": 9,
  "recent_states": 67,
  "avg_entropy": 9.754562403925279,
  "distinct_roots": 38,
  "sample_roots": [
    "\u0627\u0628\u0648",
    "\u0627\u062b\u062b",
    "\u0627\u0645\u0648",
    "\u0628\u0639\u062b",
    "\u0628\u0647\u062c",
    "\u062a\u0644\u0648",
    "\u062c\u0644\u0628",
    "\u062d\u062f\u062b",
    "\u062d\u0632\u0646",
    "\u062e\u0648\u0636"
  ]
}
```

## AI Response



