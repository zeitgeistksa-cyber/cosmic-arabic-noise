# Cosmic Arabic Noise — Project Context

## What this is
An audio synthesis engine that maps Arabic phoneme acoustics
to live cosmic data (Schumann resonance, Kp index, solar wind).

## Architecture
- `dialogue_engine.py`      — main engine, streams PCM to stdout
- `phoneme_table.py`        — 28 Arabic letters with F1/F2/F3/CoG
- `phoneme_grammar.py`      — voicing, emphasis, manner classification
- `root_semantics.py`       — root → 8-dim semantic vector
- `cosmic_semantics.py`     — live cosmic → 4-dim vector
- `tv_space_synth.py`       — fast TV-space phoneme synthesizer
- `universe_messenger.py`   — broadcasts phoneme messages, logs responses

## Data files
- `telemetry/session_*.jsonl`      — every turn: root + cosmic state
- `letter_correlations.json`       — which letters track cosmic changes
- `knowledge.jsonl`                — listener's 30-second readings

## Coding conventions
- Pure NumPy (no TensorFlow — too slow on Termux)
- Keep functions under 50 lines
- Use `sys.stderr` for logging, `sys.stdout.buffer` for audio
- Never touch imports or main() when editing

## Goals
- Discover patterns linking cosmic state to phoneme selection
- Generate evolving sound that responds to real space weather
- Find the acoustic signature of geomagnetic storms

## Files to prioritize when reading
- dialogue_engine.py
- phoneme_table.py
- letter_correlations.json
- universe_messenger.py
- tv_space_synth.py

## Files to ignore (too large / not source)
- telemetry/
- real_samples/
- proposals_old/
- .git/
- experiments/reports/
