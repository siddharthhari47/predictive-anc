# Tone forecaster study 02: development run

**Development material only.** No study-01 test recording, fresh recording or test scene was read. **Reference-signal prediction only.** Every number is how well a forecaster predicts the recording microphone's own signal 20 ms or 120 ms ahead. Nothing was played, no acoustic path was modelled, and no attenuation at an ear was measured. No real-world cancellation is claimed.

Development recordings: Inside_of_refrigerator.ogg, Microwave_oven.ogg, Table_ventilator.ogg, WWS_Aircompressor.ogg, WWS_Bediadiesellocomotiveidling.ogg, WWS_Compressor.ogg, MainsBrum50Hz.ogg, Mains_hum_60_Hz.ogg.

**Note:** First formal development run; the rule was written after the diagnostic trials in diagnosis/.

## Rule

Written after the diagnostic trials on development material (results-tone-forecaster-02/diagnosis) and before the formal development run. Candidates, all gated: the line-finder bank with a 0.2 s memory floor for line-finder tones (floor_lines0.2), and the line-finder bank with the joint band check (joint). Eligible only if, on development material: (a) whole-band boosts (whole 35-350 Hz band below -0.5 dB at either horizon, any development recording) are no more than v2 + gate has; (b) third-octave boosts (a third-octave band 1 dB or more louder, any development recording and horizon) are no more than v2 + gate has and fewer than bank_wide_lines + gate has; (c) near-boosts (a band 0.5 dB or more louder, same cases) are fewer than v2 + gate has and fewer than bank_wide_lines + gate has, a margin because study 01's candidate passed (b) on development and failed it on test; (d) third-octave boosts in the late windows of the synthetic development scenes are fewer than v2 + gate has and fewer than bank_wide_lines + gate has; (e) the tone gain is kept: the median, over development acoustic recordings with reference tones, of the tone-bin gain averaged over both horizons is at least v2 + gate's plus half of the amount by which bank_wide_lines + gate exceeds v2 + gate; (f) the median whole-band gain over development acoustic recordings, averaged over both horizons, is at least v2 + gate's minus 0.1 dB; (g) the mean synthetic development objective is at least v2 + gate's minus 0.5 dB and its synthetic windows below -0.5 dB are no more than v2 + gate has; (h) its own compute time per 10 ms block, excluding the tone-selector update that v2 also runs, is below 5 ms at the 99th percentile on every development recording and scene (offline Python, one thread, measured under the parallel pool). Among eligible candidates, pick the one with the fewest near-boosts (development recordings plus late synthetic windows, 0.5 dB or more); ties go to the higher tone-bin median. If none is eligible, no candidate is frozen and v2 stays.

| Candidate | Tone bins, median (dB) | Needed (dB) | Whole band, median (dB) | Third-octave boosts | Near-boosts | Synthetic late boosts (>= 1 / >= 0.5) | Synthetic objective (dB) | p99 ms per block | Checks failed | Eligible |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| floor_lines0.2 | 6.15 | 4.72 | 2.33 | 3 | 11 | 30 / 43 | 7.65 | 2.82 | c_near_boosts | no |
| joint | 5.56 | 4.72 | 1.59 | 1 | 8 | 17 / 23 | 7.27 | 4.08 | — | yes |
| *v2 + gate (reference)* | 3.15 | | 0.98 | 9 | 11 | 35 / 49 | 7.26 | | | |
| *bank_wide_lines + gate (reference)* | 6.29 | | 2.32 | 4 | 12 | 34 / 44 | 7.66 | | | |

Development pick: **joint**

## All methods on development material

| Method | Tone bins median, 20 / 120 ms | Whole band median, 20 / 120 ms | Whole-band boosts | Third-octave boosts (>= 1 dB) | Near-boosts (>= 0.5 dB) | Synthetic objective | Synthetic windows < -0.5 dB | Synthetic late boosts (>= 1 / >= 0.5 dB) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Predict nothing | 0.0 / 0.0 | 0.00 / 0.00 | 0 | 0 | 0 | — | — | 0 / 0 |
| v2, no gate | 3.2 / 3.4 | 1.02 / 0.82 | 0 | 8 | 11 | 7.24 | 6 | 30 / 43 |
| v2 + gate | 2.9 / 3.4 | 1.01 / 0.83 | 0 | 9 | 11 | 7.26 | 6 | 35 / 49 |
| AR adapted on prefix | 3.0 / 4.1 | 0.63 / 0.87 | 3 | 15 | 16 | — | — | 59 / 77 |
| AR refitted online | 5.4 / 5.0 | 1.58 / 1.54 | 2 | 15 | 16 | 5.00 | 7 | 54 / 59 |
| bank_wide_lines, no gate | 7.1 / 5.4 | 2.56 / 2.05 | 0 | 4 | 13 | 7.59 | 6 | 35 / 44 |
| bank_wide_lines + gate | 7.1 / 5.5 | 2.58 / 2.07 | 0 | 4 | 12 | 7.66 | 6 | 34 / 44 |
| floor_lines0.2, no gate | 6.9 / 5.3 | 2.54 / 2.09 | 0 | 3 | 11 | 7.58 | 6 | 31 / 43 |
| floor_lines0.2 + gate | 6.9 / 5.4 | 2.56 / 2.10 | 0 | 3 | 11 | 7.65 | 6 | 30 / 43 |
| joint, no gate | 5.8 / 5.1 | 1.73 / 1.43 | 0 | 1 | 8 | 7.16 | 6 | 18 / 22 |
| joint + gate | 5.9 / 5.1 | 1.75 / 1.44 | 0 | 1 | 8 | 7.27 | 6 | 17 / 23 |

