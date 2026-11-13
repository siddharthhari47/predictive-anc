# Tone forecaster study 03: development run

**Development material only.** No study-01 test recording, study-02 fresh recording, synthetic test scene or new fresh recording was read. **Reference-signal prediction only.** Every number is how well a forecaster predicts the recording microphone's own signal 20 ms or 120 ms ahead. Nothing was played, no acoustic path was modelled, and no attenuation at an ear was measured. No real-world cancellation is claimed.

Development recordings: Inside_of_refrigerator.ogg, Microwave_oven.ogg, Table_ventilator.ogg, WWS_Aircompressor.ogg, WWS_Bediadiesellocomotiveidling.ogg, WWS_Compressor.ogg, MainsBrum50Hz.ogg, Mains_hum_60_Hz.ogg. Synthetic: the 44 development scenes of studies 01 and 02 plus 8 new buzz scenes (seed 20261019; draws [{'steady': [285.8, 303.8], 'wander': [106.9, 165.9], 'harmonic': [122.6, 245.2], 'am': [182.8, 265.6]}, {'steady': [184.4, 305.2], 'wander': [122.6, 162.8], 'harmonic': [122.6, 245.2], 'am': [164.7, 303.4]}]).

## Rule

Written after the diagnostic trials on development material (results-tone-forecaster-03/diagnosis) and before the formal development run. Candidates, all gated: the joint band check of study 02 with its tie fallback capped at 0.5 dB (the fallback switched off), 1, 2 and 3 dB; above the cap only no output is allowed. Development material: the eight study-01 development recordings, the 44 development synthetic scenes and the 8 new buzz scenes. A boost is a third-octave band 1 dB or more louder; a near-boost 0.5 dB or more; both are counted over development recordings (either horizon) plus late synthetic windows. Eligible only if: (a) the boosts go down: fewer boosts than joint + gate; (b) no more near-boosts than joint + gate; (c) no more whole-band boosts (whole 35-350 Hz band below -0.5 dB on a development recording) than joint + gate; (d) the tone gain over v2 is kept: the median, over development acoustic recordings with reference tones, of the tone-bin gain averaged over both horizons is at least v2 + gate's plus half of the amount by which joint + gate exceeds v2 + gate; (e) the median whole-band gain over development acoustic recordings, averaged over both horizons, is at least joint + gate's minus 0.1 dB; (f) the mean synthetic objective is at least joint + gate's minus 0.5 dB and its synthetic windows below -0.5 dB are no more than joint + gate has; (g) its own compute time per 10 ms block at the 99th percentile, worst run, is within 0.5 ms of joint + gate's in the same run (the capped check does the same work). Among eligible candidates, pick the one with the fewest boosts, then the fewest near-boosts, then the higher tone-bin median. If none is eligible, nothing is frozen: the joint check and v2 are unchanged, and there is nothing to test on fresh recordings.

| Candidate | Boosts (rec + syn late) | Near-boosts | Whole-band boosts | Tone bins, median (dB) | Needed (dB) | Whole band, median (dB) | Synthetic objective (dB) | Windows < -0.5 dB | p99 ms per block | Checks failed | Eligible |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| cap0.5 | 1 + 23 = 24 | 36 | 0 | 2.50 | 4.35 | 1.01 | 5.85 | 6 | 11.09 | d_tone_gain_kept, e_whole_band, f_synthetic | no |
| cap1 | 1 + 24 = 25 | 38 | 0 | 2.50 | 4.35 | 1.43 | 6.58 | 6 | 11.29 | a_fewer_boosts, d_tone_gain_kept, e_whole_band | no |
| cap2 | 1 + 24 = 25 | 40 | 0 | 3.69 | 4.35 | 1.59 | 7.05 | 6 | 13.34 | a_fewer_boosts, d_tone_gain_kept | no |
| cap3 | 1 + 24 = 25 | 40 | 0 | 5.56 | 4.35 | 1.59 | 7.05 | 6 | 12.91 | a_fewer_boosts | no |
| *joint + gate (reference)* | 1 + 24 = 25 | 40 | 0 | 5.56 | | 1.59 | 7.05 | 6 | 15.26 | | |
| *v2 + gate (reference)* | 9 + 45 = 54 | 74 | 0 | 3.15 | | 0.98 | 7.02 | 6 | — | | |
| *bank_wide_lines + gate (reference)* | 4 + 50 = 54 | 72 | 0 | 6.29 | | 2.32 | 7.62 | 6 | 7.82 | | |

