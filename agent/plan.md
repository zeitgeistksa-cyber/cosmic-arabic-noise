# Development Plan

_Generated 20260924_031212_

# 3‑Phase Development Roadmap – Cosmic Arabic Noise Engine  
*(Next month, 6 weeks – 2 weeks per phase)*  

> **Goal** – Quickly tighten the core, add solid test coverage, and sketch out the next big feature set that turns the engine from a prototype into a publishable project.  

---

## Phase 1 – Quick Wins (≤ 1 hour each)

| # | Task | File(s) | What to do | Why |
|---|------|---------|------------|-----|
| 1 | **Define PHONEME_LETTERS** | `phoneme_table.py` | Add `PHONEME_LETTERS = {ch: i for i, ch in enumerate(PHONEMES)}` | Missing mapping breaks indexing in several modules. |
| 2 | **Implement `root_to_log_triad`** | `phoneme_table.py` | Convert an Arabic root string → list of three phoneme indices (using `LETTER_INDEX`). Return `None` on invalid root. | Required by `dialogue_engine.py` for selecting triads. |
| 3 | **Complete `load_roots`** | `dialogue_engine.py` | 1. Read `arabic_db/roots.txt`. 2. Filter for 3‑letter roots that are in `PHONEMES`. 3. Fallback to a hard‑coded minimal set if file missing. 4. Log count. | Ensures the engine never crashes when the DB is missing/empty. |
| 4 | **Add basic unit test for `letter_semantic`** | `tests/test_root_semantics.py` | Use `pytest` to assert that the function returns a 8‑dim array, and that a known letter (`"ب"`) yields a non‑zero vector. | Guarantees that semantic mapping stays correct as we refactor. |
| 5 | **Add README “Quick‑Start”** | `README.md` | Short 3‑line usage example: install deps, run `python -m dialogue_engine`. | Helps new contributors / users to bootstrap quickly. |
| 6 | **Lint / format with `black` & `flake8`** | All source files | Run `black .` and `flake8 .` | Keeps code style consistent for subsequent work. |

> **Deliverable** – A fully functional core that loads roots, maps them to semantic vectors, and runs without manual edits.  

---

## Phase 2 – Medium Features (≈ 1 day each)

| # | Feature | File(s) | Implementation Steps | Outcome |
|---|---------|---------|----------------------|---------|
| 1 | **Robust Cosmic Data Fetcher** | `cosmic_driver.py` | • Add optional `source_url` parameter. <br>• Use `requests.get` with timeout & retry. <br>• Fallback to local `snapshot.json`. <br>• Log errors to `agent/log.jsonl`. | Engine reliably receives live data even during network hiccups. |
| 2 | **Telemetry Export Script** | `export_snapshot.py` | • Add CLI flag `--dump-dir`. <br>• Write current cosmic state and selected root to a JSONL file per tick. <br>• Include timestamp & engine version. | Easier post‑mortem analysis and visualisation. |
| 3 | **Asynchronous Dialogue Engine** | `dialogue_engine.py` | • Wrap the main loop in `async def main()`. <br>• Use `asyncio.sleep()` for the poll interval. <br>• Allow `--async` flag to run in async mode. | Better CPU utilisation and ready for real‑time websockets. |
| 4 | **CLI Wrapper** | `main.py` | • `argparse` to expose: `--root-db`, `--cosmic-driver`, `--verbose`. <br>• Call `dialogue_engine.main()` with those args. | Users can launch the engine from a single command. |
| 5 | **Root Frequency Analyzer** | `analytics.py` | • Scan `agent/log.jsonl`. <br>• Count occurrences of each root. <br>• Output top‑N table to console and JSON. | Gives insight into engine behaviour and bias. |
| 6 | **Add Unit Tests for Cosmic Driver** | `tests/test_cosmic_driver.py` | • Mock `snapshot()` to return fixed data. <br>• Assert that `poll()` normalises values correctly. | Confidence that semantic mapping stays stable. |

> **Deliverable** – A polished, test‑covered engine that can run from CLI, logs telemetry, and is ready for real‑time operation.

---

## Phase 3 – Ambitious Ideas (1–2 weeks)

| # | Vision | File(s) | Rough Plan |
|---|--------|---------|------------|
| 1 | **Neural Mapping from Cosmic State → Root Vector** | `ml_model.py` | • Collect a dataset: cosmic vectors × selected root vectors. <br>• Train a small feed‑forward net (PyTorch) to predict root logits. <br>• Export the model to ONNX for fast inference. | Replace heuristic cosine similarity with learned mapping; improves expressivity. |
| 2 | **Temporal Dynamics via RNN** | `cosmic_semantics_advanced.py` | • Wrap current vector in a 2‑step RNN that predicts the next state. <br>• Use predictions to bias root selection. | Engine can anticipate cosmic swings, giving smoother “conversation”. |
| 3 | **Web Dashboard** | `web/` (React + FastAPI) | • FastAPI backend serves current state & root list. <br>• React front‑end visualises spectra, root usage, and lets users tweak parameters. | Makes the project discoverable and interactive. |
| 4 | **Real‑Time WebSocket Bridge** | `cosmic_websocket.py` | • Expose