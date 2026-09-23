#!/usr/bin/env python3
import numpy as np
from cosmic_driver import CosmicDriver
_history = []
_HISTORY_LEN = 20
def _norm(x, lo, hi):
    if hi <= lo: return 0.5
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))
def _safe(x, default): return default if x is None else x
def cosmic_semantic_vector(driver=None):
    if driver is None: driver = CosmicDriver(poll_interval=0)
    s = driver.poll()
    sch = _safe(s.get("schumann_score"), 50)
    kp = _safe(s.get("kp_value"), 2.0)
    wind = _safe(s.get("wind_speed"), 400)
    bz = _safe(s.get("bz"), 0.0)
    intensity   = _norm(sch, 0, 100)
    coherence   = 1.0 - _norm(kp, 0, 9)
    expansion   = _norm(wind, 250, 800)
    contraction = _norm(-bz, 0, 20)
    harmony     = 1.0 - abs(_norm(sch, 0, 100) - 0.5) * 2
    turbulence  = _norm(kp, 0, 9)
    density     = _norm(wind**2 / 1000, 60, 640)
    luminosity  = _norm(kp, 0, 9) ** 2
    _history.append((sch, kp, wind, bz))
    if len(_history) > _HISTORY_LEN: _history.pop(0)
    if len(_history) >= 5:
        h = np.array(_history[-5:], dtype=np.float64)
        d_int = float(np.tanh((h[-1,0]-h[0,0]) / 20.0))
        d_turb = float(np.tanh((h[-1,1]-h[0,1]) / 3.0))
        d_exp = float(np.tanh((h[-1,2]-h[0,2]) / 100.0))
        d_con = float(np.tanh(-(h[-1,3]-h[0,3]) / 5.0))
    else:
        d_int = d_turb = d_exp = d_con = 0.0
    return [intensity, coherence, expansion, contraction,
            harmony, turbulence, density, luminosity,
            d_int, d_turb, d_exp, d_con], s
if __name__ == "__main__":
    vec, raw = cosmic_semantic_vector()
    names = ["intensity","coherence","expansion","contraction",
             "harmony","turbulence","density","luminosity",
             "d_int","d_turb","d_exp","d_con"]
    for n, v in zip(names, vec):
        bar = "#" * int(abs(v) * 30)
        sign = "+" if v >= 0 else "-"
        print(f"{n:12s}  {sign}{abs(v):.3f}  {bar}")
