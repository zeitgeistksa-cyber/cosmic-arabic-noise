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
- agent/context.md  (11383B)
- agent/explain.md  (2290B)
- agent/log.jsonl  (2959B)
- agent/nohup.log  (7625B)
- agent/plan.md  (4847B)
- agent/suggestions.md  (4098B)
- agent/tasks.md  (4091B)
- agent_orchestrator.py  (17339B)
- analyze_cluster.py  (4678B)
- arabic_noise_engine.py  (12589B)
- autonomous_dev.py  (4560B)
- bz_fallback.py  (1517B)
- capture_per_root.py  (922B)
- compare_regimes.py  (898B)
- correlation_control.py  (1515B)
- cosmic_data.py  (5252B)
- cosmic_driver.py  (1937B)
- cosmic_semantics.py  (1525B)
- dashboard.sh  (1331B)
- dialogue_engine.py  (14155B)
- english_phoneme_table.py  (1685B)
- experiments/cosmic_semantics_v1_formula.py  (1901B)
- experiments/findings/correlation_control.txt  (548B)
- experiments/findings/english_attractor.txt  (1025B)
- experiments/findings/final_english.txt  (1025B)
- experiments/findings/final_patterns.txt  (4159B)
- experiments/findings/position_control.txt  (659B)
- experiments/patterns/20260924_032636.txt  (4159B)
- experiments/rebuild1/result_20260924_031721.txt  (2020B)
- experiments/root_semantics_v1_formula.py  (2246B)
- experiments/v1_formula/cosmic_semantics.py  (1901B)
- experiments/v1_formula/dialogue_engine.py  (12247B)
- experiments/v1_formula/root_semantics.py  (2246B)
- export.sh  (1171B)

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
"""
Root Semantics — Pure Acoustic Version (v2)
============================================
No formulas. No named axes. Every dimension is a raw number taken
directly from the Arabic phoneme table.

Each root becomes a 4-dimensional vector:
    [mean_F1, mean_F2, mean_F3, mean_CoG]

where the mean is taken across the 3 letters of the root.
This is the simplest possible acoustic representation.
If a cosmic state prefers specific roots, it must prefer them
on the basis of these raw numbers alone — no voice formula, no
manner penalty, nothing but formant and noise measurements.
"""
import numpy as np
from phoneme_table import PHONEMES


def letter_vector(letter):
    """Return the 4 raw acoustic values for one letter. No transformation."""
    if letter not in PHONEMES:
        return np.zeros(4, dtype=np.float64)
    F1, F2, F3, CoG = PHONEMES[letter]
    return np.array([F1, F2, F3, CoG], dtype=np.float64)


def root_semantic(root):
    """Return the 4-dim raw acoustic vector for a 3-letter root."""
    if len(root) != 3:
        return np.zeros(4, dtype=np.float64)
    vs = [letter_vector(c) for c in root]
    return np.mean(vs, axis=0)


def precompute(root
... (truncated)

```

### cosmic_semantics.py
```python
#!/usr/bin/env python3
"""
Cosmic Semantics — Raw Version (v2)
===================================
Four dimensions, each a raw live measurement scaled to [0,1]:

    [0] schumann_score / 100       — geomagnetic activity, 0-100
    [1] kp_value / 9               — planetary K-index, 0-9
    [2] (wind_speed - 200) / 600   — solar wind km/s, normalized
    [3] (bz + 20) / 40             — southward IMF, normalized

No named axes like "coherence" or "harmony". Just the numbers.
If a cosmic state is going to prefer specific roots, it must do so
through these 4 raw signals.
"""
import numpy as np
from cosmic_driver import CosmicDriver

_history = []
_HISTORY_LEN = 20


def _clamp01(x):
    return float(max(0.0, min(1.0, x)))


def cosmic_semantic_vector(driver=None):
    """Return a 4-dim raw vector plus the raw state dict."""
    if driver is None:
        driver = CosmicDriver(poll_interval=0)
    s = driver.poll()

    sch = s.get("schumann_score") or 50
    kp = s.get("kp_value") or 2.0
    wind = s.get("wind_speed") or 400
    bz = s.get("bz")
    if bz is None:
        bz = 0.0

    v = [
        _clamp01(sch / 100.0),
        _clamp01(kp / 9.0),
        _clamp01((wind - 200.0) / 6
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
  "session": "session_20260924_032934_dialogue.jsonl",
  "turns": 0,
  "decodes": 0,
  "distinct_roots": 0,
  "top_roots": [],
  "last_cosmic": null,
  "last_5_roots": []
}

```

## Git State
```

e101f0d Final pattern results with real Bz data
21e9eeb English attractor control result
5275c8a Corpus validation + controls + English table
57db359 Controls + corpus validation: engine has anti-Arabic phonetic attractor
f6b541e Position + correlation control tests
a35e2ba New sound: per-letter envelopes; new analysis: multi-pattern finder
d3815c7 Rebuild 1: pure acoustic vectors, raw cosmic, cluster test
f78e4dc P0: fix cosine clipping in root_semantics
---
M agent/log.jsonl
 M cosmic_data.py
 M snapshot.json
?? bz_fallback.py
?? patch_bz.py
?? patch_bz_v2.py

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



