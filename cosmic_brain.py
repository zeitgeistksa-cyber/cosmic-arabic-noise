import json, numpy as np, os, sys

# ---------- tiny MLP ----------
class MLP:
    def __init__(self, d_in=11, hid=32, d_out=6, seed=0):
        r = np.random.default_rng(seed)
        self.W1 = r.normal(0, np.sqrt(2/d_in), (d_in, hid)); self.b1 = np.zeros(hid)
        self.W2 = r.normal(0, np.sqrt(2/hid),  (hid,  hid)); self.b2 = np.zeros(hid)
        self.W3 = r.normal(0, np.sqrt(2/hid),  (hid, d_out)); self.b3 = np.zeros(d_out)

    def forward(self, X):
        z1 = X @ self.W1 + self.b1; a1 = np.maximum(z1, 0)
        z2 = a1 @ self.W2 + self.b2; a2 = np.maximum(z2, 0)
        y  = a2 @ self.W3 + self.b3
        return z1, a1, z2, a2, y

    def predict(self, X):
        return self.forward(X)[-1]

    def loss_and_grads(self, X, Y):
        z1, a1, z2, a2, yhat = self.forward(X)
        err  = yhat - Y
        loss = float(np.mean(err**2))
        d3 = 2*err / X.shape[0]
        gW3 = a2.T @ d3; gb3 = d3.sum(0)
        d2 = (d3 @ self.W3.T) * (z2 > 0)
        gW2 = a1.T @ d2; gb2 = d2.sum(0)
        d1 = (d2 @ self.W2.T) * (z1 > 0)
        gW1 = X.T @ d1; gb1 = d1.sum(0)
        return loss, (gW1, gb1, gW2, gb2, gW3, gb3)

    def params(self):
        return [self.W1, self.b1, self.W2, self.b2, self.W3, self.b3]

    def set_params(self, ps):
        self.W1, self.b1, self.W2, self.b2, self.W3, self.b3 = ps

# ---------- feature builder ----------
def features(rec, w_prev):
    eh = rec.get("entropy_hist", []) or [0.0]
    return np.array([
        rec["chunk_rms"], rec["chunk_peak"], rec["variance"],
        *w_prev,
        float(np.mean(eh)), float(np.var(eh)),
    ], dtype=np.float32)

def load_dataset(path):
    rows = [json.loads(l) for l in open(path) if l.strip()]
    if len(rows) < 10:
        raise SystemExit("not enough telemetry — run cosmic_telemetry.py first")
    X, Y = [], []
    for a, b in zip(rows[:-1], rows[1:]):
        wa = np.array(a["weights"], dtype=np.float32)
        wb = np.array(b["weights"], dtype=np.float32)
        X.append(features(a, wa))
        Y.append(wb - wa)          # target = delta
    X = np.stack(X); Y = np.stack(Y)
    mu, sd = X.mean(0), X.std(0) + 1e-6
    return (X - mu) / sd, Y, mu, sd

# ---------- Adam ----------
def adam_train(model, X, Y, epochs=200, bs=256, lr=1e-3, val_split=0.15):
    n = len(X); idx = np.random.permutation(n)
    n_val = int(n * val_split)
    val_idx, tr_idx = idx[:n_val], idx[n_val:]
    Xtr, Ytr = X[tr_idx], Y[tr_idx]
    Xva, Yva = X[val_idx], Y[val_idx]
    m = [np.zeros_like(p) for p in model.params()]
    v = [np.zeros_like(p) for p in model.params()]
    t = 0; b1, b2, eps = 0.9, 0.999, 1e-8
    for ep in range(epochs):
        perm = np.random.permutation(len(Xtr))
        for i in range(0, len(Xtr), bs):
            sl = perm[i:i+bs]
            _, grads = model.loss_and_grads(Xtr[sl], Ytr[sl])
            t += 1
            for j, (p, g) in enumerate(zip(model.params(), grads)):
                m[j] = b1*m[j] + (1-b1)*g
                v[j] = b2*v[j] + (1-b2)*(g*g)
                mh = m[j]/(1-b1**t); vh = v[j]/(1-b2**t)
                p -= lr * mh / (np.sqrt(vh) + eps)
        if ep % 20 == 0 or ep == epochs-1:
            lv = float(np.mean((model.predict(Xva) - Yva)**2))
            print(f"ep {ep:3d}  val_mse={lv:.3e}")
    return model

# ---------- save / load ----------
def save(model, mu, sd, path="cosmic_brain.npz"):
    np.savez(path, mu=mu, sd=sd,
             W1=model.W1, b1=model.b1, W2=model.W2, b2=model.b2,
             W3=model.W3, b3=model.b3)
    print(f"saved {path}")

def load(path="cosmic_brain.npz"):
    d = np.load(path)
    m = MLP()
    m.set_params([d["W1"], d["b1"], d["W2"], d["b2"], d["W3"], d["b3"]])
    return m, d["mu"], d["sd"]

# ---------- CLI ----------
if __name__ == "__main__":
    log = sys.argv[1] if len(sys.argv) > 1 else "cosmic_telemetry.jsonl"
    if not os.path.exists(log):
        raise SystemExit(f"{log} not found — run: python cosmic_telemetry.py")
    print(f"loading {log}")
    X, Y, mu, sd = load_dataset(log)
    print(f"dataset: {X.shape[0]} samples, {X.shape[1]} features")
    m = MLP()
    adam_train(m, X, Y, epochs=200)
    save(m, mu, sd)
