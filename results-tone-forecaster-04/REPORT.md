# Tone forecaster study 04: test on fresh material

**Reference-signal prediction only.** Every number is how well a forecaster predicts the recording microphone's own signal 20 ms or 120 ms ahead. Nothing was played, no acoustic path was modelled, and no attenuation at an ear was measured. No real-world cancellation is claimed.

"+ gate" always means the output after the v2 gate as that method uses it: switched (v2, joint, bank_wide_lines, gcheck) or faded (the names with fade8 or fade8in3out). The gate decides the same way in every case. gcheck is the band check that judges each setting after its own copy of the gate.

**Independence.** No selected audio was downloaded, played, decoded or scored in this project before the freeze. Titles and SHA-1s are disjoint from local external audio, local microphone recordings and study 05's reserved recordings. Credited authors are disjoint from earlier source credits, study 02 and study 05, and unique within this list. These are provenance checks based on cached metadata, not proof of independent capture events or representative real-world performance. The shared metadata search with study 05 is disclosed; no audio or outcome is shared. Files with no reference tones remain in the boost and whole-band scores, as required by the existing scoring code.

## Answer

1. **Are the gate's boosts gone, with none added? Yes.** Over the late windows of the 60 fresh synthetic scenes gcheck_fade8 + gate has 14 third-octave boosts (a band 1 dB or more louder) against 27 for joint + gate and 16 for the joint check with no gate; on the buzz scenes alone 1, 7 and 2. On the fresh recordings it has 5 against 5 for joint + gate and 5 for v2 + gate; near-boosts (0.5 dB or more) 6, 6 and 6; whole-band boosts 0, 0 and 0.
2. **Is the tone gain kept? No.** Median tone-bin gain at 20 ms over the 6 fresh acoustic recordings with reference tones: 3.3 dB for gcheck_fade8 + gate, 6.5 dB for v2 + gate and 3.3 dB for joint + gate.

Per file at 20 ms the candidate beats v2 + gate at the tones on 2 of 6 files and loses on 4 (exact sign test p = 0.688); against joint + gate the differences run from -0.00 to 0.00 dB. With this few files the median is coarse; the per-file tables are the evidence.

Whole band (35-350 Hz), the score that does not depend on how the reference tones were picked: median 0.72 dB for the candidate, 0.66 dB for joint + gate and 1.20 dB for v2 + gate at 20 ms; the candidate is ahead of v2 + gate on 2 of 6 files.

**Caveat on the tone-bin score.** The reference tones are the scored segment's lines standing 10 dB above their +-10 Hz median, chosen with hindsight. The line finder uses a similar prominence rule causally, so tone-bin gains flatter it. The whole-band score has no such bias.

## What was frozen before this run

- Development run: `results-tone-forecaster-04/development/dev-01` (its DEVELOPMENT.md). Rule:

  > Written after the diagnostic trials on development material (results-tone-forecaster-04/diagnosis) and before the formal development run. Candidates, all driven by the v2 gate's decision: the joint band check of study 02 with the gate faded instead of switched (a cosine fade over 8 blocks in and 8 out, joint_fade8; 8 in and 3 out, joint_fade8in3out; one block is 10 ms), and the band check that judges each setting after its own copy of the gate (tone_gate_fade.GatedCheckBank) with the hard gate (gcheck), the 8/8 fade (gcheck_fade8) and the 8/3 fade (gcheck_fade8in3out). Development material: the eight study-01 development recordings, the 44 development synthetic scenes and study 03's 8 buzz scenes. A boost is a third-octave band 1 dB or more louder; a near-boost 0.5 dB or more; both are counted over development recordings (either horizon) plus late synthetic windows. Eligible only if: (a) fewer boosts than joint + gate; (b) the gate's boosts are gone: on the buzz scenes, no more late boosts than the joint check with no gate at all; (c) no more near-boosts than joint + gate; (d) no more whole-band boosts (whole 35-350 Hz band below -0.5 dB on a development recording) than joint + gate; (e) the tone gain over v2 is kept: the median, over development acoustic recordings with reference tones, of the tone-bin gain averaged over both horizons is at least v2 + gate's plus half of the amount by which joint + gate exceeds v2 + gate; (f) the median whole-band gain over development acoustic recordings, averaged over both horizons, is at least joint + gate's minus 0.1 dB; (g) the mean synthetic objective is at least joint + gate's minus 0.5 dB and its synthetic windows below -0.5 dB are no more than joint + gate has; (h) the compute it adds is small: over all development runs, the median of its own 99th-percentile time per 10 ms block (fade included) minus joint + gate's in the same run is at most 1 ms. Among eligible candidates, pick the one with the fewest boosts, then the fewest near-boosts, then the higher tone-bin median. If none is eligible, nothing is frozen: the joint check and v2 are unchanged, and there is nothing to test on fresh recordings.

