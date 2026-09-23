# Arabic Phoneme Noise Engine v3.2

Self-evolving neural noise engine driven by Arabic phoneme acoustics
and the universal 2 Hz acoustic communication rhythm.

## Layout

    phoneme_table.py       -- Arabic letter acoustic fingerprints
    universal_rhythm.py    -- 2 Hz tempo constants and scorer
    arabic_noise_engine.py -- Main engine
    train_gen.py           -- Evolutionary trainer
    extract_roots.py       -- Build roots.txt from vocabulary JSON
    watch_*.py             -- Live telemetry viewers
    setup.sh               -- One-time installer (downloads root DB)
    start.sh               -- Launch engine
    export.sh              -- Bundle session for sharing
    import.sh              -- Import a shared bundle

    arabic_db/             -- Root database
    telemetry/             -- Session logs (JSONL)
    brains/                -- Evolved generations (NPZ)

## First Run

    ./setup.sh
    ./start.sh

## Full Cycle

    ./start.sh                    # run 5-15 min, Ctrl+C
    python train_gen.py           # evolve next generation
    ./start.sh                    # reload with evolved brain

## Observe Live (separate Termux session)

    python watch_roots.py
    python watch_entropy.py
    python watch_mutations.py

## Share

    ./export.sh                   # -> cosmic_ai_share_*.tar.gz
    ./import.sh <archive.tar.gz>  # -> merge into local pool
