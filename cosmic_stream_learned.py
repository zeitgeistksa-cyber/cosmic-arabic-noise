import sys, os, numpy as np, json, time
from cosmic_brain import load, features

SR    = 44100
CHUNK = 4096
BRAIN = "cosmic_brain.npz"
LOG   = "cosmic_learned.jsonl"
rng   = np.random.default_rng()

if not os.path.exists(BRAIN):
    raise SystemExit("no brain found — train first: python cosmic_brain.py")

model, MU, SD = load(BRAIN)

class Engine:
    def __init__(self):
        self.t = 0
        self.f0 = 55.0
        self.lfo_ph = 0.0
        self.drift_ph = 0.0
        self.weights = np.array([1.0, 0.7, 0.5, 0.4, 0.3, 0.2], dtype=np.float32)
        self.entropy_hist = []
        self.whine_buf = np.zeros(CHUNK)
        self.whine_timer = 0
        self.whine_left = 0
        self.whine_len = 1
        self.whine_phase = 0.0
        self.shep_ph = [0.0]*6
        self.step_scale = 0.35        # how strongly model nudges weights

    def _chunk(self, n):
        t = (self.t + np.arange(n)) / SR
        self.t += n

        dets = [0.0, 0.7, -0.5, 1.3]
        base = sum(np.sin(2*np.pi*(self.f0+d)*t) for d in dets) / len(dets)
        sub  = 0.6*np.sin(2*np.pi*27.5*t)
        self.lfo_ph   += 2*np.pi*0.07*n/SR
        self.drift_ph += 2*np.pi*0.03*n/SR
        lfo   = 0.5 + 0.5*np.sin(self.lfo_ph)
        drift = 1 + 0.015*np.sin(self.drift_ph)
        drone = base*drift*lfo + sub

        tritone = 0.35*np.sin(2*np.pi*(55*2**(6/12))*t)
        cluster = (0.22*np.sin(2*np.pi*110*t)
                 + 0.22*np.sin(2*np.pi*(110*2**(1/12))*t)
                 + 0.18*np.sin(2*np.pi*(110*2**(2/12))*t))

        whine = self.whine_buf.copy()
        if self.whine_timer <= 0 and self.whine_left <= 0:
            dur = int(rng.uniform(0.4, 2.5) * SR)
            f   = rng.uniform(7000, 13000)
            self.whine_phase = 2*np.pi*f/SR
            self.whine_left  = dur
            self.whine_len   = dur
            self.whine_timer = dur
        if self.whine_left > 0:
            k = min(n, self.whine_left)
            off = self.whine_len - self.whine_left
            win = np.hanning(self.whine_len)[off:off+k]
            phs = self.whine_phase * np.arange(k)
            phs += self.whine_phase * off
            whine[:k] += 0.07 * np.sin(phs) * win
            self.whine_left -= k
            if self.whine_left <= 0:
                self.whine_timer = int(rng.uniform(0.3, 2.0) * SR)
        self.whine_timer -= n

        shep = np.zeros(n)
        for k in range(6):
            self.shep_ph[k] += 2*np.pi*(80*2**k)*n/SR
            win = 0.5 - 0.5*np.cos(2*np.pi*((k % 6)/6))
            shep += 0.06*win*np.sin(self.shep_ph[k])

        sizzle  = 0.09*np.sin(2*np.pi*9000*t)*np.sin(2*np.pi*7.3*t)
        sizzle += 0.06*np.sin(2*np.pi*11300*t)*np.sin(2*np.pi*3.1*t)

        mix = (self.weights[0]*drone
             + self.weights[1]*tritone
             + self.weights[2]*cluster
             + self.weights[3]*whine
             + self.weights[4]*shep
             + self.weights[5]*sizzle)

        mix = np.tanh(np.sin(mix*2.2)*2.5)
        peak = np.max(np.abs(mix)) + 1e-9
        return (mix/peak*0.8).astype(np.float32)

    def _mutate(self, chunk, frame):
        rms = float(np.sqrt(np.mean(chunk**2)))
        pk  = float(np.max(np.abs(chunk)))
        var = float(np.var(chunk))
        self.entropy_hist.append(var)
        if len(self.entropy_hist) > 8:
            self.entropy_hist.pop(0)
        rec = {"chunk_rms": rms, "chunk_peak": pk,
               "variance": var, "weights": self.weights.tolist(),
               "entropy_hist": self.entropy_hist}
        x = features(rec, self.weights)
        xn = (x - MU) / SD
        delta = model.predict(xn[None, :])[0]
        self.weights = np.clip(self.weights + self.step_scale*delta, 0.1, 1.5)
        return {"ts": round(self.t/SR, 4), "frame": frame,
                "chunk_rms": rms, "chunk_peak": pk, "variance": var,
                "weights": self.weights.round(4).tolist(),
                "entropy_hist": [round(v, 6) for v in self.entropy_hist]}

def main(seconds=0, log=True):
    eng = Engine()
    start = time.time(); frame = 0
    f = open(LOG, "a") if log else None
    try:
        while True:
            if seconds and time.time() - start > seconds:
                break
            chunk = eng._chunk(CHUNK)
            rec = eng._mutate(chunk, frame)
            if f:
                f.write(json.dumps(rec) + "\n"); f.flush()
            pcm = (np.clip(chunk, -1, 1) * 32767).astype("<i2").tobytes()
            try:
                sys.stdout.buffer.write(pcm); sys.stdout.buffer.flush()
            except BrokenPipeError:
                break
            frame += 1
    finally:
        if f: f.close()

if __name__ == "__main__":
    secs = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    main(secs)
