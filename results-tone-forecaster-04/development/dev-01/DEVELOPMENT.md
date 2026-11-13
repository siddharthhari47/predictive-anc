# Tone forecaster study 04: development run

**Development material only.** No study-01 test recording, study-02 fresh recording, synthetic test scene or new fresh recording was read. **Reference-signal prediction only.** Every number is how well a forecaster predicts the recording microphone's own signal 20 ms or 120 ms ahead. Nothing was played, no acoustic path was modelled, and no attenuation at an ear was measured. No real-world cancellation is claimed.

Development recordings: Inside_of_refrigerator.ogg, Microwave_oven.ogg, Table_ventilator.ogg, WWS_Aircompressor.ogg, WWS_Bediadiesellocomotiveidling.ogg, WWS_Compressor.ogg, MainsBrum50Hz.ogg, Mains_hum_60_Hz.ogg. Synthetic: the 44 development scenes of studies 01 and 02 plus study 03's 8 buzz scenes (seed 20261019).

"+ gate" always means the output after the v2 gate as that method uses it: switched (v2, joint, bank_wide_lines, gcheck) or faded (the names with fade8 or fade8in3out). The gate decides the same way in every case. gcheck is the band check that judges each setting after its own copy of the gate.

**Note:** Formal development run. Another project's training job (train.py) and a study-05 check were using the processor, so absolute compute times run high; the rule's time check compares each candidate with joint + gate in the same run.

## Rule

Written after the diagnostic trials on development material (results-tone-forecaster-04/diagnosis) and before the formal development run. Candidates, all driven by the v2 gate's decision: the joint band check of study 02 with the gate faded instead of switched (a cosine fade over 8 blocks in and 8 out, joint_fade8; 8 in and 3 out, joint_fade8in3out; one block is 10 ms), and the band check that judges each setting after its own copy of the gate (tone_gate_fade.GatedCheckBank) with the hard gate (gcheck), the 8/8 fade (gcheck_fade8) and the 8/3 fade (gcheck_fade8in3out). Development material: the eight study-01 development recordings, the 44 development synthetic scenes and study 03's 8 buzz scenes. A boost is a third-octave band 1 dB or more louder; a near-boost 0.5 dB or more; both are counted over development recordings (either horizon) plus late synthetic windows. Eligible only if: (a) fewer boosts than joint + gate; (b) the gate's boosts are gone: on the buzz scenes, no more late boosts than the joint check with no gate at all; (c) no more near-boosts than joint + gate; (d) no more whole-band boosts (whole 35-350 Hz band below -0.5 dB on a development recording) than joint + gate; (e) the tone gain over v2 is kept: the median, over development acoustic recordings with reference tones, of the tone-bin gain averaged over both horizons is at least v2 + gate's plus half of the amount by which joint + gate exceeds v2 + gate; (f) the median whole-band gain over development acoustic recordings, averaged over both horizons, is at least joint + gate's minus 0.1 dB; (g) the mean synthetic objective is at least joint + gate's minus 0.5 dB and its synthetic windows below -0.5 dB are no more than joint + gate has; (h) the compute it adds is small: over all development runs, the median of its own 99th-percentile time per 10 ms block (fade included) minus joint + gate's in the same run is at most 1 ms. Among eligible candidates, pick the one with the fewest boosts, then the fewest near-boosts, then the higher tone-bin median. If none is eligible, nothing is frozen: the joint check and v2 are unchanged, and there is nothing to test on fresh recordings.

