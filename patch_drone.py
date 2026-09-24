from pathlib import Path
p = Path("dialogue_engine.py")
s = p.read_text()

# Add a drone state variable in __init__
old_init = "        self.turn_history = []"
new_init = """        self.turn_history = []
        self.drone_cog = 0.30      # smoothed CoG, updated per turn
        self.drone_smoothing = 0.05  # how fast the drone tracks the attractor"""

if old_init in s and "drone_cog" not in s:
    s = s.replace(old_init, new_init, 1)
    print(">> added drone state")

# Add CoG helper method right before generate_chunk
marker = "    def generate_chunk(self, cs):"
helper = '''    def _current_cog(self):
        """Return the CoG of the currently selected root."""
        from phoneme_table import PHONEMES
        if not self.current_root or len(self.current_root) != 3:
            return 0.3
        feats = [PHONEMES[c][3] for c in self.current_root if c in PHONEMES]
        if not feats:
            return 0.3
        return float(np.mean(feats))

    def generate_chunk(self, cs):'''
if marker in s and "_current_cog" not in s:
    s = s.replace(marker, helper, 1)
    print(">> added _current_cog method")

# Add the drone to the mix
old_mix = """        mixed = (ar * 0.25
                 + triad_direct[:, None] * 0.60
                 + sub_perletter[:, None] * 0.15
                 + hiss_perletter[:, None] * 0.10)"""

new_mix = """        # Smoothly track the current root's CoG
        target_cog = self._current_cog()
        self.drone_cog += self.drone_smoothing * (target_cog - self.drone_cog)

        # Drone: sub-bass at low CoG, mid at high CoG
        drone_freq = 55.0 * (2.0 ** (self.drone_cog * 2.0))  # 55 - 220 Hz
        drone = 0.06 * np.sin(2 * np.pi * drone_freq * t)

        mixed = (ar * 0.25
                 + triad_direct[:, None] * 0.60
                 + sub_perletter[:, None] * 0.15
                 + hiss_perletter[:, None] * 0.10
                 + drone[:, None])"""

if old_mix in s and "drone_freq" not in s:
    s = s.replace(old_mix, new_mix, 1)
    print(">> added drone to mix")
else:
    print("!! pattern not found — mixer might already have a drone")

p.write_text(s)
print(">> done")
