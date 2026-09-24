# Cosmic Phoneme Engine

A real-time audio engine that selects Arabic triliteral roots by
matching their acoustic fingerprints against live space-weather data.

**Live viewer:** https://zeitgeistksa-cyber.github.io/cosmic-arabic-noise/

## What it does

Every ~4.6 seconds:
1. Read live Schumann resonance, Kp index, solar wind speed
2. Normalize into a 4-dim cosmic vector
3. Pick the Arabic root whose 4-dim acoustic fingerprint best matches
4. Synthesize it as a layered noise texture
5. Log the turn with full cosmic context

6,150+ turns recorded and analyzed.

## Findings (all controlled)

**Note on cosmic dependence.** Earlier versions of this README claimed
that live cosmic state (Schumann, Kp, solar wind) correlates with
phoneme features at r = -0.46. That claim did not survive longer
sampling. The cosmic vector has been nearly constant across all
windows collected (Kp std = 0, schumann std = 1.4), and the apparent
correlations shrink toward zero as more windows accumulate. The
findings below are those that survive the extended run: they are
properties of the matcher's geometry, tested against fixed corpora,
and independent of any time-series correlation with space weather.


### 1. The acoustic attractor is stable over time

The matcher picks roots from a stable acoustic region across every
30-minute window. The region does not drift and does not depend on
cosmic variability, which is itself nearly constant on the timescales
sampled:

| cosmic dim | range over 20 windows | std |
|---|---|---|
| schumann | 35 -- 38 | 1.43 |
| kp | 1.67 -- 1.67 | 0.00 |
| wind | 304 -- 329 | 6.09 |

Because the cosmic vector barely moves, correlations between cosmic
state and phoneme features computed on short windows are dominated by
autocorrelation in the sequential data. When the window count grows,
the apparent correlations shrink toward zero. They are not reported
here as findings.

### 2. Position asymmetry is real
Root-initial emphatics: 15x over source frequency.
Root-final emphatics: 0 times in 6,150 turns.

### 3. Attractor is universal
English and Arabic phoneme tables converge on the same class:

    English top 10:  fff, sff, fsf, ffs, ssf, sfs, fss, vff, fvf, ffv
    Arabic  top 10:  zff, sff, fzz, ssf, sfh, khff, khsf, hff, fsq, sqf

### 4. Engine roots are anti-correlated with real Arabic
Spearman rho = +0.058 between engine preference and corpus frequency.
Engine #1 root (ضدد) has corpus rank 1404 of 1500.

## What this means

The engine does not speak Arabic. It speaks a universal acoustic
attractor at the intersection of:
- the log-prime triad mapping (bases 2, 3, 5)
- the hand-curated phoneme table
- live cosmic data

## Reproducing

    git clone https://github.com/zeitgeistksa-cyber/cosmic-arabic-noise
    cd cosmic-arabic-noise
    ./setup.sh
    ./start.sh

Analysis:
    python find_patterns.py
    python run_english_attractor.py
    python validate_against_corpus.py
    python position_control.py
    python correlation_control.py

## Live data
SunGeo.net, NOAA SWPC, NASA DONKI. Built with Termux on Android.

## 5. Real Arabic poetry avoids the matcher attractor

Four poems (Imru' al-Qais, Al-Mutanabbi, Nizar Qabbani, Mahmoud
Darwish) were root-extracted and tested against the current cosmic
vector. Result is significant under three independent extraction
strategies:

| Extractor | n | z-score |
|---|---|---|
| Strict | 15 | -2.17 |
| Loose | 29 | -2.02 |
| Middle | 19 | **-2.43** |

All significant at p<0.05. Real Arabic poetry systematically scores
*below* random roots against the matcher acoustic vector. The poem's
noise center-of-gravity is 26% lower than the corpus mean -- poetry
avoids the fricative region the engine's attractor prefers.

Combined with finding #4, this establishes: **the matcher
picks an acoustic region that real Arabic systematically avoids**,
across both corpus frequency and classical/modern poetry.

## 6. The Quran as a large corpus test

Full-text analysis of the Quran (6236 ayah lines,
31660 root instances, 2302
distinct roots) against the same matcher attractor:

| Metric | Value |
|---|---|
| z-score vs random | -55.084 |
| Emphatic at pos1 | 2.09% |
| Emphatic at pos3 | 1.94% |
| Ratio pos1/pos3 | 1.08 |
| F1 / F2 / F3 / CoG | 0.452 / 1.350 / 2.462 / 0.163 |

Comparison with earlier results:

| Corpus | n | z-score | Emph pos1 |
|---|---|---|---|
| Quran | 31660 | -55.08 | 2.09% |
| Poems (combined) | 19 | -2.43 | 0.00% |
| Engine attractor | 6150 | -- | 27.50% |

## 7. Why the sound is pleasant — acoustic analysis

The engine's triads are not tuned to any scale. Yet they sound consonant. Analysis with Plomp-Levelt roughness, harmonic decomposition, and amplitude-modulation spectroscopy shows why:

| Property | Value | Meaning |
|---|---|---|
| Mean roughness | 0.0000 | Tones do not beat — no sensory dissonance |
| Missing fundamental fit | 100% | Triads synthesize a phantom bass note |
| Odd harmonic fraction | 100% | Wavefolder is odd-symmetric — clarinet-like timbre |
| AM power in 0.5-4 Hz | 70.8% | Output sits in the universal acoustic communication band |

Reference roughness values (same analysis method):

| Interval | Ratio | Roughness |
|---|---|---|
| Octave | 2.00 | 0.0007 |
| Fifth | 1.50 | 0.0238 |
| Major third | 1.25 | 0.1119 |
| Whole tone | 1.125 | 0.1783 |
| Semitone | 1.06 | 0.1581 |

The engine's triads score below every familiar Western interval. That happens because the three tones are separated by hundreds of hertz — far enough that no two of them fall within the same critical band, so beating is impossible.

### The tuning system

The interval ratios are not musical in the classical sense:

- f2/f1 is approximately 5.7455, best rational approx 178/31 — irrational
- f3/f1 is approximately 18.6591, best rational approx 597/32 — irrational
- f3/f2 is approximately 3.2476, best rational approx 13/4 — familiar

The bottom-to-middle and bottom-to-top intervals have no small-integer relationship. The ear cannot file them as any known chord. But the middle-to-top interval, 13/4, is close to two octaves plus a major third — a relation the auditory system can parse.

The result is a novel-but-anchored tuning system: two unfamiliar intervals supported by one recognizable one. This is the narrow band between too-consonant (boring) and too-dissonant (noise) that the ear perceives as interesting harmony.

The pleasantness is not a design goal. It emerges from three mathematical choices that were made for other reasons:

1. Prime bases 2, 3, 5 in the logarithmic triad mapping
2. Divisors 7, 9, 11 (irrational spacing)
3. Odd-symmetric wavefolder

Each produces a specific property. Together, they produce a sound that sits at the threshold of the familiar and the strange.

### Amplitude modulation

70% of the amplitude-envelope power concentrates in the 0.5-4 Hz band — the range every acoustic animal uses for communication. This is by design: the envelopes span seconds, the roots change every 9.2 seconds, and the 2 Hz LFO modulates the letter channels. The output lives in the same band as speech, whale song, cricket chirps, and human music.