| Candidate | Boosts (rec + syn late) | Buzz late boosts | Near-boosts | Whole-band boosts | Tone bins, median (dB) | Needed (dB) | Whole band, median (dB) | Synthetic objective (dB) | Windows < -0.5 dB | p99 ms per block, median | Added over joint (ms) | Checks failed | Eligible |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| joint_fade8 | 1 + 19 = 20 | 2 | 35 | 0 | 5.50 | 4.35 | 1.59 | 6.98 | 6 | 5.72 | +0.02 | — | yes |
| joint_fade8in3out | 1 + 19 = 20 | 2 | 35 | 0 | 5.55 | 4.35 | 1.60 | 7.02 | 6 | 5.74 | +0.08 | — | yes |
| gcheck | 1 + 21 = 22 | 5 | 38 | 0 | 5.31 | 4.35 | 1.57 | 7.06 | 6 | 5.92 | +0.21 | b_gate_boosts_gone | no |
| gcheck_fade8 | 1 + 17 = 18 | 1 | 36 | 0 | 5.24 | 4.35 | 1.56 | 6.97 | 6 | 5.87 | +0.48 | — | yes |
| gcheck_fade8in3out | 1 + 18 = 19 | 2 | 33 | 0 | 5.36 | 4.35 | 1.58 | 7.02 | 6 | 5.94 | +0.27 | — | yes |
| *joint + gate (reference)* | 1 + 24 = 25 | 7 | 40 | 0 | 5.56 | | 1.59 | 7.05 | 6 | 5.67 | | | |
| *v2 + gate (reference)* | 9 + 45 = 54 | 10 | 74 | 0 | 3.15 | | 0.98 | 7.02 | 6 | — | | | |
| *bank_wide_lines + gate (reference)* | 4 + 50 = 54 | 16 | 72 | 0 | 6.29 | | 2.32 | 7.62 | 6 | 3.39 | | | |
| *v2 + fade8 (reference)* | 8 + 40 = 48 | 10 | 69 | 0 | 3.30 | | 0.98 | 6.99 | 6 | — | | | |
| *joint, no gate (reference)* | 1 + 20 = 21 | 2 | 35 | 0 | 5.48 | | 1.58 | 6.95 | 6 | — | | | |

Development pick: **gcheck_fade8**

## How often the gate switched

Summed over runs, 20 ms group (the gate shares its decision across groups). "Open" is the share of scored blocks the gate let through; "mean gain" is the faded gain (equal to "open" for a switched gate).

| Method | Part | Switches | Open | Mean gain |
|---|---|---:|---:|---:|
| v2 | recordings | 609 | 0.974 | 0.974 |
| v2 | scenes | 416 | 0.980 | 0.980 |
| bank_wide_lines | recordings | 165 | 0.989 | 0.989 |
| bank_wide_lines | scenes | 82 | 0.994 | 0.994 |
| joint | recordings | 169 | 0.986 | 0.986 |
| joint | scenes | 132 | 0.991 | 0.991 |
| v2_fade8 | recordings | 609 | 0.974 | 0.989 |
| v2_fade8 | scenes | 416 | 0.980 | 0.980 |
| joint_fade8 | recordings | 169 | 0.986 | 0.990 |
| joint_fade8 | scenes | 132 | 0.991 | 0.988 |
| joint_fade8in3out | recordings | 169 | 0.986 | 0.983 |
| joint_fade8in3out | scenes | 132 | 0.991 | 0.987 |
| gcheck | recordings | 163 | 0.986 | 0.986 |
| gcheck | scenes | 122 | 0.992 | 0.992 |
| gcheck_fade8 | recordings | 165 | 0.987 | 0.990 |
| gcheck_fade8 | scenes | 120 | 0.992 | 0.989 |
| gcheck_fade8in3out | recordings | 163 | 0.986 | 0.983 |
| gcheck_fade8in3out | scenes | 122 | 0.992 | 0.988 |

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
| v2_fade8, no gate | 3.2 / 3.4 | 1.02 / 0.82 | 0 | 8 | 11 | 7.01 | 6 | 40 / 57 |
| v2_fade8 + gate | 3.2 / 3.4 | 1.02 / 0.83 | 0 | 8 | 11 | 6.99 | 6 | 40 / 58 |
| joint_fade8, no gate | 5.8 / 5.1 | 1.73 / 1.43 | 0 | 1 | 8 | 6.95 | 6 | 20 / 27 |
| joint_fade8 + gate | 5.9 / 5.1 | 1.74 / 1.44 | 0 | 1 | 8 | 6.98 | 6 | 19 / 27 |
| joint_fade8in3out, no gate | 5.8 / 5.1 | 1.73 / 1.43 | 0 | 1 | 8 | 6.95 | 6 | 20 / 27 |
| joint_fade8in3out + gate | 5.9 / 5.1 | 1.76 / 1.44 | 0 | 1 | 8 | 7.02 | 6 | 19 / 27 |
| gcheck, no gate | 5.6 / 4.0 | 1.70 / 1.43 | 0 | 1 | 6 | 6.96 | 6 | 18 / 27 |
| gcheck + gate | 5.7 / 4.0 | 1.72 / 1.42 | 0 | 1 | 7 | 7.06 | 6 | 21 / 31 |
| gcheck_fade8, no gate | 5.8 / 4.6 | 1.73 / 1.37 | 0 | 1 | 8 | 6.94 | 6 | 18 / 28 |
| gcheck_fade8 + gate | 5.9 / 4.6 | 1.74 / 1.38 | 0 | 1 | 8 | 6.97 | 6 | 17 / 28 |
| gcheck_fade8in3out, no gate | 5.9 / 4.7 | 1.74 / 1.39 | 0 | 1 | 8 | 6.96 | 6 | 17 / 26 |
| gcheck_fade8in3out + gate | 6.0 / 4.7 | 1.77 / 1.39 | 0 | 1 | 8 | 7.02 | 6 | 18 / 25 |

