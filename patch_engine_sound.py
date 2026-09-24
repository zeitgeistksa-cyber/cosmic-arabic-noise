#!/usr/bin/env python3
"""Replace generate_chunk with a phoneme-preserving version."""
import re
from pathlib import Path

p = Path("dialogue_engine.py")
s = p.read_text()

# Find and replace the entire generate_chunk method
pattern = re.compile(
    r"    def generate_chunk\(self, cs\):.*?(?=\n    def )",
    re.DOTALL
)

new_method = '''    def generate_chunk(self, cs):
        self._step_physics()
        if self.chunk_counter - self.turn_start_chunk >= self.turn_chunks:
            self._new_turn(self.chunk_counter)
        t = (self.sample_clock + np.arange(cs)) / self.sr
        self.sample_clock += cs
        self.chunk_counter += 1

        # Position within current turn (0..1), per-sample
        turn_start_s = self.turn_start_chunk * CHUNK / self.sr
        turn_dur_s = self.turn_chunks * CHUNK / self.sr
        turn_pos = np.clip((t - turn_start_s) / turn_dur_s, 0.0, 1.0)

        cx, cy, cz, cw = self.chaos_state
        sub = np.sin(2*np.pi*(30.0+5.0*np.sin(0.1*t))*t)
        fm  = np.sin(2*np.pi*140.0*t + 4.0*np.sin(2*np.pi*63.3*t))
        sw  = np.sin(2*np.pi*(200.0+3000.0*(0.5+0.5*np.sin(0.05*t)))*t)
        pn  = np.random.randn(cs)*(0.5+0.5*np.sin(0.3*t))

        cosmic = np.stack([
            np.sin(2*np.pi*0.05*t),
            np.full(cs, cx/30.0), np.full(cs, cy/30.0), np.full(cs, cz/30.0),
            np.full(cs, np.sin(self.phases[0])),
            np.full(cs, np.sin(self.phases[2])),
            np.full(cs, np.sin(self.phases[4])),
            sub, fm, sw, pn,
            np.cos(2*np.pi*7.83*t),
        ], axis=-1)

        arabic = self._phoneme_latent(cs, t)
        latent = np.concatenate([cosmic, arabic], axis=-1)

        h1 = np.sin(self.omega_0*(latent @ self.W1))
        h2 = np.sin(self.omega_0*1.2*(h1 @ self.W2))
        ar = np.tanh(h2 @ self.W_out)   # SIREN texture

        # ---- Direct triad with per-letter envelopes ----
        triad_direct = np.zeros(cs)
        sub_perletter = np.zeros(cs)
        hiss_perletter = np.zeros(cs)

        if self.current_triad is not None and len(self.current_root) == 3:
            f1, f2, f3 = self.current_triad
            letters = list(self.current_root)

            # Triangular envelopes for three overlapping syllables
            def env_seg(pos, start, end):
                center = 0.5 * (start + end)
                half = 0.5 * (end - start) + 1e-9
                return np.maximum(0.0, 1.0 - np.abs(pos - center) / half)

            env1 = env_seg(turn_pos, 0.00, 0.42)
            env2 = env_seg(turn_pos, 0.29, 0.71)
            env3 = env_seg(turn_pos, 0.58, 1.00)

            triad_direct = (env1 * np.sin(2*np.pi*f1*t)
                            + env2 * np.sin(2*np.pi*f2*t)
                            + env3 * np.sin(2*np.pi*f3*t))

            # Per-letter character
            from phoneme_grammar import VOICED, EMPHATIC, MANNER

            def char(c):
                if c not in PHONEMES:
                    return 0.0, 0.0
                voice = 1.0 if c in VOICED else 0.0
                emph = 1.0 if c in EMPHATIC else 0.0
                manner = MANNER.get(c, 0.5)
                sub_gain = voice * (1.0 - manner) * 0.5 + emph * 0.3
                hiss_gain = manner * 0.4
                return sub_gain, hiss_gain

            s0, h0 = char(letters[0])
            s1, h1c = char(letters[1])
            s2, h2c = char(letters[2])

            sub_perletter = (s0 * env1 + s1 * env2 + s2 * env3) * sub
            hiss_perletter = (h0 * env1 + h1c * env2 + h2c * env3) * pn

        # ---- Final mix ----
        mixed = (ar * 0.25                    # SIREN texture, subtle
                 + triad_direct * 0.60        # the phoneme triads
                 + sub_perletter * 0.15       # per-letter sub thump
                 + hiss_perletter * 0.10)     # per-letter hiss

        sat = np.tanh(np.sin(mixed*2.2)*2.8)
        mv = np.max(np.abs(sat)) + 1e-9
        fs = (sat / mv) * 0.98

        # Acoustic fingerprint
        if self.chunk_counter % 100 == 0:
            int16 = (np.clip(fs, -1.0, 1.0) * 32767).astype(np.int16)
            heard = decode_output(int16)
            self.log({"type": "decode", "heard": heard,
                      "intended_root": self.current_root})
            print(f"[decode] intended={self.current_root}  "
                  f"heard_as={heard}", file=sys.stderr, flush=True)

        return (np.clip(fs, -1.0, 1.0) * 32767).astype(np.int16)

'''

m = pattern.search(s)
if m:
    s = s[:m.start()] + new_method + s[m.end():]
    p.write_text(s)
    print(">> dialogue_engine.py: generate_chunk replaced")
else:
    print("!! could not find generate_chunk method")
