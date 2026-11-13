# Tone forecaster: development run

**Development material only.** No test recording or test scene was read. Reference-signal prediction at the recording microphone; not cancellation at an ear.

Development recordings: Inside_of_refrigerator.ogg, Microwave_oven.ogg, Table_ventilator.ogg, WWS_Aircompressor.ogg, WWS_Bediadiesellocomotiveidling.ogg, WWS_Compressor.ogg, MainsBrum50Hz.ogg, Mains_hum_60_Hz.ogg.

**Change since the earlier development run:** dev-01 (kept unchanged in development/dev-01) used a sliding-window median in the line finder that cost about 2.6 ms per update; both line-finder candidates failed check (e) on time. dev-02 computes the same median with scipy.ndimage.median_filter (bit-identical values, about 0.1 ms). No forecast should change. The frozen protocol also gains a secondary ablation (the chosen candidate without its line finder). The rule is unchanged.

## Rule (stated before the first development run)

Among the gated candidates (v2 with longer fit windows, and the observer-bank variants), pick the one with the highest median, over development acoustic recordings that have reference tones, of the tone-bin gain averaged over both horizons. Eligible only if, on development material: (a) whole-band boosts (whole 35-350 Hz band below -0.5 dB at either horizon, any development recording) are no more than v2 + gate has; (b) third-octave boosts (a third-octave band 1 dB or more louder, any development recording and horizon) are no more than v2 + gate has; (c) the median whole-band gain over development acoustic recordings, averaged over both horizons, is at least v2 + gate's minus 0.1 dB; (d) the mean synthetic development objective (release-study objective) is at least v2 + gate's minus 0.5 dB and its synthetic windows below -0.5 dB are no more than v2 + gate has; (e) the compute time it adds per 10 ms block, excluding the tone-selector update that v2 also runs, is below 5 ms at the 99th percentile (offline Python, one thread, measured under the parallel pool). AR methods are comparators, not candidates: they give no per-tone output, which tune-by-ear needs. If no candidate is eligible, v2 stays.

| Candidate | Tone bins, median (dB) | Whole band, median (dB) | Synthetic objective (dB) | p99 ms per block | Checks failed | Eligible |
|---|---:|---:|---:|---:|---|---|
| v2_fit0.6 | 3.6 | 1.18 | 6.98 | 4.57 | — | yes |
| v2_fit1.2 | 3.7 | 1.09 | 6.24 | 6.72 | d_synthetic, e_time | no |
| bank_narrow | 3.4 | 1.14 | 7.47 | 1.87 | b_third_octave_boosts | no |
| bank_mid | 3.6 | 1.16 | 7.51 | 1.70 | — | yes |
| bank_wide | 3.5 | 1.20 | 7.53 | 1.72 | — | yes |
| bank_narrow_lines | 7.4 | 2.08 | 7.59 | 3.89 | b_third_octave_boosts | no |
| bank_wide_lines | 6.3 | 2.32 | 7.66 | 4.14 | — | yes |

Development pick: **bank_wide_lines**

## All methods on development material

| Method | Tone bins median, 20 / 120 ms | Whole band median, 20 / 120 ms | Whole-band boosts | Third-octave boosts | Synthetic objective | Synthetic windows < -0.5 dB | Synthetic late whole band (mean / min) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Predict nothing | 0.0 / 0.0 | 0.00 / 0.00 | 0 | 0 | — | — | 0.00 / 0.00 |
| v2, no gate | 3.2 / 3.4 | 1.02 / 0.82 | 0 | 8 | 7.24 | 6 | 10.39 / -0.45 |
| v2 + gate | 2.9 / 3.4 | 1.01 / 0.83 | 0 | 9 | 7.26 | 6 | 10.37 / -0.41 |
| AR adapted on prefix | 3.0 / 4.1 | 0.63 / 0.87 | 3 | 15 | — | — | 8.51 / -10.32 |
| AR refitted online | 5.4 / 5.0 | 1.58 / 1.54 | 2 | 15 | 5.00 | 7 | 9.99 / -0.46 |
| v2_fit0.6, no gate | 3.6 / 3.6 | 1.23 / 1.07 | 0 | 2 | 6.91 | 6 | 9.88 / -0.52 |
| v2_fit0.6 + gate | 3.3 / 3.6 | 1.23 / 1.08 | 0 | 4 | 6.98 | 6 | 9.89 / -0.41 |
| v2_fit1.2, no gate | 3.7 / 3.6 | 1.12 / 0.95 | 0 | 1 | 6.12 | 6 | 9.18 / -0.00 |
| v2_fit1.2 + gate | 3.7 / 3.6 | 1.13 / 0.98 | 0 | 3 | 6.24 | 6 | 9.23 / -0.00 |
| bank_narrow, no gate | 3.2 / 3.5 | 1.19 / 0.88 | 0 | 9 | 7.47 | 6 | 10.64 / -0.05 |
| bank_narrow + gate | 3.0 / 3.5 | 1.19 / 0.92 | 0 | 10 | 7.47 | 6 | 10.64 / -0.05 |
| bank_mid, no gate | 3.6 / 3.7 | 1.22 / 0.93 | 0 | 5 | 7.44 | 6 | 10.85 / -0.05 |
| bank_mid + gate | 3.4 / 3.7 | 1.22 / 0.96 | 0 | 6 | 7.51 | 6 | 10.89 / -0.05 |
| bank_wide, no gate | 3.6 / 3.6 | 1.23 / 1.15 | 0 | 3 | 7.46 | 6 | 10.88 / -0.00 |
| bank_wide + gate | 3.4 / 3.6 | 1.23 / 1.14 | 0 | 6 | 7.53 | 6 | 10.92 / -0.00 |
| bank_narrow_lines, no gate | 8.1 / 6.1 | 2.38 / 1.65 | 0 | 14 | 7.58 | 6 | 10.90 / -0.17 |
| bank_narrow_lines + gate | 7.8 / 6.2 | 2.45 / 1.71 | 0 | 15 | 7.59 | 6 | 10.91 / -0.17 |
| bank_wide_lines, no gate | 7.1 / 5.4 | 2.56 / 2.05 | 0 | 4 | 7.59 | 6 | 11.01 / -0.17 |
| bank_wide_lines + gate | 7.1 / 5.5 | 2.58 / 2.07 | 0 | 4 | 7.66 | 6 | 11.05 / -0.17 |