## Synthetic late boosts by family (>= 1 dB / >= 0.5 dB)

| Method | buzz | standard | wander |
|---|---:|---:|---:|
| v2, no gate | 10 / 14 | 27 / 36 | 3 / 7 |
| v2 + gate | 10 / 14 | 28 / 38 | 7 / 11 |
| bank_wide_lines, no gate | 16 / 16 | 19 / 28 | 16 / 16 |
| bank_wide_lines + gate | 16 / 16 | 18 / 28 | 16 / 16 |
| joint, no gate | 2 / 5 | 16 / 20 | 2 / 2 |
| joint + gate | 7 / 9 | 15 / 21 | 2 / 2 |
| v2_fade8, no gate | 10 / 14 | 27 / 36 | 3 / 7 |
| v2_fade8 + gate | 10 / 14 | 27 / 35 | 3 / 9 |
| joint_fade8, no gate | 2 / 5 | 16 / 20 | 2 / 2 |
| joint_fade8 + gate | 2 / 5 | 15 / 20 | 2 / 2 |
| joint_fade8in3out, no gate | 2 / 5 | 16 / 20 | 2 / 2 |
| joint_fade8in3out + gate | 2 / 6 | 15 / 19 | 2 / 2 |
| gcheck, no gate | 2 / 6 | 16 / 20 | 0 / 1 |
| gcheck + gate | 5 / 9 | 15 / 21 | 1 / 1 |
| gcheck_fade8, no gate | 1 / 6 | 16 / 20 | 1 / 2 |
| gcheck_fade8 + gate | 1 / 6 | 15 / 20 | 1 / 2 |
| gcheck_fade8in3out, no gate | 1 / 5 | 16 / 20 | 0 / 1 |
| gcheck_fade8in3out + gate | 2 / 5 | 15 / 19 | 1 / 1 |

## Boosts on the development recordings