- Frozen candidate: **gcheck_fade8** ({"nb_tau": 0.0, "lines": true, "options": {}, "kind": "gated_check", "fade": {"in_blocks": 8, "out_blocks": 8, "shape": "cosine"}})
- Comparators: predict nothing; v2 with and without its gate (today's engine); ridge AR adapted on each file's first 40% (prefix AR) and refitted every second on past samples (online AR); the study-01 line-finder bank (bank_wide_lines); the study-02 joint check (joint); and v2 with the 8-block fade (v2_fade8).
- Primary question: Only if a candidate is frozen. On material no study-04 choice used: (1) are the gate's boosts gone, with none added: does the frozen candidate have fewer third-octave boosts (a band 1 dB or more louder) than joint + gate over the late windows of the fresh synthetic scenes, and no more than joint + gate over the fresh recordings (either horizon)? (2) Is the tone gain kept: is its median tone-bin gain at 20 ms, over the fresh acoustic recordings with reference tones, above v2 + gate's? The two parts are answered separately. The other candidates, v2 with the fade, the study-02 fresh recordings and the study-01 test recordings are reported for information and answer nothing.
- Fresh recordings scored (6): Het_vermalen_van_fruit_in_een_blender_-_SoundCloud_-_marloeskunst.ogg, Laser_printer,_2015-01-23.ogg, Photocopie.ogg, Mobile_lift_stage.ogg, Mil_Mi-8MTV-1_helicopter_starting_up.ogg, Wiki_Motor_lancha.wav. Missing, not replaced: Paisaje_sonoro_-_Aves_y_motor_de_auto.wav, Cogwheel_loco_Rigi_vsb.ogg.

## Fresh synthetic scenes

60 scenes in three families (standard, drifting, buzz) from seeds 20261040, 20261041 and 20261042, odd 10 Hz bands, more than 2 Hz from every development frequency. Every frequency a study-04 development scene used is excluded (the study-02 development list and study 03's buzz draws). The study-01, release-study and study-02 synthetic test draws are not excluded: no study-04 choice used them, and excluding the study-02 test draws as well within 2 Hz leaves no room for the standard and drifting scenes in odd bands (checked with a draw before this freeze; study 02 met the same limit with study 01's draws).

| Method | Objective (dB) | Windows < -0.5 dB | Late whole band, mean / min (dB) | Late tone bins, median (dB) | Late boosts (>= 1 / >= 0.5 dB) |
|---|---:|---:|---:|---:|---:|
| Predict nothing | — | — | 0.00 / 0.00 | 0.0 | 0 / 0 |
| v2, no gate | 6.88 | 7 | 9.24 / -0.54 | 12.9 | 49 / 72 |
| v2 + gate | 6.88 | 7 | 9.22 / -0.52 | 11.7 | 53 / 76 |
| AR adapted on prefix | — | — | 8.74 / -10.24 | 18.7 | 82 / 115 |
| AR refitted online | 5.60 | 7 | 9.83 / -0.51 | 18.4 | 78 / 95 |
| bank_wide_lines, no gate | 7.50 | 6 | 10.15 / 0.00 | 18.2 | 58 / 72 |
| bank_wide_lines + gate | 7.55 | 6 | 10.18 / 0.00 | 18.2 | 59 / 70 |
| joint, no gate | 6.68 | 6 | 9.07 / 0.00 | 9.1 | 16 / 38 |
| joint + gate | 6.74 | 6 | 9.12 / 0.00 | 9.1 | 27 / 43 |
| v2_fade8, no gate | 6.88 | 7 | 9.24 / -0.54 | 12.9 | 49 / 72 |
| v2_fade8 + gate | 6.86 | 7 | 9.22 / -0.52 | 11.7 | 49 / 72 |
| joint_fade8, no gate | 6.68 | 6 | 9.07 / 0.00 | 9.1 | 16 / 38 |
| joint_fade8 + gate | 6.69 | 6 | 9.08 / 0.00 | 9.1 | 15 / 38 |
| joint_fade8in3out, no gate | 6.68 | 6 | 9.07 / 0.00 | 9.1 | 16 / 38 |
| joint_fade8in3out + gate | 6.71 | 6 | 9.10 / 0.00 | 9.1 | 16 / 38 |
| gcheck, no gate | 6.76 | 6 | 9.19 / -0.13 | 9.7 | 17 / 41 |
| gcheck + gate | 6.83 | 6 | 9.24 / -0.10 | 9.7 | 24 / 44 |
| gcheck_fade8, no gate | 6.69 | 6 | 9.09 / 0.00 | 9.1 | 17 / 37 |
| gcheck_fade8 + gate | 6.70 | 6 | 9.10 / 0.00 | 9.1 | 14 / 36 |
| gcheck_fade8in3out, no gate | 6.71 | 6 | 9.11 / 0.00 | 9.4 | 17 / 40 |
| gcheck_fade8in3out + gate | 6.74 | 6 | 9.13 / 0.00 | 9.4 | 17 / 37 |

Late boosts by family (>= 1 dB / >= 0.5 dB):

| Method | buzz | standard | wander |
|---|---:|---:|---:|
| v2, no gate | 23 / 23 | 15 / 30 | 11 / 19 |
| v2 + gate | 23 / 23 | 19 / 32 | 11 / 21 |
| bank_wide_lines, no gate | 24 / 24 | 17 / 25 | 17 / 23 |
| bank_wide_lines + gate | 24 / 24 | 18 / 23 | 17 / 23 |
| joint, no gate | 2 / 9 | 12 / 17 | 2 / 12 |
| joint + gate | 7 / 13 | 13 / 16 | 7 / 14 |
| v2_fade8, no gate | 23 / 23 | 15 / 30 | 11 / 19 |
| v2_fade8 + gate | 23 / 23 | 15 / 30 | 11 / 19 |
| joint_fade8, no gate | 2 / 9 | 12 / 17 | 2 / 12 |
| joint_fade8 + gate | 2 / 10 | 11 / 17 | 2 / 11 |
| joint_fade8in3out, no gate | 2 / 9 | 12 / 17 | 2 / 12 |
| joint_fade8in3out + gate | 3 / 10 | 11 / 14 | 2 / 14 |
| gcheck, no gate | 3 / 12 | 12 / 17 | 2 / 12 |
| gcheck + gate | 5 / 14 | 13 / 16 | 6 / 14 |
| gcheck_fade8, no gate | 3 / 9 | 12 / 17 | 2 / 11 |
| gcheck_fade8 + gate | 1 / 9 | 11 / 17 | 2 / 10 |
| gcheck_fade8in3out, no gate | 2 / 10 | 12 / 17 | 3 / 13 |
| gcheck_fade8in3out + gate | 3 / 10 | 11 / 14 | 3 / 13 |

By family (mean objective dB / late whole band dB):

| Method | buzz | standard | wander |
|---|---:|---:|---:|
| Predict nothing | — / 0.00 | — / 0.00 | — / 0.00 |
| v2, no gate | 6.02 / 5.99 | 7.89 / 11.86 | 4.70 / 4.63 |
| v2 + gate | 6.01 / 5.97 | 7.91 / 11.86 | 4.65 / 4.56 |
| AR adapted on prefix | — / 9.44 | — / 9.07 | — / 7.05 |
| AR refitted online | 7.67 / 9.53 | 4.83 / 10.81 | 5.84 / 7.18 |
| bank_wide_lines, no gate | 7.63 / 7.65 | 8.02 / 12.31 | 5.83 / 6.18 |
| bank_wide_lines + gate | 7.62 / 7.65 | 8.09 / 12.36 | 5.83 / 6.18 |
| joint, no gate | 5.63 / 5.35 | 7.54 / 11.64 | 5.13 / 5.11 |
| joint + gate | 5.63 / 5.34 | 7.65 / 11.71 | 5.14 / 5.11 |
| v2_fade8, no gate | 6.02 / 5.99 | 7.89 / 11.86 | 4.70 / 4.63 |
| v2_fade8 + gate | 6.02 / 5.98 | 7.86 / 11.84 | 4.69 / 4.59 |
| joint_fade8, no gate | 5.63 / 5.35 | 7.54 / 11.64 | 5.13 / 5.11 |
| joint_fade8 + gate | 5.63 / 5.34 | 7.56 / 11.65 | 5.13 / 5.11 |
| joint_fade8in3out, no gate | 5.63 / 5.35 | 7.54 / 11.64 | 5.13 / 5.11 |
| joint_fade8in3out + gate | 5.63 / 5.33 | 7.60 / 11.68 | 5.13 / 5.10 |
| gcheck, no gate | 6.01 / 5.89 | 7.54 / 11.64 | 5.16 / 5.17 |
| gcheck + gate | 6.02 / 5.90 | 7.65 / 11.71 | 5.18 / 5.18 |
| gcheck_fade8, no gate | 5.68 / 5.45 | 7.54 / 11.64 | 5.15 / 5.12 |
| gcheck_fade8 + gate | 5.68 / 5.44 | 7.56 / 11.65 | 5.14 / 5.11 |
| gcheck_fade8in3out, no gate | 5.75 / 5.50 | 7.54 / 11.64 | 5.18 / 5.13 |
| gcheck_fade8in3out + gate | 5.75 / 5.49 | 7.60 / 11.68 | 5.17 / 5.12 |

## Fresh recordings

| Method | Tone bins median, 20 / 120 ms | Whole band median, 20 / 120 ms | Whole-band boosts | Third-octave boosts (>= 1 dB) | Near-boosts (>= 0.5 dB) | Synthetic objective | Synthetic windows < -0.5 dB | Synthetic late boosts (>= 1 / >= 0.5 dB) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Predict nothing | 0.0 / 0.0 | 0.00 / 0.00 | 0 | 0 | 0 | — | — | — |
| v2, no gate | 6.5 / 5.3 | 1.21 / 1.05 | 0 | 5 | 6 | — | — | — |
| v2 + gate | 6.5 / 5.3 | 1.20 / 1.04 | 0 | 5 | 6 | — | — | — |
| AR adapted on prefix | 3.6 / 0.8 | 0.15 / -0.01 | 4 | 9 | 11 | — | — | — |
| AR refitted online | 5.1 / 3.5 | 1.19 / 0.64 | 2 | 8 | 9 | — | — | — |
| bank_wide_lines, no gate | 6.2 / 5.3 | 1.25 / 1.10 | 0 | 6 | 6 | — | — | — |
| bank_wide_lines + gate | 6.2 / 5.3 | 1.24 / 1.10 | 0 | 6 | 6 | — | — | — |
| joint, no gate | 3.1 / 2.5 | 0.66 / 0.60 | 0 | 5 | 6 | — | — | — |
| joint + gate | 3.3 / 2.6 | 0.66 / 0.59 | 0 | 5 | 6 | — | — | — |
| v2_fade8, no gate | 6.5 / 5.3 | 1.21 / 1.05 | 0 | 5 | 6 | — | — | — |
| v2_fade8 + gate | 6.5 / 5.3 | 1.20 / 1.05 | 0 | 5 | 6 | — | — | — |
| joint_fade8, no gate | 3.1 / 2.5 | 0.66 / 0.60 | 0 | 5 | 6 | — | — | — |
| joint_fade8 + gate | 3.2 / 2.6 | 0.66 / 0.60 | 0 | 5 | 6 | — | — | — |
| joint_fade8in3out, no gate | 3.1 / 2.5 | 0.66 / 0.60 | 0 | 5 | 6 | — | — | — |
| joint_fade8in3out + gate | 3.3 / 2.6 | 0.66 / 0.59 | 0 | 5 | 6 | — | — | — |
| gcheck, no gate | 3.3 / 2.6 | 0.66 / 0.60 | 0 | 5 | 5 | — | — | — |
| gcheck + gate | 3.4 / 2.7 | 0.66 / 0.59 | 0 | 5 | 6 | — | — | — |
| gcheck_fade8, no gate | 3.2 / 2.7 | 0.72 / 0.60 | 0 | 5 | 6 | — | — | — |
| gcheck_fade8 + gate | 3.3 / 2.8 | 0.72 / 0.60 | 0 | 5 | 6 | — | — | — |
| gcheck_fade8in3out, no gate | 3.2 / 2.6 | 0.73 / 0.60 | 0 | 5 | 6 | — | — | — |
| gcheck_fade8in3out + gate | 3.3 / 2.7 | 0.73 / 0.59 | 0 | 5 | 6 | — | — | — |

### Boosts

- v2 + gate: third-octave +1.7 dB on Mobile_lift_stage.ogg at 20 ms; third-octave +6.4 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 20 ms; third-octave +9.0 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 120 ms; third-octave +6.2 dB on Wiki_Motor_lancha.wav at 20 ms; third-octave +5.2 dB on Wiki_Motor_lancha.wav at 120 ms; near (0.5-1 dB): Mobile_lift_stage.ogg 120 ms +0.95
- AR adapted on prefix: whole band -1.17 dB on Het_vermalen_van_fruit_in_een_blender_-_SoundCloud_-_marloeskunst.ogg at 20 ms; whole band -0.92 dB on Het_vermalen_van_fruit_in_een_blender_-_SoundCloud_-_marloeskunst.ogg at 120 ms; whole band -0.69 dB on Mobile_lift_stage.ogg at 120 ms; whole band -1.24 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 20 ms; third-octave +7.8 dB on Het_vermalen_van_fruit_in_een_blender_-_SoundCloud_-_marloeskunst.ogg at 20 ms; third-octave +2.2 dB on Het_vermalen_van_fruit_in_een_blender_-_SoundCloud_-_marloeskunst.ogg at 120 ms; third-octave +1.3 dB on Laser_printer,_2015-01-23.ogg at 20 ms; third-octave +4.9 dB on Mobile_lift_stage.ogg at 20 ms; third-octave +5.9 dB on Mobile_lift_stage.ogg at 120 ms; third-octave +11.7 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 20 ms; third-octave +7.4 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 120 ms; third-octave +17.6 dB on Wiki_Motor_lancha.wav at 20 ms; third-octave +16.0 dB on Wiki_Motor_lancha.wav at 120 ms; near (0.5-1 dB): Photocopie.ogg 20 ms +0.98, Photocopie.ogg 120 ms +0.73
- AR refitted online: whole band -0.87 dB on Het_vermalen_van_fruit_in_een_blender_-_SoundCloud_-_marloeskunst.ogg at 20 ms; whole band -0.65 dB on Het_vermalen_van_fruit_in_een_blender_-_SoundCloud_-_marloeskunst.ogg at 120 ms; third-octave +5.0 dB on Het_vermalen_van_fruit_in_een_blender_-_SoundCloud_-_marloeskunst.ogg at 20 ms; third-octave +1.8 dB on Het_vermalen_van_fruit_in_een_blender_-_SoundCloud_-_marloeskunst.ogg at 120 ms; third-octave +4.3 dB on Mobile_lift_stage.ogg at 20 ms; third-octave +4.2 dB on Mobile_lift_stage.ogg at 120 ms; third-octave +10.5 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 20 ms; third-octave +4.9 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 120 ms; third-octave +12.3 dB on Wiki_Motor_lancha.wav at 20 ms; third-octave +14.9 dB on Wiki_Motor_lancha.wav at 120 ms; near (0.5-1 dB): Laser_printer,_2015-01-2 20 ms +0.96
- bank_wide_lines + gate: third-octave +4.9 dB on Mobile_lift_stage.ogg at 20 ms; third-octave +4.5 dB on Mobile_lift_stage.ogg at 120 ms; third-octave +6.9 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 20 ms; third-octave +8.4 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 120 ms; third-octave +6.1 dB on Wiki_Motor_lancha.wav at 20 ms; third-octave +6.6 dB on Wiki_Motor_lancha.wav at 120 ms
- joint + gate: third-octave +1.7 dB on Mobile_lift_stage.ogg at 20 ms; third-octave +3.3 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 20 ms; third-octave +6.1 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 120 ms; third-octave +6.2 dB on Wiki_Motor_lancha.wav at 20 ms; third-octave +5.3 dB on Wiki_Motor_lancha.wav at 120 ms; near (0.5-1 dB): Mobile_lift_stage.ogg 120 ms +0.75
- v2_fade8 + gate: third-octave +1.6 dB on Mobile_lift_stage.ogg at 20 ms; third-octave +5.6 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 20 ms; third-octave +8.6 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 120 ms; third-octave +6.2 dB on Wiki_Motor_lancha.wav at 20 ms; third-octave +5.2 dB on Wiki_Motor_lancha.wav at 120 ms; near (0.5-1 dB): Mobile_lift_stage.ogg 120 ms +0.79
- joint_fade8 + gate: third-octave +1.5 dB on Mobile_lift_stage.ogg at 20 ms; third-octave +3.0 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 20 ms; third-octave +6.0 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 120 ms; third-octave +6.2 dB on Wiki_Motor_lancha.wav at 20 ms; third-octave +5.3 dB on Wiki_Motor_lancha.wav at 120 ms; near (0.5-1 dB): Mobile_lift_stage.ogg 120 ms +0.59
- joint_fade8in3out + gate: third-octave +1.5 dB on Mobile_lift_stage.ogg at 20 ms; third-octave +3.2 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 20 ms; third-octave +6.0 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 120 ms; third-octave +6.2 dB on Wiki_Motor_lancha.wav at 20 ms; third-octave +5.3 dB on Wiki_Motor_lancha.wav at 120 ms; near (0.5-1 dB): Mobile_lift_stage.ogg 120 ms +0.56
- gcheck + gate: third-octave +1.7 dB on Mobile_lift_stage.ogg at 20 ms; third-octave +3.3 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 20 ms; third-octave +6.1 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 120 ms; third-octave +6.2 dB on Wiki_Motor_lancha.wav at 20 ms; third-octave +5.3 dB on Wiki_Motor_lancha.wav at 120 ms; near (0.5-1 dB): Mobile_lift_stage.ogg 120 ms +0.68
- gcheck_fade8 + gate: third-octave +1.5 dB on Mobile_lift_stage.ogg at 20 ms; third-octave +3.0 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 20 ms; third-octave +6.0 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 120 ms; third-octave +6.2 dB on Wiki_Motor_lancha.wav at 20 ms; third-octave +5.3 dB on Wiki_Motor_lancha.wav at 120 ms; near (0.5-1 dB): Mobile_lift_stage.ogg 120 ms +0.56
- gcheck_fade8in3out + gate: third-octave +1.5 dB on Mobile_lift_stage.ogg at 20 ms; third-octave +3.3 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 20 ms; third-octave +6.0 dB on Mil_Mi-8MTV-1_helicopter_starting_up.ogg at 120 ms; third-octave +6.3 dB on Wiki_Motor_lancha.wav at 20 ms; third-octave +5.3 dB on Wiki_Motor_lancha.wav at 120 ms; near (0.5-1 dB): Mobile_lift_stage.ogg 120 ms +0.50

### Per recording: tone bins (dB, 20 / 120 ms)

| Recording | Tones (Hz) | v2 + gate | AR adapted on prefix | AR refitted online | bank_wide_lines + gate | joint + gate | v2_fade8 + gate | joint_fade8 + gate | joint_fade8in3out + gate | gcheck + gate | gcheck_fade8 + gate | gcheck_fade8in3out + gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Het_vermalen_van_fruit_in_een_blender_-_ | 238, 282, 287 | 0.0 / -0.0 | -2.8 / -2.5 | -2.8 / -1.7 | 0.7 / 0.5 | 0.0 / 0.0 | 0.0 / -0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| Laser_printer,_2015-01-23.ogg | 105, 158, 292 | 0.4 / 0.4 | 3.5 / 1.9 | 4.6 / 2.5 | 1.4 / 1.0 | 0.5 / 0.5 | 0.4 / 0.4 | 0.5 / 0.5 | 0.5 / 0.5 | 0.5 / 0.5 | 0.5 / 0.5 | 0.5 / 0.5 |
| Photocopie.ogg | 83, 99, 141, 182, 212, 332 | 7.3 / 5.6 | 3.7 / 4.0 | 5.6 / 5.2 | 7.0 / 5.9 | 6.8 / 5.8 | 7.3 / 5.5 | 6.8 / 5.8 | 6.8 / 5.8 | 6.8 / 5.8 | 6.8 / 5.8 | 6.8 / 5.8 |
| Mobile_lift_stage.ogg | 38, 75, 113, 150, 188, 201 | 9.8 / 8.2 | 6.5 / 0.6 | 10.6 / 4.6 | 10.2 / 8.7 | 4.9 / 2.7 | 9.8 / 8.2 | 4.9 / 2.7 | 4.9 / 2.7 | 5.2 / 2.9 | 4.9 / 3.0 | 4.8 / 3.0 |
| Mil_Mi-8MTV-1_helicopter_starting_up.ogg | 56, 111, 207, 223, 239, 301 | 5.6 / 5.0 | -1.8 / 0.8 | 3.8 / 1.6 | 5.5 / 4.7 | 1.6 / 2.5 | 5.6 / 5.0 | 1.6 / 2.5 | 1.6 / 2.5 | 1.6 / 2.5 | 1.6 / 2.5 | 1.7 / 2.5 |
| Wiki_Motor_lancha.wav | 123, 157, 172, 236, 256, 342 | 20.0 / 14.6 | 11.7 / 0.8 | 17.8 / 6.9 | 20.3 / 14.9 | 8.6 / 5.5 | 20.0 / 14.6 | 8.6 / 5.5 | 8.6 / 5.5 | 8.6 / 5.5 | 8.6 / 5.5 | 8.4 / 5.4 |

### Per recording: whole band (dB, 20 / 120 ms)

| Recording | Tones (Hz) | v2 + gate | AR adapted on prefix | AR refitted online | bank_wide_lines + gate | joint + gate | v2_fade8 + gate | joint_fade8 + gate | joint_fade8in3out + gate | gcheck + gate | gcheck_fade8 + gate | gcheck_fade8in3out + gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Het_vermalen_van_fruit_in_een_blender_-_ | 238, 282, 287 | 0.0 / -0.0 | -1.2 / -0.9 | -0.9 / -0.7 | 0.2 / 0.0 | 0.0 / -0.0 | 0.0 / -0.0 | 0.0 / -0.0 | 0.0 / -0.0 | 0.0 / -0.0 | 0.0 / -0.0 | 0.0 / -0.0 |
| Laser_printer,_2015-01-23.ogg | 105, 158, 292 | 0.0 / -0.0 | 0.4 / 0.2 | 0.5 / 0.3 | 0.1 / 0.1 | 0.1 / 0.1 | 0.0 / -0.0 | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 |
| Photocopie.ogg | 83, 99, 141, 182, 212, 332 | 0.3 / 0.2 | -0.1 / 0.1 | 0.4 / 0.3 | 0.4 / 0.3 | 0.4 / 0.4 | 0.3 / 0.2 | 0.4 / 0.4 | 0.4 / 0.4 | 0.4 / 0.4 | 0.4 / 0.4 | 0.4 / 0.4 |
| Mobile_lift_stage.ogg | 38, 75, 113, 150, 188, 201 | 7.4 / 6.1 | 4.4 / -0.7 | 7.4 / 2.3 | 7.4 / 5.8 | 3.8 / 2.0 | 7.4 / 6.1 | 3.7 / 1.9 | 3.8 / 2.0 | 3.9 / 2.1 | 3.8 / 2.2 | 3.7 / 2.2 |
| Mil_Mi-8MTV-1_helicopter_starting_up.ogg | 56, 111, 207, 223, 239, 301 | 2.1 / 1.9 | -1.2 / 0.2 | 1.9 / 0.9 | 2.1 / 1.9 | 0.9 / 0.8 | 2.1 / 1.9 | 0.9 / 0.8 | 0.9 / 0.8 | 0.9 / 0.8 | 1.0 / 0.8 | 1.1 / 0.8 |
| Wiki_Motor_lancha.wav | 123, 157, 172, 236, 256, 342 | 14.2 / 11.5 | 9.1 / -0.1 | 13.5 / 5.1 | 14.0 / 11.3 | 7.2 / 5.1 | 14.2 / 11.5 | 7.2 / 5.1 | 7.2 / 5.1 | 8.2 / 5.1 | 7.2 / 5.1 | 6.1 / 5.0 |

A file marked "capture unknown" is kept out of the medians; its boosts still count.

## Secondary: seen recordings (not independent)

Secondary, not independent: the study-01 test recordings and the study-02 fresh recordings (Buzzing_Speakers.ogg among them). Study 02 and 03 read their results; no study-04 choice was made on them.

| Method | Tone bins median, 20 / 120 ms | Whole band median, 20 / 120 ms | Whole-band boosts | Third-octave boosts (>= 1 dB) | Near-boosts (>= 0.5 dB) | Synthetic objective | Synthetic windows < -0.5 dB | Synthetic late boosts (>= 1 / >= 0.5 dB) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Predict nothing | 0.0 / 0.0 | 0.00 / 0.00 | 0 | 0 | 0 | — | — | — |
| v2, no gate | 2.3 / 2.4 | 0.09 / 0.05 | 0 | 7 | 14 | — | — | — |
| v2 + gate | 2.3 / 2.4 | 0.09 / 0.05 | 0 | 7 | 14 | — | — | — |
| AR adapted on prefix | 6.7 / 3.6 | 0.44 / 0.06 | 3 | 30 | 30 | — | — | — |
| AR refitted online | 7.0 / 4.4 | 0.64 / 0.33 | 2 | 25 | 29 | — | — | — |
| bank_wide_lines, no gate | 3.6 / 3.2 | 0.38 / 0.06 | 0 | 10 | 17 | — | — | — |
| bank_wide_lines + gate | 3.6 / 3.2 | 0.38 / 0.06 | 0 | 10 | 17 | — | — | — |
| joint, no gate | 3.0 / 2.5 | 0.20 / 0.15 | 0 | 2 | 4 | — | — | — |
| joint + gate | 3.0 / 2.5 | 0.20 / 0.15 | 0 | 2 | 4 | — | — | — |
| v2_fade8, no gate | 2.3 / 2.4 | 0.09 / 0.05 | 0 | 7 | 14 | — | — | — |
| v2_fade8 + gate | 2.3 / 2.4 | 0.09 / 0.05 | 0 | 7 | 14 | — | — | — |
| joint_fade8, no gate | 3.0 / 2.5 | 0.20 / 0.15 | 0 | 2 | 4 | — | — | — |
| joint_fade8 + gate | 3.0 / 2.5 | 0.20 / 0.15 | 0 | 2 | 4 | — | — | — |
| joint_fade8in3out, no gate | 3.0 / 2.5 | 0.20 / 0.15 | 0 | 2 | 4 | — | — | — |
| joint_fade8in3out + gate | 3.0 / 2.5 | 0.20 / 0.15 | 0 | 2 | 4 | — | — | — |
| gcheck, no gate | 3.0 / 2.5 | 0.20 / 0.15 | 0 | 2 | 3 | — | — | — |
| gcheck + gate | 3.0 / 2.5 | 0.20 / 0.15 | 0 | 2 | 3 | — | — | — |
| gcheck_fade8, no gate | 3.0 / 2.5 | 0.20 / 0.15 | 0 | 2 | 4 | — | — | — |
| gcheck_fade8 + gate | 3.0 / 2.5 | 0.20 / 0.15 | 0 | 2 | 4 | — | — | — |
| gcheck_fade8in3out, no gate | 3.0 / 2.5 | 0.20 / 0.15 | 0 | 2 | 4 | — | — | — |
| gcheck_fade8in3out + gate | 3.0 / 2.5 | 0.20 / 0.15 | 0 | 2 | 4 | — | — | — |

### Boosts

- v2 + gate: third-octave +1.6 dB on Air_conditioner_hum_2_Gravity_Sound_.wav at 20 ms; third-octave +1.9 dB on Air_conditioner_hum_2_Gravity_Sound_.wav at 120 ms; third-octave +1.6 dB on Air_conditioner_hum_Gravity_Sound_.wav at 20 ms; third-octave +1.9 dB on Air_conditioner_hum_Gravity_Sound_.wav at 120 ms; third-octave +8.1 dB on Buzzing_Speakers.ogg at 20 ms; third-octave +11.5 dB on Buzzing_Speakers.ogg at 120 ms; third-octave +1.1 dB on 60-hz.wav at 20 ms; near (0.5-1 dB): Ventilator_in_een_tunnel 120 ms +0.72, Fan_Gravity_Sound_.wav 120 ms +0.93, Sistema_de_ventilaci_n.o 20 ms +0.77, Sistema_de_ventilaci_n.o 120 ms +0.95, Ventilador_de_estudio.og 20 ms +0.83, Ventilador_de_estudio.og 120 ms +0.73, Montreal_Clock_Tower_clo 20 ms +0.67
- bank_wide_lines + gate: third-octave +1.0 dB on Server_Room_Antti_Luode_.mp3 at 20 ms; third-octave +1.7 dB on Omvormer_en_compressor_van_een_tram_-_SoundCloud_-_Beeld_en_Geluid.ogg at 120 ms; third-octave +1.1 dB on Fan_Gravity_Sound_.wav at 20 ms; third-octave +1.6 dB on Fan_Gravity_Sound_.wav at 120 ms; third-octave +1.5 dB on Sistema_de_ventilaci_n.ogg at 20 ms; third-octave +1.5 dB on Sistema_de_ventilaci_n.ogg at 120 ms; third-octave +51.9 dB on The_Sound_of_MOXIE_at_Work_on_Mars_(PIA26041).wav at 20 ms; third-octave +54.4 dB on The_Sound_of_MOXIE_at_Work_on_Mars_(PIA26041).wav at 120 ms; third-octave +8.9 dB on Buzzing_Speakers.ogg at 20 ms; third-octave +9.2 dB on Buzzing_Speakers.ogg at 120 ms; near (0.5-1 dB): Server_Room_Antti_Luode_ 120 ms +0.71, Omvormer_en_compressor_v 20 ms +1.00, Ventilator_in_een_tunnel 20 ms +0.66, Ventilator_in_een_tunnel 120 ms +0.88, Air_conditioner_hum_2_Gr 120 ms +0.58, Montreal_Clock_Tower_clo 20 ms +0.58, 60-hz.wav 20 ms +0.53
- joint + gate: third-octave +7.3 dB on Buzzing_Speakers.ogg at 20 ms; third-octave +5.6 dB on Buzzing_Speakers.ogg at 120 ms; near (0.5-1 dB): Sistema_de_ventilaci_n.o 20 ms +0.53, Sistema_de_ventilaci_n.o 120 ms +0.93
- v2_fade8 + gate: third-octave +1.6 dB on Air_conditioner_hum_2_Gravity_Sound_.wav at 20 ms; third-octave +1.9 dB on Air_conditioner_hum_2_Gravity_Sound_.wav at 120 ms; third-octave +1.6 dB on Air_conditioner_hum_Gravity_Sound_.wav at 20 ms; third-octave +1.9 dB on Air_conditioner_hum_Gravity_Sound_.wav at 120 ms; third-octave +7.0 dB on Buzzing_Speakers.ogg at 20 ms; third-octave +8.7 dB on Buzzing_Speakers.ogg at 120 ms; third-octave +1.1 dB on 60-hz.wav at 20 ms; near (0.5-1 dB): Ventilator_in_een_tunnel 120 ms +0.72, Fan_Gravity_Sound_.wav 120 ms +0.93, Sistema_de_ventilaci_n.o 20 ms +0.77, Sistema_de_ventilaci_n.o 120 ms +0.95, Ventilador_de_estudio.og 20 ms +0.83, Ventilador_de_estudio.og 120 ms +0.73, Montreal_Clock_Tower_clo 20 ms +0.67
- joint_fade8 + gate: third-octave +5.0 dB on Buzzing_Speakers.ogg at 20 ms; third-octave +3.3 dB on Buzzing_Speakers.ogg at 120 ms; near (0.5-1 dB): Sistema_de_ventilaci_n.o 20 ms +0.53, Sistema_de_ventilaci_n.o 120 ms +0.93
- joint_fade8in3out + gate: third-octave +3.9 dB on Buzzing_Speakers.ogg at 20 ms; third-octave +3.1 dB on Buzzing_Speakers.ogg at 120 ms; near (0.5-1 dB): Sistema_de_ventilaci_n.o 20 ms +0.53, Sistema_de_ventilaci_n.o 120 ms +0.93
- gcheck + gate: third-octave +7.3 dB on Buzzing_Speakers.ogg at 20 ms; third-octave +5.5 dB on Buzzing_Speakers.ogg at 120 ms; near (0.5-1 dB): Sistema_de_ventilaci_n.o 120 ms +0.93
- gcheck_fade8 + gate: third-octave +4.9 dB on Buzzing_Speakers.ogg at 20 ms; third-octave +3.2 dB on Buzzing_Speakers.ogg at 120 ms; near (0.5-1 dB): Sistema_de_ventilaci_n.o 20 ms +0.53, Sistema_de_ventilaci_n.o 120 ms +0.93
- gcheck_fade8in3out + gate: third-octave +3.8 dB on Buzzing_Speakers.ogg at 20 ms; third-octave +2.9 dB on Buzzing_Speakers.ogg at 120 ms; near (0.5-1 dB): Sistema_de_ventilaci_n.o 20 ms +0.53, Sistema_de_ventilaci_n.o 120 ms +0.93

### Per recording: tone bins (dB, 20 / 120 ms)

| Recording | Tones (Hz) | v2 + gate | AR adapted on prefix | AR refitted online | bank_wide_lines + gate | joint + gate | v2_fade8 + gate | joint_fade8 + gate | joint_fade8in3out + gate | gcheck + gate | gcheck_fade8 + gate | gcheck_fade8in3out + gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Server_Room_Antti_Luode_.mp3 | 52, 147, 220, 247, 294, 330 | 1.2 / 0.8 | 6.7 / 2.3 | 7.0 / 3.0 | 3.3 / 1.4 | 3.0 / 1.2 | 1.2 / 0.8 | 3.0 / 1.2 | 3.0 / 1.2 | 3.0 / 1.2 | 3.0 / 1.2 | 3.0 / 1.2 |
| Ventilator_in_een_tunnel_-_SoundCloud_-_ | 43, 57, 64, 97, 129, 244 | 0.5 / 0.3 | 3.7 / 1.9 | 5.3 / 3.1 | 3.0 / 1.8 | 2.2 / 0.9 | 0.5 / 0.3 | 2.2 / 0.9 | 2.2 / 0.9 | 2.2 / 0.9 | 2.2 / 0.9 | 2.2 / 0.9 |
| Air_conditioner_hum_2_Gravity_Sound_.wav | 55, 164, 178, 219, 274, 328 | 4.4 / 3.9 | 7.6 / 7.2 | 8.5 / 7.4 | 5.7 / 5.2 | 5.2 / 4.9 | 4.4 / 3.9 | 5.2 / 4.9 | 5.2 / 4.9 | 5.2 / 4.9 | 5.2 / 4.9 | 5.2 / 4.9 |
| Air_conditioner_hum_Gravity_Sound_.wav | 55, 110, 164, 219, 274, 328 | 5.2 / 4.1 | 9.1 / 7.3 | 9.3 / 7.6 | 7.9 / 6.8 | 6.2 / 5.6 | 5.2 / 4.1 | 6.2 / 5.6 | 6.2 / 5.6 | 6.2 / 5.6 | 6.2 / 5.6 | 6.2 / 5.6 |
| Fan_Gravity_Sound_.wav | 42, 120 | 0.5 / 0.5 | 13.1 / 3.8 | 12.7 / 3.7 | 3.6 / 1.3 | 0.6 / 0.6 | 0.5 / 0.5 | 0.6 / 0.6 | 0.6 / 0.6 | 0.6 / 0.6 | 0.6 / 0.6 | 0.6 / 0.6 |
| Sistema_de_ventilaci_n.ogg | 82, 106, 120, 162, 173, 240 | 14.8 / 12.1 | 19.0 / 15.3 | 19.6 / 15.6 | 17.9 / 14.4 | 15.2 / 13.3 | 14.8 / 12.1 | 15.2 / 13.3 | 15.2 / 13.3 | 15.4 / 13.3 | 15.2 / 13.3 | 15.2 / 13.3 |
| Ventilador_de_estudio.ogg | 38, 113, 120, 226 | 2.3 / 2.4 | 2.7 / 3.6 | 3.0 / 4.4 | 3.5 / 3.2 | 2.6 / 2.5 | 2.3 / 2.4 | 2.6 / 2.5 | 2.6 / 2.5 | 2.6 / 2.5 | 2.6 / 2.5 | 2.6 / 2.5 |
| Sounds_made_by_a_fan.wav | 83, 165, 331 | 7.8 / 6.9 | -0.7 / -0.1 | 5.1 / 4.7 | 8.6 / 7.5 | 7.3 / 6.4 | 7.8 / 6.9 | 7.3 / 6.4 | 7.3 / 6.4 | 6.7 / 6.8 | 7.4 / 6.4 | 7.4 / 6.8 |
| Pump.ogg | 70, 105, 120, 240, 268, 326 | 0.8 / 0.6 | 3.0 / 1.8 | 3.7 / 2.4 | 3.2 / 2.7 | 1.2 / 1.1 | 0.8 / 0.6 | 1.2 / 1.1 | 1.2 / 1.1 | 1.2 / 1.1 | 1.2 / 1.1 | 1.2 / 1.1 |
| The_Sound_of_MOXIE_at_Work_on_Mars_(PIA2 | 160 | 0.0 / 0.0 | -48.8 / -46.6 | -45.4 / -43.2 | -38.6 / -38.2 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| Montreal_Clock_Tower_clock_mechanism.fla | 69, 95, 120, 138, 240 | 7.8 / 6.0 | 13.6 / 8.6 | 14.1 / 9.0 | 10.5 / 7.6 | 8.4 / 6.8 | 7.8 / 6.0 | 8.4 / 6.8 | 8.4 / 6.8 | 8.4 / 6.8 | 8.4 / 6.8 | 8.4 / 6.8 |
| Lille_subway_noise.wav | 58, 78, 169 | 0.0 / 0.0 | -1.5 / -1.6 | -1.0 / -0.9 | -0.0 / -0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| Buzzing_Speakers.ogg | 117, 150, 167, 217, 267, 283 | 5.1 / 4.6 | 7.3 / 6.1 | 9.8 / 7.0 | 7.6 / 6.3 | 5.0 / 4.8 | 5.1 / 4.6 | 5.0 / 4.7 | 5.0 / 4.7 | 5.0 / 4.8 | 5.0 / 4.7 | 5.0 / 4.7 |
| 60-hz.wav (not acoustic) | 60, 120, 180, 240, 300 | 41.7 / 37.4 | 48.5 / 40.0 | 49.0 / 40.2 | 40.2 / 37.3 | 37.5 / 37.3 | 41.7 / 37.4 | 37.5 / 37.3 | 37.5 / 37.3 | 37.5 / 37.3 | 37.5 / 37.3 | 37.5 / 37.3 |

## Gate activity

| Method | Part | Switches | Open | Mean gain |
|---|---|---:|---:|---:|
| v2 | recordings | 54 | 0.990 | 0.990 |
| v2 | scenes | 452 | 0.981 | 0.981 |
| bank_wide_lines | recordings | 33 | 0.995 | 0.995 |
| bank_wide_lines | scenes | 88 | 0.995 | 0.995 |
| joint | recordings | 21 | 0.993 | 0.993 |
| joint | scenes | 168 | 0.991 | 0.991 |
| v2_fade8 | recordings | 54 | 0.990 | 0.995 |
| v2_fade8 | scenes | 452 | 0.981 | 0.981 |
| joint_fade8 | recordings | 21 | 0.993 | 0.994 |
| joint_fade8 | scenes | 168 | 0.991 | 0.989 |
| joint_fade8in3out | recordings | 21 | 0.993 | 0.991 |
| joint_fade8in3out | scenes | 168 | 0.991 | 0.987 |
| gcheck | recordings | 21 | 0.993 | 0.993 |
| gcheck | scenes | 135 | 0.992 | 0.992 |
| gcheck_fade8 | recordings | 23 | 0.993 | 0.994 |
| gcheck_fade8 | scenes | 160 | 0.992 | 0.989 |
| gcheck_fade8in3out | recordings | 25 | 0.991 | 0.989 |
| gcheck_fade8in3out | scenes | 155 | 0.992 | 0.987 |

## Compute time

Offline Python, one thread per process, measured under the parallel pool. "Own" excludes the tone-selector update that v2 also runs and includes the fade. One block is 10 ms of audio.

| Method | Own ms per block, mean | Own p99, median over runs | Own p99, worst run | Own worst block | ms per block incl. selector, mean |
|---|---:|---:|---:|---:|---:|
| bank_wide_lines | 0.72 | 3.09 | 6.60 | 49.5 | 1.05 |
| joint | 1.79 | 5.69 | 8.45 | 42.9 | 2.13 |
| joint_fade8 | 1.82 | 5.66 | 7.99 | 53.6 | 2.13 |
| joint_fade8in3out | 1.83 | 6.10 | 8.66 | 47.2 | 2.14 |
| gcheck | 1.89 | 5.89 | 9.61 | 47.6 | 2.23 |
| gcheck_fade8 | 2.02 | 6.39 | 8.24 | 47.2 | 2.33 |
| gcheck_fade8in3out | 2.01 | 6.12 | 8.13 | 50.0 | 2.31 |

## Fresh recordings and credits

| File | Author | Licence | Seconds | Counted as acoustic |
|---|---|---|---:|---|
| Het_vermalen_van_fruit_in_een_blender_-_SoundCloud_-_marloeskunst.ogg | marloeskunst | CC BY 3.0 | 31 | yes |
| Laser_printer,_2015-01-23.ogg | Finn Årup Nielsen | CC BY-SA 3.0 | 81 | yes |
| Photocopie.ogg | Luk | CC BY-SA 3.0 | 18 | yes |
| Mobile_lift_stage.ogg | T.Voekler | CC BY-SA 3.0 | 34 | yes |
| Mil_Mi-8MTV-1_helicopter_starting_up.ogg | H.dav.are | CC BY-SA 4.0 | 19 | yes |
| Wiki_Motor_lancha.wav | Vega16 | CC BY-SA 4.0 | 15 | yes |
| Paisaje_sonoro_-_Aves_y_motor_de_auto.wav | Luis Alvaz | CC BY-SA 4.0 | 52 | yes |
| Cogwheel_loco_Rigi_vsb.ogg | Audrius Meskauskas | Public domain | 22 | yes |

Files are local only, in `external-audio/wikimedia-commons-fresh-04`, from Wikimedia Commons (each file's page is https://commons.wikimedia.org/wiki/ followed by its title).

Runtime: 15.0 minutes. Created 2026-10-19T19:08:31.484843+00:00. Numbers: `test/test.json`. Frozen protocol: `protocol.json`.
