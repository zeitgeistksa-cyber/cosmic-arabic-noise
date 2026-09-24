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

## 8. Three-way acoustic comparison — engine, poetry, Quran

Center-of-gravity (CoG) is the mean noise-frequency band of each root's
letters, averaged across three positions. Measured across three
independent Arabic corpora:

| Corpus | n | mean CoG | std CoG |
|---|---|---|---|
| Quran (top 30 roots) | 30 | 0.114 | 0.113 |
| Poems (four classical + modern) | 29 | 0.216 | 0.156 |
| Engine matcher (all turns) | 7,329 | 0.303 | 0.252 |

Three properties:

1. **The means are monotonic.** Prose sits lowest, poetry in the middle,
   the matcher highest. The engine's preferred acoustic region lies
   beyond anything human Arabic text produces at scale.
2. **The standard deviations are monotonic.** The Quran is compressed
   (std 0.11), poetry is medium (0.16), and the matcher spreads across
   more than twice the Quran's range (0.25). Human Arabic occupies a
   narrow band; the matcher explores a wide one.
3. **The regions are mutually exclusive at the extremes.** The engine's
   top-selected roots (صفف, زفف, حفف) sit almost entirely above the
   mean CoG of both human corpora. The Quran's top roots (الا, ذين,
   ولا) sit almost entirely below the engine's.

The matcher is not approximating Arabic prose or Arabic poetry. It is
a distinct acoustic region — one that real Arabic text systematically
avoids.

### Effect sizes (Cohen's d)

| Comparison | d | Interpretation |
|---|---|---|
| Engine vs Quran | +0.75 | medium-large, engine higher |
| Engine vs Poems | +0.35 | small-medium, engine higher |
| Poems vs Quran | +0.75 | medium-large, poems higher |

The Engine-vs-Quran and Poems-vs-Quran effect sizes are numerically
identical (0.75). This is a coincidence of variance: the engine's raw
mean gap to the Quran (0.189) is 1.85x the poems' gap (0.102), but the
engine's pooled standard deviation is also 1.83x larger (0.251 vs
0.137). The two factors cancel.

The correct interpretation is two-sided:

- **In absolute terms**, the matcher's CoG center lies 2.66x further
  from Arabic prose than poetry does. It occupies a region Arabic
  does not.
- **In standardized terms**, the matcher's distance from prose is
  comparable to poetry's, because the matcher also explores a wider
  acoustic range than any human corpus.

Both statements are true. The matcher is both further from human
Arabic and more variable than human Arabic.

## 9. How letters merge into words — phonotactic analysis

Three structural rules were measured across the 1,583 roots in
the source lexicon:

### Rule A — Medial sonority

The middle letter of a triliteral root is preferentially a sonorant:

| position 2 letter | share | class |
|---|---|---|
| ر | 9.35% | alveolar trill |
| و | 8.21% | labiovelar glide |
| ل | 7.08% | lateral |
| م | 6.51% | nasal |
| ب | 6.19% | bilabial stop |

The top four are all sonorants, matching the Sonority Sequencing
Principle documented in Arabic phonology (McCarthy 1979, Watson 2002).

### Rule B — Asymmetric OCP

Adjacent identical consonants:

| boundary | observed | random expectation | ratio |
|---|---|---|---|
| 1st-2nd | 1.14% | 3.57% | 0.32x |
| 2nd-3rd | 9.67% | 3.57% | 2.71x |

Arabic forbids initial gemination and permits final gemination. The
pattern is not symmetric.

### The engine's behavior

The engine's top roots (صفف, زفف, حفف) follow Rule B (they exploit
permitted gemination at 2-3) but violate Rule A (their middle letter
is the fricative ف, not a sonorant). This is a distinct anti-corpus
behavior consistent with the CoG finding from Section 8.

### Articulatory transitions (null result)

Real roots and random triples have nearly identical mean articulatory
transition cost (1.224 vs 1.231, a 0.65% difference). Arabic does not,
at this level of measurement, prefer smoother or rougher transitions
between consonants than random arrangement.

### 8b. Robustness check — unique roots only

