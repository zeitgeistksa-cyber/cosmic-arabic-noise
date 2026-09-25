#!/data/data/com.termux/files/usr/bin/bash
set -e

ROOT="$HOME/letter_ml_lab"
mkdir -p "$ROOT"/{synth,tests,dataset,wavs,logs,aider,gemini}

# ============================================================
# PHONEME SYNTHESIZER  (formant-based)
# ============================================================
cat > "$ROOT/synth/phoneme_synth.py" <<'EOF'
"""Formant-based phoneme synthesis for letter-sound tests."""
import numpy as np

SR = 22050  # lower SR is fine for phonemes, faster on phone

# Formant table: phoneme -> [F1, F2, F3] Hz + voicing + noise mix
FORMANTS = {
    "a":  (730, 1090, 2440, 1.0, 0.0),
    "e":  (530, 1840, 2480, 1.0, 0.0),
    "i":  (270, 2290, 3010, 1.0, 0.0),
    "o":  (570,  840, 2410, 1.0, 0.0),
    "u":  (300,  870, 2240, 1.0, 0.0),
    "p":  (400, 1100, 2200, 0.2, 0.8),
    "t":  (400, 1600, 2600, 0.2, 0.8),
    "k":  (400, 1800, 2400, 0.2, 0.8),
    "b":  (400, 1100, 2200, 0.8, 0.2),
    "d":  (400, 1600, 2600, 0.8, 0.2),
    "g":  (400, 1800, 2400, 0.8, 0.2),
    "s":  (500, 4000, 6500, 0.0, 1.0),
    "sh": (500, 2500, 4000, 0.0, 1.0),
    "f":  (500, 3500, 6000, 0.0, 1.0),
    "th": (500, 2500, 5500, 0.0, 1.0),
    "z":  (500, 4000, 6500, 0.4, 0.6),
    "v":  (500, 3500, 6000, 0.4, 0.6),
    "m":  (250,  900, 2200, 1.0, 0.0),
    "n":  (250, 1700, 2600, 1.0, 0.0),
    "ng": (250, 2300, 2750, 1.0, 0.0),
    "l":  (350, 1100, 2600, 1.0, 0.0),
    "r":  (310, 1060, 1380, 1.0, 0.0),
    "w":  (300,  610, 2200, 1.0, 0.0),
    "y":  (270, 2290, 3010, 1.0, 0.0),
}

def synthesize(phoneme, duration=0.35, f0=120.0, jitter=0.0,
               formant_shift=1.0, contour="flat", seed=0):
    rng = np.random.default_rng(seed)
    n = int(duration * SR)
    t = np.arange(n) / SR

    if phoneme not in FORMANTS:
        raise ValueError(f"unknown phoneme {phoneme}")
    F1, F2, F3, voicing, noise_mix = FORMANTS[phoneme]
    F1, F2, F3 = F1*formant_shift, F2*formant_shift, F3*formant_shift

    # pitch contour
    if contour == "rise":
        f0_curve = f0 * (1 + 0.5*t/duration)
    elif contour == "fall":
        f0_curve = f0 * (1.5 - 0.5*t/duration)
    elif contour == "wave":
        f0_curve = f0 * (1 + 0.2*np.sin(2*np.pi*3*t))
    else:
        f0_curve = np.full(n, f0)

    # glottal source (sawtooth approximation with harmonics)
    phase = 2*np.pi*np.cumsum(f0_curve)/SR
    if jitter > 0:
        phase += rng.normal(0, jitter, n)
    source = np.zeros(n)
    for k in range(1, 25):
        if k*f0 > SR*0.45: break
        source += np.sin(k*phase)/k

    # formant filter via 3 resonant sines
    def formant(sig, freq, bw=80):
        env = np.exp(-bw*t)
        return sig * np.sin(2*np.pi*freq*t) * env

    voiced = (formant(source, F1) + 0.7*formant(source, F2)
            + 0.4*formant(source, F3))

    # noise source (for fricatives)
    noise = rng.standard_normal(n)
    if phoneme in ("s","sh","f","th","z","v"):
        noise *= np.exp(-t*2)
    noise_out = noise * (F2/4000.0)

    sig = voicing*voiced + noise_mix*noise_out

    # attack/decay envelope
    atk = int(0.02*SR); rel = int(0.08*SR)
    env = np.ones(n)
    env[:atk] = np.linspace(0, 1, atk)
    env[-rel:] = np.linspace(1, 0, rel)
    sig *= env

    peak = np.max(np.abs(sig)) + 1e-9
    return (sig/peak*0.9).astype(np.float32)