- v2 + gate: third-octave +1.2 dB on Table_ventilator.ogg at 20 ms; third-octave +1.3 dB on Table_ventilator.ogg at 120 ms; third-octave +1.4 dB on WWS_Aircompressor.ogg at 20 ms; third-octave +2.5 dB on WWS_Aircompressor.ogg at 120 ms; third-octave +8.3 dB on WWS_Bediadiesellocomotiveidling.ogg at 20 ms; third-octave +12.3 dB on WWS_Bediadiesellocomotiveidling.ogg at 120 ms; third-octave +1.4 dB on MainsBrum50Hz.ogg at 20 ms; third-octave +2.6 dB on Mains_hum_60_Hz.ogg at 20 ms; third-octave +4.4 dB on Mains_hum_60_Hz.ogg at 120 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.65, MainsBrum50Hz.ogg 120 ms +0.85
- bank_wide_lines + gate: third-octave +1.1 dB on WWS_Bediadiesellocomotiveidling.ogg at 20 ms; third-octave +1.7 dB on WWS_Compressor.ogg at 120 ms; third-octave +4.1 dB on Mains_hum_60_Hz.ogg at 20 ms; third-octave +6.5 dB on Mains_hum_60_Hz.ogg at 120 ms; near (0.5-1 dB): Inside_of_refrigerator.o 20 ms +0.84, Microwave_oven.ogg 120 ms +0.84, Table_ventilator.ogg 20 ms +0.84, Table_ventilator.ogg 120 ms +0.80, WWS_Aircompressor.ogg 20 ms +0.93, WWS_Aircompressor.ogg 120 ms +0.88, WWS_Compressor.ogg 20 ms +0.77, MainsBrum50Hz.ogg 20 ms +0.53
- joint + gate: third-octave +1.4 dB on Mains_hum_60_Hz.ogg at 20 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.84, Table_ventilator.ogg 20 ms +0.63, Table_ventilator.ogg 120 ms +0.74, WWS_Aircompressor.ogg 20 ms +0.91, WWS_Aircompressor.ogg 120 ms +0.77, MainsBrum50Hz.ogg 20 ms +0.53, Mains_hum_60_Hz.ogg 120 ms +0.93
- v2_fade8 + gate: third-octave +1.1 dB on Table_ventilator.ogg at 20 ms; third-octave +1.2 dB on Table_ventilator.ogg at 120 ms; third-octave +1.9 dB on WWS_Aircompressor.ogg at 120 ms; third-octave +8.1 dB on WWS_Bediadiesellocomotiveidling.ogg at 20 ms; third-octave +12.2 dB on WWS_Bediadiesellocomotiveidling.ogg at 120 ms; third-octave +1.4 dB on MainsBrum50Hz.ogg at 20 ms; third-octave +2.6 dB on Mains_hum_60_Hz.ogg at 20 ms; third-octave +4.4 dB on Mains_hum_60_Hz.ogg at 120 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.76, WWS_Aircompressor.ogg 20 ms +0.96, MainsBrum50Hz.ogg 120 ms +0.85
- joint_fade8 + gate: third-octave +1.4 dB on Mains_hum_60_Hz.ogg at 20 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.84, Table_ventilator.ogg 20 ms +0.50, Table_ventilator.ogg 120 ms +0.69, WWS_Aircompressor.ogg 20 ms +0.66, WWS_Aircompressor.ogg 120 ms +0.56, MainsBrum50Hz.ogg 20 ms +0.53, Mains_hum_60_Hz.ogg 120 ms +0.93
- joint_fade8in3out + gate: third-octave +1.4 dB on Mains_hum_60_Hz.ogg at 20 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.84, Table_ventilator.ogg 20 ms +0.52, Table_ventilator.ogg 120 ms +0.69, WWS_Aircompressor.ogg 20 ms +0.67, WWS_Aircompressor.ogg 120 ms +0.57, MainsBrum50Hz.ogg 20 ms +0.53, Mains_hum_60_Hz.ogg 120 ms +0.93
- gcheck + gate: third-octave +1.4 dB on Mains_hum_60_Hz.ogg at 20 ms; near (0.5-1 dB): Table_ventilator.ogg 20 ms +0.58, Table_ventilator.ogg 120 ms +0.66, WWS_Aircompressor.ogg 20 ms +0.92, WWS_Aircompressor.ogg 120 ms +0.79, MainsBrum50Hz.ogg 20 ms +0.53, Mains_hum_60_Hz.ogg 120 ms +0.93
- gcheck_fade8 + gate: third-octave +1.4 dB on Mains_hum_60_Hz.ogg at 20 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.84, Table_ventilator.ogg 20 ms +0.50, Table_ventilator.ogg 120 ms +0.73, WWS_Aircompressor.ogg 20 ms +0.66, WWS_Aircompressor.ogg 120 ms +0.57, MainsBrum50Hz.ogg 20 ms +0.53, Mains_hum_60_Hz.ogg 120 ms +0.93
- gcheck_fade8in3out + gate: third-octave +1.4 dB on Mains_hum_60_Hz.ogg at 20 ms; near (0.5-1 dB): Microwave_oven.ogg 120 ms +0.83, Table_ventilator.ogg 20 ms +0.51, Table_ventilator.ogg 120 ms +0.67, WWS_Aircompressor.ogg 20 ms +0.67, WWS_Aircompressor.ogg 120 ms +0.58, MainsBrum50Hz.ogg 20 ms +0.53, Mains_hum_60_Hz.ogg 120 ms +0.93

## Synthetic late windows with a boost (>= 1 dB), by scene

