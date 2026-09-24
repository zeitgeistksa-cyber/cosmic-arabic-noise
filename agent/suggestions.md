# Code Suggestions

_Generated 20260924_031212_

**TODO List**

[ ] **P0** Implement robust fallback for missing roots file in `dialogue_engine.load_roots` – gracefully handle `roots.txt` absence and log a clear warning.  
[ ] **P0** Add unit tests for `root_semantics.letter_semantic` to confirm all 8 semantic axes stay within [0, 1] bounds.  
[ ] **P0** Fix missing imports in `root_semantics.py` – import `MAKHRAJ`, `VOICED`, `EMPHATIC`, and `MANNER` from `phoneme_grammar`.  
[ ] **P0** Implement caching of pre‑computed root semantic vectors in `root_semantics.precompute` to avoid repeated calculations.  
[ ] **P0** Ensure `universal_rhythm_lfo` handles negative time inputs gracefully by clamping or normalising `t`.  
[ ] **P0** Add an `__all__` export list in `root_semantics.py` for public functions.  
[ ] **P1** Add a command‑line interface to `dialogue_engine.py` to run a single dialogue turn or a quick test mode.  
[ ] **P1** Implement graceful shutdown handling (SIGTERM/SIGINT) in `keep_running.sh` or the main process.  
[ ] **P1** Provide fallback behavior in `cosmic_semantics.cosmic_semantic_vector` when `CosmicDriver.poll()` fails or returns `None`.  
[ ] **P1** Optimize history handling in `cosmic_semantics` by reusing a NumPy array instead of reallocating every call.  
[ ] **P2** Add a descriptive docstring to `extract_roots.py` explaining the input root format and output.  
[ ] **P2** Ensure `phoneme_table.PHONEME_LETTERS` is correctly defined and exported.  
[ ] **P2** Add missing imports for `root_semantic` and `precompute` in `dialogue_engine.py`.  
[ ] **P2** Log the selected root and its cosine similarity score to the telemetry JSONL file.  
[ ] **P2** Add a dependency check for `numpy` in the project's `requirements.txt` or CI configuration.  

---

### Top‑3 Code Changes

#### 1. `dialogue_engine.py` – Robust fallback for missing roots file

**Why:** Prevents crashes and ensures the engine continues running even if the roots database is absent.

```python
def load_roots():
    txt = Path("arabic_db/roots.txt")
    if txt.exists():
        lines = [ln.strip() for ln in txt.read_text(encoding="utf-8").splitlines()]
        valid = [r for r in lines if len(r) == 3 and all(c in PHONEMES for c in r)]
        if valid:
            print(f"[dialogue] loaded {len(valid)} roots", file=sys.stderr, flush=True)
            return valid
        print("[dialogue] roots file found but no valid roots parsed", file=sys.stderr)
    else:
        print("[dialogue] roots file missing; using empty root list", file=sys.stderr)
    return []  # safe fallback
```

---

#### 2. `root_semantics.py` – Add missing imports

**Why:** `MAKHRAJ`, `VOICED`, `EMPHATIC`, and `MANNER` are required for semantic calculation; missing imports cause a runtime NameError.

```python
from phoneme_grammar import MAKHRAJ, VOICED, EMPHATIC, MANNER
```

Add this line near the existing imports:

```python
import numpy as np
from phoneme_table import PHONEMES
# ───────────────────────────────────────────────────────
# NEW IMPORTS
from phoneme_grammar import MAKHRAJ, VOICED, EMPHATIC, MANNER
```

---

#### 3. `root_semantics.py` – Cache pre‑computed root semantic vectors

**Why:** Re‑computing the 8‑dimensional vector for every root on each dialogue turn is wasteful; caching improves performance.

```python
# Module‑level cache for root semantic vectors
_root_semantic_cache = {}

def precompute(root: str):
    """Return the 8‑dimensional semantic vector for a root, using cache."""
    if root in _root_semantic_cache:
        return _root_semantic_cache[root]
    vector = np.array([letter_semantic(ch) for ch in root]).mean(axis=0)
    _root_semantic_cache[root] = vector
    return vector
```

Replace the existing `precompute` implementation (if any) with the above snippet, ensuring that `letter_semantic` remains unchanged. This change guarantees that each unique root is computed only once during the program’s lifetime.