EOF

# ============================================================
# FEATURE EXTRACTOR  (for ML)
# ============================================================
cat > "$ROOT/synth/features.py" <<'EOF'
"""Feature extraction for letter-sound ML classification."""
import numpy as np

def mfcc_like(sig, sr, n_filters=26, n_coeffs=13):
    """Cheap MFCC approximation: mel-spaced FFT + DCT."""
    n_fft = 1024
    hop = 512
    frames = []
    for i in range(0, len(sig)-n_fft, hop):
        frames.append(sig[i:i+n_fft] * np.hanning(n_fft))
    if not frames:
        return np.zeros(n_coeffs)
    frames = np.stack(frames)
    mag = np.abs(np.fft.rfft(frames, axis=1))
    mel = np.linspace(0, sr/2, n_filters)
    bins = np.floor((n_fft+1)*mel/sr).astype(int)
    bins = np.clip(bins, 0, mag.shape[1]-1)
    filtered = np.array([mag[:, bins[i]:bins[i+1]].mean(1)
                        for i in range(len(bins)-1)]).T
    filtered = np.log(filtered + 1e-9)
    # DCT-II
    N = filtered.shape[1]
    k = np.arange(n_coeffs)[:, None]
    n = np.arange(N)[None, :]
    dct = np.cos(np.pi*k*(2*n+1)/(2*N))
    return (filtered @ dct.T).mean(0)

def extract(sig, sr):
    eps = 1e-9
    rms = float(np.sqrt(np.mean(sig**2)))
    zcr = float(np.mean(np.abs(np.diff(np.sign(sig)))))
    spec = np.abs(np.fft.rfft(sig))
    freqs = np.fft.rfftfreq(len(sig), 1/sr)
    centroid = float(np.sum(freqs*spec)/(np.sum(spec)+eps))
    spread = float(np.sqrt(np.sum(((freqs-centroid)**2)*spec)/(np.sum(spec)+eps)))
    peak_f = float(freqs[np.argmax(spec)])
    rolloff = float(freqs[np.searchsorted(np.cumsum(spec),
                    0.85*np.sum(spec))])
    mfcc = mfcc_like(sig, sr)
    return {
        "rms": rms, "zcr": zcr,
        "centroid": centroid, "spread": spread,
        "peak_f": peak_f, "rolloff": rolloff,
        **{f"mfcc_{i}": float(v) for i, v in enumerate(mfcc)},
    }
EOF

# ============================================================
# 100-TEST GENERATOR
# ============================================================
cat > "$ROOT/tests/generate_100.py" <<'EOF'
"""Generate 100 letter-sound tests across 10 categories."""
import sys, os, json, hashlib
import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from synth.phoneme_synth import synthesize, SR
from synth.features import extract

CATEGORIES = {
    "vowel":      ["a","e","i","o","u"],
    "plosive":    ["p","t","k","b","d","g"],
    "fricative":  ["s","sh","f","th","z","v"],
    "nasal":      ["m","n","ng"],
    "approximant":["l","r","w","y"],
    "digraph":    ["th","sh","ch","ph","wh"],
    "diphthong":  ["ai","au","ei","ou"],
    "contour":    ["rise","fall","wave","flat"],
    "cv":         ["ba","ta","ki","mo"],
    "emotion":    ["calm","angry","happy","sad","tense"],
}

def build_test(idx, category, phoneme, seed):
    rng = np.random.default_rng(seed)
    ph = phoneme if phoneme in ("a","e","i","o","u","p","t","k","b","d","g",
                                 "s","sh","f","th","z","v","m","n","ng",
                                 "l","r","w","y") else "a"
    dur = float(rng.uniform(0.20, 0.50))
    f0  = float(rng.uniform(90, 220))
    jit = float(rng.uniform(0.0, 0.05))
    shift = float(rng.uniform(0.85, 1.20))
    contour = "flat"
    if category == "contour":
        contour = phoneme
    if category == "emotion":
        contour = {"calm":"flat","angry":"rise","happy":"wave",
                   "sad":"fall","tense":"wave"}.get(phoneme, "flat")
        f0 *= {"calm":1.0,"angry":1.3,"happy":1.2,"sad":0.8,"tense":1.4}.get(phoneme,1.0)

    sig = synthesize(ph, duration=dur, f0=f0, jitter=jit,
                     formant_shift=shift, contour=contour, seed=seed)
    feats = extract(sig, SR)
    return {
        "test_id": f"{category}_{phoneme}_{idx:03d}",
        "category": category,
        "phoneme": phoneme,
        "label": f"{category}_{phoneme}",
        "duration": dur, "f0": f0, "jitter": jit, "shift": shift,
        "contour": contour,
        "features": feats,
    }

