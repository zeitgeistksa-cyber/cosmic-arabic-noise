#!/usr/bin/env python3
"""
Phase controller: maps live cosmic state to expected CoG and adjustment.

The phase diagram from the project findings:
  - Kp = 1.67, Schumann = 38:  CoG ~ 0.30 (calm attractor)
  - Kp = 1.67, Schumann = 35:  CoG ~ 0.41 (calm-low-Schumann drift)
  - Kp >= 2.0:                 CoG ~ 0.74 (active attractor)

Fits a simple bilinear model and reports the "distance" between the
engine's current attractor and the target for current cosmic state.
"""
import numpy as np

# The phase diagram — anchored from real data
PHASE_ANCHORS = {
    (1.67, 38.0): 0.302,
    (1.67, 35.0): 0.410,
    (2.00, 38.0): 0.744,
    (2.33, 38.0): 0.775,
}

def expected_cog(kp, schumann):
    """Bilinear interpolation of the phase diagram."""
    if kp is None: kp = 1.67
    if schumann is None: schumann = 38.0

    # Clamp to known range
    kp = max(1.0, min(3.0, kp))
    schumann = max(30.0, min(45.0, schumann))

    # Two-regime fit: Kp < 2 vs Kp >= 2
    if kp < 2.0:
        # Interpolate between (1.67, 35) -> 0.410 and (1.67, 38) -> 0.302
        # Slope in schumann: -0.036 per unit
        base = 0.302
        sch_shift = (38.0 - schumann) * 0.036
        kp_shift = (kp - 1.67) * 0.6  # rise as Kp approaches 2
        return float(np.clip(base + sch_shift + kp_shift, 0.2, 1.0))
    else:
        # Active regime: ~0.75 regardless of schumann
        base = 0.744
        kp_shift = (kp - 2.0) * 0.05
        return float(np.clip(base + kp_shift, 0.5, 1.0))

def current_engine_cog(turns_recent):
    """CoG from the most recent N turns."""
    from phoneme_table import PHONEMES
    if not turns_recent:
        return None
    cogs = []
    for t in turns_recent:
        r = t.get("root")
        if not r or len(r) != 3: continue
        feats = [PHONEMES[c][3] for c in r if c in PHONEMES]
        if feats:
            cogs.append(float(np.mean(feats)))
    return float(np.mean(cogs)) if cogs else None

def drift(target, actual):
    """Signed difference. Positive = engine too bright."""
    if target is None or actual is None:
        return None
    return actual - target

if __name__ == "__main__":
    # Test the interpolator
    for kp, sch in [(1.67, 38), (1.67, 35), (2.0, 38), (2.33, 38)]:
        print(f"  Kp={kp}  Sch={sch}  expected CoG = {expected_cog(kp, sch):.3f}")