Development pick: **none (the joint check and v2 stay as they are)**

## How often each cap acted

Summed over horizon groups and runs. A decision is a band check after the first 4 s buffer and 5 checks. "Fallback" means the tie rule loosened the limit past 0.5 dB; "cap binding" means the cap, not the tie rule, set the limit; "silent" means only no output was allowed.

| Candidate | Part | Decisions | Fallback | Cap binding | Silent | Setting switches |
|---|---|---:|---:|---:|---:|---:|
| cap0.5 | recordings | 1281 | 0 | 371 | 166 | 77 |
| cap0.5 | scenes | 1196 | 0 | 293 | 93 | 91 |
| cap1 | recordings | 1281 | 371 | 104 | 79 | 70 |
| cap1 | scenes | 1196 | 293 | 34 | 12 | 87 |
| cap2 | recordings | 1281 | 371 | 35 | 28 | 74 |
| cap2 | scenes | 1196 | 293 | 1 | 0 | 83 |
| cap3 | recordings | 1281 | 371 | 0 | 0 | 72 |
| cap3 | scenes | 1196 | 293 | 0 | 0 | 84 |

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
| cap0.5, no gate | 2.7 / 2.2 | 1.22 / 0.80 | 0 | 1 | 6 | 5.76 | 6 | 21 / 26 |
| cap0.5 + gate | 2.8 / 2.2 | 1.23 / 0.80 | 0 | 1 | 6 | 5.85 | 6 | 23 / 30 |
| cap1, no gate | 2.7 / 2.3 | 1.52 / 1.34 | 0 | 1 | 6 | 6.48 | 6 | 20 / 27 |
| cap1 + gate | 2.8 / 2.3 | 1.52 / 1.34 | 0 | 1 | 6 | 6.58 | 6 | 24 / 32 |
| cap2, no gate | 4.2 / 3.3 | 1.73 / 1.43 | 0 | 1 | 6 | 6.95 | 6 | 20 / 27 |
| cap2 + gate | 4.1 / 3.3 | 1.75 / 1.44 | 0 | 1 | 8 | 7.05 | 6 | 24 / 32 |
| cap3, no gate | 5.8 / 5.1 | 1.73 / 1.43 | 0 | 1 | 8 | 6.95 | 6 | 20 / 27 |
| cap3 + gate | 5.9 / 5.1 | 1.75 / 1.44 | 0 | 1 | 8 | 7.05 | 6 | 24 / 32 |

## Boosts on the development recordings