def main(out_dir="dataset", wav_dir="wavs", n_per_cat=10, base_seed=0):
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(wav_dir, exist_ok=True)
    rows = []
    idx = 0
    for cat, items in CATEGORIES.items():
        for v in range(n_per_cat):
            phoneme = items[v % len(items)]
            seed = base_seed + idx * 7919
            rec = build_test(idx, cat, phoneme, seed)
            # save wav
            rng = np.random.default_rng(seed)
            ph = rec["phoneme"] if rec["phoneme"] in ("a","e","i","o","u",
                "p","t","k","b","d","g","s","sh","f","th","z","v",
                "m","n","ng","l","r","w","y") else "a"
            sig = synthesize(ph, duration=rec["duration"], f0=rec["f0"],
                             jitter=rec["jitter"], formant_shift=rec["shift"],
                             contour=rec["contour"], seed=seed)
            fname = os.path.join(wav_dir, f"{rec['test_id']}.wav")
            wavfile.write(fname, SR, (sig*32767).astype(np.int16))
            rows.append(rec)
            idx += 1
    # write JSONL
    with open(os.path.join(out_dir, "letters_100.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    # summary
    print(f"wrote {len(rows)} tests")
    cats = {}
    for r in rows:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    for c, n in sorted(cats.items()):
        print(f"  {c:12s} {n} tests")
    return rows

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    main(n_per_cat=n)
EOF

# ============================================================
# BATCH RUNNER  (analyze + verdict per test)
# ============================================================
cat > "$ROOT/tests/run_100.py" <<'EOF'
"""Run all 100 tests and log ML-ready verdicts."""
import sys, os, json, time
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset = os.path.join(root, "dataset", "letters_100.jsonl")
    log_path = os.path.join(root, "logs", "run_100_telemetry.jsonl")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    with open(dataset) as f:
        rows = [json.loads(l) for l in f]

    results = []
    start = time.time()
    for i, rec in enumerate(rows):
        feats = rec["features"]
        # cheap classifier rules for smoke testing
        verdict = "unknown"
        if feats["zcr"] > 0.3 and feats["centroid"] > 3000:
            verdict = "fricative"
        elif feats["rms"] > 0.15 and feats["zcr"] < 0.15:
            verdict = "voiced"
        elif feats["peak_f"] < 400:
            verdict = "low"
        else:
            verdict = "mid"

        results.append({
            "test_id": rec["test_id"],
            "category": rec["category"],
            "label": rec["label"],
            "verdict": verdict,
            "match": verdict in rec["category"] or rec["category"] in verdict,
            "features": feats,
        })
        if (i+1) % 20 == 0:
            print(f"[*] processed {i+1}/{len(rows)}")

    with open(log_path, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # summary
    matched = sum(1 for r in results if r["match"])
    print(f"\n[summary] {matched}/{len(results)} matched "
          f"({100*matched/len(results):.1f}%) in {time.time()-start:.1f}s")
    print(f"[summary] log → {log_path}")

if __name__ == "__main__":
    main()
EOF

# ============================================================
# AIDER CONFIG
# ============================================================
cat > "$ROOT/aider/.aider.conf.yml" <<'EOF'
# Aider config for letter_ml_lab
model: gemini/gemini-2.0-flash-exp
weak-model: gemini/gemini-1.5-flash-8b
editor-model: gemini/gemini-2.0-flash-exp
auto-commits: false
dirty-commits: false
stream: true
map-tokens: 2048
attribute-author: false
attribute-committer: false
show-model-warnings: false
EOF

cat > "$ROOT/aider/prompt_phase1.md" <<'EOF'
# Aider Prompt — Phase 1: Analyze 100-test dataset

Context: I ran `python tests/generate_100.py 10` and `python tests/run_100.py`.
Read the files:
- dataset/letters_100.jsonl       (100 test records + features)
- logs/run_100_telemetry.jsonl    (verdicts from rule-based classifier)

Task:
1. Load both JSONL files with Python + pandas.
2. Print: total tests, per-category count, per-verdict count.
3. Compute accuracy of the rule-based classifier vs. the label.
4. Identify which categories get misclassified most.
5. Suggest 3 improvements to the feature extractor.

Output: a markdown report to `reports/phase1_analysis.md`.
Do not modify any code yet — analysis only.
EOF

cat > "$ROOT/aider/prompt_phase2.md" <<'EOF'
# Aider Prompt — Phase 2: Improve classifier

Read `reports/phase1_analysis.md` and the current `tests/run_100.py`.

Task:
1. Replace the rule-based classifier with a KNN classifier
   using sklearn (or pure numpy if sklearn unavailable).
2. Split 100 samples 70/30 train/test.
3. Report accuracy, confusion matrix, per-category F1.
4. Save the model to `models/knn.pkl`.
5. Update `run_100.py` to use the trained model.
6. Re-run and log to `logs/run_100_v2.jsonl`.

Keep dependencies minimal (numpy + scipy only if possible).
EOF

cat > "$ROOT/aider/prompt_phase3.md" <<'EOF'
# Aider Prompt — Phase 3: Expand to 1000 tests

Read `tests/generate_100.py`.

Task:
1. Parameterize n_per_cat so it can generate 100 per category
   → 1000 tests total.
2. Add data augmentation: ±5% pitch shift, ±10% time stretch,
   ±3 dB gain, tiny noise.
3. Each augmented sample must be tagged with the original test_id.
4. Save to `dataset/letters_1000.jsonl` + `wavs_aug/`.
5. Update `run_100.py` to auto-detect dataset size.
EOF

# ============================================================
# GEMINI PROMPTS
# ============================================================
cat > "$ROOT/gemini/prompts.md" <<'EOF'
# Gemini Prompts for letter_ml_lab

## Prompt A — Data audit
Here are 100 letter-sound tests as JSONL (attached).
Each row has: test_id, category, phoneme, label, features{rms, zcr,
centroid, spread, peak_f, rolloff, mfcc_0..12}.
Tell me:
- which categories are linearly separable in feature space,
- which overlap,
- which 3 features are most discriminative (use Fisher score),
- 5 new features to add.

## Prompt B — Architecture search
Given the 100-sample dataset, propose 3 classifier architectures
that would work offline on Termux (no GPU):
- Model A: KNN with cosine distance
- Model B: 1D CNN over the raw waveform
- Model C: Gradient-boosted trees on features
For each: pros, cons, expected accuracy, training time on phone.

## Prompt C — Test design
I want to extend the 10 categories × 10 variants to a
10 × 100 design. Propose 100 sub-variants per category
that stress-test the classifier (adversarial pairs,
minimal pairs, noisy conditions, cross-speaker).

## Prompt D — Deploy plan
Design a workflow where:
1. Aider edits code
2. The test runner regenerates data
3. Gemini scores the run
4. If score < threshold, Aider mutates the feature extractor
5. Loop until convergence
Give me the shell orchestration.
EOF

# ============================================================
# ORCHESTRATOR  (run all 100 tests)
# ============================================================
cat > "$ROOT/run_100_tests.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
set -e
cd "$(dirname "$0")"

echo "=============================================="
echo "  🧪  100-TEST LETTER-SOUND ML HARNESS"
echo "=============================================="

mkdir -p dataset wavs logs reports models

echo "[*] step 1/4 — generating 100 tests..."
python tests/generate_100.py 10

echo "[*] step 2/4 — running classifier..."
python tests/run_100.py

echo "[*] step 3/4 — building reports directory..."
mkdir -p reports
python - <<PY
import json
rows = [json.loads(l) for l in open("logs/run_100_telemetry.jsonl")]
with open("reports/summary.md", "w") as f:
    f.write("# 100-Test Summary\n\n")
    f.write(f"Total tests: {len(rows)}\n\n")
    cats = {}
    for r in rows:
        cats.setdefault(r["category"], []).append(r["match"])
    f.write("| Category | Tests | Matched | Accuracy |\n")
    f.write("|---|---|---|---|\n")
    for c, m in sorted(cats.items()):
        f.write(f"| {c} | {len(m)} | {sum(m)} | {100*sum(m)/len(m):.0f}% |\n")
print("wrote reports/summary.md")
PY

echo "[*] step 4/4 — done. files:"
ls -1 dataset/ wavs/ logs/ reports/ | head -30

echo
echo "=============================================="
echo "  ✅ COMPLETE"
echo "=============================================="
echo "  dataset/letters_100.jsonl"
echo "  logs/run_100_telemetry.jsonl"
echo "  reports/summary.md"
echo "  wavs/*.wav  (100 files)"
echo "=============================================="
EOF
chmod +x "$ROOT/run_100_tests.sh"

# ============================================================
# README
# ============================================================
cat > "$ROOT/README.md" <<'EOF'
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
EOF

echo "✅ letter_ml_lab built at $ROOT"
echo "   next: cd $ROOT && ./run_100_tests.sh"
