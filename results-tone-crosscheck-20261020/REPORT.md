# Per-tone fade across the earlier source cohort

**Post-hoc diagnostic, not a new held-out test.** All six files were already scored in study 04. The study-05 candidate and settings were unchanged; no parameter search or new model selection occurred. Both frozen primary studies retain their original results.

All figures describe reference-microphone waveform prediction, not ear-level sound reduction.

| Method | Tone gain, 20 / 120 ms (dB) | Whole-band gain, 20 / 120 ms (dB) | Band boosts | Whole-band boosts |
|---|---:|---:|---:|---:|
| v2 | 6.46 / 5.30 | 1.20 / 1.04 | 5 | 0 |
| Joint check | 3.26 / 2.61 | 0.66 / 0.59 | 5 | 0 |
| 100 ms per-tone fade | 3.39 / 2.84 | 0.81 / 0.63 | 5 | 0 |

Boost counts use 12 recording-by-horizon cases: two horizons for each of six files. The band threshold is at least 1 dB amplification in any third-octave band; the whole-band threshold is greater than 0.5 dB amplification.

## Paired source results

- Against v2, tone gain at 20 ms: 2 wins, 4 losses, 0 ties. Descriptive sign-test p=0.688.
- Against Joint check, tone gain at 20 ms: 3 wins, 3 losses, 0 ties. Descriptive sign-test p=1.000.

| File | v2 tone gain | Joint tone gain | Per-tone fade tone gain |
|---|---:|---:|---:|
| Het_vermalen_van_fruit_in_een_blender_-_SoundCloud_-_marloeskunst.ogg | 0.03 | 0.05 | 0.04 |
| Laser_printer,_2015-01-23.ogg | 0.39 | 0.53 | 0.53 |
| Photocopie.ogg | 7.33 | 6.82 | 6.75 |
| Mobile_lift_stage.ogg | 9.75 | 4.90 | 4.65 |
| Mil_Mi-8MTV-1_helicopter_starting_up.ogg | 5.59 | 1.61 | 2.14 |
| Wiki_Motor_lancha.wav | 20.03 | 8.61 | 11.19 |

## Integrity and limits

- All 30 comparator checks match the original study-04 score rows within numerical tolerance.
- The diagnostic was planned after seeing both primary outcomes. Its findings cannot be counted as independent confirmation or used to tune a method and then call this cohort fresh.
- Source code, both protocols, input hashes and candidate settings matched the frozen records.
- CPU timing from this parallel run does not qualify the live system.
- The live engine remains v2 pending stronger source-general evidence, timing and physical-path validation.

[Plan](C:/Users/talk2.000/Desktop/Claude/predictive-anc/results-tone-crosscheck-20261020/plan.json) · [Full diagnostic](C:/Users/talk2.000/Desktop/Claude/predictive-anc/results-tone-crosscheck-20261020/diagnostic.json)
