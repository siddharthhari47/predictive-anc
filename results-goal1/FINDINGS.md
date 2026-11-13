# Goal 1 — first real microphone trial

Reference prediction only; no output playback or ear-level cancellation measured.

Source: fan near laptop. Input: `goal1_fan_01.wav`. Duration: 30.0 s.
Capture quality: PASS.

Reported conditions: There was also talking, music, or other noise. Mixed-noise control; this trial does not isolate a steady fan.

## Held-out finding

At 20 ms, validation selected Zero forecast. Held-out low-band prediction gain: 0.00 dB; full-reference NRMSE: 1.000. TARGET NOT MET.
At 120 ms, validation selected Zero forecast. Held-out low-band prediction gain: 0.00 dB; full-reference NRMSE: 1.000. TARGET NOT MET.

The stated horizon is the start of the next 10 ms forecast block. Models use reference history only. Selection uses validation data; the test partition is evaluated afterward.

| Method | Horizon ms | Selected | Validation low-band gain dB | Test low-band gain dB | Test full gain dB | Test NRMSE |
|---|---:|---|---:|---:|---:|---:|
| Zero forecast | 20 | yes | 0.00 | 0.00 | 0.00 | 1.000 |
| Hold last sample | 20 |  | -3.00 | -3.45 | -2.90 | 1.396 |
| Repeat last cycle | 20 |  | -2.73 | -3.12 | -3.08 | 1.426 |
| Tone tracker | 20 |  | -0.07 | -0.18 | -0.05 | 1.006 |
| Linear AR | 20 |  | -0.21 | -0.44 | -0.29 | 1.034 |
| Neural MLP | 20 |  | -0.94 | -1.36 | -0.92 | 1.112 |
| Zero forecast | 120 | yes | 0.00 | 0.00 | 0.00 | 1.000 |
| Hold last sample | 120 |  | -2.91 | -3.46 | -2.85 | 1.388 |
| Repeat last cycle | 120 |  | -2.96 | -2.94 | -2.97 | 1.408 |
| Tone tracker | 120 |  | -0.09 | -0.23 | -0.07 | 1.008 |
| Linear AR | 120 |  | -0.22 | -0.47 | -0.31 | 1.036 |
| Neural MLP | 120 |  | -1.02 | -1.46 | -1.04 | 1.127 |

## Interpretation and next step

The current recording does not meet the forecast target. Inspect whether stable tonal energy is present and whether laptop input processing changes it. Test a more stationary or more tonal source, or adjust source/microphone placement; preserve this failed trial. Do not enable anti-noise output from this result.

- Prediction gain compares future reference waveform error with zero prediction. It is not measured cancellation at an ear.
- Low-band scoring uses the same causal 35–350 Hz Butterworth filter on actual and error signals, with 0.5 s discarded for startup. This is a predefined weighting of prediction error, not a new input supplied to the predictors.
- Full-reference scoring is at the 2 kHz analysis rate after causal anti-alias resampling; it does not cover noise above 1 kHz.
- The laptop's AGC, suppression and echo-processing state is unknown. Device-reported input latency is not an acoustic round-trip measurement.
- 1 neural fit(s) reported optimization warnings; details are preserved in assessment.json.
- One capture is one session. There is no independent-session generalization or near-ear calibration evidence yet.
