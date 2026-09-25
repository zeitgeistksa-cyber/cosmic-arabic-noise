import numpy as np
from scipy.io import wavfile

SR = 44100
DUR = 30
t = np.linspace(0, DUR, int(SR * DUR), False)

def drone(freq, detune):
    return 0.3*np.sin(2*np.pi*freq*t) + 0.3*np.sin(2*np.pi*(freq+detune)*t)

base = drone(55, 0.7)
tritone = 0.2*np.sin(2*np.pi*(55 * 2**(6/12))*t)
cluster = 0.15*np.sin(2*np.pi*110*t) + 0.15*np.sin(2*np.pi*(110 * 2**(1/12))*t)

lfo = 0.5 + 0.5*np.sin(2*np.pi*0.1*t)
drone = base * lfo

whine = np.zeros_like(t)
for start in range(0, DUR, 3):
    idx = (t >= start) & (t < start+2)
    freq = np.random.uniform(8000, 12000)
    whine[idx] = 0.05*np.sin(2*np.pi*freq*t[idx])

noise = np.random.randn(len(t)) * 0.02
gate = (np.sin(2*np.pi*0.5*t) > 0.8).astype(float)
noise *= gate

shepard = np.zeros_like(t)
for k in range(5):
    f = 100 * 2**(k + (t % 4)/4)
    shepard += 0.02*np.sin(2*np.pi*f*t)
shepard *= np.sin(np.pi*(t % 4)/4)

mix = drone + tritone + cluster + whine + noise + shepard
mix = mix / np.max(np.abs(mix)) * 0.7
fade = np.minimum(1, t/2) * np.minimum(1, (DUR-t)/2)
mix *= fade

wavfile.write("cosmic_annoyance.wav", SR, (mix*32767).astype(np.int16))
