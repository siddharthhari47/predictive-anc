# Study 04: frozen offline result

**Frozen criteria: not all passed.** Candidate: `gcheck_fade8_gated`. Reference-microphone prediction only; no playback or ear-level measurement.

6 fresh recordings; 60 fresh synthetic scenes; 6 acoustic recordings with reference tones. Missing files: ['Paisaje_sonoro_-_Aves_y_motor_de_auto.wav', 'Cogwheel_loco_Rigi_vsb.ogg']. The unchanged frozen test ran once in 15.00 minutes.

## Frozen questions

- fewer synthetic late boosts and no more recording boosts: **yes**.
- tone gain above v2: **no**.

## Fresh-recording evidence

| Method | Tone bins, 20 / 120 ms (dB) | Whole band, 20 / 120 ms (dB) | Band boosts | Whole-band boosts |
|---|---:|---:|---:|---:|
| Predict nothing | 0.00 / 0.00 | 0.00 / 0.00 | 0 | 0 |
| v2 (current engine) | 6.46 / 5.30 | 1.20 / 1.04 | 5 | 0 |
| Joint check | 3.26 / 2.61 | 0.66 / 0.59 | 5 | 0 |
| Frozen fade candidate | 3.25 / 2.77 | 0.72 / 0.60 | 5 | 0 |
| Prefix-adapted AR | 3.60 / 0.83 | 0.15 / -0.01 | 9 | 4 |
| Online AR | 5.10 / 3.55 | 1.19 / 0.64 | 8 | 2 |

Band boosts count recording-by-horizon cases with at least one third-octave band amplified by 1 dB or more; whole-band boosts use a greater-than-0.5 dB amplification threshold. Each file contributes two cases (20 and 120 ms). Positive prediction gain means reduced reference-waveform error; it is not measured sound reduction at an ear.

## Fresh synthetic evidence

| Method | All late band boosts | Sudden-change late band boosts |
|---|---:|---:|
| Predict nothing | 0 | 0 |
| v2 (current engine) | 53 | 10 |
| Joint check | 27 | 13 |
| Frozen fade candidate | 14 | 11 |
| Prefix-adapted AR | 82 | 12 |
| Online AR | 78 | 12 |

## Uncertainty and integrity

- Against Joint check, at 20 ms on paired tonal files: 1 wins, 2 losses, 3 ties; exact two-sided sign-test p=1.000.
- Against v2 (current engine), at 20 ms on paired tonal files: 2 wins, 4 losses, 0 ties; exact two-sided sign-test p=0.688.
- These are small, purposively selected samples. Reference tones are located with hindsight for scoring; that does not feed future data to the causal predictors, but it can flatter tone-focused metrics.
- This review recounts boosts and recomputes medians from saved scores; it does not rerun the predictors, retune a candidate or replace any held-out recording.
- Timing during a multiprocessing offline run is not a quiet-machine real-time qualification. The live engine remains v2.

[Full frozen report](C:/Users/talk2.000/Desktop/Claude/predictive-anc/results-tone-forecaster-04/REPORT.md) · [Audit](C:/Users/talk2.000/Documents/Codex/2026-10-15/referenced-chatgpt-conversation-this-is-an/outputs/anc-studies-20261020/study-04-review.json)
