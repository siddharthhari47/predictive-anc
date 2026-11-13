# Tone forecaster study 05: test on fresh material

**Reference-signal prediction only.** Every number is how well a forecaster predicts the recording microphone's own signal 20 ms or 120 ms ahead. Nothing was played, no acoustic path was modelled, and no attenuation at an ear was measured. No real-world cancellation is claimed.

**Independence.** Independent of all earlier work in this project: the eight recordings were chosen on 19 Oct 2026 by their Commons title, description, length, licence and author only, from a metadata search kept in results-tone-forecaster-05/fresh-metadata. None was downloaded, played or analysed before this protocol was frozen. No author also made a development recording, a study-01 recording or a study-02 fresh recording, and none comes from the Work With Sounds collection that supplied three development recordings. Four were chosen because their descriptions say the sound starts, stops or changes speed (the fan, the screwdriver and the two train start-ups), since this study is about sudden changes and starts.

## Answer

Primary question: Only if a candidate is frozen. On fresh material the project has never used: (1) does the frozen candidate + gate have fewer late boost windows (a band 1 dB or more louder, either horizon) than joint + gate on the fresh synthetic change scenes? (2) On the fresh recordings, does it have no more third-octave boosts and no more whole-band boosts than joint + gate? (3) Is its median tone-bin gain at 20 ms, over the fresh acoustic recordings with reference tones, above v2 + gate's? Answered separately. Secondary, reported but not part of the question: the whole-band gain against joint + gate, which the fades raised on two development recordings.

**Yes.**

1. **Fewer boosts where the sound changes suddenly? Yes.** On the 18 fresh change scenes fade0.1_linear + gate has 14 late windows with a band 1 dB or more louder, against 25 for the joint check + gate and 25 for v2 + gate (both horizons).
2. **No more boosts on the fresh recordings? Yes.** Third-octave boosts 2 against 2 for the joint check + gate and 2 for v2 + gate; whole-band boosts 0, 0 and 0. Near-boosts (0.5 dB or more): 3, 3 and 4.
3. **Tone gain still above v2's? Yes.** Median tone-bin gain at 20 ms over the 6 fresh acoustic recordings with reference tones: 2.2 dB for fade0.1_linear + gate, 2.0 dB for the joint check + gate and 0.9 dB for v2 + gate.

Against the joint check + gate, per file at 20 ms: ahead at the tones on 4 of 6 files, behind on 2 (exact sign test p = 0.688), differences -0.5 to 0.6 dB; ahead on the whole band on 5 of 7 files.
Against v2 + gate, per file at 20 ms: ahead at the tones on 2 of 6 files, behind on 4 (exact sign test p = 0.688), differences -3.2 to 2.8 dB; ahead on the whole band on 4 of 7 files.

With this few files the medians are coarse; the per-file tables are the evidence. The reference tones are chosen with hindsight (lines 10 dB above their +-10 Hz median), which flatters the line finder; the whole-band score has no such bias.

## What was frozen before this run

