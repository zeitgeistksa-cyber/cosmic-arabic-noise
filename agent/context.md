# Project Brief

Repository: cosmic-arabic-noise

A self-evolving neural noise engine driven by Arabic phoneme acoustics, live cosmic data (Schumann resonance, solar wind, Kp index), and the universal 2 Hz communication rhythm. The engine speaks Arabic roots as structured noise in dialogue with live space-weather data.

## Files

- .gitignore  (187B)
- .nojekyll  (0B)
- .vercel/README.txt  (520B)
- .vercel/project.json  (124B)
- .vercelignore  (144B)
- README.md  (1517B)
- agent/context.md  (11588B)
- agent/explain.md  (1799B)
- agent/log.jsonl  (2378B)
- agent/nohup.log  (7625B)
- agent/plan.md  (7042B)
- agent/suggestions.md  (3906B)
- agent/tasks.md  (3899B)
- agent_orchestrator.py  (17339B)
- arabic_noise_engine.py  (12589B)
- autonomous_dev.py  (4560B)
- cosmic_data.py  (3912B)
- cosmic_driver.py  (1937B)
- cosmic_semantics.py  (1901B)
- dashboard.sh  (1331B)
- dialogue_engine.py  (12247B)
- export.sh  (1171B)
- export_snapshot.py  (2136B)
- extract_roots.py  (1644B)
- import.sh  (628B)
- index.html  (2663B)
- keep_running.sh  (176B)
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
    print("[dialogue] fallbac
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
PHONEME_LETTERS = se
... (truncated)

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
    luminosity  = F3 / 3.0   
... (truncated)

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
        d_exp = float(
... (truncated)

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
            sub_boost = min(1.0, max(0.0, (wind - 300) / 500.
... (truncated)

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

## Telemetry Digest
```json

{
  "session": "session_20260924_014738_dialogue.jsonl",
  "turns": 1263,
  "decodes": 1263,
  "distinct_roots": 42,
  "top_roots": [
    [
      "ضدد",
      335
    ],
    [
      "زبد",
      205
    ],
    [
      "ذبب",
      126
    ],
    [
      "ردد",
      77
    ],
    [
      "دبر",
      51
    ],
    [
      "برد",
      51
    ],
    [
      "بدر",
      46
    ],
    [
      "درر",
      36
    ],
    [
      "ندد",
      33
    ],
    [
      "برر",
      30
    ]
  ],
  "last_cosmic": {
    "schumann_score": 35,
    "kp_value": 1.67,
    "wind_speed": 304,
    "bz": null
  },
  "last_5_roots": [
    "ندد",
    "لبد",
    "برد",
    "بدر",
    "برد"
  ]
}

```

## Git State
```

f78e4dc P0: fix cosine clipping in root_semantics
99a9be2 Move viewer files to repo root for GitHub Pages
250e964 Force refresh for GitHub Pages dropdown
6ee72e8 snapshot: 2026-09-23T23:38:11Z
af98938 Point README at GitHub Pages viewer
30e74ce Remove vercel.json — using GitHub Pages instead
8dfc912 Tell Vercel to serve /public
bf3552b Add vercelignore to trim deploy size
---
M agent/log.jsonl
 M snapshot.json

```

## Recent AI Proposals

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




### proposal_20260924_012257.md
# Proposal 20260924_012257

## Telemetry

```json
{
  "recent_mutations": 7,
  "recent_states": 62,
  "avg_entropy": 9.757830237322025,
  "distinct_roots": 43,
  "sample_roots": [
    "\u0627\u0645\u0648",
    "\u0628\u062f\u0648",
    "\u0628\u0631\u0645",
    "\u0628\u0633\u0644",
    "\u0628\u0637\u0634",
    "\u0628\u0644\u0648",
    "\u062a\u0644\u0648",
    "\u062b\u0628\u0637",
    "\u062b\u0631\u0628",
    "\u062c\u0631\u0641"
  ]
}
```

## AI Response



