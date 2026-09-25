"""Load saved model, classify a WAV file."""
import sys, os, json
import numpy as np
from scipy.io import wavfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from synth.features import extract

CATMAP = {
    "a":"vowel","e":"vowel","i":"vowel","o":"vowel","u":"vowel",
    "p":"plosive","t":"plosive","k":"plosive","b":"plosive","d":"plosive","g":"plosive",
    "s":"fricative","sh":"fricative","f":"fricative","th":"fricative","z":"fricative","v":"fricative",
    "m":"nasal","n":"nasal","ng":"nasal",
    "l":"approximant","r":"approximant","w":"approximant","y":"approximant",
    "rise":"contour","fall":"contour","wave":"contour",
}

def load_model(path=None):
    if path is None:
        path = os.path.join(ROOT, "models", "mlp_supervised.npz")
    d = np.load(path, allow_pickle=True)
    return {
        "W1": d["W1"], "b1": d["b1"],
        "W2": d["W2"], "b2": d["b2"],
        "W3": d["W3"], "b3": d["b3"],
        "mu": d["mu"], "sd": d["sd"],
        "keys": list(d["feature_keys"]),
        "classes": list(d["phoneme_classes"]),
    }

TEMP = 0.5   # <1 sharpens confidence

def forward(model, X):
    z1 = X @ model["W1"] + model["b1"]; a1 = np.maximum(z1, 0)
    z2 = a1 @ model["W2"] + model["b2"]; a2 = np.maximum(z2, 0)
    z3 = (a2 @ model["W3"] + model["b3"]) / TEMP
    z3 -= z3.max(axis=1, keepdims=True)
    e = np.exp(z3)
    return e / e.sum(axis=1, keepdims=True)

def predict_wav(path, model):
    sr, sig = wavfile.read(path)
    # convert to float mono
    if sig.ndim > 1:
        sig = sig.mean(axis=1)
    sig = sig.astype(np.float64) / (np.max(np.abs(sig)) + 1e-9)
    # resample if needed (features expect 22050)
    feats = extract(sig.astype(np.float32), sr)
    x = np.array([feats[k] for k in model["keys"]], dtype=np.float64)
    x = (x - model["mu"]) / model["sd"]
    P = forward(model, x[None, :])[0]
    top = np.argsort(-P)[:3]
    return [(model["classes"][i], float(P[i]),
             CATMAP.get(model["classes"][i], "other")) for i in top]

def main():
    if len(sys.argv) < 2:
        print("usage: python predict.py <file.wav>")
        sys.exit(1)
    model = load_model()
    path = sys.argv[1]
    results = predict_wav(path, model)
    print(f"\nfile: {path}")
    print(f"top-3 predictions:")
    for phoneme, prob, cat in results:
        bar = "█" * int(prob * 30)
        print(f"  {phoneme:5s} ({cat:12s})  {prob*100:5.1f}%  {bar}")
    cat_conf = {}
    for _, prob, cat in results:
        cat_conf[cat] = cat_conf.get(cat, 0) + prob
    print(f"\n  top category: {max(cat_conf, key=cat_conf.get)}"
          f"  ({max(cat_conf.values())*100:.1f}% cumulative)")

if __name__ == "__main__":
    main()
