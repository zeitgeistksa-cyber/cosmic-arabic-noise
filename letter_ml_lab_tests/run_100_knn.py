"""Phoneme-level KNN, scored at category level."""
import sys, os, json
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CATMAP = {
    "a":"vowel","e":"vowel","i":"vowel","o":"vowel","u":"vowel",
    "p":"plosive","t":"plosive","k":"plosive","b":"plosive","d":"plosive","g":"plosive",
    "s":"fricative","sh":"fricative","f":"fricative","th":"fricative","z":"fricative","v":"fricative",
    "m":"nasal","n":"nasal","ng":"nasal",
    "l":"approximant","r":"approximant","w":"approximant","y":"approximant",
    "rise":"contour","fall":"contour","wave":"contour","flat":"contour",
}

def load(p):
    with open(p) as f:
        return [json.loads(l) for l in f]

def to_matrix(rows):
    keys = sorted(rows[0]["features"].keys())
    X = np.array([[r["features"][k] for k in keys] for r in rows], dtype=np.float64)
    y = np.array([r["phoneme"] for r in rows])
    return X, y

def standardize(Xtr, Xte):
    mu = Xtr.mean(0); sd = Xtr.std(0) + 1e-9
    return (Xtr-mu)/sd, (Xte-mu)/sd

def knn(Xtr, ytr, Xte, k):
    Xn = Xtr / (np.linalg.norm(Xtr, axis=1, keepdims=True) + 1e-9)
    Xq = Xte / (np.linalg.norm(Xte, axis=1, keepdims=True) + 1e-9)
    sim = Xq @ Xn.T
    idx = np.argsort(-sim, axis=1)[:, :k]
    preds = []
    for row in idx:
        votes = {}
        for j in row:
            votes[ytr[j]] = votes.get(ytr[j], 0) + 1
        preds.append(max(votes, key=votes.get))
    return np.array(preds)

def strat_folds(y, n_folds=5, seed=0):
    rng = np.random.default_rng(seed)
    folds = [[] for _ in range(n_folds)]
    for cls in np.unique(y):
        idx = np.where(y == cls)[0]
        rng.shuffle(idx)
        for i, j in enumerate(idx):
            folds[i % n_folds].append(j)
    return [np.array(f) for f in folds]

def main():
    rows = load(os.path.join(ROOT, "dataset", "letters_100.jsonl"))
    X, y = to_matrix(rows)
    print(f"n={len(rows)}  phonemes={sorted(set(y))}")

    y_cat = np.array([CATMAP.get(p, "other") for p in y])
    classes = sorted(set(y_cat))

    folds = strat_folds(y, 5, seed=0)
    accs = {k: [] for k in (1,3,5,7,9)}
    for f in range(5):
        te = folds[f]
        tr = np.concatenate([folds[i] for i in range(5) if i != f])
        Xtr, Xte = standardize(X[tr], X[te])
        for k in accs:
            preds = knn(Xtr, y[tr], Xte, k)
            preds_cat = np.array([CATMAP.get(p, "other") for p in preds])
            accs[k].append(float(np.mean(preds_cat == y_cat[te])))

    print()
    for k in sorted(accs):
        m = np.mean(accs[k]) * 100
        s = np.std(accs[k]) * 100
        print(f"  k={k}  cat-acc={m:.1f}% ± {s:.1f}")

    best_k = max(accs, key=lambda k: np.mean(accs[k]))
    best_m = np.mean(accs[best_k]) * 100
    best_s = np.std(accs[best_k]) * 100
    print(f"\n[*] best k={best_k}  cat CV acc = {best_m:.1f}% ± {best_s:.1f}")

    # confusion
    confusion = np.zeros((len(classes), len(classes)), dtype=int)
    cidx = {c: i for i, c in enumerate(classes)}
    for f in range(5):
        te = folds[f]
        tr = np.concatenate([folds[i] for i in range(5) if i != f])
        Xtr, Xte = standardize(X[tr], X[te])
        preds = knn(Xtr, y[tr], Xte, best_k)
        preds_cat = np.array([CATMAP.get(p, "other") for p in preds])
        for t, p in zip(y_cat[te], preds_cat):
            if t in cidx and p in cidx:
                confusion[cidx[t], cidx[p]] += 1

    rep = os.path.join(ROOT, "reports", "knn_summary.md")
    os.makedirs(os.path.dirname(rep), exist_ok=True)
    with open(rep, "w") as f:
        f.write("# KNN (phoneme labels, category scoring)\n\n")
        f.write(f"- n = {len(rows)}\n")
        f.write(f"- Best k = {best_k}\n")
        f.write(f"- Category CV = **{best_m:.1f}% ± {best_s:.1f}**\n\n")
        f.write("## Confusion (category)\n\n")
        f.write("| true \\ pred | " + " | ".join(classes) + " |\n")
        f.write("|" + "---|" * (len(classes)+1) + "\n")
        for i, c in enumerate(classes):
            f.write(f"| {c} | " + " | ".join(str(confusion[i,j]) for j in range(len(classes))) + " |\n")
    print(f"[*] report → {rep}")

if __name__ == "__main__":
    main()
