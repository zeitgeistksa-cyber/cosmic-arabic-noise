"""English consonants with matched acoustic values, same dimensions as Arabic table."""
ENGLISH_PHONEMES = {
    "p": [0.35, 1.10, 2.30, 0.10],   # matched to ب
    "b": [0.35, 1.10, 2.30, 0.10],
    "t": [0.40, 1.70, 2.60, 0.56],   # matched to ت
    "d": [0.35, 1.70, 2.60, 0.06],   # matched to د
    "k": [0.40, 1.60, 2.50, 0.31],   # matched to ك
    "g": [0.35, 1.60, 2.50, 0.20],
    "f": [0.40, 1.20, 2.40, 0.88],   # matched to ف
    "v": [0.35, 1.20, 2.40, 0.80],
    "s": [0.40, 1.70, 2.60, 0.94],   # matched to س
    "z": [0.35, 1.70, 2.60, 0.81],   # matched to ز
    "sh": [0.40, 1.90, 2.60, 0.50],  # matched to ش
    "th": [0.38, 1.60, 2.50, 0.75],  # matched to ث
    "dh": [0.35, 1.60, 2.50, 0.69],  # matched to ذ
    "m": [0.30, 1.10, 2.20, 0.00],   # matched to م
    "n": [0.30, 1.60, 2.50, 0.00],   # matched to ن
    "l": [0.40, 1.20, 2.60, 0.00],   # matched to ل
    "r": [0.50, 1.30, 2.40, 0.15],   # matched to ر
    "w": [0.35, 0.80, 2.20, 0.00],   # matched to و
    "y": [0.30, 2.20, 2.90, 0.00],   # matched to ي
    "h": [0.50, 1.40, 2.40, 0.38],   # matched to ه
}
ENGLISH_LETTER_INDEX = {ch: i+1 for i, ch in enumerate(ENGLISH_PHONEMES.keys())}

def root_to_log_triad(root):
    """Same logarithmic formula as Arabic table — primes 2,3,5."""
    if len(root) not in (2, 3):
        return None
    try:
        idxs = [ENGLISH_LETTER_INDEX[c] for c in root]
    except KeyError:
        return None
    bases = [2.0, 3.0, 5.0][:len(root)]
    divs = [7.0, 9.0, 11.0][:len(root)]
    start = [55.0, 110.0, 220.0][:len(root)]
    return tuple(start[i] * (bases[i] ** (idxs[i] / divs[i]))
                 for i in range(len(root)))
