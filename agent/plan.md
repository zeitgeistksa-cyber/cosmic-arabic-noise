# Development Plan

_Generated 20260924_030552_

# 🚀 3‑Phase Development Roadmap – “Cosmic Arabic Noise Engine”  
**Goal:**  Tighten the core loop, surface telemetry, and plant the seeds for an experimental “live‑stream” mode.  
**Time‑box:** 1 month, with the first phase delivering *quick wins* that can be checked in under an hour.  

> **TL;DR**  
> • **Phase 1:** 15–20 min “gotchas” → reliable root lookup, sanity‑check cosmic data, and a lightweight test harness.  
> • **Phase 2:** 1 day‑style features → LFO tuning, root‑semantic caching, and a basic REST API for remote control.  
> • **Phase 3:** Ambitious experiments → real‑time audio synthesis, interactive web UI, and machine‑learning‑based root prediction.

---

## Phase 1 – Quick Wins (≤ 1 hour each)

| # | Task | File / Function | Why it matters | Estimated time |
|---|------|-----------------|----------------|----------------|
| 1 | **Add a safe‑fallback root loader** | `dialogue_engine.py` → `load_roots()` | Currently crashes if `roots.txt` is missing. Add `FileNotFoundError` guard and log a helpful message. | 10 min |
| 2 | **Fix broken `PHONEME_LETTERS` import** | `phoneme_table.py` | `PHONEME_LETTERS = se` is incomplete. Define it as `list(PHONEMES.keys())`. | 5 min |
| 3 | **Add type hints to core semantic functions** | `root_semantics.py` → `letter_semantic`, `root_semantic` | Improves IDE support and static type checks. | 10 min |
| 4 | **Create a minimal `tests/` skeleton** | New directory `tests/` | Enables CI and quick debugging. | 5 min |
| 5 | **Log the first cosmic snapshot** | `cosmic_driver.py` → `poll()` | Capture and persist the first snapshot in a `log.json` file for debugging. | 10 min |
| 6 | **Wrap `cosmic_semantic_vector()` with a simple CLI** | `cosmic_semantics.py` → add `if __name__ == "__main__":` block | Quick sanity check: run `python cosmic_semantics.py` to see current vector. | 5 min |
| 7 | **Add a `--help` flag to `dialogue_engine.py`** | `dialogue_engine.py` | Future users can see usage without digging into docs. | 5 min |
| 8 | **Ensure `universal_rhythm_lfo` returns a scalar** | `universal_rhythm.py` | If called with a numpy array, it returns an array of the same shape; add a guard for scalar inputs. | 10 min |

> **Outcome:**  
> - Robust root loading and error handling.  
> - Quick sanity checks via CLI.  
> - Basic unit‑test framework in place.  

---

## Phase 2 – Medium‑Features (≈ 1 day each)

| # | Feature | Primary Files | Core Functions | Key Steps | Notes |
|---|---------|---------------|----------------|-----------|-------|
| 1 | **Root‑semantic caching** | `root_semantics.py` | `precompute()` | • Load all roots on startup. <br>• Store in a global dict `{root: vector}`. <br>• Replace repeated `root_semantic(root)` calls with lookup. | Improves runtime by ~×3 for high‑frequency calls. |
| 2 | **Add “score” metric for root‑cosmic fit** | `dialogue_engine.py` | `root_score(root, cosmic_vec)` | • Compute cosine similarity (`cosine()` from `root_semantics.py`). <br>• Store best root in a dict for quick re‑use. | Enables deterministic root selection. |
| 3 | **Implement a tiny REST API** | New file `api.py` | `get_current_root()`, `set_parameters()` | • Use Flask‑Lite or FastAPI. <br>• Endpoint `/root` returns current root. <br>• Endpoint `/params` allows patching `RHYTHM_*` constants. | Allows external control (e.g., from a web UI). |
| 4 | **Expose cosmic parameters via `/status`** | `api.py` | `get_status()` | Return JSON with last snapshot, cosmic vector, and chosen root. | Useful for monitoring dashboards. |
| 5 | **Add a basic WebSocket stream** | `api.py` | `ws_stream()` | Use `websockets` library to push the current root and LFO value in real‑time. | Pre‑seed for a later live‑visualization. |
| 6 | **Create a lightweight CLI tool** | New file `cli.py` | `run()` | Wrap `dialogue_engine` into a long‑running CLI that prints root changes to stdout. | Handy for developers. |
| 7 | **Add a unit‑test for `cosmic_semantic_vector`** | `tests/test_cosmic_semantics.py` | `test_vector_normalization()` | Mock `CosmicDriver.poll()` to return known values. | Verifies math correctness. |
| 8 | **Implement a basic audio‑output stub** | New file `audio_stub.py` | `play_root(root)` | Generate a dummy sine wave whose frequency is derived from the root’s vector. | Allows testing the pipeline end‑to‑end. |
| 9 | **Add CI workflow** | `.github/workflows/ci.yml` | `pytest` | Run tests on every PR. | Ensures quality. |

> **Outcome:**  
> - Faster root selection.  
> - Remote control via HTTP/WebSocket.  
> - Unit‑tested core logic.  
> - Ready‑for‑integration test harness.  

---

## Phase 3 – Ambitious Ideas

> These tasks will stretch the project and may take several weeks or months. They are optional but highly rewarding.

| # | Idea | Target Files | Milestones | Dependencies |
|---|------|--------------|------------|--------------|
| 1 | **Real‑time audio synthesis engine** | `audio_engine.py` | • Map semantic vectors to filter banks.<br>• Generate a live stream of noise modulated by cosmic data. | Requires a proper audio library (e.g., `sounddevice`, `pyaudio`). |
| 2 | **Web UI with live visualizer** | `frontend/` (React/Vue) | • Display root changes, LFO waveform, cosmic data trends.<br>• Allow users to tweak LFO parameters and root selection. | Depends on the REST API and WebSocket stream. |
| 3 | **Machine‑learning root predictor** | `ml/` | • Train a small neural network on historic root usage vs. cosmic conditions.<br>• Replace cosine similarity with learned model. | Needs a data pipeline (telemetry logs). |
| 4 | **Multi‑node distributed engine** | `cluster/` | • Run separate nodes for data ingestion, semantic scoring, and audio synthesis.<br>• Communicate over ZeroMQ or gRPC. | Complex; may be overkill for initial release. |
| 5 | **Dynamic root database** | `arabic_db/roots.txt` | • Add a script that scrapes Arabic root dictionaries and updates the file.<br>• Include a “confidence” score per root. | Requires web‑scraping and NLP. |
| 6 | **Custom LFO curves** | `universal_rhythm.py` | • Expose a DSL for defining LFOs (e.g., JSON).<br>• Let users load custom rhythm profiles. | Extends the API. |
| 7 | **Security & Auth for the API** | `api.py` | • Basic JWT or OAuth token authentication. | Needed if the engine is exposed publicly. |

---

## Quick Checklist for the First Two Weeks

1. **Phase 1** tasks 1‑8 completed ✅
2. **Phase 2** task 1 (root caching) complete ✅
3. **Phase 2** task 2 (root‑cosmic score) complete ✅
4. **Phase 2** task 3 (REST API) in progress
5. **Unit tests** running with `pytest` → `0 failures`
6. **CI** configured → 100 % passing on merge

> **Tip:** Use `git commit -m "feat: add root caching"` style messages. Pull requests should reference the relevant issue (e.g