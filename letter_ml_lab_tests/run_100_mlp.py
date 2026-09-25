"""Tiny MLP classifier — pure numpy, Adam optimiser."""
import sys, os, json, time
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
    y_phoneme = np.array([r["phoneme"] for r in rows])
    y_cat = np.array([CATMAP.get(p, "other") for p in y_phoneme])
    return X, y_phoneme, y_cat

def onehot(y, classes):
    idx = {c:i for i,c in enumerate(classes)}
    Y = np.zeros((len(y), len(classes)))
    for i, c in enumerate(y):
        Y[i, idx[c]] = 1.0
    return Y

class MLP:
    def __init__(self, d_in, n_classes, hid=64, seed=0):
        r = np.random.default_rng(seed)
        self.W1 = r.normal(0, np.sqrt(2/d_in), (d_in, hid)); self.b1 = np.zeros(hid)
        self.W2 = r.normal(0, np.sqrt(2/hid),  (hid, hid));  self.b2 = np.zeros(hid)
        self.W3 = r.normal(0, np.sqrt(2/hid),  (hid, n_classes)); self.b3 = np.zeros(n_classes)

    def forward(self, X):
        z1 = X @ self.W1 + self.b1; a1 = np.maximum(z1, 0)
        z2 = a1 @ self.W2 + self.b2; a2 = np.maximum(z2, 0)
        z3 = a2 @ self.W3 + self.b3
        # softmax
        z3 -= z3.max(axis=1, keepdims=True)
        e = np.exp(z3); return e / e.sum(axis=1, keepdims=True), (z1,a1,z2,a2)

    def loss_grad(self, X, Y):
        P, cache = self.forward(X)
        n = len(X)
        loss = -np.mean(np.sum(Y * np.log(P + 1e-9), axis=1))
        gz3 = (P - Y) / n
        z1,a1,z2,a2 = cache
        gW3 = a2.T @ gz3; gb3 = gz3.sum(0)
        gz2 = (gz3 @ self.W3.T) * (z2 > 0)
        gW2 = a1.T @ gz2; gb2 = gz2.sum(0)
        gz1 = (gz2 @ self.W2.T) * (z1 > 0)
        gW1 = X.T @ gz1; gb1 = gz1.sum(0)
        return loss, (gW1,gb1,gW2,gb2,gW3,gb3)

    def params(self):
        return [self.W1,self.b1,self.W2,self.b2,self.W3,self.b3]

def adam_train(model, X, Y, epochs=300, bs=32, lr=1e-3):
    m = [np.zeros_like(p) for p in model.params()]
    v = [np.zeros_like(p) for p in model.params()]
    t = 0; b1, b2, eps = 0.9, 0.999, 1e-8
    for ep in range(epochs):
        perm = np.random.permutation(len(X))
        for i in range(0, len(X), bs):
            sl = perm[i:i+bs]
            _, grads = model.loss_grad(X[sl], Y[sl])
            t += 1
            for j, (p, g) in enumerate(zip(model.params(), grads)):
                m[j] = b1*m[j] + (1-b1)*g
                v[j] = b2*v[j] + (1-b2)*(g*g)
                mh = m[j]/(1-b1**t); vh = v[j]/(1-b2**t)
                p -= lr * mh / (np.sqrt(vh) + eps)
        if ep % 50 == 0:
            P, _ = model.forward(X)
            acc = float(np.mean(P.argmax(1) == Y.argmax(1)))
            print(f"  ep {ep:3d}  acc={acc*100:.1f}%")
    return model

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
    np.random.seed(0)
    rows = load(os.path.join(ROOT, "dataset", "letters_100.jsonl"))
    X, y_ph, y_cat = to_matrix(rows)
    classes = sorted(set(y_ph))
    print(f"n={len(rows)}  phonemes={len(classes)}")

    folds = strat_folds(y_ph, 5, seed=0)
    accs = []
    confusion = np.zeros((6,6), dtype=int)
    cat_classes = sorted(set(y_cat))
    ccidx = {c:i for i,c in enumerate(cat_classes)}

    for f in range(5):
        te = folds[f]
        tr = np.concatenate([folds[i] for i in range(5) if i != f])
        # standardize
        mu = X[tr].mean(0); sd = X[tr].std(0) + 1e-9
        Xtr = (X[tr]-mu)/sd; Xte = (X[te]-mu)/sd
        Ytr = onehot(y_ph[tr], classes)

        model = MLP(X.shape[1], len(classes), hid=64, seed=f)
        adam_train(model, Xtr, Ytr, epochs=300)

        P, _ = model.forward(Xte)
        pred_idx = P.argmax(1)
        pred_ph = np.array(classes)[pred_idx]
        pred_cat = np.array([CATMAP.get(p, "other") for p in pred_ph])
        acc = float(np.mean(pred_cat == y_cat[te]))
        accs.append(acc)
        for t, p in zip(y_cat[te], pred_cat):
            if t in ccidx and p in ccidx:
                confusion[ccidx[t], ccidx[p]] += 1
        print(f"  fold {f}: cat-acc={acc*100:.1f}%")

    m = np.mean(accs)*100; s = np.std(accs)*100
    print(f"\n[*] MLP 5-fold CV = {m:.1f}% ± {s:.1f}")

    rep = os.path.join(ROOT, "reports", "mlp_summary.md")
    with open(rep, "w") as f:
        f.write("# MLP Report (5-fold CV)\n\n")
        f.write(f"- n = {len(rows)}\n")
        f.write(f"- Hidden = 64\n")
        f.write(f"- Epochs = 300\n")
        f.write(f"- CV accuracy = **{m:.1f}% ± {s:.1f}**\n\n")
        f.write("## Confusion (category)\n\n")
        f.write("| true \\ pred | " + " | ".join(cat_classes) + " |\n")
        f.write("|" + "---|" * (len(cat_classes)+1) + "\n")
        for i, c in enumerate(cat_classes):
            f.write(f"| {c} | " + " | ".join(str(confusion[i,j]) for j in range(len(cat_classes))) + " |\n")
    print(f"[*] report → {rep}")

if __name__ == "__main__":
    main()
