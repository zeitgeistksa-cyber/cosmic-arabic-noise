import json, time, numpy as np
from cosmic_stream import Engine, CHUNK

LOG = "cosmic_telemetry.jsonl"

def main(seconds=120):
    eng = Engine()
    start = time.time()
    frame = 0
    with open(LOG, "a") as f:
        while time.time() - start < seconds:
            chunk = eng.step(CHUNK)
            rec = {
                "ts":        round(time.time() - start, 4),
                "frame":     frame,
                "chunk_rms": float(np.sqrt(np.mean(chunk**2))),
                "chunk_peak":float(np.max(np.abs(chunk))),
                "variance":  float(np.var(chunk)),
                "weights":   eng.weights.round(4).tolist(),
                "f0":        eng.f0,
                "lfo_ph":    round(eng.lfo_ph, 4),
                "entropy_hist": [round(v, 6) for v in eng.entropy_hist],
            }
            f.write(json.dumps(rec) + "\n")
            f.flush()
            frame += 1
    print(f"wrote {frame} frames to {LOG}")

if __name__ == "__main__":
    main(120)