## Boosts on the development recordings

- v2 + gate: third-octave +1.2 dB on Table_ventilator.ogg at 20 ms; third-octave +1.3 dB on Table_ventilator.ogg at 120 ms; third-octave +1.4 dB on WWS_Aircompressor.ogg at 20 ms; third-octave +2.5 dB on WWS_Aircompressor.ogg at 120 ms; third-octave +8.3 dB on WWS_Bediadiesellocomotiveidling.ogg at 20 ms; third-octave +12.3 dB on WWS_Bediadiesellocomotiveidling.ogg at 120 ms; third-octave +1.4 dB on MainsBrum50Hz.ogg at 20 ms; third-octave +2.6 dB on Mains_hum_60_Hz.ogg at 20 ms; third-octave +4.4 dB on Mains_hum_60_Hz.ogg at 120 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.65, MainsBrum50Hz.ogg 120 ms +0.85
- bank_wide_lines + gate: third-octave +1.1 dB on WWS_Bediadiesellocomotiveidling.ogg at 20 ms; third-octave +1.7 dB on WWS_Compressor.ogg at 120 ms; third-octave +4.1 dB on Mains_hum_60_Hz.ogg at 20 ms; third-octave +6.5 dB on Mains_hum_60_Hz.ogg at 120 ms; near (0.5-1 dB): Inside_of_refrigerator.o 20 ms +0.84, Microwave_oven.ogg 120 ms +0.84, Table_ventilator.ogg 20 ms +0.84, Table_ventilator.ogg 120 ms +0.80, WWS_Aircompressor.ogg 20 ms +0.93, WWS_Aircompressor.ogg 120 ms +0.88, WWS_Compressor.ogg 20 ms +0.77, MainsBrum50Hz.ogg 20 ms +0.53
- floor_lines0.2 + gate: third-octave +1.6 dB on WWS_Compressor.ogg at 120 ms; third-octave +4.1 dB on Mains_hum_60_Hz.ogg at 20 ms; third-octave +6.5 dB on Mains_hum_60_Hz.ogg at 120 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.85, Table_ventilator.ogg 20 ms +0.77, Table_ventilator.ogg 120 ms +0.75, WWS_Aircompressor.ogg 20 ms +0.92, WWS_Aircompressor.ogg 120 ms +0.81, WWS_Bediadiesellocomotiv 20 ms +0.57, WWS_Compressor.ogg 20 ms +0.68, MainsBrum50Hz.ogg 20 ms +0.53
- joint + gate: third-octave +1.4 dB on Mains_hum_60_Hz.ogg at 20 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.84, Table_ventilator.ogg 20 ms +0.63, Table_ventilator.ogg 120 ms +0.74, WWS_Aircompressor.ogg 20 ms +0.91, WWS_Aircompressor.ogg 120 ms +0.77, MainsBrum50Hz.ogg 20 ms +0.53, Mains_hum_60_Hz.ogg 120 ms +0.93

## Per recording: tone bins (dB, 20 / 120 ms)

| Recording | Tones (Hz) | v2 + gate | AR adapted on prefix | AR refitted online | bank_wide_lines + gate | floor_lines0.2 + gate | joint + gate |
|---|---|---:|---:|---:|---:|---:|---:|
| Microwave_oven.ogg | 100, 173, 200, 300, 350 | 3.7 / 3.7 | 15.5 / 11.2 | 17.8 / 13.1 | 14.8 / 12.0 | 14.7 / 12.0 | 9.1 / 5.1 |
| Table_ventilator.ogg | 59, 67, 100, 119, 134, 202 | 6.1 / 4.5 | 0.3 / 0.4 | 5.4 / 5.0 | 7.1 / 5.5 | 6.9 / 5.4 | 5.9 / 5.2 |
| WWS_Aircompressor.ogg | 161, 169, 177, 185, 194, 225 | 2.9 / 3.4 | -0.5 / 4.5 | 1.5 / 11.6 | 8.2 / 8.3 | 8.2 / 8.3 | 8.1 / 7.1 |
| WWS_Bediadiesellocomotiveidling.ogg | 51, 56, 61, 86, 91, 132 | 1.7 / 0.5 | 6.3 / 4.1 | 6.3 / 4.3 | 4.0 / 2.5 | 3.7 / 2.3 | 2.8 / 2.2 |
| WWS_Compressor.ogg | 36, 54, 63, 72, 81, 90 | 0.3 / -0.0 | 3.0 / 2.2 | 3.2 / 2.6 | 6.5 / 5.3 | 6.5 / 5.4 | 1.5 / 0.1 |
| MainsBrum50Hz.ogg (electrical) | 50, 100, 150, 200, 250, 350 | 29.0 / 27.9 | 9.6 / 7.2 | 14.8 / 14.8 | 30.1 / 29.6 | 30.1 / 29.6 | 30.1 / 29.6 |
| Mains_hum_60_Hz.ogg (electrical) | 60, 119, 180, 240, 300, 315 | 51.8 / 49.7 | 45.1 / 44.4 | 8.9 / 8.9 | 52.8 / 50.6 | 52.8 / 50.6 | 51.9 / 49.9 |