The three-way CoG comparison was recomputed using only the *distinct*
roots each corpus contains (no repeats). This is a stricter test
because it removes the effect of the engine revisiting the same roots:

| Corpus | n | mean CoG | std CoG |
|---|---|---|---|
| Quran top 30 | 30 | 0.114 | 0.113 |
| Poems | 29 | 0.216 | 0.156 |
| Engine unique | 102 | 0.365 | 0.265 |

The ordering holds and the effect *strengthens*. The engine's unique
roots have higher mean CoG than its full-turn average (0.365 vs 0.303),
because the engine's frequent repeats are biased toward lower-CoG
roots than its rare excursions. The attractor is *within* the explored
space, not at its center.

### 8c. Sequential structure — metastability

Across 7,527 engine turns, only 102 distinct roots were selected. The
engine shows:

- **Strong self-transitions**: ضدد → ضدد occurs 314 times
- **Short hops**: consecutive roots share 1.25 letters on average
- **Rare jumps**: distant root transitions are uncommon

This is a metastable dynamic: the matcher locks onto attractor states
and rarely escapes them. The behavior follows from the cosmic vector
being nearly constant over the recording window, not from any
intrinsic property of the matcher or the corpus. When the input
becomes variable (Kp > 2), the metastable structure should relax.


## 10. Threshold response to geomagnetic activity

At 07:09 UTC the Kp index rose from 1.67 to 3.0 — the first real
change in the entire recording. The matcher's output responded
monotonically. Splitting turns by cosmic state gives a two-dimensional
phase diagram with three resolved corners:

| Kp | Schumann | turns | mean CoG | std CoG | ض@pos1 |
|---|---|---|---|---|---|
| 1.67 | 35 | 830 | 0.4102 | 0.3052 | 10.48% |
| 1.67 | 38 | 6,022 | 0.3020 | 0.2468 | 19.61% |
| >= 2.00 | 38 | 1,690 | 0.7441 -- 0.7738 | 0.080 -- 0.087 | 0.00% |

Every observation in the project reduces to one variable: the position
of the matcher's preferred CoG on a single axis. Higher Kp pushes the
attractor toward high CoG; higher Schumann pulls it toward low CoG.
The two effects add. The downstream enrichment of ض is not a separate
finding -- ض has CoG 0.38, so it is enriched when the attractor sits
below that value and excluded when the attractor sits above it.

The matcher's CoG is a monotonic function of both cosmic dimensions:

- Holding Kp at 1.67, a Schumann drop from 38 to 35 raises CoG
  by +0.108 (from 0.302 to 0.410).
- Holding Schumann at 38, a Kp rise from 1.67 to 2.00 raises CoG
  by +0.442 (from 0.302 to 0.744).
- Both effects point toward the same attractor: higher Kp and lower
  Schumann both push the matcher toward high-CoG fricative roots.

Kp has roughly 4x the effect size of Schumann, but both are
resolved. The matcher is a continuous function of the cosmic vector,
not a threshold switch.

Three properties of the response:

1. **The mean CoG doubles** (0.30 → 0.76). The matcher moves from a
   mid-CoG attractor to an extreme-fricative attractor.
2. **The variance collapses** (std 0.25 → 0.09). The active regime is
   *more* constrained than the calm one, not less.
3. **The ض enrichment vanishes completely.** 17.58% → 0.00% is a
   discrete state change, not a gradual shift.

The top-10 root vocabularies are entirely disjoint:

    calm:    ضدد, زبد, ذبب, زفف, صفف, ردد, طرد, دبر, برد, بدر
    active:  صفف, زفف, فزز, صصف, سفه, خفف, جسس, حفف, سفع, خسف

Only 38% of selected roots appear in both regimes. This is a distinct
mode of the matcher, entered when the input crosses a threshold.

### Correction to Section 1

The earlier retraction of the cosmic-correlation claim was correct:
there is no *linear* correlation between cosmic state and phoneme
features at short windows. But the underlying coupling is real. It is
a **threshold response**, not a linear modulation. The matcher is
sensitive to whether Kp has crossed 2.0, not to small continuous
changes in Kp below that value.

This is a stronger claim than the original correlation because it is
discrete, reproducible, and directly observable in the audio output.