- v2 + gate: third-octave +1.2 dB on Table_ventilator.ogg at 20 ms; third-octave +1.3 dB on Table_ventilator.ogg at 120 ms; third-octave +1.4 dB on WWS_Aircompressor.ogg at 20 ms; third-octave +2.5 dB on WWS_Aircompressor.ogg at 120 ms; third-octave +8.3 dB on WWS_Bediadiesellocomotiveidling.ogg at 20 ms; third-octave +12.3 dB on WWS_Bediadiesellocomotiveidling.ogg at 120 ms; third-octave +1.4 dB on MainsBrum50Hz.ogg at 20 ms; third-octave +2.6 dB on Mains_hum_60_Hz.ogg at 20 ms; third-octave +4.4 dB on Mains_hum_60_Hz.ogg at 120 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.65, MainsBrum50Hz.ogg 120 ms +0.85
- bank_wide_lines + gate: third-octave +1.1 dB on WWS_Bediadiesellocomotiveidling.ogg at 20 ms; third-octave +1.7 dB on WWS_Compressor.ogg at 120 ms; third-octave +4.1 dB on Mains_hum_60_Hz.ogg at 20 ms; third-octave +6.5 dB on Mains_hum_60_Hz.ogg at 120 ms; near (0.5-1 dB): Inside_of_refrigerator.o 20 ms +0.84, Microwave_oven.ogg 120 ms +0.84, Table_ventilator.ogg 20 ms +0.84, Table_ventilator.ogg 120 ms +0.80, WWS_Aircompressor.ogg 20 ms +0.93, WWS_Aircompressor.ogg 120 ms +0.88, WWS_Compressor.ogg 20 ms +0.77, MainsBrum50Hz.ogg 20 ms +0.53
- joint + gate: third-octave +1.4 dB on Mains_hum_60_Hz.ogg at 20 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.84, Table_ventilator.ogg 20 ms +0.63, Table_ventilator.ogg 120 ms +0.74, WWS_Aircompressor.ogg 20 ms +0.91, WWS_Aircompressor.ogg 120 ms +0.77, MainsBrum50Hz.ogg 20 ms +0.53, Mains_hum_60_Hz.ogg 120 ms +0.93
- cap0.5 + gate: third-octave +1.4 dB on Mains_hum_60_Hz.ogg at 20 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.84, Table_ventilator.ogg 20 ms +0.65, Table_ventilator.ogg 120 ms +0.73, MainsBrum50Hz.ogg 20 ms +0.53, Mains_hum_60_Hz.ogg 120 ms +0.93
- cap1 + gate: third-octave +1.4 dB on Mains_hum_60_Hz.ogg at 20 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.84, Table_ventilator.ogg 20 ms +0.63, Table_ventilator.ogg 120 ms +0.74, MainsBrum50Hz.ogg 20 ms +0.53, Mains_hum_60_Hz.ogg 120 ms +0.93
- cap2 + gate: third-octave +1.4 dB on Mains_hum_60_Hz.ogg at 20 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.84, Table_ventilator.ogg 20 ms +0.63, Table_ventilator.ogg 120 ms +0.74, WWS_Aircompressor.ogg 20 ms +0.70, WWS_Aircompressor.ogg 120 ms +0.59, MainsBrum50Hz.ogg 20 ms +0.53, Mains_hum_60_Hz.ogg 120 ms +0.93
- cap3 + gate: third-octave +1.4 dB on Mains_hum_60_Hz.ogg at 20 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.84, Table_ventilator.ogg 20 ms +0.63, Table_ventilator.ogg 120 ms +0.74, WWS_Aircompressor.ogg 20 ms +0.91, WWS_Aircompressor.ogg 120 ms +0.77, MainsBrum50Hz.ogg 20 ms +0.53, Mains_hum_60_Hz.ogg 120 ms +0.93

## Synthetic late windows with a boost (>= 1 dB), by scene

- v2, no gate: buzz_am 4, buzz_harmonic 1, buzz_steady 2, buzz_wander 3, drifting_tones 1, harmonic_tones 3, single_tone 2, source_change_9s 6, tone_appears_9s 5, tones_in_rumble 3, tones_stop_9s 4, unrelated_tones 2, wander_fast 2, wander_mixed_noisy 1, weak_tones_in_noise 1
- v2 + gate: buzz_am 4, buzz_harmonic 1, buzz_steady 2, buzz_wander 3, drifting_tones 1, harmonic_tones 3, single_tone 2, source_change_9s 6, tone_appears_9s 5, tones_in_rumble 5, tones_stop_9s 3, unrelated_tones 2, wander_am_rumble 4, wander_fast 2, wander_mixed_noisy 1, weak_tones_in_noise 1
- bank_wide_lines, no gate: buzz_am 4, buzz_harmonic 4, buzz_steady 4, buzz_wander 4, drifting_tones 3, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 5, wander_am_rumble 4, wander_fast 4, wander_mixed_noisy 4, wander_slow 4
- bank_wide_lines + gate: buzz_am 4, buzz_harmonic 4, buzz_steady 4, buzz_wander 4, drifting_tones 3, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 4, wander_am_rumble 4, wander_fast 4, wander_mixed_noisy 4, wander_slow 4
- joint, no gate: buzz_am 2, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 4, wander_fast 2
- joint + gate: buzz_am 4, buzz_wander 3, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 3, wander_fast 2
- cap0.5, no gate: drifting_tones 2, harmonic_tones 1, single_tone 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 4, wander_fast 2
- cap0.5 + gate: buzz_wander 3, drifting_tones 2, harmonic_tones 1, single_tone 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 3, wander_fast 2
- cap1, no gate: buzz_am 2, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 4, wander_fast 2
- cap1 + gate: buzz_am 4, buzz_wander 3, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 3, wander_fast 2
- cap2, no gate: buzz_am 2, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 4, wander_fast 2
- cap2 + gate: buzz_am 4, buzz_wander 3, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 3, wander_fast 2
- cap3, no gate: buzz_am 2, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 4, wander_fast 2
- cap3 + gate: buzz_am 4, buzz_wander 3, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 3, wander_fast 2

