#!/usr/bin/env python3
"""Cosmic driver: maps live space data to sonic engine parameters."""
import time, json
from cosmic_data import snapshot

class CosmicDriver:
    def __init__(self, poll_interval=60):
        self.poll_interval = poll_interval
        self.last_poll = 0
        self.state = {
            "schumann_score": 50,
            "kp_value": 2.0,
            "wind_speed": 400,
            "bz": 0.0,
            "energy": 0.5,
            "chaos_boost": 0.0,
            "sub_boost": 0.5,
        }

    def poll(self):
        now = time.time()
        if now - self.last_poll < self.poll_interval:
            return self.state
        self.last_poll = now
        try:
            s = snapshot()
            sch = s.get("schumann_score", 50)
            kp = s.get("kp_value", 2.0)
            wind = s.get("wind_speed", 400)
            bz = s.get("bz", 0.0)
            # Energy: normalized 0-1 from Schumann score
            energy = min(1.0, max(0.0, sch / 100.0))
            # Chaos boost: Kp index 0-9 -> 0-1
            chaos_boost = min(1.0, kp / 9.0)
            # Sub boost: fast solar wind -> more low-end
            sub_boost = min(1.0, max(0.0, (wind - 300) / 500.0))
            self.state.update({
                "schumann_score": sch,
                "kp_value": kp,
                "wind_speed": wind,
                "bz": bz,
                "energy": energy,
                "chaos_boost": chaos_boost,
                "sub_boost": sub_boost,
            })
        except Exception:
            pass
        return self.state

    def modulation_factor(self):
        """Return a scalar in [0.5, 2.0] for overall intensity."""
        s = self.state
        return 0.5 + 1.5 * (0.5 * s["energy"] + 0.5 * s["chaos_boost"])

if __name__ == "__main__":
    d = CosmicDriver(poll_interval=0)
    print(json.dumps(d.poll(), indent=2))
    print(f"modulation_factor = {d.modulation_factor():.3f}")
