# Goal 1 — first real microphone trial

Reference prediction only; no output playback or ear-level cancellation measured.

Source: fan only; user confirmed quiet room and airflow away from laptop. Input: `reference.wav`. Duration: 30.0 s.
Capture quality: PASS.

Reported conditions: Only the fan is running; no talking/music; airflow away from laptop microphone. Controlled fan-only trial as reported by the user. Acoustic source isolation is not independently verified.

## Held-out finding

At 20 ms, validation selected Zero forecast. Held-out low-band prediction gain: 0.00 dB; full-reference NRMSE: 1.000. TARGET NOT MET.
At 120 ms, validation selected Zero forecast. Held-out low-band prediction gain: 0.00 dB; full-reference NRMSE: 1.000. TARGET NOT MET.

The stated horizon is the start of the next 10 ms forecast block. Models use reference history only. Selection uses validation data; the test partition is evaluated afterward.

| Method | Horizon ms | Selected | Validation low-band gain dB | Test low-band gain dB | Test full gain dB | Test NRMSE |
|---|---:|---|---:|---:|---:|---:|
| Zero forecast | 20 | yes | 0.00 | 0.00 | 0.00 | 1.000 |
| Hold last sample | 20 |  | -1.40 | -1.82 | -3.22 | 1.448 |
| Repeat last cycle | 20 |  | -2.61 | -2.73 | -3.00 | 1.413 |
| Tone tracker | 20 |  | -0.19 | -0.19 | -0.17 | 1.020 |
| Linear AR | 20 |  | -0.10 | -0.14 | -0.11 | 1.013 |
| Neural MLP | 20 |  | -0.85 | -1.23 | -1.16 | 1.143 |
| Zero forecast | 120 | yes | 0.00 | 0.00 | 0.00 | 1.000 |
| Hold last sample | 120 |  | -1.45 | -1.80 | -3.14 | 1.436 |
| Repeat last cycle | 120 |  | -2.79 | -2.89 | -3.11 | 1.431 |
| Tone tracker | 120 |  | -0.28 | -0.16 | -0.15 | 1.017 |
| Linear AR | 120 |  | -0.07 | -0.10 | -0.08 | 1.010 |
| Neural MLP | 120 |  | -0.76 | -1.04 | -0.97 | 1.118 |

## Interpretation and next step

The current recording does not meet the forecast target. Inspect whether stable tonal energy is present and whether laptop input processing changes it. Test a more stationary or more tonal source, or adjust source/microphone placement; preserve this failed trial. Do not enable anti-noise output from this result.

- Prediction gain compares future reference waveform error with zero prediction. It is not measured cancellation at an ear.
- Low-band scoring uses the same causal 35–350 Hz Butterworth filter on actual and error signals, with 0.5 s discarded for startup. This is a predefined weighting of prediction error, not a new input supplied to the predictors.
- Full-reference scoring is at the 2 kHz analysis rate after causal anti-alias resampling; it does not cover noise above 1 kHz.
- The laptop's AGC, suppression and echo-processing state is unknown. Device-reported input latency is not an acoustic round-trip measurement.
- 1 neural fit(s) reported optimization warnings; details are preserved in assessment.json.
- One capture is one session. There is no independent-session generalization or near-ear calibration evidence yet.
