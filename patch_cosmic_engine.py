#!/usr/bin/env python3
"""Patch arabic_noise_engine.py to modulate sound with live cosmic data."""
from pathlib import Path

p = Path("arabic_noise_engine.py")
s = p.read_text()

# 1) Import the cosmic driver at the top
if "from cosmic_driver import CosmicDriver" not in s:
    s = s.replace(
        "from universal_rhythm import universal_rhythm_lfo",
        "from universal_rhythm import universal_rhythm_lfo\nfrom cosmic_driver import CosmicDriver"
    )

# 2) Initialize the driver in __init__
if "self.cosmic = CosmicDriver" not in s:
    s = s.replace(
        "self.roots = load_roots()",
        "self.cosmic = CosmicDriver(poll_interval=60)\n        self.roots = load_roots()"
    )

# 3) Apply cosmic modulation inside generate_chunk
old = "        sat = np.tanh(np.sin(mixed*2.5)*3.0)"
new = """        # ---- Cosmic modulation: live space data shapes the sound ----
        cs = self.cosmic.poll()
        mod = self.cosmic.modulation_factor()
        chaos_boost = cs.get("chaos_boost", 0.0)
        sub_boost = cs.get("sub_boost", 0.5)
        # Boost wavefolding when Kp index is high (geomagnetic storm)
        fold_gain = 2.5 * (1.0 + 0.8 * chaos_boost)
        # Boost sub-band energy when solar wind is fast
        mixed = mixed + 0.3 * sub_boost * sub[:, None]
        sat = np.tanh(np.sin(mixed * fold_gain) * (3.0 * mod))

        # Log cosmic state every 50 chunks
        if self.chunk_counter % 50 == 0:
            self.logger.log({
                "type": "cosmic",
                "chunk": self.chunk_counter,
                "schumann_score": cs.get("schumann_score"),
                "kp_value": cs.get("kp_value"),
                "wind_speed": cs.get("wind_speed"),
                "modulation": mod,
            })"""
if old in s:
    s = s.replace(old, new)
    p.write_text(s)
    print(">> Patched arabic_noise_engine.py with cosmic modulation")
else:
    print("!! Could not find wavefolding line. Inspect with:")
    print("   grep -n 'sat = np.tanh' arabic_noise_engine.py")
