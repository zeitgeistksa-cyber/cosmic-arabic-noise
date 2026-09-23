#!/usr/bin/env python3
"""
Cosmic semantic vector: 8 dimensions of universal state.
  [0] intensity     -- how energetic is the cosmos right now
  [1] coherence     -- how ordered vs chaotic
  [2] expansion     -- solar wind outflow
  [3] contraction   -- Bz southward (magnetic reconnection)
  [4] harmony       -- Schumann quietness
  [5] turbulence    -- Kp storm level
  [6] density       -- plasma density proxy from wind speed
  [7] luminosity    -- X-ray flux from solar flares
"""
import math
from cosmic_driver import CosmicDriver

def _norm(x, lo, hi):
    if hi <= lo: return 0.5
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))

def cosmic_semantic_vector(driver=None):
    """Return (vector, raw_state) tuple."""
    if driver is None:
        driver = CosmicDriver(poll_interval=0)
    s = driver.poll()
    sch = s.get("schumann_score", 50)
    kp = s.get("kp_value", 2.0)
    wind = s.get("wind_speed", 400)
    bz = s.get("bz", 0.0)

    intensity   = _norm(sch, 0, 100)
    coherence   = 1.0 - _norm(kp, 0, 9)                 # calm = coherent
    expansion   = _norm(wind, 250, 800)
    contraction = _norm(-bz, 0, 20)                     # southward Bz
    harmony     = 1.0 - abs(_norm(sch, 0, 100) - 0.5)*2 # calm center
    turbulence  = _norm(kp, 0, 9)
    density     = _norm(wind**2 / 1000, 60, 640)
    # X-ray not in basic snapshot; proxy from Kp spikes
    luminosity  = _norm(kp, 0, 9) ** 2

    return ([intensity, coherence, expansion, contraction,
             harmony, turbulence, density, luminosity], s)

if __name__ == "__main__":
    vec, raw = cosmic_semantic_vector()
    names = ["intensity","coherence","expansion","contraction",
             "harmony","turbulence","density","luminosity"]
    for n, v in zip(names, vec):
        bar = "#" * int(v * 30)
        print(f"{n:12s}  {v:.3f}  {bar}")
