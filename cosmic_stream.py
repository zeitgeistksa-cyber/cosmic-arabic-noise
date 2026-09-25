import sys, numpy as np

SR      = 44100
CHUNK   = 4096
rng     = np.random.default_rng()

class Engine:
    def __init__(self):
        self.t          = 0
        self.f0         = 55.0
        self.lfo_ph     = 0.0
        self.drift_ph   = 0.0
        self.weights    = np.array([1.0, 0.7, 0.5, 0.4, 0.3, 0.2])
        self.entropy_hist = []
        self.whine_buf  = np.zeros(CHUNK)
        self.whine_timer = 0
        self.shep_ph    = [0.0]*6
        self.shep_win   = 0.0

    def step(self, n):
        t  = (self.t + np.arange(n)) / SR
        self.t += n

        # --- drone: 4 detuned sines + sub ---
        dets = [0.0, 0.7, -0.5, 1.3]
        base = sum(np.sin(2*np.pi*(self.f0+d)*t) for d in dets) / len(dets)
        sub  = 0.6*np.sin(2*np.pi*27.5*t)

        self.lfo_ph   += 2*np.pi*0.07*n/SR
        self.drift_ph += 2*np.pi*0.03*n/SR
        lfo   = 0.5 + 0.5*np.sin(self.lfo_ph)
        drift = 1 + 0.015*np.sin(self.drift_ph)
        drone = base*drift*lfo + sub

        # --- dissonance ---
        tritone = 0.35*np.sin(2*np.pi*(55*2**(6/12))*t)
        cluster = (0.22*np.sin(2*np.pi*110*t)
                 + 0.22*np.sin(2*np.pi*(110*2**(1/12))*t)
                 + 0.18*np.sin(2*np.pi*(110*2**(2/12))*t))

        # --- whine: random bursts, phase-continuous ---
        whine = self.whine_buf.copy()
        if self.whine_timer <= 0:
            dur = int(rng.uniform(0.4, 2.5) * SR)
            f   = rng.uniform(7000, 13000)
            self.whine_phase = 2*np.pi*f
            self.whine_left  = dur
            self.whine_len   = dur
            self.whine_timer = dur + int(rng.uniform(0.3, 2.0)*SR)
        if self.whine_left > 0:
            k = min(n, self.whine_left)
            win = np.hanning(self.whine_len)[self.whine_len - self.whine_left :
                                             self.whine_len - self.whine_left + k]
            ph = (self.whine_phase/SR) * np.arange(self.whine_left - k, self.whine_left)
            whine[:k] += 0.07 * np.sin(ph) * win
            self.whine_left -= k
        self.whine_timer -= n

        # --- shepard (phase-based) ---
        shep = np.zeros(n)
        for k in range(6):
            self.shep_ph[k] += 2*np.pi*(80*2**k)*n/SR
            win = 0.5 - 0.5*np.cos(2*np.pi*((k) % 6 / 6))
            shep += 0.06*win*np.sin(self.shep_ph[k])

        # --- sizzle ---
        sizzle = 0.09*np.sin(2*np.pi*9000*t)*np.sin(2*np.pi*7.3*t)
        sizzle += 0.06*np.sin(2*np.pi*11300*t)*np.sin(2*np.pi*3.1*t)

        mix = (self.weights[0]*drone
             + self.weights[1]*tritone
             + self.weights[2]*cluster
             + self.weights[3]*whine
             + self.weights[4]*shep
             + self.weights[5]*sizzle)

        # saturation
        mix = np.tanh(np.sin(mix*2.2)*2.5)

        # self-mutation on entropy
        v = float(np.var(mix))
        self.entropy_hist.append(v)
        if len(self.entropy_hist) > 8:
            self.entropy_hist.pop(0)
            if np.var(self.entropy_hist) < 1e-5:
                self.weights += rng.normal(0, 0.15, size=self.weights.shape)
                self.weights = np.clip(self.weights, 0.1, 1.5)

        peak = np.max(np.abs(mix)) + 1e-9
        return (mix/peak*0.8).astype(np.float32)

def main():
    eng = Engine()
    while True:
        chunk = eng.step(CHUNK)
        pcm   = (np.clip(chunk, -1, 1) * 32767).astype('<i2').tobytes()
        try:
            sys.stdout.buffer.write(pcm)
            sys.stdout.buffer.flush()
        except BrokenPipeError:
            break

if __name__ == "__main__":
    main()
