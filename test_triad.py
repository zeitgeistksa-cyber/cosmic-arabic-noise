import numpy as np, wave
from phoneme_table import root_to_log_triad
SR = 44100
DUR = 3.0
N = int(SR * DUR)
t = np.arange(N) / SR
for root in ["ضدد", "بدر", "طرد", "نور"]:
    f1, f2, f3 = root_to_log_triad(root)
    sig = (0.4 * np.sin(2*np.pi*f1*t) +
           0.3 * np.sin(2*np.pi*f2*t) +
           0.3 * np.sin(2*np.pi*f3*t))
    sig = np.tanh(sig * 1.5) * 0.9
    int16 = (sig * 32767).astype(np.int16)
    with wave.open(f"triad_{root}.wav", "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(int16.tobytes())
    print(f"{root}: f1={f1:.1f} f2={f2:.1f} f3={f3:.1f}")
