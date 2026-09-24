"""cosmic-arabic-noise ML library.

Loads data from the experiments directory and exposes it as
standard ML-friendly formats: pandas DataFrames, numpy arrays,
and torch datasets (if torch is installed).
"""
from .datasets.roots import load_engine_turns, load_quran_roots, load_poem_roots
from .datasets.features import root_to_features, features_to_dataframe
from .datasets.cosmic import load_cosmic_series

__all__ = [
    "load_engine_turns",
    "load_quran_roots",
    "load_poem_roots",
    "root_to_features",
    "features_to_dataframe",
    "load_cosmic_series",
]