## Per recording: tone bins (dB, 20 / 120 ms)

| Recording | Tones (Hz) | v2 + gate | AR adapted on prefix | AR refitted online | bank_wide_lines + gate | joint + gate | cap0.5 + gate | cap1 + gate | cap2 + gate | cap3 + gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Microwave_oven.ogg | 100, 173, 200, 300, 350 | 3.7 / 3.7 | 15.5 / 11.2 | 17.8 / 13.1 | 14.8 / 12.0 | 9.1 / 5.1 | 8.7 / 5.1 | 9.1 / 5.1 | 9.1 / 5.1 | 9.1 / 5.1 |
| Table_ventilator.ogg | 59, 67, 100, 119, 134, 202 | 6.1 / 4.5 | 0.3 / 0.4 | 5.4 / 5.0 | 7.1 / 5.5 | 5.9 / 5.2 | 5.9 / 5.2 | 5.9 / 5.2 | 5.9 / 5.2 | 5.9 / 5.2 |
| WWS_Aircompressor.ogg | 161, 169, 177, 185, 194, 225 | 2.9 / 3.4 | -0.5 / 4.5 | 1.5 / 11.6 | 8.2 / 8.3 | 8.1 / 7.1 | 1.7 / 0.9 | 2.4 / 2.3 | 4.1 / 3.3 | 8.1 / 7.1 |
| WWS_Bediadiesellocomotiveidling.ogg | 51, 56, 61, 86, 91, 132 | 1.7 / 0.5 | 6.3 / 4.1 | 6.3 / 4.3 | 4.0 / 2.5 | 2.8 / 2.2 | 2.8 / 2.2 | 2.8 / 2.2 | 2.8 / 2.2 | 2.8 / 2.2 |
| WWS_Compressor.ogg | 36, 54, 63, 72, 81, 90 | 0.3 / -0.0 | 3.0 / 2.2 | 3.2 / 2.6 | 6.5 / 5.3 | 1.5 / 0.1 | 1.5 / 0.1 | 1.5 / 0.1 | 1.5 / 0.1 | 1.5 / 0.1 |
| MainsBrum50Hz.ogg (electrical) | 50, 100, 150, 200, 250, 350 | 29.0 / 27.9 | 9.6 / 7.2 | 14.8 / 14.8 | 30.1 / 29.6 | 30.1 / 29.6 | 30.1 / 29.6 | 30.1 / 29.6 | 30.1 / 29.6 | 30.1 / 29.6 |
| Mains_hum_60_Hz.ogg (electrical) | 60, 119, 180, 240, 300, 315 | 51.8 / 49.7 | 45.1 / 44.4 | 8.9 / 8.9 | 52.8 / 50.6 | 51.9 / 49.9 | 51.9 / 49.9 | 51.9 / 49.9 | 51.9 / 49.9 | 51.9 / 49.9 |

## Per recording: whole band (dB, 20 / 120 ms)

