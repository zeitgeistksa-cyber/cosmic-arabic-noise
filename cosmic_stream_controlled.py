import sys, os, json, time, numpy as np
from cosmic_brain import load, features

SR, CHUNK = 44100, 4096
STATE = "/tmp/cosmic_state.json"
BRAIN = "cosmic_brain.npz"
LOG   = "cosmic_controlled.jsonl"
rng   = np.random.default_rng()

DEFAULTS = {
    "master": 0.8, "step_scale": 0.35,
    "weights": [1.0, 0.7, 0.5, 0.4, 0.3, 0.2],
    "lfo_rate": 0.07, "drift_rate": 0.03,
    "sub_gain": 0.6, "whine_gain": 0.07,
    "sizzle_gain": 0.09, "shep_gain": 0.06,
    "frozen": False, "panic": False,
}

def read_state():
    try:
        with open(STATE) as f:
            return {**DEFAULTS, **json.load(f)}
    except Exception:
        return dict(DEFAULTS)

USE_BRAIN = os.path.exists(BRAIN)
if USE_BRAIN:
    model, MU, SD = load(BRAIN)
else:
    print("[warn] no brain found, running random mutation")

class Engine:
    def __init__(self):
        self.t = 0
        self.f0 = 55.0
        self.lfo_ph = 0.0
        self.drift_ph = 0.0
        self.weights = np.array(DEFAULTS["weights"], dtype=np.float32)
        self.entropy_hist = []
        self.whine_left = 0
        self.whine_len  = 1
        self.whine_phase= 0.0
        self.whine_timer= 0
        self.shep_ph = [0.0]*6
        self._state = read_state()
        self._state_age = 0

    def _refresh_state(self):
        # re-read every ~10 chunks
        self._state_age += 1
        if self._state_age >= 10:
            self._state = read_state()
            self._state_age = 0

    def chunk(self, n):
        self._refresh_state()
        S = self._state

        t = (self.t + np.arange(n)) / SR
        self.t += n

        dets = [0.0, 0.7, -0.5, 1.3]
        base = sum(np.sin(2*np.pi*(self.f0+d)*t) for d in dets) / len(dets)
        sub  = S["sub_gain"]*np.sin(2*np.pi*27.5*t)

        self.lfo_ph   += 2*np.pi*S["lfo_rate"]   * n/SR
        self.drift_ph += 2*np.pi*S["drift_rate"] * n/SR
        lfo   = 0.5 + 0.5*np.sin(self.lfo_ph)
        drift = 1 + 0.015*np.sin(self.drift_ph)
        drone = base*drift*lfo + sub

        tritone = 0.35*np.sin(2*np.pi*(55*2**(6/12))*t)
        cluster = (0.22*np.sin(2*np.pi*110*t)
                 + 0.22*np.sin(2*np.pi*(110*2**(1/12))*t)
                 + 0.18*np.sin(2*np.pi*(110*2**(2/12))*t))

        whine = np.zeros(n)
        if self.whine_timer <= 0 and self.whine_left <= 0:
            dur = int(rng.uniform(0.4, 2.5)*SR)
            f   = rng.uniform(7000, 13000)
            self.whine_phase = 2*np.pi*f/SR
            self.whine_left  = dur
            self.whine_len   = dur
            self.whine_timer = dur
        if self.whine_left > 0:
            k = min(n, self.whine_left)
            off = self.whine_len - self.whine_left
            win = np.hanning(self.whine_len)[off:off+k]
            phs = self.whine_phase * (off + np.arange(k))
            whine[:k] += S["whine_gain"]*np.sin(phs)*win
            self.whine_left -= k
            if self.whine_left <= 0:
                self.whine_timer = int(rng.uniform(0.3, 2.0)*SR)
        self.whine_timer -= n

        shep = np.zeros(n)
        for k in range(6):
            self.shep_ph[k] += 2*np.pi*(80*2**k)*n/SR
            win = 0.5 - 0.5*np.cos(2*np.pi*(k % 6)/6)
            shep += S["shep_gain"]*win*np.sin(self.shep_ph[k])

        sizzle  = S["sizzle_gain"]*np.sin(2*np.pi*9000*t)*np.sin(2*np.pi*7.3*t)
        sizzle += 0.06*np.sin(2*np.pi*11300*t)*np.sin(2*np.pi*3.1*t)

        w = self.weights
        mix = (w[0]*drone + w[1]*tritone + w[2]*cluster
             + w[3]*whine + w[4]*shep + w[5]*sizzle)

        mix = np.tanh(np.sin(mix*2.2)*2.5)
        if S["panic"]:
            mix[:] = 0.0
        peak = np.max(np.abs(mix)) + 1e-9
        return (mix/peak*S["master"]).astype(np.float32)

    def mutate(self, ch, frame):
        S = self._state
        rms = float(np.sqrt(np.mean(ch**2)))
        pk  = float(np.max(np.abs(ch)))
        var = float(np.var(ch))
        self.entropy_hist.append(var)
        if len(self.entropy_hist) > 8:
            self.entropy_hist.pop(0)

        # allow direct override from state
        self.weights = np.array(S["weights"], dtype=np.float32)

        if not S["frozen"] and USE_BRAIN:
            rec = {"chunk_rms": rms, "chunk_peak": pk, "variance": var,
                   "weights": self.weights.tolist(),
                   "entropy_hist": self.entropy_hist}
            x = features(rec, self.weights)
            xn = (x - MU) / SD
            delta = model.predict(xn[None, :])[0]
            self.weights = np.clip(self.weights + S["step_scale"]*delta, 0.1, 1.5)
        return {"ts": round(self.t/SR, 4), "frame": frame,
                "rms": rms, "peak": pk, "var": var,
                "weights": self.weights.round(4).tolist(),
                "frozen": S["frozen"], "master": S["master"]}

def main(secs=0):
    eng = Engine(); start = time.time(); frame = 0
    f = open(LOG, "a")
    try:
        while True:
            if secs and time.time() - start > secs:
                break
            ch = eng.chunk(CHUNK)
            rec = eng.mutate(ch, frame)
            f.write(json.dumps(rec) + "\n"); f.flush()
            pcm = (np.clip(ch, -1, 1)*32767).astype("<i2").tobytes()
            try:
                sys.stdout.buffer.write(pcm); sys.stdout.buffer.flush()
            except BrokenPipeError:
                break
            frame += 1
    finally:
        f.close()

if __name__ == "__main__":
    secs = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    main(secs)
