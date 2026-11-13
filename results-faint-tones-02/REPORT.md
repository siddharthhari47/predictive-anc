# Faint-hum detector, frozen test (results-faint-tones-02)

**Verdict: FAIL, 2 of 5 bars passed.** It invents no tones in noise and very few in voice-like sound, and it locks onto hums as loud as Sid's fan. It is not reliable at the fainter level the bar asked for. The rooms bar failed because of a merge bug, fixed after the test. The timing bar failed because the test measured without the taper cache the live engine uses. All synthetic; no audio was played or recorded for this study.

Run 01 crashed before saving any score (44.1 kHz files; see `results-faint-tones-01/RUN_FAILED.md`). This is the rerun with the same settings, seeds and bars. Script: `research-tools/faint_tones_study.py`. Detector: `anc_lab/faint_tones.py`.

## Why a second detector

The frozen detector is a multitaper F-test. It asks whether a window holds one phase-steady sinusoid. Sid's fan hum (200 Hz, `results-live-listen-02`) stands +17.6 to +20 dB over the floor, but it wanders about 2 Hz. On Sid's 13 s recording, its F score near 200 Hz had a median of 5.8 against a pass mark of 27.7 (1 s window). With 2 or 4 s windows, it never came within half the pass mark. Longer listening does not rescue it, because the hum is not phase-steady.

The new detector asks a different question. Is there a narrow peak in the averaged spectrum that stays put for seconds?

- **Peak:** a 4 s Welch spectrum (1 s Hann pieces), with the peak at least 7 dB over the ±20 Hz median floor and no wider than 6 Hz at half power.
- **Hold:** found in 20 of the last 24 updates (one every 0.25 s), within 2 Hz.
- **Release:** after 8 misses.

It only adds tones the F-test did not find. The settings were chosen on Sid's recording and synthetic seed 100, then frozen in `protocol.json` before any test seed was scored.

## Bars

| Bar | Result |
|---|---|
| white and pink noise: no faint tone active in any update, on every seed | pass |
| voice-like sound (with and without background noise): faint tone active in at most 10% of updates on at least 8 of 10 seeds | pass |
| hum at -15 dB in pink noise: locked within 3 Hz of 200 Hz in at least 80% of updates after 15 s, and first lock by 15 s, on at least 8 of 10 seeds | **FAIL** |
| the 14 stored rooms: every tone the frozen detector reports is still reported at every update | **FAIL** |
| one combined update (both detectors) p99 at most 2 ms on this machine, CPU only | **FAIL** |

Hum bar: 4 of 10 seeds met it (needed 8). Timing bar: combined update median 5.24 ms, p99 10.42 ms, uncached, against 2 ms. Rooms bar: tg-036-r0 lost a frozen tone in 6 updates.

## Synthetic cases (10 fresh seeds, 60 s each)

Hum levels are tone power against noise power inside 35–350 Hz. "Any tone" is the share of updates where the faint detector reported something. "Locked" is the share of updates after 15 s with a tone within 3 Hz of 200 Hz.

| Case | Any tone, median | Locked, median | Seeds ≥ 80% locked | First lock, median |
|---|---|---|---|---|
| white | 0% (max 0%) | – | – | – |
| pink | 0% (max 0%) | – | – | – |
| voice | 0% (max 5%) | – | – | – |
| voice+pink | 0% (max 13%) | – | – | – |
| hum -25 dB in pink | 0% (max 0%) | 0% | 0/10 | never |
| hum -25 dB under voice | 4% (max 10%) | 0% | 0/10 | never |
| hum -20 dB in pink | 0% (max 0%) | 0% | 0/10 | never |
| hum -20 dB under voice | 0% (max 12%) | 0% | 0/10 | never |
| hum -15 dB in pink | 63% (max 86%) | 79% | 5/10 | 8.88 s |
| hum -15 dB under voice | 2% (max 21%) | 2% | 0/10 | 39.00 s |
| hum -10 dB in pink | 86% (max 86%) | 100% | 10/10 | 8.75 s |
| hum -10 dB under voice | 61% (max 85%) | 73% | 4/10 | 10.50 s |

Under voice-like sound, the hum is masked at −15 dB and below, and only partly found at −10 dB. The voice material is a synthetic stand-in: gliding four-harmonic syllables, not real speech.

## Real recordings in external-audio/ (reported only, no bar)

The faint detector reported at least one tone on 14 of 14 files. On 7 of them, every reported frequency sat within 3 Hz of an after-the-fact reference peak (at least 10 dB over ±10 Hz). On 5, none did; those may be real weaker lines or false ones, and this study cannot tell which. Per-file lists are in `results.json`.

## Found after the test (diagnosis, not part of the verdict)

- **Sid's hum on this scale.** In the listen-02 measure (0.25 Hz bins, 100 Hz median floor), synthetic hums read +4.9 / +8.8 / +13.7 / +18.6 dB at −20 / −15 / −10 / −5 dB. Sid's fan read +17.6 (shared) and +20.0 (exclusive), and Sid's suppressed recording +13.1. So Sid's hum is at or above the −10 dB case, which locked on 10 of 10 seeds, all by 8.75 s. Sid's recording locked at 9.25 s in development. The live window has not been run with this detector.
- **Merge bug.** The combined list was sorted by frequency and then cut to 6, so a faint tone could push out the highest strict one (tg-036: 288.1 Hz dropped for 156.4 Hz). It is fixed: strict tones keep their places and faint ones only fill free slots. After the fix, no stored room loses a strict tone at any update. There is a new unit test.
- **Timing with the taper cache,** one stored room. Strict alone: median 0.88, p99 1.24 ms. Faint alone: median 0.57, p99 0.88 ms. Combined: median 1.48, p99 1.89 ms. Strict uncached: median 3.96 ms. The faint part runs once per 0.25 s, so on update blocks it adds about 0.6–0.9 ms. Whether the live runner still meets its 5 ms reserve has not been tested.

## What changed in the app

`tune --engine faint` (or `tune-faint.bat`) runs the smoothed engine with this detector added. The default stays `smoothed`, because the detector failed its frozen test and its live timing is unmeasured.
