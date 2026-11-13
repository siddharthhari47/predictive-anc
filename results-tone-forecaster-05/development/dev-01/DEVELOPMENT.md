# Tone forecaster study 05: development run

**Development material only.** No study-01 test recording, study-02 fresh recording, synthetic test scene or new fresh recording was read. **Reference-signal prediction only.** Every number is how well a forecaster predicts the recording microphone's own signal 20 ms or 120 ms ahead. Nothing was played, no acoustic path was modelled, and no attenuation at an ear was measured. No real-world cancellation is claimed.

Development recordings: Inside_of_refrigerator.ogg, Microwave_oven.ogg, Table_ventilator.ogg, WWS_Aircompressor.ogg, WWS_Bediadiesellocomotiveidling.ogg, WWS_Compressor.ogg, MainsBrum50Hz.ogg, Mains_hum_60_Hz.ogg. Synthetic: the 44 development scenes of studies 01 and 02 plus study 03's 8 buzz scenes (seed 20261019).

## Rule

Written after the diagnostic trials on development material (results-tone-forecaster-05/diagnosis) and before the formal development run. Candidates, all gated: the joint band check of study 02 with each tone fading in and out of every output setting instead of switching: raised-cosine fades of 0.05, 0.1 and 0.2 s; a 0.1 s linear fade; a 0.1 s fade plus a 0.3 s cross-fade when the check changes its setting; and a 0.1 s fade with a 0.2 s start floor instead of 0.1 s. Development material: the eight study-01 development recordings, the 44 development synthetic scenes and study 03's 8 buzz scenes. A boost is a third-octave band 1 dB or more louder; a near-boost 0.5 dB or more; both are counted over development recordings (either horizon) plus late synthetic windows. The change scenes are tone_appears_9s, tones_stop_9s and source_change_9s. Eligible only if: (a) fewer boosts than joint + gate; (b) fewer boosts on the change scenes than joint + gate; (c) no more near-boosts than joint + gate; (d) no more whole-band boosts (whole 35-350 Hz band below -0.5 dB on a development recording) than joint + gate; (e) the tone gain over v2 is kept: the median, over development acoustic recordings with reference tones, of the tone-bin gain averaged over both horizons is at least v2 + gate's plus half of the amount by which joint + gate exceeds v2 + gate; (f) the median whole-band gain over development acoustic recordings, averaged over both horizons, is at least joint + gate's minus 0.1 dB; (g) the mean synthetic objective is at least joint + gate's minus 0.5 dB and its synthetic windows below -0.5 dB are no more than joint + gate has; (h) its own compute time per 10 ms block at the 99th percentile, median over runs, is within 0.5 ms of joint's in the same run. Study 03 used the worst run instead, which swings with the shared machine's load: in the study-05 trial the fade code with one-block fades (the joint check's own forecasts) was 2.5 ms slower than the joint check on its worst run, while timed side by side in one process, after the output step was made an array step, it is about 0.1 ms slower on average and 0.3-0.4 ms at the median 99th percentile (diagnosis timing01, timing02). Among eligible candidates, pick the one with the fewest boosts, then the fewest near-boosts, then the higher tone-bin median. If none is eligible, nothing is frozen: the joint check and v2 are unchanged, and there is nothing to test.

| Candidate | Boosts (rec + syn late) | On change scenes | Near-boosts | Whole-band boosts | Tone bins, median (dB) | Needed (dB) | Whole band, median (dB) | Synthetic objective (dB) | Windows < -0.5 dB | p99 ms per block, median over runs | Checks failed | Eligible |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| fade0.05 | 1 + 17 = 18 | 10 | 33 | 0 | 5.68 | 4.35 | 2.33 | 7.04 | 6 | 3.81 | — | yes |
| fade0.1 | 1 + 14 = 15 | 7 | 28 | 0 | 5.67 | 4.35 | 2.36 | 7.03 | 6 | 3.84 | — | yes |
| fade0.2 | 1 + 15 = 16 | 7 | 25 | 0 | 5.59 | 4.35 | 2.36 | 7.03 | 6 | 3.90 | — | yes |
| fade0.1_linear | 1 + 14 = 15 | 7 | 26 | 0 | 5.73 | 4.35 | 2.35 | 7.04 | 6 | 3.97 | — | yes |
| fade0.1_switch0.3 | 1 + 14 = 15 | 7 | 27 | 0 | 5.66 | 4.35 | 2.35 | 7.03 | 6 | 3.89 | — | yes |
| fade0.1_start0.2 | 0 + 14 = 14 | 7 | 27 | 0 | 5.67 | 4.35 | 2.36 | 6.45 | 6 | 3.92 | g_synthetic | no |
| *joint + gate (reference)* | 1 + 24 = 25 | 14 | 40 | 0 | 5.56 | | 1.59 | 7.05 | 6 | 3.72 | | |
| *v2 + gate (reference)* | 9 + 45 = 54 | 14 | 74 | 0 | 3.15 | | 0.98 | 7.02 | 6 | — | | |
| *bank_wide_lines + gate (reference)* | 4 + 50 = 54 | 15 | 72 | 0 | 6.29 | | 2.32 | 7.62 | 6 | 2.43 | | |

Development pick: **fade0.1_linear**

## How often the fades acted

Summed over horizon groups, output settings and runs. A "ghost" is a tone the selector dropped while some setting was still fading it out; it runs on from its last phasor until it is silent. "Fading tone-blocks" counts (setting, tone, block) cells with a level strictly between 0 and 1.

| Candidate | Part | Ghosts | Fading tone-blocks |
|---|---|---:|---:|
| fade0.05 | recordings | 2372 | 84982 |
| fade0.05 | scenes | 76 | 10691 |
| fade0.1 | recordings | 2376 | 112507 |
| fade0.1 | scenes | 76 | 19989 |
| fade0.2 | recordings | 2376 | 159392 |
| fade0.2 | scenes | 76 | 36164 |
| fade0.1_linear | recordings | 2376 | 112507 |
| fade0.1_linear | scenes | 76 | 19989 |
| fade0.1_switch0.3 | recordings | 2376 | 112507 |
| fade0.1_switch0.3 | scenes | 76 | 19989 |
| fade0.1_start0.2 | recordings | 2376 | 112507 |
| fade0.1_start0.2 | scenes | 76 | 19989 |

## All methods on development material

| Method | Tone bins median, 20 / 120 ms | Whole band median, 20 / 120 ms | Whole-band boosts | Third-octave boosts (>= 1 dB) | Near-boosts (>= 0.5 dB) | Synthetic objective | Synthetic windows < -0.5 dB | Synthetic late boosts (>= 1 / >= 0.5 dB) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Predict nothing | 0.0 / 0.0 | 0.00 / 0.00 | 0 | 0 | 0 | — | — | 0 / 0 |
| v2, no gate | 3.2 / 3.4 | 1.02 / 0.82 | 0 | 8 | 11 | 7.01 | 6 | 40 / 57 |
| v2 + gate | 2.9 / 3.4 | 1.01 / 0.83 | 0 | 9 | 11 | 7.02 | 6 | 45 / 63 |
| AR adapted on prefix | 3.0 / 4.1 | 0.63 / 0.87 | 3 | 15 | 16 | — | — | 75 / 93 |
| AR refitted online | 5.4 / 5.0 | 1.58 / 1.54 | 2 | 15 | 16 | 5.40 | 7 | 70 / 75 |
| bank_wide_lines, no gate | 7.1 / 5.4 | 2.56 / 2.05 | 0 | 4 | 13 | 7.56 | 6 | 51 / 60 |
| bank_wide_lines + gate | 7.1 / 5.5 | 2.58 / 2.07 | 0 | 4 | 12 | 7.62 | 6 | 50 / 60 |
| joint, no gate | 5.8 / 5.1 | 1.73 / 1.43 | 0 | 1 | 8 | 6.95 | 6 | 20 / 27 |
| joint + gate | 5.9 / 5.1 | 1.75 / 1.44 | 0 | 1 | 8 | 7.05 | 6 | 24 / 32 |
| fade0.05, no gate | 6.0 / 5.3 | 2.46 / 2.19 | 0 | 1 | 5 | 6.93 | 6 | 13 / 22 |
| fade0.05 + gate | 6.1 / 5.3 | 2.48 / 2.19 | 0 | 1 | 6 | 7.04 | 6 | 17 / 27 |
| fade0.1, no gate | 5.9 / 5.3 | 2.46 / 2.21 | 0 | 1 | 4 | 6.92 | 6 | 8 / 18 |
| fade0.1 + gate | 5.9 / 5.4 | 2.49 / 2.22 | 0 | 1 | 6 | 7.03 | 6 | 14 / 22 |
| fade0.2, no gate | 5.8 / 5.3 | 2.47 / 2.20 | 0 | 1 | 4 | 6.90 | 6 | 11 / 18 |
| fade0.2 + gate | 5.8 / 5.4 | 2.50 / 2.21 | 0 | 1 | 4 | 7.03 | 6 | 15 / 21 |
| fade0.1_linear, no gate | 5.9 / 5.4 | 2.46 / 2.19 | 0 | 1 | 4 | 6.93 | 6 | 8 / 17 |
| fade0.1_linear + gate | 6.0 / 5.5 | 2.49 / 2.21 | 0 | 1 | 6 | 7.04 | 6 | 14 / 20 |
| fade0.1_switch0.3, no gate | 5.9 / 5.3 | 2.45 / 2.21 | 0 | 1 | 4 | 6.91 | 6 | 8 / 17 |
| fade0.1_switch0.3 + gate | 5.9 / 5.4 | 2.48 / 2.22 | 0 | 1 | 6 | 7.03 | 6 | 14 / 21 |
| fade0.1_start0.2, no gate | 5.9 / 5.3 | 2.46 / 2.21 | 0 | 0 | 3 | 6.31 | 6 | 10 / 18 |
| fade0.1_start0.2 + gate | 5.9 / 5.4 | 2.49 / 2.22 | 0 | 0 | 5 | 6.45 | 6 | 14 / 22 |

### Boosts on the development recordings

- v2 + gate: third-octave +1.2 dB on Table_ventilator.ogg at 20 ms; third-octave +1.3 dB on Table_ventilator.ogg at 120 ms; third-octave +1.4 dB on WWS_Aircompressor.ogg at 20 ms; third-octave +2.5 dB on WWS_Aircompressor.ogg at 120 ms; third-octave +8.3 dB on WWS_Bediadiesellocomotiveidling.ogg at 20 ms; third-octave +12.3 dB on WWS_Bediadiesellocomotiveidling.ogg at 120 ms; third-octave +1.4 dB on MainsBrum50Hz.ogg at 20 ms; third-octave +2.6 dB on Mains_hum_60_Hz.ogg at 20 ms; third-octave +4.4 dB on Mains_hum_60_Hz.ogg at 120 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.65, MainsBrum50Hz.ogg 120 ms +0.85
- bank_wide_lines + gate: third-octave +1.1 dB on WWS_Bediadiesellocomotiveidling.ogg at 20 ms; third-octave +1.7 dB on WWS_Compressor.ogg at 120 ms; third-octave +4.1 dB on Mains_hum_60_Hz.ogg at 20 ms; third-octave +6.5 dB on Mains_hum_60_Hz.ogg at 120 ms; near (0.5-1 dB): Inside_of_refrigerator.o 20 ms +0.84, Microwave_oven.ogg 120 ms +0.84, Table_ventilator.ogg 20 ms +0.84, Table_ventilator.ogg 120 ms +0.80, WWS_Aircompressor.ogg 20 ms +0.93, WWS_Aircompressor.ogg 120 ms +0.88, WWS_Compressor.ogg 20 ms +0.77, MainsBrum50Hz.ogg 20 ms +0.53
- joint + gate: third-octave +1.4 dB on Mains_hum_60_Hz.ogg at 20 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.84, Table_ventilator.ogg 20 ms +0.63, Table_ventilator.ogg 120 ms +0.74, WWS_Aircompressor.ogg 20 ms +0.91, WWS_Aircompressor.ogg 120 ms +0.77, MainsBrum50Hz.ogg 20 ms +0.53, Mains_hum_60_Hz.ogg 120 ms +0.93
- fade0.05 + gate: third-octave +1.4 dB on Mains_hum_60_Hz.ogg at 20 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.83, Table_ventilator.ogg 120 ms +0.65, WWS_Aircompressor.ogg 20 ms +0.64, MainsBrum50Hz.ogg 20 ms +0.53, Mains_hum_60_Hz.ogg 120 ms +0.93
- fade0.1 + gate: third-octave +1.4 dB on Mains_hum_60_Hz.ogg at 20 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.83, Table_ventilator.ogg 120 ms +0.56, WWS_Aircompressor.ogg 20 ms +0.53, MainsBrum50Hz.ogg 20 ms +0.53, Mains_hum_60_Hz.ogg 120 ms +0.93
- fade0.2 + gate: third-octave +1.4 dB on Mains_hum_60_Hz.ogg at 20 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.83, MainsBrum50Hz.ogg 20 ms +0.53, Mains_hum_60_Hz.ogg 120 ms +0.93
- fade0.1_linear + gate: third-octave +1.4 dB on Mains_hum_60_Hz.ogg at 20 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.83, Table_ventilator.ogg 120 ms +0.54, WWS_Aircompressor.ogg 20 ms +0.52, MainsBrum50Hz.ogg 20 ms +0.53, Mains_hum_60_Hz.ogg 120 ms +0.93
- fade0.1_switch0.3 + gate: third-octave +1.4 dB on Mains_hum_60_Hz.ogg at 20 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.83, Table_ventilator.ogg 120 ms +0.56, WWS_Aircompressor.ogg 20 ms +0.53, MainsBrum50Hz.ogg 20 ms +0.53, Mains_hum_60_Hz.ogg 120 ms +0.93
- fade0.1_start0.2 + gate: near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.83, Table_ventilator.ogg 120 ms +0.55, WWS_Aircompressor.ogg 20 ms +0.53, MainsBrum50Hz.ogg 20 ms +0.52, Mains_hum_60_Hz.ogg 20 ms +0.69

### Per recording: tone bins (dB, 20 / 120 ms)

| Recording | Tones (Hz) | v2 + gate | AR adapted on prefix | AR refitted online | bank_wide_lines + gate | joint + gate | fade0.05 + gate | fade0.1 + gate | fade0.2 + gate | fade0.1_linear + gate | fade0.1_switch0.3 + gate | fade0.1_start0.2 + gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Microwave_oven.ogg | 100, 173, 200, 300, 350 | 3.7 / 3.7 | 15.5 / 11.2 | 17.8 / 13.1 | 14.8 / 12.0 | 9.1 / 5.1 | 9.1 / 11.9 | 9.0 / 11.7 | 6.1 / 11.8 | 9.1 / 11.8 | 10.1 / 11.9 | 9.0 / 11.7 |
| Table_ventilator.ogg | 59, 67, 100, 119, 134, 202 | 6.1 / 4.5 | 0.3 / 0.4 | 5.4 / 5.0 | 7.1 / 5.5 | 5.9 / 5.2 | 5.9 / 5.2 | 5.7 / 5.1 | 5.7 / 4.8 | 5.7 / 4.9 | 5.7 / 5.1 | 5.7 / 5.1 |
| WWS_Aircompressor.ogg | 161, 169, 177, 185, 194, 225 | 2.9 / 3.4 | -0.5 / 4.5 | 1.5 / 11.6 | 8.2 / 8.3 | 8.1 / 7.1 | 8.2 / 8.5 | 8.2 / 8.5 | 8.2 / 8.5 | 8.3 / 8.5 | 8.2 / 8.5 | 8.2 / 8.5 |
| WWS_Bediadiesellocomotiveidling.ogg | 51, 56, 61, 86, 91, 132 | 1.7 / 0.5 | 6.3 / 4.1 | 6.3 / 4.3 | 4.0 / 2.5 | 2.8 / 2.2 | 2.8 / 2.5 | 2.8 / 2.4 | 2.9 / 2.4 | 2.8 / 2.5 | 2.8 / 2.4 | 2.8 / 2.4 |
| WWS_Compressor.ogg | 36, 54, 63, 72, 81, 90 | 0.3 / -0.0 | 3.0 / 2.2 | 3.2 / 2.6 | 6.5 / 5.3 | 1.5 / 0.1 | 6.1 / 5.3 | 5.9 / 5.4 | 5.8 / 5.4 | 6.0 / 5.5 | 5.9 / 5.4 | 5.9 / 5.4 |
| MainsBrum50Hz.ogg (electrical) | 50, 100, 150, 200, 250, 350 | 29.0 / 27.9 | 9.6 / 7.2 | 14.8 / 14.8 | 30.1 / 29.6 | 30.1 / 29.6 | 30.1 / 29.6 | 30.1 / 29.6 | 30.1 / 29.6 | 30.1 / 29.6 | 30.1 / 29.6 | 30.1 / 29.6 |
| Mains_hum_60_Hz.ogg (electrical) | 60, 119, 180, 240, 300, 315 | 51.8 / 49.7 | 45.1 / 44.4 | 8.9 / 8.9 | 52.8 / 50.6 | 51.9 / 49.9 | 51.9 / 49.9 | 51.9 / 49.9 | 51.9 / 49.9 | 51.9 / 49.9 | 51.9 / 49.9 | 48.7 / 46.7 |

### Per recording: whole band (dB, 20 / 120 ms)

| Recording | Tones (Hz) | v2 + gate | AR adapted on prefix | AR refitted online | bank_wide_lines + gate | joint + gate | fade0.05 + gate | fade0.1 + gate | fade0.2 + gate | fade0.1_linear + gate | fade0.1_switch0.3 + gate | fade0.1_start0.2 + gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Inside_of_refrigerator.ogg | none | 0.2 / 0.1 | -1.3 / -0.8 | -1.2 / -0.6 | -0.1 / -0.0 | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 | 0.2 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 |
| Microwave_oven.ogg | 100, 173, 200, 300, 350 | 1.9 / 1.8 | 2.4 / 1.8 | 2.8 / 2.6 | 3.4 / 3.2 | 3.0 / 2.3 | 3.0 / 3.2 | 3.0 / 3.2 | 2.6 / 3.2 | 3.0 / 3.2 | 3.1 / 3.2 | 3.0 / 3.2 |
| Table_ventilator.ogg | 59, 67, 100, 119, 134, 202 | 2.4 / 1.5 | -0.2 / -0.0 | 1.5 / 1.8 | 2.7 / 2.1 | 2.5 / 2.1 | 2.5 / 2.1 | 2.4 / 2.1 | 2.5 / 2.0 | 2.5 / 2.0 | 2.4 / 2.1 | 2.5 / 2.1 |
| WWS_Aircompressor.ogg | 161, 169, 177, 185, 194, 225 | 2.2 / 2.4 | -0.5 / 3.3 | 1.0 / 7.6 | 5.1 / 5.3 | 5.2 / 4.8 | 5.3 / 5.5 | 5.4 / 5.6 | 5.5 / 5.6 | 5.4 / 5.6 | 5.4 / 5.6 | 5.4 / 5.6 |
| WWS_Bediadiesellocomotiveidling.ogg | 51, 56, 61, 86, 91, 132 | 0.1 / -0.4 | 1.6 / 1.2 | 1.7 / 1.3 | 1.2 / 0.8 | 1.0 / 0.8 | 1.0 / 0.8 | 1.1 / 0.8 | 1.1 / 0.8 | 1.1 / 0.8 | 1.1 / 0.8 | 1.1 / 0.8 |
| WWS_Compressor.ogg | 36, 54, 63, 72, 81, 90 | 0.1 / -0.1 | 1.5 / 0.5 | 1.6 / 0.6 | 2.5 / 2.0 | 0.8 / 0.0 | 2.5 / 2.3 | 2.5 / 2.4 | 2.5 / 2.4 | 2.5 / 2.4 | 2.5 / 2.4 | 2.5 / 2.4 |
| MainsBrum50Hz.ogg (electrical) | 50, 100, 150, 200, 250, 350 | 23.4 / 22.5 | 9.4 / 7.0 | 9.3 / 9.3 | 24.1 / 24.0 | 24.0 / 23.9 | 24.0 / 23.9 | 24.0 / 23.9 | 24.0 / 23.9 | 24.0 / 23.9 | 24.0 / 23.9 | 24.0 / 23.9 |
| Mains_hum_60_Hz.ogg (electrical) | 60, 119, 180, 240, 300, 315 | 36.2 / 36.0 | 42.8 / 42.3 | 6.8 / 6.8 | 36.0 / 35.5 | 36.2 / 36.1 | 36.2 / 36.1 | 36.2 / 36.1 | 36.2 / 36.1 | 36.2 / 36.1 | 36.2 / 36.1 | 36.0 / 35.9 |

## Synthetic families (mean objective dB / late whole band dB)

| Method | buzz | standard | wander |
|---|---:|---:|---:|
| Predict nothing | — / 0.00 | — / 0.00 | — / 0.00 |
| v2, no gate | 5.71 / 6.74 | 7.86 / 11.72 | 4.45 / 4.42 |
| v2 + gate | 5.71 / 6.73 | 7.90 / 11.70 | 4.39 / 4.35 |
| AR adapted on prefix | — / 9.69 | — / 8.90 | — / 6.78 |
| AR refitted online | 7.59 / 9.73 | 4.80 / 10.65 | 5.92 / 7.03 |
| bank_wide_lines, no gate | 7.42 / 8.04 | 8.00 / 12.18 | 5.75 / 5.71 |
| bank_wide_lines + gate | 7.41 / 8.04 | 8.08 / 12.23 | 5.75 / 5.71 |
| joint, no gate | 5.84 / 5.99 | 7.65 / 11.85 | 4.95 / 5.33 |
| joint + gate | 5.84 / 6.01 | 7.79 / 11.94 | 4.94 / 5.33 |
| fade0.05, no gate | 5.72 / 5.93 | 7.63 / 11.83 | 4.98 / 5.45 |
| fade0.05 + gate | 5.73 / 5.96 | 7.79 / 11.94 | 4.98 / 5.45 |
| fade0.1, no gate | 5.72 / 5.92 | 7.61 / 11.81 | 5.00 / 5.48 |
| fade0.1 + gate | 5.73 / 5.95 | 7.78 / 11.93 | 5.00 / 5.48 |
| fade0.2, no gate | 5.74 / 6.02 | 7.57 / 11.78 | 5.01 / 5.51 |
| fade0.2 + gate | 5.75 / 6.04 | 7.76 / 11.91 | 5.01 / 5.51 |
| fade0.1_linear, no gate | 5.77 / 6.04 | 7.62 / 11.82 | 5.00 / 5.49 |
| fade0.1_linear + gate | 5.77 / 6.06 | 7.78 / 11.93 | 5.00 / 5.49 |
| fade0.1_switch0.3, no gate | 5.72 / 5.93 | 7.60 / 11.81 | 4.99 / 5.48 |
| fade0.1_switch0.3 + gate | 5.73 / 5.96 | 7.77 / 11.93 | 4.98 / 5.48 |
| fade0.1_start0.2, no gate | 5.32 / 5.92 | 6.87 / 11.78 | 4.76 / 5.49 |
| fade0.1_start0.2 + gate | 5.33 / 5.95 | 7.07 / 11.92 | 4.76 / 5.49 |

## Synthetic late windows with a boost (>= 1 dB), by scene

Both horizons count. The change scenes are tone_appears_9s, tones_stop_9s, source_change_9s.

- v2, no gate: buzz_am 4, buzz_harmonic 1, buzz_steady 2, buzz_wander 3, drifting_tones 1, harmonic_tones 3, single_tone 2, source_change_9s 6, tone_appears_9s 5, tones_in_rumble 3, tones_stop_9s 4, unrelated_tones 2, wander_fast 2, wander_mixed_noisy 1, weak_tones_in_noise 1
- v2 + gate: buzz_am 4, buzz_harmonic 1, buzz_steady 2, buzz_wander 3, drifting_tones 1, harmonic_tones 3, single_tone 2, source_change_9s 6, tone_appears_9s 5, tones_in_rumble 5, tones_stop_9s 3, unrelated_tones 2, wander_am_rumble 4, wander_fast 2, wander_mixed_noisy 1, weak_tones_in_noise 1
- bank_wide_lines, no gate: buzz_am 4, buzz_harmonic 4, buzz_steady 4, buzz_wander 4, drifting_tones 3, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 5, wander_am_rumble 4, wander_fast 4, wander_mixed_noisy 4, wander_slow 4
- bank_wide_lines + gate: buzz_am 4, buzz_harmonic 4, buzz_steady 4, buzz_wander 4, drifting_tones 3, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 4, wander_am_rumble 4, wander_fast 4, wander_mixed_noisy 4, wander_slow 4
- joint, no gate: buzz_am 2, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 4, wander_fast 2
- joint + gate: buzz_am 4, buzz_wander 3, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 3, wander_fast 2
- fade0.05, no gate: buzz_am 1, drifting_tones 1, source_change_9s 4, tone_appears_9s 3, tones_stop_9s 3, wander_fast 1
- fade0.05 + gate: buzz_am 2, buzz_wander 3, drifting_tones 1, source_change_9s 4, tone_appears_9s 3, tones_stop_9s 3, wander_fast 1
- fade0.1, no gate: drifting_tones 1, source_change_9s 3, tones_stop_9s 3, wander_fast 1
- fade0.1 + gate: buzz_am 2, buzz_wander 3, drifting_tones 1, source_change_9s 4, tones_stop_9s 3, wander_fast 1
- fade0.2, no gate: buzz_am 1, buzz_steady 1, drifting_tones 1, source_change_9s 3, tones_stop_9s 4, wander_fast 1
- fade0.2 + gate: buzz_am 2, buzz_steady 1, buzz_wander 3, drifting_tones 1, source_change_9s 4, tones_stop_9s 3, wander_fast 1
- fade0.1_linear, no gate: drifting_tones 1, source_change_9s 3, tones_stop_9s 3, wander_fast 1
- fade0.1_linear + gate: buzz_am 2, buzz_wander 3, drifting_tones 1, source_change_9s 4, tones_stop_9s 3, wander_fast 1
- fade0.1_switch0.3, no gate: drifting_tones 1, source_change_9s 3, tones_stop_9s 3, wander_fast 1
- fade0.1_switch0.3 + gate: buzz_am 2, buzz_wander 3, drifting_tones 1, source_change_9s 4, tones_stop_9s 3, wander_fast 1
- fade0.1_start0.2, no gate: drifting_tones 1, source_change_9s 4, tones_stop_9s 4, wander_fast 1
- fade0.1_start0.2 + gate: buzz_am 2, buzz_wander 3, drifting_tones 1, source_change_9s 4, tones_stop_9s 3, wander_fast 1

## Compute time

Offline Python, one thread per process, measured under the parallel pool. "Own" excludes the tone-selector update that v2 also runs. One block is 10 ms of audio.

| Method | Own ms per block, mean | Own p99, median over runs | Own p99, worst run | Own worst block | ms per block incl. selector, mean |
|---|---:|---:|---:|---:|---:|
| bank_wide_lines | 0.61 | 2.43 | 5.36 | 35.6 | 0.88 |
| joint | 1.48 | 3.72 | 7.71 | 48.6 | 1.74 |
| fade0.05 | 1.45 | 3.81 | 8.64 | 41.2 | 1.71 |
| fade0.1 | 1.53 | 3.84 | 9.20 | 39.8 | 1.80 |
| fade0.2 | 1.48 | 3.90 | 8.38 | 34.2 | 1.74 |
| fade0.1_linear | 1.42 | 3.97 | 7.70 | 25.9 | 1.67 |
| fade0.1_switch0.3 | 1.39 | 3.89 | 7.31 | 32.5 | 1.64 |
| fade0.1_start0.2 | 1.36 | 3.92 | 7.23 | 17.3 | 1.60 |

Runtime: 5.1 minutes.