- v2, no gate: buzz_am 4, buzz_harmonic 1, buzz_steady 2, buzz_wander 3, drifting_tones 1, harmonic_tones 3, single_tone 2, source_change_9s 6, tone_appears_9s 5, tones_in_rumble 3, tones_stop_9s 4, unrelated_tones 2, wander_fast 2, wander_mixed_noisy 1, weak_tones_in_noise 1
- v2 + gate: buzz_am 4, buzz_harmonic 1, buzz_steady 2, buzz_wander 3, drifting_tones 1, harmonic_tones 3, single_tone 2, source_change_9s 6, tone_appears_9s 5, tones_in_rumble 5, tones_stop_9s 3, unrelated_tones 2, wander_am_rumble 4, wander_fast 2, wander_mixed_noisy 1, weak_tones_in_noise 1
- bank_wide_lines, no gate: buzz_am 4, buzz_harmonic 4, buzz_steady 4, buzz_wander 4, drifting_tones 3, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 5, wander_am_rumble 4, wander_fast 4, wander_mixed_noisy 4, wander_slow 4
- bank_wide_lines + gate: buzz_am 4, buzz_harmonic 4, buzz_steady 4, buzz_wander 4, drifting_tones 3, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 4, wander_am_rumble 4, wander_fast 4, wander_mixed_noisy 4, wander_slow 4
- joint, no gate: buzz_am 2, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 4, wander_fast 2
- joint + gate: buzz_am 4, buzz_wander 3, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 3, wander_fast 2
- v2_fade8, no gate: buzz_am 4, buzz_harmonic 1, buzz_steady 2, buzz_wander 3, drifting_tones 1, harmonic_tones 3, single_tone 2, source_change_9s 6, tone_appears_9s 5, tones_in_rumble 3, tones_stop_9s 4, unrelated_tones 2, wander_fast 2, wander_mixed_noisy 1, weak_tones_in_noise 1
- v2_fade8 + gate: buzz_am 4, buzz_harmonic 1, buzz_steady 2, buzz_wander 3, drifting_tones 1, harmonic_tones 3, single_tone 2, source_change_9s 6, tone_appears_9s 5, tones_in_rumble 4, tones_stop_9s 3, unrelated_tones 2, wander_fast 2, wander_mixed_noisy 1, weak_tones_in_noise 1
- joint_fade8, no gate: buzz_am 2, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 4, wander_fast 2
- joint_fade8 + gate: buzz_am 2, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 3, wander_fast 2
- joint_fade8in3out, no gate: buzz_am 2, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 4, wander_fast 2
- joint_fade8in3out + gate: buzz_am 2, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 3, wander_fast 2
- gcheck, no gate: buzz_am 1, buzz_wander 1, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 4
- gcheck + gate: buzz_am 2, buzz_wander 3, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 3, wander_fast 1
- gcheck_fade8, no gate: buzz_am 1, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 4, wander_fast 1
- gcheck_fade8 + gate: buzz_am 1, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 3, wander_fast 1
- gcheck_fade8in3out, no gate: buzz_am 1, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 4
- gcheck_fade8in3out + gate: buzz_am 1, buzz_wander 1, drifting_tones 1, source_change_9s 6, tone_appears_9s 5, tones_stop_9s 3, wander_fast 1

## Per recording: tone bins (dB, 20 / 120 ms)