## Per recording: tone bins (dB, 20 / 120 ms)

| Recording | Tones (Hz) | v2 + gate | AR adapted on prefix | AR refitted online | v2_fit0.6 + gate | v2_fit1.2 + gate | bank_narrow + gate | bank_mid + gate | bank_wide + gate | bank_narrow_lines + gate | bank_wide_lines + gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Microwave_oven.ogg | 100, 173, 200, 300, 350 | 3.7 / 3.7 | 15.5 / 11.2 | 17.8 / 13.1 | 3.7 / 3.6 | 3.7 / 3.6 | 3.6 / 3.5 | 3.8 / 3.7 | 3.8 / 3.7 | 15.4 / 12.5 | 14.8 / 12.0 |
| Table_ventilator.ogg | 59, 67, 100, 119, 134, 202 | 6.1 / 4.5 | 0.3 / 0.4 | 5.4 / 5.0 | 5.5 / 4.2 | 4.8 / 3.9 | 6.7 / 4.8 | 6.8 / 5.1 | 6.0 / 4.7 | 8.6 / 6.2 | 7.1 / 5.5 |
| WWS_Aircompressor.ogg | 161, 169, 177, 185, 194, 225 | 2.9 / 3.4 | -0.5 / 4.5 | 1.5 / 11.6 | 3.3 / 3.9 | 3.7 / 3.8 | 3.0 / 3.7 | 3.4 / 3.7 | 3.4 / 3.6 | 7.8 / 8.5 | 8.2 / 8.3 |
| WWS_Bediadiesellocomotiveidling.og | 51, 56, 61, 86, 91, 132 | 1.7 / 0.5 | 6.3 / 4.1 | 6.3 / 4.3 | 1.4 / 1.0 | 0.9 / 0.6 | 1.6 / 1.5 | 1.5 / 1.1 | 1.5 / 1.2 | 3.9 / 4.4 | 4.0 / 2.5 |
| WWS_Compressor.ogg | 36, 54, 63, 72, 81, 90 | 0.3 / -0.0 | 3.0 / 2.2 | 3.2 / 2.6 | 0.2 / 0.1 | 0.2 / 0.1 | 0.2 / 0.1 | 0.2 / 0.1 | 0.3 / 0.0 | 6.5 / 5.1 | 6.5 / 5.3 |
| MainsBrum50Hz.ogg (electrical) | 50, 100, 150, 200, 250, 350 | 29.0 / 27.9 | 9.6 / 7.2 | 14.8 / 14.8 | 29.5 / 28.7 | 29.5 / 29.0 | 29.2 / 28.2 | 30.0 / 29.5 | 30.1 / 29.6 | 29.3 / 28.3 | 30.1 / 29.6 |
| Mains_hum_60_Hz.ogg (electrical) | 60, 119, 180, 240, 300, 315 | 51.8 / 49.7 | 45.1 / 44.4 | 8.9 / 8.9 | 50.1 / 48.2 | 47.8 / 46.5 | 52.7 / 50.1 | 52.7 / 50.1 | 52.8 / 50.6 | 52.7 / 50.1 | 52.8 / 50.6 |

## Per recording: whole band (dB, 20 / 120 ms)

