"""Supervised training with proper train/val/test + model persistence."""
import sys, os, json, time
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))

CATMAP = {
    "a":"vowel","e":"vowel","i":"vowel","o":"vowel","u":"vowel",
    "p":"plosive","t":"plosive","k":"plosive","b":"plosive","d":"plosive","g":"plosive",
    "s":"fricative","sh":"fricative","f":"fricative","th":"fricative","z":"fricative","v":"fricative",
    "m":"nasal","n":"nasal","ng":"nasal",
    "l":"approximant","r":"approximant","w":"approximant","y":"approximant",
    "rise":"contour","fall":"contour","wave":"contour",
}

def load(path):
    with open(path) as f:
        return [json.loads(l) for l in f]

def to_matrix(rows):
    keys = sorted(rows[0]["features"].keys())
    X = np.array([[r["features"][k] for k in keys] for r in rows], dtype=np.float64)
    y_ph = np.array([r["phoneme"] for r in rows])
    return X, y_ph, keys

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
        z3 -= z3.max(axis=1, keepdims=True)
        e = np.exp(z3)
        return e / e.sum(axis=1, keepdims=True), (z1,a1,z2,a2)

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

    def set_params(self, ps):
        self.W1,self.b1,self.W2,self.b2,self.W3,self.b3 = ps

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
                p -= lr * (m[j]/(1-b1**t)) / (np.sqrt(v[j]/(1-b2**t)) + eps)
    return model

def main():
    np.random.seed(0)
    ds = os.path.join(ROOT, "dataset", "letters_100.jsonl")
    rows = load(ds)
    X, y_ph, keys = to_matrix(rows)
    classes = sorted(set(y_ph))
    print(f"n={len(rows)}  phonemes={len(classes)}")

    # ── 70/15/15 train/val/test split ──
    idx = np.random.permutation(len(rows))
    n = len(rows)
    n_tr, n_va = int(0.7*n), int(0.15*n)
    tr, va, te = idx[:n_tr], idx[n_tr:n_tr+n_va], idx[n_tr+n_va:]

    mu = X[tr].mean(0); sd = X[tr].std(0) + 1e-9
    Xtr = (X[tr]-mu)/sd; Xva = (X[va]-mu)/sd; Xte = (X[te]-mu)/sd
    Ytr = onehot(y_ph[tr], classes)
    Yva = onehot(y_ph[va], classes)
    Yte = onehot(y_ph[te], classes)

    model = MLP(X.shape[1], len(classes), hid=64, seed=0)
    print("training...")
    adam_train(model, Xtr, Ytr, epochs=400, bs=32)

    # evaluate on all three
    for name, Xs, ys in [("train", Xtr, y_ph[tr]),
                         ("val",   Xva, y_ph[va]),
                         ("test",  Xte, y_ph[te])]:
        P, _ = model.forward(Xs)
        pred_ph = np.array(classes)[P.argmax(1)]
        pred_cat = np.array([CATMAP.get(p, "other") for p in pred_ph])
        true_cat = np.array([CATMAP.get(p, "other") for p in ys])
        acc = float(np.mean(pred_cat == true_cat))
        print(f"  {name:5s} cat-acc = {acc*100:.1f}%")

    # save model + metadata
    os.makedirs(os.path.join(ROOT, "models"), exist_ok=True)
    path = os.path.join(ROOT, "models", "mlp_supervised.npz")
    np.savez(
        path,
        W1=model.W1, b1=model.b1,
        W2=model.W2, b2=model.b2,
        W3=model.W3, b3=model.b3,
        mu=mu, sd=sd,
        feature_keys=np.array(keys),
        phoneme_classes=np.array(classes),
    )
    print(f"\n[*] saved model → {path}")
    print(f"    {len(keys)} features, {len(classes)} classes")
    print(f"    load with: predict.py")

if __name__ == "__main__":
    main()
