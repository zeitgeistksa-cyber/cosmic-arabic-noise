# Task List

_Generated 20260924_030552_

**TODO List**

```
[ ] [P0] Resolve dialogue_engine root loading fallback – complete the truncated error handling and provide a graceful fallback when roots.txt is missing or corrupted.
[ ] [P0] Ensure root_semantics precomputation runs on import – call the precompute routine at module load to cache semantic vectors for fast lookup.
[ ] [P0] Update train_gen.py to consume the newly cached root semantic vectors – modify the training pipeline to import and use root_semantic from root_semantics instead of recalculating each batch.
[ ] [P1] Add type hints to dialogue_engine functions – improve readability and IDE support.
[ ] [P1] Remove hard‑coded SR/CHUNK values from dialogue_engine – expose them as config parameters.
[ ] [P1] Implement graceful shutdown handling in keep_running.sh – trap SIGTERM and ensure telemetry is flushed.
[ ] [P1] Refactor universal_rhythm.lfo to use SciPy's signal library – enhance waveform accuracy.
[ ] [P2] Write unit tests for root_semantics letter_semantic – validate the semantic axes against known inputs.
[ ] [P2] Add a cache for cosmic_semantic_vector results – reduce redundant polling when called in quick succession.
[ ] [P2] Simplify cosmic_driver.poll to return a dict of only relevant keys – avoid leaking internal state.
[ ] [P2] Create a Dockerfile for deployment – enable reproducible container builds.
[ ] [P2] Add logging configuration to main – centralise log level via environment variable.
[ ] [P2] Update README with a quick‑start guide – help new contributors run the engine locally.
[ ] [P2] Clean up unused imports in dialogue_engine – reduce import overhead.
[ ] [P2] Convert the root list to a set for O(1) membership checks – speed up root validation.
```

---

### Top 3 Code Changes

---

**1. `dialogue_engine.py` – Fix root loading fallback**

**Why:** The current fallback is truncated, causing a runtime error when `roots.txt` is missing or malformed. We need a clear, safe fallback that loads a default root list or exits gracefully.

```python
# dialogue_engine.py
def load_roots():
    txt = Path("arabic_db/roots.txt")
    if txt.exists():
        lines = [ln.strip() for ln in txt.read_text(encoding="utf-8").splitlines()]
        valid = [r for r in lines if len(r) == 3 and all(c in PHONEMES for c in r)]
        if valid:
            print(f"[dialogue] loaded {len(valid)} roots", file=sys.stderr, flush=True)
            return valid
    # Fallback: use a minimal built‑in list or exit
    print("[dialogue] warning: roots.txt missing or invalid – using built‑in defaults", file=sys.stderr, flush=True)
    default_roots = ["الل", "الأ"]  # example short roots
    if not default_roots:
        raise RuntimeError("[dialogue] no valid roots available; aborting")
    return default_roots
```

---

**2. `root_semantics.py` – Trigger precomputation on import**

**Why:** `root_semantics` exposes `root_semantic()` but never pre‑computes the vector cache, leading to repeated expensive calculations. Calling `precompute()` at import ensures the cache is ready.

```python
# root_semantics.py
# At module import, pre‑compute the semantic vectors for all known roots
precompute()
```

---

**3. `train_gen.py` – Consume cached root semantic vectors**

*(Assuming `train_gen.py` exists in the repo; if not, this change shows how to integrate the new cache.)*

**Why:** Training data generation benefits from fast root‑to‑vector lookup; using the cached vectors from `root_semantics` speeds up batch creation and reduces CPU usage.

```python
# train_gen.py
from root_semantics import root_semantic

def generate_training_batch(batch_size=32):
    roots = load_roots()   # load from file or fallback
    batch_vectors = np.stack([root_semantic(r) for r in np.random.choice(roots, batch_size)])
    return batch_vectors
```