| Recording | Tones (Hz) | v2 + gate | AR adapted on prefix | AR refitted online | bank_wide_lines + gate | joint + gate | v2_fade8 + gate | joint_fade8 + gate | joint_fade8in3out + gate | gcheck + gate | gcheck_fade8 + gate | gcheck_fade8in3out + gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Microwave_oven.ogg | 100, 173, 200, 300, 350 | 3.7 / 3.7 | 15.5 / 11.2 | 17.8 / 13.1 | 14.8 / 12.0 | 9.1 / 5.1 | 3.7 / 3.6 | 9.0 / 5.1 | 9.1 / 5.1 | 13.6 / 4.0 | 9.0 / 10.6 | 13.4 / 10.7 |
| Table_ventilator.ogg | 59, 67, 100, 119, 134, 202 | 6.1 / 4.5 | 0.3 / 0.4 | 5.4 / 5.0 | 7.1 / 5.5 | 5.9 / 5.2 | 6.1 / 4.5 | 5.9 / 5.1 | 5.9 / 5.2 | 5.7 / 4.9 | 5.9 / 4.6 | 6.0 / 4.7 |
| WWS_Aircompressor.ogg | 161, 169, 177, 185, 194, 225 | 2.9 / 3.4 | -0.5 / 4.5 | 1.5 / 11.6 | 8.2 / 8.3 | 8.1 / 7.1 | 3.2 / 3.4 | 8.3 / 7.1 | 8.3 / 7.1 | 8.0 / 7.3 | 8.2 / 7.2 | 8.3 / 6.8 |
| WWS_Bediadiesellocomotiveidling.ogg | 51, 56, 61, 86, 91, 132 | 1.7 / 0.5 | 6.3 / 4.1 | 6.3 / 4.3 | 4.0 / 2.5 | 2.8 / 2.2 | 1.7 / 0.5 | 2.7 / 2.2 | 2.8 / 2.2 | 2.8 / 2.5 | 2.7 / 2.5 | 2.7 / 2.5 |
| WWS_Compressor.ogg | 36, 54, 63, 72, 81, 90 | 0.3 / -0.0 | 3.0 / 2.2 | 3.2 / 2.6 | 6.5 / 5.3 | 1.5 / 0.1 | 0.3 / -0.0 | 1.5 / 0.1 | 1.5 / 0.1 | 1.5 / 0.1 | 1.5 / 0.1 | 1.5 / 0.1 |
| MainsBrum50Hz.ogg (electrical) | 50, 100, 150, 200, 250, 350 | 29.0 / 27.9 | 9.6 / 7.2 | 14.8 / 14.8 | 30.1 / 29.6 | 30.1 / 29.6 | 29.0 / 27.9 | 30.1 / 29.6 | 30.1 / 29.6 | 30.1 / 29.6 | 30.1 / 29.6 | 30.1 / 29.6 |
| Mains_hum_60_Hz.ogg (electrical) | 60, 119, 180, 240, 300, 315 | 51.8 / 49.7 | 45.1 / 44.4 | 8.9 / 8.9 | 52.8 / 50.6 | 51.9 / 49.9 | 51.8 / 49.7 | 51.9 / 49.9 | 51.9 / 49.9 | 51.9 / 49.9 | 51.9 / 49.9 | 51.9 / 49.9 |

## Per recording: whole band (dB, 20 / 120 ms)

