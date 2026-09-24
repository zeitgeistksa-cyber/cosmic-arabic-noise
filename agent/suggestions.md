# Code Suggestions

_Generated 20260924_033937_

**TODO List**

```
[ ] [P0] Add missing imports and guard statements in dialogue_engine.py – Ensure all modules referenced (phoneme_table, phoneme_grammar, etc.) are present and imported correctly to avoid runtime ImportError.
[ ] [P0] Implement robust root loading with fallback – Load roots from arabic_db/roots.txt, validate length and phoneme membership, and fall back to a hard‑coded safe list if the file is missing or corrupt.
[ ] [P0] Add graceful shutdown handling in dialogue_engine.py – Catch SIGINT/SIGTERM and cleanly stop the engine, flushing telemetry and closing any open sockets.
[ ] [P0] Validate PHONEMES contains all required Arabic letters – Add a check at import time and warn or error if any expected key is missing.
[ ] [P0] Ensure cosmic_semantic_vector uses a fresh driver poll on each call – Avoid stale data by forcing driver.poll() each time or adding a timestamp check.
[ ] [P1] Implement root_semantics.precompute to cache all root vectors – Store the 4‑dim vectors in a dictionary for fast lookup during engine operation.
[ ] [P1] Add type annotations to root_semantics functions – Improve static analysis and readability of letter_vector, root_semantic, and precompute.
[ ] [P1] Remove unused imports in dialogue_engine.py – Keep the module lean and avoid confusing linters.
[ ] [P1] Add cosine similarity calculation in dialogue_engine.py – Compute a similarity score between a root vector and the current cosmic vector to select the best root.
[ ] [P1] Add logging for cosmic_driver.poll failures – Record any exceptions or missing data so that issues can be diagnosed quickly.
[ ] [P1] Cache the cosmic_semantic_vector result for a short window – Prevent excessive polling of live data if the engine reads more often than the driver’s poll_interval.
[ ] [P2] Refactor dialogue_engine to use asyncio for live data handling – Make the engine non‑blocking and able to integrate with other async components.
[ ] [P2] Document the universal_rhythm.lfo and rhythm_score functions – Explain the harmonic content and expected frequency range for future contributors.
[ ] [P2] Add unit tests for root_semantics precompute and vector normalization – Ensure that caching and mean calculations are correct across all roots.
[ ] [P2] Add unit tests for cosmic_semantics normalization – Verify that all four dimensions stay within [0,1] and handle edge cases.
[ ] [P2] Add support for Arabic diacritics removal in root_semantics – Normalize roots before vectorization so that diacritics do not affect the acoustic values.
[ ] [P2] Update README.md with a step‑by‑step guide to run the engine locally – Help new users set up the environment and launch the dialogue loop.
[ ] [P2] Add a simple config file (e.g., engine.cfg) for poll_interval and telemetry paths – Decouple hard‑coded constants from code.
[ ] [P2] Add coverage metrics for the core modules – Ensure that future changes keep the test coverage above 80 %.
```

---

**Top‑3 Code Changes**

### dialogue_engine.py
**Why:** Provide a robust root‑loading routine that validates the data and supplies a fallback list.

```python
def load_roots():
    """Load Arabic 3‑letter roots from disk, validate, and fall back to a safe list."""
    txt = Path("arabic_db/roots.txt")
    fallback = ["لمل", "بحن", "تلك"]   # small safe set of valid roots
    roots = []

    if txt.exists():
        try:
            lines = [ln.strip() for ln in txt.read_text(encoding="utf‑8").splitlines()]
            roots = [r for r in lines
                     if len(r) == 3 and all(c in PHONEMES for c in r)]
        except Exception as e:
            print(f"[dialogue] error reading roots file: {e}", file=sys.stderr, flush=True)

    if not roots:
        print("[dialogue] using fallback root list", file=sys.stderr, flush=True)
        roots = fallback

    print(f"[dialogue] loaded {len(roots)} roots", file=sys.stderr, flush=True)
    return roots
```

### root_semantics.py
**Why:** Cache all root vectors to avoid recomputing the mean formants every