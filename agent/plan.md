# Development Plan

_Generated 20260924_033937_

## 🚀 3‑Phase Development Roadmap (Next Month)

> *The goal is to move **cosmic‑arabic‑noise** from a collection of half‑finished scripts to a reproducible, self‑documenting, and testable engine.*

| Phase | Time per task | Focus | Key Deliverables |
|-------|---------------|-------|------------------|
| **Phase 1 – Quick Wins** | < 1 hr each | Resolve import/run‑errors, add basic scaffolding, create smoke tests | Functional imports, runnable examples |
| **Phase 2 – Medium Features** | ≈ 1 day each | Core engine logic, telemetry, UI hooks, simple persistence | Root‑selection algorithm, live‑data loop, minimal dashboard |
| **Phase 3 – Ambitious Ideas** | ≈ 2‑3 days each | Advanced learning, optimisation, packaging, CI | Neural mapping, evolutionary root‑search, Docker & Vercel deployment |

> **Tip** – Keep each task focused on *one file/function*.  
> If a change touches multiple modules, split into sub‑tasks.

---

## Phase 1 – Quick Wins (≤ 1 hr each)

| # | File | Task | Why it matters |
|---|------|------|----------------|
| 1 | `phoneme_table.py` | Define `PHONEME_LETTERS` and add `root_to_log_triad(root)` helper | `dialogue_engine` imports these; otherwise the module fails on import. |
| 2 | `phoneme_grammar.py` | Stub `root_grammar` & `prosody` returning sane defaults | Prevents `ImportError` in `dialogue_engine`. |
| 3 | `root_semantics.py` | Ensure `root_semantic` returns `np.ndarray` of dtype `float64` (already does) and add a quick `__repr__` for debugging | Gives clear debug output during unit‑tests. |
| 4 | `cosmic_semantics.py` | Finish truncated vector logic and expose `cosmic_semantic_vector()` fully | Current truncation breaks the engine. |
| 5 | `cosmic_driver.py` | Add a minimal `snapshot()` stub that returns a deterministic dict | Allows the driver to run in isolation. |
| 6 | `dialogue_engine.py` | Trim the long comment block and add a guard `if __name__ == "__main__": main()` that prints the first root | Gives an immediate “hello world” of the engine. |
| 7 | `README.md` | Add a **“Getting Started”** section with a one‑liner `python -m dialogue_engine` | Improves onboarding. |
| 8 | `tests/test_basic_imports.py` | Quick PyTest that imports all top‑level modules | Provides a smoke‑test suite to catch future regressions. |

> **Execution** – Each task can be tackled in under an hour if you copy/paste the minimal code snippets (provided in the “Implementation Snippet” column below).  

---

### Implementation Snippets

**1. `phoneme_table.py`**

```python
# Add at the end of the file
PHONEME_LETTERS = list(PHONEMES.keys())

def root_to_log_triad(root: str) -> list[str]:
    """
    Return the three phonemes of a root as a list.
    Raises ValueError if the root is not 3 letters or contains unknown phonemes.
    """
    if len(root) != 3:
        raise ValueError(f"Root must be 3 letters: {root!r}")
    triad = []
    for ch in root:
        if ch not in PHONEMES:
            raise ValueError(f"Unknown phoneme {ch!r} in root {root!r}")
        triad.append(ch)
    return triad
```

**2. `phoneme_grammar.py` (create file if missing)**

```python
#!/usr/bin/env python3
"""Simple placeholder grammar and prosody utilities."""

def root_grammar(root: str) -> str:
    """Return a string describing the root’s morphological class."""
    return "verb" if root[0] in "بتثجحخ" else "noun"

def prosody(root: str) -> dict:
    """Return a trivial prosody dict (duration, pitch)."""
    return {"duration": 0.3, "pitch": 150.0}
```

**3. `cosmic_semantics.py` (complete vector)**

```python
# Replace the truncated section
v = [
    _clamp01(sch / 100.0),
    _clamp01(kp / 9.0),
    _clamp01((wind - 200.0) / 600.0),
    _clamp01((bz + 20.0) / 40.0),
]
return np.array(v, dtype=np.float64), s
```

**4. `cosmic_driver.py` (stub snapshot)**

```python
def snapshot():
    """Return a deterministic snapshot for unit tests."""
    return {
        "schumann_score": 70,
        "kp_value": 5.0,
        "wind_speed": 550,
        "bz": -10.0,
    }
```

**5. `dialogue_engine.py` (entry point)**

```python
def main():
    driver = CosmicDriver()
    vec, state = cosmic_semantic_vector(driver)
    roots = load_roots()
    print("Cosmic vector:", vec)
    print("First root candidate:", roots[0] if roots else None)

if __name__ == "__main__":
    main()
```

---

## Phase 2 – Medium Features (≈ 1 day each)

| # | Feature | Files | Key Functions | Acceptance Criteria |
|---|---------|-------|---------------|----------------------|
| 1 | **Root Selection Engine** | `dialogue_engine.py` | `choose_best_root(driver)` | Returns the root with highest cosine similarity to the cosmic vector. |
| 2 | **Telemetry Logger** | `agent_orchestrator.py`, `agent/log.jsonl` | `log_turn(root, vec, score)` | Appends JSON line after each selection. |
| 3 | **Live Dashboard** | `dashboard.sh`, `public/index.html` | `update_dashboard()` (JS) | Web UI shows last 20 roots and cosmic data in real time. |
| 4 | **Command‑line Flags** | `dialogue_engine.py` | `--dry-run`, `--list-roots` | Allows testing without live data. |
| 5 | **Unit Tests** |