| Recording | Tones (Hz) | v2 + gate | AR adapted on prefix | AR refitted online | bank_wide_lines + gate | joint + gate | v2_fade8 + gate | joint_fade8 + gate | joint_fade8in3out + gate | gcheck + gate | gcheck_fade8 + gate | gcheck_fade8in3out + gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Inside_of_refrigerator.ogg | none | 0.2 / 0.1 | -1.3 / -0.8 | -1.2 / -0.6 | -0.1 / -0.0 | 0.1 / 0.1 | 0.2 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 |
| Microwave_oven.ogg | 100, 173, 200, 300, 350 | 1.9 / 1.8 | 2.4 / 1.8 | 2.8 / 2.6 | 3.4 / 3.2 | 3.0 / 2.3 | 1.9 / 1.8 | 3.0 / 2.3 | 3.0 / 2.3 | 3.4 / 2.1 | 3.0 / 3.1 | 3.4 / 3.1 |
| Table_ventilator.ogg | 59, 67, 100, 119, 134, 202 | 2.4 / 1.5 | -0.2 / -0.0 | 1.5 / 1.8 | 2.7 / 2.1 | 2.5 / 2.1 | 2.3 / 1.5 | 2.5 / 2.1 | 2.5 / 2.1 | 2.4 / 2.0 | 2.5 / 1.9 | 2.5 / 2.0 |
| WWS_Aircompressor.ogg | 161, 169, 177, 185, 194, 225 | 2.2 / 2.4 | -0.5 / 3.3 | 1.0 / 7.6 | 5.1 / 5.3 | 5.2 / 4.8 | 2.4 / 2.5 | 5.3 / 4.8 | 5.3 / 4.8 | 5.1 / 4.9 | 5.2 / 4.8 | 5.3 / 4.7 |
| WWS_Bediadiesellocomotiveidling.ogg | 51, 56, 61, 86, 91, 132 | 0.1 / -0.4 | 1.6 / 1.2 | 1.7 / 1.3 | 1.2 / 0.8 | 1.0 / 0.8 | 0.2 / -0.4 | 1.0 / 0.8 | 1.0 / 0.8 | 1.0 / 0.8 | 1.0 / 0.8 | 1.0 / 0.8 |
| WWS_Compressor.ogg | 36, 54, 63, 72, 81, 90 | 0.1 / -0.1 | 1.5 / 0.5 | 1.6 / 0.6 | 2.5 / 2.0 | 0.8 / 0.0 | 0.1 / -0.1 | 0.8 / 0.0 | 0.8 / 0.0 | 0.8 / 0.0 | 0.8 / 0.0 | 0.8 / 0.0 |
| MainsBrum50Hz.ogg (electrical) | 50, 100, 150, 200, 250, 350 | 23.4 / 22.5 | 9.4 / 7.0 | 9.3 / 9.3 | 24.1 / 24.0 | 24.0 / 23.9 | 23.4 / 22.5 | 24.0 / 23.9 | 24.0 / 23.9 | 24.0 / 23.9 | 24.0 / 23.9 | 24.0 / 23.9 |
| Mains_hum_60_Hz.ogg (electrical) | 60, 119, 180, 240, 300, 315 | 36.2 / 36.0 | 42.8 / 42.3 | 6.8 / 6.8 | 36.0 / 35.5 | 36.2 / 36.1 | 36.2 / 36.0 | 36.2 / 36.1 | 36.2 / 36.1 | 36.2 / 36.1 | 36.2 / 36.1 | 36.2 / 36.1 |

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
| v2_fade8, no gate | 5.71 / 6.74 | 7.86 / 11.72 | 4.45 / 4.42 |
| v2_fade8 + gate | 5.71 / 6.73 | 7.83 / 11.68 | 4.44 / 4.41 |
| joint_fade8, no gate | 5.84 / 5.99 | 7.65 / 11.85 | 4.95 / 5.33 |
| joint_fade8 + gate | 5.84 / 6.00 | 7.69 / 11.88 | 4.94 / 5.33 |
| joint_fade8in3out, no gate | 5.84 / 5.99 | 7.65 / 11.85 | 4.95 / 5.33 |
| joint_fade8in3out + gate | 5.83 / 5.99 | 7.74 / 11.91 | 4.94 / 5.33 |
| gcheck, no gate | 5.89 / 6.16 | 7.65 / 11.85 | 4.95 / 5.42 |
| gcheck + gate | 5.89 / 6.16 | 7.79 / 11.94 | 4.95 / 5.41 |
| gcheck_fade8, no gate | 5.75 / 6.02 | 7.65 / 11.85 | 4.93 / 5.34 |
| gcheck_fade8 + gate | 5.75 / 6.03 | 7.69 / 11.88 | 4.93 / 5.35 |
| gcheck_fade8in3out, no gate | 5.88 / 6.07 | 7.65 / 11.85 | 4.91 / 5.28 |
| gcheck_fade8in3out + gate | 5.87 / 6.06 | 7.74 / 11.91 | 4.90 / 5.28 |

## Compute time

Offline Python, one thread per process, measured under the parallel pool. "Own" excludes the tone-selector update that v2 also runs and, for a faded method, includes the fade. One block is 10 ms of audio. The rule compares each candidate with joint + gate run by run, so a busy machine slows both.

| Method | Own ms per block, mean | Own p99, median over runs | Own p99, worst run | Own worst block | ms per block incl. selector, mean |
|---|---:|---:|---:|---:|---:|
| bank_wide_lines | 0.83 | 3.39 | 5.41 | 28.0 | 1.18 |
| joint | 1.99 | 5.67 | 8.04 | 37.7 | 2.34 |
| joint_fade8 | 2.03 | 5.72 | 8.27 | 23.2 | 2.34 |
| joint_fade8in3out | 2.04 | 5.74 | 8.22 | 29.6 | 2.35 |
| gcheck | 2.14 | 5.92 | 8.48 | 47.1 | 2.50 |
| gcheck_fade8 | 2.27 | 5.87 | 8.42 | 47.3 | 2.58 |
| gcheck_fade8in3out | 2.27 | 5.94 | 8.57 | 38.3 | 2.59 |

The fade alone, as an engine would run it (one BlockFade per horizon group, one step per block):

| Method | Fade p99 ms per block, median over runs | Fade worst block (ms) |
|---|---:|---:|
| v2_fade8 | 0.071 | 1.521 |
| joint_fade8 | 0.072 | 1.263 |
| joint_fade8in3out | 0.068 | 1.270 |
| gcheck_fade8 | 0.069 | 1.301 |
| gcheck_fade8in3out | 0.068 | 1.394 |

Runtime: 6.6 minutes.