- Development run: `results-tone-forecaster-05/development/dev-01` (its DEVELOPMENT.md). Rule:

  > Written after the diagnostic trials on development material (results-tone-forecaster-05/diagnosis) and before the formal development run. Candidates, all gated: the joint band check of study 02 with each tone fading in and out of every output setting instead of switching: raised-cosine fades of 0.05, 0.1 and 0.2 s; a 0.1 s linear fade; a 0.1 s fade plus a 0.3 s cross-fade when the check changes its setting; and a 0.1 s fade with a 0.2 s start floor instead of 0.1 s. Development material: the eight study-01 development recordings, the 44 development synthetic scenes and study 03's 8 buzz scenes. A boost is a third-octave band 1 dB or more louder; a near-boost 0.5 dB or more; both are counted over development recordings (either horizon) plus late synthetic windows. The change scenes are tone_appears_9s, tones_stop_9s and source_change_9s. Eligible only if: (a) fewer boosts than joint + gate; (b) fewer boosts on the change scenes than joint + gate; (c) no more near-boosts than joint + gate; (d) no more whole-band boosts (whole 35-350 Hz band below -0.5 dB on a development recording) than joint + gate; (e) the tone gain over v2 is kept: the median, over development acoustic recordings with reference tones, of the tone-bin gain averaged over both horizons is at least v2 + gate's plus half of the amount by which joint + gate exceeds v2 + gate; (f) the median whole-band gain over development acoustic recordings, averaged over both horizons, is at least joint + gate's minus 0.1 dB; (g) the mean synthetic objective is at least joint + gate's minus 0.5 dB and its synthetic windows below -0.5 dB are no more than joint + gate has; (h) its own compute time per 10 ms block at the 99th percentile, median over runs, is within 0.5 ms of joint's in the same run. Study 03 used the worst run instead, which swings with the shared machine's load: in the study-05 trial the fade code with one-block fades (the joint check's own forecasts) was 2.5 ms slower than the joint check on its worst run, while timed side by side in one process, after the output step was made an array step, it is about 0.1 ms slower on average and 0.3-0.4 ms at the median 99th percentile (diagnosis timing01, timing02). Among eligible candidates, pick the one with the fewest boosts, then the fewest near-boosts, then the higher tone-bin median. If none is eligible, nothing is frozen: the joint check and v2 are unchanged, and there is nothing to test.

- Frozen candidate: **fade0.1_linear** ({"kind": "react", "nb_tau": 0.0, "lines": true, "options": {"fade_in_seconds": 0.1, "fade_out_seconds": 0.1, "shape": "linear"}})
- Comparators: predict nothing; v2 with and without its realized-error gate (today's engine); ridge AR adapted on each file's first 40% (prefix AR) and refitted every second on past samples (online AR); the study-01 line-finder bank (bank_wide_lines); and the study-02 joint check (joint), with and without the gate.
- Fresh recordings scored (7): Ventilador.ogg, Akkuschrauber_–_Cordless_Screwdriver.ogg, ÖBB_Taurus_Start-Up.ogg, Son_démarrage_Mp14-8.ogg, Elektrorasur-01.ogg, Propeller-plane-flying-steady-01.wav, Sewerage_pumping_station_(Starnberg-Leutstetten_PW83)_c.ogg. Missing, not replaced: Noise-Pollution-Filters-Bird-Communities-Based-on-Vocal-Frequency-pone.0027052.s001.ogg.

## All methods on the fresh recordings

| Method | Tone bins median, 20 / 120 ms | Whole band median, 20 / 120 ms | Whole-band boosts | Third-octave boosts (>= 1 dB) | Near-boosts (>= 0.5 dB) | Synthetic objective | Synthetic windows < -0.5 dB | Synthetic late boosts (>= 1 / >= 0.5 dB) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Predict nothing | 0.0 / 0.0 | 0.00 / 0.00 | 0 | 0 | 0 | — | — | — |
| v2, no gate | 0.9 / 0.6 | 0.11 / 0.00 | 0 | 3 | 5 | — | — | — |
| v2 + gate | 0.9 / 0.6 | 0.11 / 0.01 | 0 | 2 | 4 | — | — | — |
| AR adapted on prefix | 5.1 / 3.2 | -0.21 / -0.28 | 2 | 12 | 13 | — | — | — |
| AR refitted online | 6.0 / 2.9 | 1.16 / 0.14 | 1 | 11 | 11 | — | — | — |
| bank_wide_lines, no gate | 4.2 / 1.6 | 0.94 / 0.20 | 0 | 6 | 7 | — | — | — |
| bank_wide_lines + gate | 4.2 / 1.6 | 0.94 / 0.25 | 0 | 5 | 6 | — | — | — |
| joint, no gate | 2.0 / 0.9 | 0.42 / 0.06 | 0 | 2 | 2 | — | — | — |
| joint + gate | 2.0 / 0.9 | 0.42 / 0.06 | 0 | 2 | 3 | — | — | — |
| fade0.1_linear, no gate | 2.2 / 0.9 | 0.43 / 0.07 | 0 | 3 | 4 | — | — | — |
| fade0.1_linear + gate | 2.2 / 0.9 | 0.43 / 0.07 | 0 | 2 | 3 | — | — | — |

### Boosts

- v2 + gate: third-octave +11.4 dB on Propeller-plane-flying-steady-01.wav at 20 ms; third-octave +11.3 dB on Propeller-plane-flying-steady-01.wav at 120 ms; near (0.5-1 dB): Ventilador.ogg 120 ms +0.90, Sewerage_pumping_station 20 ms +0.51
- AR adapted on prefix: whole band -0.56 dB on Akkuschrauber_–_Cordless_Screwdriver.ogg at 120 ms; whole band -0.81 dB on ÖBB_Taurus_Start-Up.ogg at 20 ms; third-octave +5.5 dB on Ventilador.ogg at 20 ms; third-octave +5.9 dB on Ventilador.ogg at 120 ms; third-octave +8.3 dB on Akkuschrauber_–_Cordless_Screwdriver.ogg at 20 ms; third-octave +7.7 dB on Akkuschrauber_–_Cordless_Screwdriver.ogg at 120 ms; third-octave +2.7 dB on ÖBB_Taurus_Start-Up.ogg at 20 ms; third-octave +2.0 dB on ÖBB_Taurus_Start-Up.ogg at 120 ms; third-octave +3.1 dB on Son_démarrage_Mp14-8.ogg at 20 ms; third-octave +2.8 dB on Elektrorasur-01.ogg at 20 ms; third-octave +7.1 dB on Propeller-plane-flying-steady-01.wav at 20 ms; third-octave +5.9 dB on Propeller-plane-flying-steady-01.wav at 120 ms; third-octave +1.9 dB on Sewerage_pumping_station_(Starnberg-Leutstetten_PW83)_c.ogg at 20 ms; third-octave +1.6 dB on Sewerage_pumping_station_(Starnberg-Leutstetten_PW83)_c.ogg at 120 ms; near (0.5-1 dB): Elektrorasur-01.ogg 120 ms +0.94
- AR refitted online: whole band -0.99 dB on Akkuschrauber_–_Cordless_Screwdriver.ogg at 120 ms; third-octave +3.7 dB on Ventilador.ogg at 20 ms; third-octave +5.2 dB on Ventilador.ogg at 120 ms; third-octave +4.8 dB on Akkuschrauber_–_Cordless_Screwdriver.ogg at 20 ms; third-octave +1.9 dB on Akkuschrauber_–_Cordless_Screwdriver.ogg at 120 ms; third-octave +1.7 dB on ÖBB_Taurus_Start-Up.ogg at 20 ms; third-octave +1.5 dB on ÖBB_Taurus_Start-Up.ogg at 120 ms; third-octave +1.7 dB on Son_démarrage_Mp14-8.ogg at 20 ms; third-octave +1.8 dB on Elektrorasur-01.ogg at 20 ms; third-octave +6.5 dB on Propeller-plane-flying-steady-01.wav at 20 ms; third-octave +5.0 dB on Propeller-plane-flying-steady-01.wav at 120 ms; third-octave +2.1 dB on Sewerage_pumping_station_(Starnberg-Leutstetten_PW83)_c.ogg at 20 ms
- bank_wide_lines + gate: third-octave +2.0 dB on Ventilador.ogg at 120 ms; third-octave +1.3 dB on Akkuschrauber_–_Cordless_Screwdriver.ogg at 20 ms; third-octave +1.4 dB on Akkuschrauber_–_Cordless_Screwdriver.ogg at 120 ms; third-octave +10.1 dB on Propeller-plane-flying-steady-01.wav at 20 ms; third-octave +11.6 dB on Propeller-plane-flying-steady-01.wav at 120 ms; near (0.5-1 dB): Sewerage_pumping_station 120 ms +0.75
- joint + gate: third-octave +7.7 dB on Propeller-plane-flying-steady-01.wav at 20 ms; third-octave +7.3 dB on Propeller-plane-flying-steady-01.wav at 120 ms; near (0.5-1 dB): Ventilador.ogg 120 ms +0.62
- fade0.1_linear + gate: third-octave +1.7 dB on Propeller-plane-flying-steady-01.wav at 20 ms; third-octave +3.2 dB on Propeller-plane-flying-steady-01.wav at 120 ms; near (0.5-1 dB): Ventilador.ogg 120 ms +0.55

### Per recording: tone bins (dB, 20 / 120 ms)

| Recording | Tones (Hz) | v2 + gate | AR adapted on prefix | AR refitted online | bank_wide_lines + gate | joint + gate | fade0.1_linear + gate |
|---|---|---:|---:|---:|---:|---:|---:|
| Ventilador.ogg | 98, 120, 130, 152, 185, 195 | 21.8 / 16.2 | 11.2 / 6.6 | 17.8 / 10.6 | 24.2 / 17.2 | 20.5 / 15.0 | 21.1 / 15.3 |
| Akkuschrauber_–_Cordless_Screwdriver.ogg | 49, 75, 90, 128, 307, 310 | 0.3 / 0.1 | 0.6 / -0.2 | 3.2 / -1.1 | 3.6 / 1.4 | 0.1 / 0.0 | 0.1 / 0.0 |
| ÖBB_Taurus_Start-Up.ogg | 58, 262, 294 | 0.2 / 0.0 | 4.0 / 3.5 | 2.8 / 2.6 | 0.2 / 0.2 | 0.3 / 0.1 | 0.3 / 0.2 |
| Elektrorasur-01.ogg | 46, 64, 128, 192, 256, 280 | 1.4 / 1.0 | 3.5 / 3.0 | 4.2 / 3.3 | 1.8 / 1.6 | 1.3 / 1.3 | 1.3 / 1.3 |
| Propeller-plane-flying-steady-01.wav | 66, 104, 132, 157, 198, 314 | 6.7 / 5.7 | 12.1 / 6.3 | 12.2 / 6.5 | 9.5 / 6.3 | 4.0 / 2.2 | 3.6 / 3.3 |
| Sewerage_pumping_station_(Starnberg-Leut | 66, 88, 112, 130, 156, 269 | 0.3 / 0.2 | 6.2 / 0.7 | 7.8 / 2.0 | 4.9 / 1.6 | 2.8 / 0.5 | 3.1 / 0.5 |

### Per recording: whole band (dB, 20 / 120 ms)

| Recording | Tones (Hz) | v2 + gate | AR adapted on prefix | AR refitted online | bank_wide_lines + gate | joint + gate | fade0.1_linear + gate |
|---|---|---:|---:|---:|---:|---:|---:|
| Ventilador.ogg | 98, 120, 130, 152, 185, 195 | 10.1 / 9.1 | 7.2 / 4.8 | 9.0 / 6.9 | 10.5 / 9.2 | 10.1 / 9.0 | 10.3 / 9.1 |
| Akkuschrauber_–_Cordless_Screwdriver.ogg | 49, 75, 90, 128, 307, 310 | 0.1 / -0.0 | -0.2 / -0.6 | 1.2 / -1.0 | 1.6 / 0.3 | 0.0 / -0.1 | 0.0 / -0.1 |
| ÖBB_Taurus_Start-Up.ogg | 58, 262, 294 | -0.0 / -0.0 | -0.8 / -0.4 | -0.4 / -0.1 | -0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| Son_démarrage_Mp14-8.ogg | none | 0.0 / 0.0 | -0.3 / -0.1 | -0.1 / -0.1 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| Elektrorasur-01.ogg | 46, 64, 128, 192, 256, 280 | 0.4 / 0.3 | -0.2 / -0.3 | 0.3 / 0.1 | 0.5 / 0.4 | 0.4 / 0.4 | 0.4 / 0.4 |
| Propeller-plane-flying-steady-01.wav | 66, 104, 132, 157, 198, 314 | 3.8 / 3.3 | 5.1 / 2.8 | 5.2 / 3.0 | 4.5 / 3.1 | 2.5 / 1.6 | 2.4 / 2.1 |
| Sewerage_pumping_station_(Starnberg-Leut | 66, 88, 112, 130, 156, 269 | 0.1 / 0.0 | 1.0 / -0.3 | 1.8 / 0.4 | 0.9 / -0.1 | 0.7 / 0.1 | 0.8 / 0.1 |

## Synthetic families (mean objective dB / late whole band dB)

| Method | standard | wander |
|---|---:|---:|
| Predict nothing | — / 0.00 | — / 0.00 |
| v2, no gate | 7.90 / 11.81 | 4.69 / 4.66 |
| v2 + gate | 7.92 / 11.79 | 4.63 / 4.60 |
| AR adapted on prefix | — / 9.01 | — / 7.13 |
| AR refitted online | 4.84 / 10.77 | 5.91 / 7.27 |
| bank_wide_lines, no gate | 8.03 / 12.26 | 5.82 / 6.21 |
| bank_wide_lines + gate | 8.09 / 12.30 | 5.82 / 6.21 |
| joint, no gate | 7.50 / 11.48 | 5.14 / 5.17 |
| joint + gate | 7.62 / 11.56 | 5.15 / 5.19 |
| fade0.1_linear, no gate | 7.45 / 11.39 | 5.20 / 5.22 |
| fade0.1_linear + gate | 7.58 / 11.48 | 5.21 / 5.22 |

## Synthetic late windows with a boost (>= 1 dB), by scene

Both horizons count. The change scenes are tone_appears_9s, tones_stop_9s, source_change_9s.

- v2, no gate: source_change_9s 10, tone_appears_9s 10, tones_stop_9s 4, wander_fast 5, wander_mixed_noisy 1, wander_slow 5, weak_tones_in_noise 2
- v2 + gate: source_change_9s 10, tone_appears_9s 10, tones_in_rumble 9, tones_stop_9s 5, wander_fast 5, wander_mixed_noisy 1, wander_slow 5, weak_tones_in_noise 2
- bank_wide_lines, no gate: drifting_tones 12, source_change_9s 11, tone_appears_9s 10, tones_stop_9s 3, wander_am_rumble 4, wander_fast 6, wander_mixed_noisy 3, wander_slow 6
- bank_wide_lines + gate: drifting_tones 12, source_change_9s 11, tone_appears_9s 10, tones_stop_9s 7, wander_am_rumble 4, wander_fast 6, wander_mixed_noisy 3, wander_slow 6
- joint, no gate: drifting_tones 2, source_change_9s 11, tone_appears_9s 10, tones_stop_9s 2, wander_fast 2, wander_slow 1
- joint + gate: drifting_tones 2, source_change_9s 11, tone_appears_9s 10, tones_stop_9s 4, wander_fast 5, wander_slow 1
- fade0.1_linear, no gate: drifting_tones 3, source_change_9s 3, tone_appears_9s 2, tones_stop_9s 3, wander_fast 1, wander_slow 1
- fade0.1_linear + gate: drifting_tones 3, source_change_9s 8, tone_appears_9s 2, tones_stop_9s 4, wander_fast 4, wander_slow 1

## Fresh synthetic scenes

84 scenes from seeds 20261022 and 20261023, odd 10 Hz bands, more than 2 Hz from every development frequency and study 03's buzz draws. Study 02's synthetic test draws are not excluded: every odd-band frequency lies within 2 Hz of one of them, so excluding them leaves no room (checked before this freeze). No study-05 choice used them; the scenes here have new seeds, so new noise and phases.

| Method | Objective (dB) | Windows < -0.5 dB | Late whole band, mean / min (dB) | Late tone bins, median (dB) | Late boosts (>= 1 / >= 0.5 dB) | On change scenes (>= 1 dB) |
|---|---:|---:|---:|---:|---:|---:|
| Predict nothing | — | — | 0.00 / 0.00 | 0.0 | 0 / 0 | 0 |
| v2, no gate | 7.44 | 13 | 10.79 / -0.59 | 27.6 | 37 / 55 | 24 |
| v2 + gate | 7.45 | 13 | 10.76 / -0.56 | 16.7 | 47 / 65 | 25 |
| AR adapted on prefix | — | — | 8.74 / -10.28 | 29.8 | 79 / 136 | 24 |
| AR refitted online | 4.99 | 13 | 10.27 / -0.55 | 29.7 | 75 / 101 | 25 |
| bank_wide_lines, no gate | 7.71 | 12 | 11.40 / 0.00 | 28.2 | 55 / 64 | 24 |
| bank_wide_lines + gate | 7.76 | 12 | 11.43 / 0.00 | 28.2 | 59 / 66 | 28 |
| joint, no gate | 7.17 | 12 | 10.58 / 0.00 | 27.1 | 28 / 43 | 23 |
| joint + gate | 7.26 | 12 | 10.65 / 0.00 | 27.1 | 33 / 45 | 25 |
| fade0.1_linear, no gate | 7.13 | 12 | 10.50 / 0.00 | 27.1 | 13 / 30 | 8 |
| fade0.1_linear + gate | 7.24 | 12 | 10.59 / 0.00 | 27.1 | 22 / 33 | 14 |

## Compute time

Offline Python, one thread per process, measured under the parallel pool. "Own" excludes the tone-selector update that v2 also runs. One block is 10 ms of audio.

| Method | Own ms per block, mean | Own p99, median over runs | Own p99, worst run | Own worst block | ms per block incl. selector, mean |
|---|---:|---:|---:|---:|---:|
| bank_wide_lines | 0.60 | 2.81 | 4.28 | 13.7 | 0.90 |
| joint | 1.51 | 4.63 | 6.36 | 12.7 | 1.81 |
| fade0.1_linear | 1.53 | 4.58 | 7.31 | 42.9 | 1.83 |

## Fresh recordings and credits

| File | Author | Licence | Seconds | Counted as acoustic |
|---|---|---|---:|---|
| Ventilador.ogg | Armartinell | CC BY-SA 4.0 | 18 | yes |
| Akkuschrauber_–_Cordless_Screwdriver.ogg | Maximilian Schönherr | CC BY-SA 4.0 | 39 | yes |
| ÖBB_Taurus_Start-Up.ogg | 3LM6wjuS | CC BY-SA 4.0 | 17 | yes |
| Son_démarrage_Mp14-8.ogg | Lodaï | CC BY-SA 4.0 | 25 | yes |
| Elektrorasur-01.ogg | Priwo | Public domain | 20 | yes |
| Propeller-plane-flying-steady-01.wav | Versatile Virtuoso | CC BY-SA 4.0 | 20 | yes |
| Sewerage_pumping_station_(Starnberg-Leutstetten_PW83)_c.ogg | PaulSch | CC0 | 100 | yes |
| Noise-Pollution-Filters-Bird-Communities-Based-on-Vocal-Frequency-pone.0027052.s001.ogg | Francis C, Ortega C, Cruz A | CC BY 2.5 | 15 | yes |

Files are local only, in `external-audio/wikimedia-commons-fresh-05`, from Wikimedia Commons (each file's page is https://commons.wikimedia.org/wiki/ followed by its title).

Runtime: 2.5 minutes. Created 2026-10-20T13:13:30.953855+00:00. Numbers: `test/test.json`. Frozen protocol: `protocol.json`.
