#!/usr/bin/env python3
"""
Cosmic Semantics — Raw Version (v2)
===================================
Four dimensions, each a raw live measurement scaled to [0,1]:

    [0] schumann_score / 100       — geomagnetic activity, 0-100
    [1] kp_value / 9               — planetary K-index, 0-9
    [2] (wind_speed - 200) / 600   — solar wind km/s, normalized
    [3] (bz + 20) / 40             — southward IMF, normalized

No named axes like "coherence" or "harmony". Just the numbers.
If a cosmic state is going to prefer specific roots, it must do so
through these 4 raw signals.
"""
import numpy as np
from cosmic_driver import CosmicDriver

_history = []
_HISTORY_LEN = 20


def _clamp01(x):
    return float(max(0.0, min(1.0, x)))


def cosmic_semantic_vector(driver=None):
    """Return a 4-dim raw vector plus the raw state dict."""
    if driver is None:
        driver = CosmicDriver(poll_interval=0)
    s = driver.poll()

    sch = s.get("schumann_score") or 50
    kp = s.get("kp_value") or 2.0
    wind = s.get("wind_speed") or 400
    bz = s.get("bz")
    if bz is None:
        bz = 0.0

    v = [
        _clamp01(sch / 100.0),
        _clamp01(kp / 9.0),
        _clamp01((wind - 200.0) / 600.0),
        _clamp01((bz + 20.0) / 40.0),
    ]
    return v, s


if __name__ == "__main__":
    vec, raw = cosmic_semantic_vector()
    names = ["schumann", "kp", "wind", "bz"]
    for n, v in zip(names, vec):
        bar = "#" * int(v * 40)
        print(f"{n:10s}  {v:.3f}  {bar}")
    print(f"\nraw: {raw}")