| Recording | Tones (Hz) | v2 + gate | AR adapted on prefix | AR refitted online | v2_fit0.6 + gate | v2_fit1.2 + gate | bank_narrow + gate | bank_mid + gate | bank_wide + gate | bank_narrow_lines + gate | bank_wide_lines + gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Inside_of_refrigerator.ogg | none | 0.2 / 0.1 | -1.3 / -0.8 | -1.2 / -0.6 | 0.2 / 0.2 | 0.2 / 0.2 | 0.2 / 0.1 | 0.2 / 0.1 | 0.2 / 0.1 | -0.1 / -0.3 | -0.1 / -0.0 |
| Microwave_oven.ogg | 100, 173, 200, 300, 350 | 1.9 / 1.8 | 2.4 / 1.8 | 2.8 / 2.6 | 1.9 / 1.9 | 1.9 / 1.9 | 1.8 / 1.7 | 1.9 / 1.8 | 1.9 / 1.9 | 3.2 / 2.9 | 3.4 / 3.2 |
| Table_ventilator.ogg | 59, 67, 100, 119, 134, 202 | 2.4 / 1.5 | -0.2 / -0.0 | 1.5 / 1.8 | 2.3 / 1.8 | 2.1 / 1.7 | 2.3 / 1.3 | 2.5 / 1.5 | 2.4 / 1.9 | 2.5 / 1.5 | 2.7 / 2.1 |
| WWS_Aircompressor.ogg | 161, 169, 177, 185, 194, 225 | 2.2 / 2.4 | -0.5 / 3.3 | 1.0 / 7.6 | 2.5 / 2.9 | 2.9 / 2.9 | 2.3 / 2.8 | 2.7 / 2.8 | 2.6 / 2.8 | 4.8 / 5.3 | 5.1 / 5.3 |
| WWS_Bediadiesellocomotiveidling.og | 51, 56, 61, 86, 91, 132 | 0.1 / -0.4 | 1.6 / 1.2 | 1.7 / 1.3 | 0.5 / 0.4 | 0.3 / 0.2 | 0.6 / 0.5 | 0.5 / 0.4 | 0.5 / 0.4 | 1.0 / 1.1 | 1.2 / 0.8 |
| WWS_Compressor.ogg | 36, 54, 63, 72, 81, 90 | 0.1 / -0.1 | 1.5 / 0.5 | 1.6 / 0.6 | 0.1 / -0.0 | 0.1 / 0.0 | 0.1 / 0.0 | 0.0 / 0.0 | 0.1 / -0.0 | 2.4 / 1.9 | 2.5 / 2.0 |
| MainsBrum50Hz.ogg (electrical) | 50, 100, 150, 200, 250, 350 | 23.4 / 22.5 | 9.4 / 7.0 | 9.3 / 9.3 | 23.8 / 23.6 | 24.0 / 23.9 | 23.2 / 22.1 | 24.0 / 23.8 | 24.0 / 23.9 | 23.4 / 22.3 | 24.1 / 24.0 |
| Mains_hum_60_Hz.ogg (electrical) | 60, 119, 180, 240, 300, 315 | 36.2 / 36.0 | 42.8 / 42.3 | 6.8 / 6.8 | 36.2 / 36.1 | 36.1 / 36.0 | 36.1 / 35.8 | 36.1 / 35.8 | 36.2 / 36.0 | 36.0 / 35.3 | 36.0 / 35.5 |

## Synthetic families (mean objective dB / late whole band dB)

| Method | standard | wander |
|---|---:|---:|
| Predict nothing | — / 0.00 | — / 0.00 |
| v2, no gate | 7.86 / 11.72 | 4.45 / 4.42 |
| v2 + gate | 7.90 / 11.70 | 4.39 / 4.35 |
| AR adapted on prefix | — / 8.90 | — / 6.78 |
| AR refitted online | 4.80 / 10.65 | 5.92 / 7.03 |
| v2_fit0.6, no gate | 7.53 / 11.14 | 4.13 / 4.20 |
| v2_fit0.6 + gate | 7.61 / 11.15 | 4.14 / 4.21 |
| v2_fit1.2, no gate | 6.74 / 10.38 | 3.34 / 3.78 |
| v2_fit1.2 + gate | 6.87 / 10.43 | 3.44 / 3.83 |
| bank_narrow, no gate | 8.02 / 11.91 | 4.98 / 4.91 |
| bank_narrow + gate | 8.03 / 11.91 | 4.98 / 4.91 |
| bank_mid, no gate | 7.98 / 12.16 | 5.01 / 4.93 |
| bank_mid + gate | 8.06 / 12.21 | 5.01 / 4.93 |
| bank_wide, no gate | 8.00 / 12.19 | 5.05 / 4.97 |
| bank_wide + gate | 8.08 / 12.24 | 5.05 / 4.97 |
| bank_narrow_lines, no gate | 8.01 / 12.08 | 5.65 / 5.60 |
| bank_narrow_lines + gate | 8.02 / 12.08 | 5.65 / 5.60 |
| bank_wide_lines, no gate | 8.00 / 12.18 | 5.75 / 5.71 |
| bank_wide_lines + gate | 8.08 / 12.23 | 5.75 / 5.71 |

Runtime: 1.9 minutes.
