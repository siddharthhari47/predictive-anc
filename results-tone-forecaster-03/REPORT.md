# Tone forecaster study 03: a ceiling on the joint check's tie fallback

**Reference-signal prediction only.** Every number is how well a forecaster predicts the recording microphone's own signal 20 ms or 120 ms ahead. Nothing was played, no acoustic path was modelled, and no attenuation at an ear was measured. No real-world cancellation is claimed.

**No test was run.** No capped candidate met the development rule, so the frozen protocol (`protocol.json`) has no candidate. No fresh recordings were chosen or downloaded, and nothing was scored on test material. Everything below is development material: the eight study-01 development recordings, the 44 development synthetic scenes and 8 new development buzz scenes.

## Answer

1. **Does a cap remove the remaining boosts? No.** The joint check + gate had 25 boosts on development material (a third-octave band 1 dB or more louder: 1 on the recordings, 24 in late synthetic windows). Caps of 1, 2 and 3 dB had 25 as well. A cap of 0.5 dB, which switches the fallback off, had 24. It removed the 4 buzz_am boosts and added 3 elsewhere, on drifting, harmonic and single tones, where the fallback had kept the tones alive.
2. **Is the tone gain kept? Only by the caps that change nothing.** Median tone-bin gain over both horizons: joint 5.56 dB, v2 3.15 dB. Cap 3 kept 5.56 dB, because it never once set the limit. Cap 2 kept 3.69 dB, cap 1 and cap 0.5 kept 2.50 dB, under v2. The caps of 2 dB or less lost tone gain on one file, WWS_Aircompressor, whose tones fell from 8.1 / 7.1 dB to as little as 1.7 / 0.9 dB.

| Development material | v2 + gate | Joint + gate | Cap 0.5 | Cap 1 | Cap 2 | Cap 3 |
|---|---:|---:|---:|---:|---:|---:|
| Boosts, 1 dB (recordings + late synthetic) | 9 + 45 | 1 + 24 | 1 + 23 | 1 + 24 | 1 + 24 | 1 + 24 |
| Near-boosts, 0.5 dB | 74 | 40 | 36 | 38 | 40 | 40 |
| Tone bins, median of both horizons (needed 4.35) | 3.15 | 5.56 | 2.50 | 2.50 | 3.69 | 5.56 |
| Whole band, median of both horizons | 0.98 | 1.59 | 1.01 | 1.43 | 1.59 | 1.59 |
| Synthetic objective (dB) | 7.02 | 7.05 | 5.85 | 6.58 | 7.05 | 7.05 |
| Checks failed | | | d, e, f | a, d, e | a, d | a |

Full tables: `development/dev-01/DEVELOPMENT.md`. Rule: in the same file and in `protocol.json`.

## Where the joint check's boosts come from

The fallback is not where they come from on this material. Of the joint check's 25:

- **14 come from sudden changes.** source_change_9s 6, tone_appears_9s 5, tones_stop_9s 3. The sound changes at 9 s and the scored windows start at 8 s. The check takes medians over the last 16 checks, 8 s of history, so it can't react in time. v2 + gate has exactly the same counts on these scenes.
- **5 come from the gate.** On the buzz scenes the joint check had 2 boosts without the gate and 7 with it. The band check measures each setting's output before the gate, so it can't see what the gate's on/off switching adds.
- **3 are on drifting tones** (drifting_tones 1, wander_fast 2), the case the fallback was added for. They stay with or without the cap.
- **1 comes from the start.** The only recording boost (+1.4 dB, Mains_hum_60_Hz, 20 ms) falls before the check's first decision, about 6.5 s in, while it still uses its start setting. No cap can reach it.

Caps acted where the fallback was doing useful work. Counted over each whole recording, the fallback set the limit in 371 of 1281 decisions. Cap 1 left only "no output" in 79, and 78 of those were on WWS_Aircompressor, which is where the tone gain went. The two mains clips never reach a decision at all.

## Whether this explains Buzzing_Speakers.ogg

It does not say. The study-02 notes named the fallback as the likely cause of that file's two boosts. That file is seen and was not used here, so this study can't confirm or rule that out for that file. The development buzz scenes, built to look like it, point at the gate instead.

## Timing

Worst-run 99th-percentile compute time per 10 ms block was 11 to 15 ms for every check variant, and 7.8 ms for the study-01 bank. The median over runs was 6.7 to 7.0 ms. Study 02 measured 4.1 ms for the joint check. A training job from another project was using the processor during this run, so these figures say more about the machine than the method. The rule compared each cap with the joint check in the same run, and all passed that check. The joint check needs a timing run on a quiet machine before it goes anywhere near the live engine.

## What was frozen

`protocol.json`: the development run, the rule and its table, the candidates and comparators, the decision (no candidate), and SHA-256 checksums of fifteen code files (study 02's twelve plus `tone_cap.py`, `forecaster_study_03.py` and `forecaster_report_03.py`). Trials before the rule are in `diagnosis/` (see its README). Nothing in study 01's or study 02's folders or frozen code was changed.

Created 19 Oct 2026 by Claude.