## Per recording: whole band (dB, 20 / 120 ms)

| Recording | Tones (Hz) | v2 + gate | AR adapted on prefix | AR refitted online | bank_wide_lines + gate | floor_lines0.2 + gate | joint + gate |
|---|---|---:|---:|---:|---:|---:|---:|
| Inside_of_refrigerator.ogg | none | 0.2 / 0.1 | -1.3 / -0.8 | -1.2 / -0.6 | -0.1 / -0.0 | 0.2 / 0.1 | 0.1 / 0.1 |
| Microwave_oven.ogg | 100, 173, 200, 300, 350 | 1.9 / 1.8 | 2.4 / 1.8 | 2.8 / 2.6 | 3.4 / 3.2 | 3.4 / 3.2 | 3.0 / 2.3 |
| Table_ventilator.ogg | 59, 67, 100, 119, 134, 202 | 2.4 / 1.5 | -0.2 / -0.0 | 1.5 / 1.8 | 2.7 / 2.1 | 2.7 / 2.1 | 2.5 / 2.1 |
| WWS_Aircompressor.ogg | 161, 169, 177, 185, 194, 225 | 2.2 / 2.4 | -0.5 / 3.3 | 1.0 / 7.6 | 5.1 / 5.3 | 5.2 / 5.3 | 5.2 / 4.8 |
| WWS_Bediadiesellocomotiveidling.ogg | 51, 56, 61, 86, 91, 132 | 0.1 / -0.4 | 1.6 / 1.2 | 1.7 / 1.3 | 1.2 / 0.8 | 1.2 / 0.8 | 1.0 / 0.8 |
| WWS_Compressor.ogg | 36, 54, 63, 72, 81, 90 | 0.1 / -0.1 | 1.5 / 0.5 | 1.6 / 0.6 | 2.5 / 2.0 | 2.5 / 2.1 | 0.8 / 0.0 |
| MainsBrum50Hz.ogg (electrical) | 50, 100, 150, 200, 250, 350 | 23.4 / 22.5 | 9.4 / 7.0 | 9.3 / 9.3 | 24.1 / 24.0 | 24.1 / 24.0 | 24.0 / 23.9 |
| Mains_hum_60_Hz.ogg (electrical) | 60, 119, 180, 240, 300, 315 | 36.2 / 36.0 | 42.8 / 42.3 | 6.8 / 6.8 | 36.0 / 35.5 | 35.8 / 35.7 | 36.2 / 36.1 |

## Synthetic families (mean objective dB / late whole band dB)

| Method | standard | wander |
|---|---:|---:|
| Predict nothing | — / 0.00 | — / 0.00 |
| v2, no gate | 7.86 / 11.72 | 4.45 / 4.42 |
| v2 + gate | 7.90 / 11.70 | 4.39 / 4.35 |
| AR adapted on prefix | — / 8.90 | — / 6.78 |
| AR refitted online | 4.80 / 10.65 | 5.92 / 7.03 |
| bank_wide_lines, no gate | 8.00 / 12.18 | 5.75 / 5.71 |
| bank_wide_lines + gate | 8.08 / 12.23 | 5.75 / 5.71 |
| floor_lines0.2, no gate | 8.00 / 12.18 | 5.71 / 5.72 |
| floor_lines0.2 + gate | 8.09 / 12.24 | 5.71 / 5.72 |
| joint, no gate | 7.65 / 11.85 | 4.95 / 5.33 |
| joint + gate | 7.79 / 11.94 | 4.94 / 5.33 |

## Compute time

Offline Python, one thread per process, measured under the parallel pool. "Own" excludes the tone-selector update that v2 also runs. One block is 10 ms of audio.

| Method | Own ms per block, mean | Own p99, median over runs | Own p99, worst run | Own worst block | ms per block incl. selector, mean |
|---|---:|---:|---:|---:|---:|
| bank_wide_lines | 0.39 | 1.73 | 2.75 | 5.4 | 0.60 |
| floor_lines0.2 | 0.45 | 1.80 | 2.82 | 7.1 | 0.67 |
| joint | 0.94 | 2.96 | 4.08 | 5.9 | 1.15 |

Runtime: 1.1 minutes.
