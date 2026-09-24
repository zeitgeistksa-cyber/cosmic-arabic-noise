"""Root-to-feature extraction, matching the model's own representation."""
import numpy as np
from pathlib import Path
import sys

# Import the project's phoneme table
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from phoneme_table import PHONEMES, root_to_log_triad
from phoneme_grammar import VOICED, EMPHATIC, MANNER


def root_to_features(root):
    """Return a feature dict for one root.

    Includes:
      - position features (which letter is where)
      - acoustic averages (F1, F2, F3, CoG)
      - triad frequencies
      - phoneme grammar counts
    """
    if not root or len(root) != 3:
        return None

    letters = list(root)
    feats = {
        "root": root,
        "c0": letters[0], "c1": letters[1], "c2": letters[2],
        "voice_count": sum(1 for c in letters if c in VOICED),
        "emph_count": sum(1 for c in letters if c in EMPHATIC),
        "manner_avg": float(np.mean([MANNER.get(c, 0.5) for c in letters])),
        "c0_voice": 1 if letters[0] in VOICED else 0,
        "c1_voice": 1 if letters[1] in VOICED else 0,
        "c2_voice": 1 if letters[2] in VOICED else 0,
        "c0_emph": 1 if letters[0] in EMPHATIC else 0,
        "c1_emph": 1 if letters[1] in EMPHATIC else 0,
        "c2_emph": 1 if letters[2] in EMPHATIC else 0,
    }

    # Acoustic fingerprint
    if all(c in PHONEMES for c in letters):
        f1s, f2s, f3s, cogs = [], [], [], []
        for c in letters:
            F1, F2, F3, CoG = PHONEMES[c]
            f1s.append(F1); f2s.append(F2); f3s.append(F3); cogs.append(CoG)
        feats["mean_F1"] = float(np.mean(f1s))
        feats["mean_F2"] = float(np.mean(f2s))
        feats["mean_F3"] = float(np.mean(f3s))
        feats["mean_CoG"] = float(np.mean(cogs))

    # Triad
    triad = root_to_log_triad(root)
    if triad:
        feats["triad_f1"] = float(triad[0])
        feats["triad_f2"] = float(triad[1])
        feats["triad_f3"] = float(triad[2])
        feats["triad_spread"] = float(triad[2] - triad[0])

    return feats


def features_to_dataframe(roots):
    """Convert a list of roots to a pandas DataFrame."""
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas required: pip install pandas")
    rows = [root_to_features(r) for r in roots]
    rows = [r for r in rows if r is not None]
    return pd.DataFrame(rows)
