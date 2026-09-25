"""Generate 100 letter-sound tests — every category is a real distinct sound."""
import sys, os, json
import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from synth.phoneme_synth import synthesize, SR, FORMANTS
from synth.features import extract

# Map compound names → single phonemes we can actually synthesize
ALIAS = {
    # digraphs
    "ch": "sh", "ph": "f", "wh": "w",
    # diphthongs → pick the more distinctive vowel
    "ai": "a", "au": "a", "ei": "e", "ou": "o",
    # cv syllables → use the vowel part
    "ba": "a", "ta": "a", "ki": "i", "mo": "o",
    # contour/emotion → base vowel is "a"; contour encodes the difference
    "rise": "a", "fall": "a", "wave": "a", "flat": "a",
    "calm": "a", "angry": "a", "happy": "a", "sad": "a", "tense": "a",
}

CATEGORIES = {
    "vowel":      ["a","e","i","o","u"],
    "plosive":    ["p","t","k","b","d","g"],
    "fricative":  ["s","sh","f","th","z","v"],
    "nasal":      ["m","n","ng"],
    "approximant":["l","r","w","y"],
    "contour":    ["rise","fall","wave"],
}

def resolve_phoneme(name):
    if name in FORMANTS:
        return name
    return ALIAS.get(name, "a")

def build_test(idx, category, name, seed):
    rng = np.random.default_rng(seed)
    ph = resolve_phoneme(name)

    dur    = float(rng.uniform(0.20, 0.50))
    f0     = float(rng.uniform(90, 220))
    jit    = float(rng.uniform(0.0, 0.05))
    shift  = float(rng.uniform(0.85, 1.20))
    contour = "flat"

    if category == "contour":
        contour = name
    if category == "emotion":
        contour = {"calm":"flat","angry":"rise","happy":"wave",
                   "sad":"fall","tense":"wave"}.get(name, "flat")
        f0 *= {"calm":1.0,"angry":1.3,"happy":1.2,"sad":0.8,"tense":1.4}.get(name,1.0)

    sig = synthesize(ph, duration=dur, f0=f0, jitter=jit,
                     formant_shift=shift, contour=contour, seed=seed)
    feats = extract(sig, SR)
    return {
        "test_id": f"{category}_{name}_{idx:03d}",
        "category": category,
        "phoneme":  name,       # original name
        "resolved": ph,         # what was actually synthesized
        "label":    f"{category}_{name}",
        "duration": dur, "f0": f0, "jitter": jit, "shift": shift,
        "contour":  contour,
        "features": feats,
    }

def main(out_dir="dataset", wav_dir="wavs", n_per_cat=10, base_seed=0):
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(wav_dir, exist_ok=True)
    rows = []
    idx = 0
    for cat, items in CATEGORIES.items():
        for v in range(n_per_cat):
            name = items[v % len(items)]
            seed = base_seed + idx * 7919
            rec  = build_test(idx, cat, name, seed)

            ph = rec["resolved"]
            sig = synthesize(ph, duration=rec["duration"], f0=rec["f0"],
                             jitter=rec["jitter"], formant_shift=rec["shift"],
                             contour=rec["contour"], seed=seed)
            fname = os.path.join(wav_dir, f"{rec['test_id']}.wav")
            wavfile.write(fname, SR, (sig*32767).astype(np.int16))
            rows.append(rec)
            idx += 1

    with open(os.path.join(out_dir, "letters_100.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"wrote {len(rows)} tests")
    for c in CATEGORIES:
        n = sum(1 for r in rows if r["category"] == c)
        print(f"  {c:12s} {n}")
    return rows

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    main(n_per_cat=n)
