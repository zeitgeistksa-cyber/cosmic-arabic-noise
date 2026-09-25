# 🧪 letter_ml_lab — 100-Test Letter-Sound ML Harness

10 phoneme categories × 10 variants = 100 tests.
Outputs: JSONL dataset + WAV files + telemetry + report.

## Quick start
    cd ~/letter_ml_lab
    ./run_100_tests.sh

## Layout
    synth/    formant phoneme synth + feature extractor
    tests/    generate_100.py, run_100.py
    dataset/  letters_100.jsonl
    wavs/     100 phoneme WAVs
    logs/     telemetry JSONL
    reports/  markdown summaries
    aider/    Aider config + prompt pack
    gemini/   Gemini prompt pack

## Aider loop
    cd ~/letter_ml_lab
    aider --config aider/.aider.conf.yml
    > /read aider/prompt_phase1.md
    > follow the prompt

## Gemini loop
    Paste gemini/prompts.md prompts into Gemini
    with dataset/letters_100.jsonl attached.

## Next phases
    Phase 2: KNN classifier
    Phase 3: 1000 tests + augmentation
    Phase 4: CNN on raw waveform
    Phase 5: Aider ↔ Gemini auto-loop