| Recording | Tones (Hz) | v2 + gate | AR adapted on prefix | AR refitted online | bank_wide_lines + gate | joint + gate | cap0.5 + gate | cap1 + gate | cap2 + gate | cap3 + gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Inside_of_refrigerator.ogg | none | 0.2 / 0.1 | -1.3 / -0.8 | -1.2 / -0.6 | -0.1 / -0.0 | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 |
| Microwave_oven.ogg | 100, 173, 200, 300, 350 | 1.9 / 1.8 | 2.4 / 1.8 | 2.8 / 2.6 | 3.4 / 3.2 | 3.0 / 2.3 | 2.9 / 2.3 | 3.0 / 2.3 | 3.0 / 2.3 | 3.0 / 2.3 |
| Table_ventilator.ogg | 59, 67, 100, 119, 134, 202 | 2.4 / 1.5 | -0.2 / -0.0 | 1.5 / 1.8 | 2.7 / 2.1 | 2.5 / 2.1 | 2.5 / 2.1 | 2.5 / 2.1 | 2.5 / 2.1 | 2.5 / 2.1 |
| WWS_Aircompressor.ogg | 161, 169, 177, 185, 194, 225 | 2.2 / 2.4 | -0.5 / 3.3 | 1.0 / 7.6 | 5.1 / 5.3 | 5.2 / 4.8 | 1.4 / 0.8 | 2.0 / 1.9 | 3.2 / 2.6 | 5.2 / 4.8 |
| WWS_Bediadiesellocomotiveidling.ogg | 51, 56, 61, 86, 91, 132 | 0.1 / -0.4 | 1.6 / 1.2 | 1.7 / 1.3 | 1.2 / 0.8 | 1.0 / 0.8 | 1.0 / 0.8 | 1.0 / 0.8 | 1.0 / 0.8 | 1.0 / 0.8 |
| WWS_Compressor.ogg | 36, 54, 63, 72, 81, 90 | 0.1 / -0.1 | 1.5 / 0.5 | 1.6 / 0.6 | 2.5 / 2.0 | 0.8 / 0.0 | 0.8 / 0.0 | 0.8 / 0.0 | 0.8 / 0.0 | 0.8 / 0.0 |
| MainsBrum50Hz.ogg (electrical) | 50, 100, 150, 200, 250, 350 | 23.4 / 22.5 | 9.4 / 7.0 | 9.3 / 9.3 | 24.1 / 24.0 | 24.0 / 23.9 | 24.0 / 23.9 | 24.0 / 23.9 | 24.0 / 23.9 | 24.0 / 23.9 |
| Mains_hum_60_Hz.ogg (electrical) | 60, 119, 180, 240, 300, 315 | 36.2 / 36.0 | 42.8 / 42.3 | 6.8 / 6.8 | 36.0 / 35.5 | 36.2 / 36.1 | 36.2 / 36.1 | 36.2 / 36.1 | 36.2 / 36.1 | 36.2 / 36.1 |

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
| cap0.5, no gate | 4.46 / 4.71 | 6.22 / 10.61 | 4.95 / 5.33 |
| cap0.5 + gate | 4.47 / 4.74 | 6.36 / 10.70 | 4.94 / 5.33 |
| cap1, no gate | 5.59 / 5.60 | 7.02 / 11.85 | 4.95 / 5.33 |
| cap1 + gate | 5.60 / 5.63 | 7.16 / 11.94 | 4.94 / 5.33 |
| cap2, no gate | 5.84 / 5.99 | 7.65 / 11.85 | 4.95 / 5.33 |
| cap2 + gate | 5.84 / 6.01 | 7.79 / 11.94 | 4.94 / 5.33 |
| cap3, no gate | 5.84 / 5.99 | 7.65 / 11.85 | 4.95 / 5.33 |
| cap3 + gate | 5.84 / 6.01 | 7.79 / 11.94 | 4.94 / 5.33 |

## Compute time

Offline Python, one thread per process, measured under the parallel pool. "Own" excludes the tone-selector update that v2 also runs. One block is 10 ms of audio.

| Method | Own ms per block, mean | Own p99, median over runs | Own p99, worst run | Own worst block | ms per block incl. selector, mean |
|---|---:|---:|---:|---:|---:|
| bank_wide_lines | 1.00 | 4.12 | 7.82 | 17.2 | 1.46 |
| joint | 2.53 | 6.95 | 15.26 | 30.7 | 3.00 |
| cap0.5 | 2.48 | 6.85 | 11.09 | 20.9 | 2.95 |
| cap1 | 2.48 | 6.99 | 11.29 | 24.0 | 2.95 |
| cap2 | 2.47 | 6.74 | 13.34 | 28.8 | 2.94 |
| cap3 | 2.45 | 6.83 | 12.91 | 23.4 | 2.91 |

Runtime: 6.3 minutes.
