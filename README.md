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

### 1. Cosmic state correlates with acoustic features
| correlation | r | null baseline |
|---|---|---|
| schumann <-> manner_avg | -0.458 | +0.017 |
| wind <-> manner_avg | -0.396 | - |
| kp <-> voice_count | +0.284 | - |
| kp <-> emph_count | -0.276 | - |

Null test: 5 runs of random cosmic x random roots -> |r| < 0.05 in all.

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
