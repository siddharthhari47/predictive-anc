# Study 05: frozen offline result

**Frozen criteria: passed.** Candidate: `fade0.1_linear_gated`. Reference-microphone prediction only; no playback or ear-level measurement.

7 fresh recordings; 84 fresh synthetic scenes; 6 acoustic recordings with reference tones. Missing files: ['Noise-Pollution-Filters-Bird-Communities-Based-on-Vocal-Frequency-pone.0027052.s001.ogg']. The unchanged frozen test ran once in 2.49 minutes.

## Frozen questions

- fewer change boosts: **yes**.
- no more recording boosts: **yes**.
- tone gain above v2: **yes**.

## Fresh-recording evidence

| Method | Tone bins, 20 / 120 ms (dB) | Whole band, 20 / 120 ms (dB) | Band boosts | Whole-band boosts |
|---|---:|---:|---:|---:|
| Predict nothing | 0.00 / 0.00 | 0.00 / 0.00 | 0 | 0 |
| v2 (current engine) | 0.85 / 0.61 | 0.11 / 0.01 | 2 | 0 |
| Joint check | 2.05 / 0.88 | 0.42 / 0.06 | 2 | 0 |
| Frozen fade candidate | 2.20 / 0.88 | 0.43 / 0.07 | 2 | 0 |
| Prefix-adapted AR | 5.11 / 3.22 | -0.21 / -0.28 | 12 | 2 |
| Online AR | 5.97 / 2.93 | 1.16 / 0.14 | 11 | 1 |

Band boosts count recording-by-horizon cases with at least one third-octave band amplified by 1 dB or more; whole-band boosts use a greater-than-0.5 dB amplification threshold. Each file contributes two cases (20 and 120 ms). Positive prediction gain means reduced reference-waveform error; it is not measured sound reduction at an ear.

## Fresh synthetic evidence

| Method | All late band boosts | Sudden-change late band boosts |
|---|---:|---:|
| Predict nothing | 0 | 0 |
| v2 (current engine) | 47 | 25 |
| Joint check | 33 | 25 |
| Frozen fade candidate | 22 | 14 |
| Prefix-adapted AR | 79 | 24 |
| Online AR | 75 | 25 |

## Uncertainty and integrity

- Against Joint check, at 20 ms on paired tonal files: 4 wins, 2 losses, 0 ties; exact two-sided sign-test p=0.688.
- Against v2 (current engine), at 20 ms on paired tonal files: 2 wins, 4 losses, 0 ties; exact two-sided sign-test p=0.688.
- These are small, purposively selected samples. Reference tones are located with hindsight for scoring; that does not feed future data to the causal predictors, but it can flatter tone-focused metrics.
- This review recounts boosts and recomputes medians from saved scores; it does not rerun the predictors, retune a candidate or replace any held-out recording.
- Timing during a multiprocessing offline run is not a quiet-machine real-time qualification. The live engine remains v2.

[Full frozen report](C:/Users/talk2.000/Desktop/Claude/predictive-anc/results-tone-forecaster-05/REPORT.md) · [Audit](C:/Users/talk2.000/Documents/Codex/2026-10-15/referenced-chatgpt-conversation-this-is-an/outputs/anc-studies-20261020/study-05-review.json)
