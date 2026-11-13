# Predictive ANC lab — first offline results

OFFLINE SIMULATION ONLY; no physical ANC or safe SPL validated

Seeds: (7, 19, 43). Total runtime: 55.9 s.

All values use the same held-out physical interval per scene/seed. Positive attenuation means lower residual power; negative means amplification. Ranges below are min/max across seeds, not confidence intervals.

| Scene | Transport / calibration | Method | Mean attenuation dB | Seed range dB | Test prediction NRMSE |
|---|---|---|---:|---:|---:|
| steady | wired_fixed | No control | 0.00 | 0.00 to 0.00 | — |
| steady | wired_fixed | Naive inversion | -4.59 | -4.59 to -4.59 | — |
| steady | wired_fixed | Linear AR (direct) | 21.32 | 21.25 to 21.39 | 0.041 |
| steady | wired_fixed | Causal neural MLP | 21.16 | 21.07 to 21.21 | 0.044 |
| steady | wired_fixed | Tone tracker | 21.36 | 21.29 to 21.43 | 0.040 |
| steady | wired_fixed | Future oracle (noncausal) | 21.69 | 21.63 to 21.77 | 0.000 |
| steady | wired_fixed | FxNLMS + error mic | 21.28 | 21.20 to 21.34 | — |
| steady | wired_jitter | No control | 0.00 | 0.00 to 0.00 | — |
| steady | wired_jitter | Naive inversion | -4.56 | -4.56 to -4.55 | — |
| steady | wired_jitter | Linear AR (direct) | 15.23 | 15.06 to 15.46 | 0.041 |
| steady | wired_jitter | Causal neural MLP | 15.20 | 15.04 to 15.41 | 0.044 |
| steady | wired_jitter | Tone tracker | 15.25 | 15.08 to 15.46 | 0.040 |
| steady | wired_jitter | Future oracle (noncausal) | 15.27 | 15.11 to 15.51 | 0.000 |
| steady | wired_jitter | FxNLMS + error mic | 14.87 | 14.69 to 15.08 | — |
| steady | wireless_fixed | No control | 0.00 | 0.00 to 0.00 | — |
| steady | wireless_fixed | Naive inversion | 2.82 | 2.82 to 2.83 | — |
| steady | wireless_fixed | Linear AR (direct) | 21.32 | 21.25 to 21.40 | 0.041 |
| steady | wireless_fixed | Causal neural MLP | 21.17 | 21.14 to 21.21 | 0.044 |
| steady | wireless_fixed | Tone tracker | 21.35 | 21.28 to 21.43 | 0.040 |
| steady | wireless_fixed | Future oracle (noncausal) | 21.69 | 21.63 to 21.77 | 0.000 |
| steady | wireless_fixed | FxNLMS + error mic | 20.45 | 20.40 to 20.52 | — |
| steady | wireless_jitter | No control | 0.00 | 0.00 to 0.00 | — |
| steady | wireless_jitter | Naive inversion | -0.02 | -0.16 to 0.05 | — |
| steady | wireless_jitter | Linear AR (direct) | 0.58 | 0.46 to 0.79 | 0.041 |
| steady | wireless_jitter | Causal neural MLP | 0.58 | 0.45 to 0.80 | 0.044 |
| steady | wireless_jitter | Tone tracker | 0.58 | 0.46 to 0.79 | 0.040 |
| steady | wireless_jitter | Future oracle (noncausal) | 0.57 | 0.45 to 0.78 | 0.000 |
| steady | wireless_jitter | FxNLMS + error mic | -1.52 | -1.70 to -1.31 | — |
| steady | wired_miscalibrated | No control | 0.00 | 0.00 to 0.00 | — |
| steady | wired_miscalibrated | Naive inversion | -5.15 | -5.16 to -5.15 | — |
| steady | wired_miscalibrated | Linear AR (direct) | 8.19 | 8.17 to 8.22 | 0.041 |
| steady | wired_miscalibrated | Causal neural MLP | 8.16 | 8.15 to 8.17 | 0.044 |
| steady | wired_miscalibrated | Tone tracker | 8.19 | 8.17 to 8.22 | 0.040 |
| steady | wired_miscalibrated | Future oracle (noncausal) | 8.13 | 8.11 to 8.16 | 0.000 |
| steady | wired_miscalibrated | FxNLMS + error mic | 21.26 | 21.18 to 21.31 | — |
| drifting | wired_fixed | No control | 0.00 | 0.00 to 0.00 | — |
| drifting | wired_fixed | Naive inversion | -4.52 | -4.52 to -4.51 | — |
| drifting | wired_fixed | Linear AR (direct) | 20.29 | 20.27 to 20.31 | 0.061 |
| drifting | wired_fixed | Causal neural MLP | 20.09 | 20.06 to 20.14 | 0.064 |
| drifting | wired_fixed | Tone tracker | 16.56 | 16.54 to 16.57 | 0.137 |
| drifting | wired_fixed | Future oracle (noncausal) | 21.70 | 21.63 to 21.78 | 0.000 |
| drifting | wired_fixed | FxNLMS + error mic | 18.10 | 17.93 to 18.25 | — |
| drifting | wired_jitter | No control | 0.00 | 0.00 to 0.00 | — |
| drifting | wired_jitter | Naive inversion | -4.48 | -4.49 to -4.48 | — |
| drifting | wired_jitter | Linear AR (direct) | 14.89 | 14.67 to 15.28 | 0.061 |
| drifting | wired_jitter | Causal neural MLP | 14.90 | 14.65 to 15.29 | 0.064 |
| drifting | wired_jitter | Tone tracker | 13.55 | 13.27 to 14.00 | 0.137 |
| drifting | wired_jitter | Future oracle (noncausal) | 15.18 | 15.03 to 15.47 | 0.000 |
| drifting | wired_jitter | FxNLMS + error mic | 13.90 | 13.73 to 14.17 | — |
| drifting | wireless_fixed | No control | 0.00 | 0.00 to 0.00 | — |
| drifting | wireless_fixed | Naive inversion | 10.79 | 10.78 to 10.81 | — |
| drifting | wireless_fixed | Linear AR (direct) | 11.65 | 11.63 to 11.66 | 0.273 |
| drifting | wireless_fixed | Causal neural MLP | 14.78 | 14.69 to 14.82 | 0.178 |
| drifting | wireless_fixed | Tone tracker | 12.04 | 12.03 to 12.04 | 0.258 |
| drifting | wireless_fixed | Future oracle (noncausal) | 21.70 | 21.63 to 21.78 | 0.000 |
| drifting | wireless_fixed | FxNLMS + error mic | 10.18 | 10.12 to 10.26 | — |
| drifting | wireless_jitter | No control | 0.00 | 0.00 to 0.00 | — |
| drifting | wireless_jitter | Naive inversion | 0.87 | 0.76 to 1.09 | — |
| drifting | wireless_jitter | Linear AR (direct) | 0.15 | -0.07 to 0.36 | 0.273 |
| drifting | wireless_jitter | Causal neural MLP | 0.38 | 0.16 to 0.59 | 0.178 |
| drifting | wireless_jitter | Tone tracker | 0.51 | 0.33 to 0.76 | 0.258 |
| drifting | wireless_jitter | Future oracle (noncausal) | 0.55 | 0.41 to 0.72 | 0.000 |
| drifting | wireless_jitter | FxNLMS + error mic | -1.13 | -1.46 to -0.89 | — |
| drifting | wired_miscalibrated | No control | 0.00 | 0.00 to 0.00 | — |
| drifting | wired_miscalibrated | Naive inversion | -5.05 | -5.05 to -5.05 | — |
| drifting | wired_miscalibrated | Linear AR (direct) | 7.56 | 7.54 to 7.58 | 0.061 |
| drifting | wired_miscalibrated | Causal neural MLP | 7.98 | 7.92 to 8.01 | 0.064 |
| drifting | wired_miscalibrated | Tone tracker | 7.78 | 7.75 to 7.80 | 0.137 |
| drifting | wired_miscalibrated | Future oracle (noncausal) | 8.07 | 8.05 to 8.09 | 0.000 |
| drifting | wired_miscalibrated | FxNLMS + error mic | 17.30 | 17.01 to 17.51 | — |
| unpredictable | wired_fixed | No control | 0.00 | 0.00 to 0.00 | — |
| unpredictable | wired_fixed | Naive inversion | -3.51 | -3.56 to -3.47 | — |
| unpredictable | wired_fixed | Linear AR (direct) | 2.62 | 2.54 to 2.71 | 0.735 |
| unpredictable | wired_fixed | Causal neural MLP | 2.74 | 2.65 to 2.85 | 0.725 |
| unpredictable | wired_fixed | Tone tracker | 2.99 | 2.91 to 3.08 | 0.703 |
| unpredictable | wired_fixed | Future oracle (noncausal) | 16.71 | 16.21 to 17.17 | 0.000 |
| unpredictable | wired_fixed | FxNLMS + error mic | 2.88 | 2.82 to 2.96 | — |
| unpredictable | wired_jitter | No control | 0.00 | 0.00 to 0.00 | — |
| unpredictable | wired_jitter | Naive inversion | -3.29 | -3.35 to -3.25 | — |
| unpredictable | wired_jitter | Linear AR (direct) | 2.64 | 2.57 to 2.73 | 0.735 |
| unpredictable | wired_jitter | Causal neural MLP | 2.71 | 2.65 to 2.80 | 0.725 |
| unpredictable | wired_jitter | Tone tracker | 2.89 | 2.82 to 2.97 | 0.703 |
| unpredictable | wired_jitter | Future oracle (noncausal) | 6.17 | 5.97 to 6.30 | 0.000 |
| unpredictable | wired_jitter | FxNLMS + error mic | 2.79 | 2.74 to 2.87 | — |
| unpredictable | wireless_fixed | No control | 0.00 | 0.00 to 0.00 | — |
| unpredictable | wireless_fixed | Naive inversion | -0.26 | -0.32 to -0.20 | — |
| unpredictable | wireless_fixed | Linear AR (direct) | 2.64 | 2.57 to 2.74 | 0.734 |
| unpredictable | wireless_fixed | Causal neural MLP | 2.71 | 2.60 to 2.85 | 0.727 |
| unpredictable | wireless_fixed | Tone tracker | 2.96 | 2.88 to 3.05 | 0.706 |
| unpredictable | wireless_fixed | Future oracle (noncausal) | 16.71 | 16.21 to 17.17 | 0.000 |
| unpredictable | wireless_fixed | FxNLMS + error mic | 2.84 | 2.77 to 2.92 | — |
| unpredictable | wireless_jitter | No control | 0.00 | 0.00 to 0.00 | — |
| unpredictable | wireless_jitter | Naive inversion | -0.81 | -0.88 to -0.75 | — |
| unpredictable | wireless_jitter | Linear AR (direct) | 0.19 | 0.07 to 0.36 | 0.734 |
| unpredictable | wireless_jitter | Causal neural MLP | 0.18 | 0.05 to 0.33 | 0.727 |
| unpredictable | wireless_jitter | Tone tracker | 0.24 | 0.16 to 0.40 | 0.706 |
| unpredictable | wireless_jitter | Future oracle (noncausal) | -0.53 | -0.67 to -0.33 | 0.000 |
| unpredictable | wireless_jitter | FxNLMS + error mic | -0.56 | -0.70 to -0.38 | — |
| unpredictable | wired_miscalibrated | No control | 0.00 | 0.00 to 0.00 | — |
| unpredictable | wired_miscalibrated | Naive inversion | -4.14 | -4.17 to -4.11 | — |
| unpredictable | wired_miscalibrated | Linear AR (direct) | 2.03 | 2.01 to 2.07 | 0.735 |
| unpredictable | wired_miscalibrated | Causal neural MLP | 2.07 | 2.02 to 2.14 | 0.725 |
| unpredictable | wired_miscalibrated | Tone tracker | 2.37 | 2.32 to 2.46 | 0.703 |
| unpredictable | wired_miscalibrated | Future oracle (noncausal) | -0.71 | -0.85 to -0.60 | 0.000 |
| unpredictable | wired_miscalibrated | FxNLMS + error mic | 2.87 | 2.80 to 2.96 | — |

## Interpretation limits

- Causal predictors fit only the first training partition; all training target samples precede its boundary. Validation is reported separately; test is chronological and untouched during training.
- Tone frequencies come from training audio, with causal local phase/frequency refits during evaluation. Linear and neural models are frozen. No model is selected using test results.
- Calibrated predictive controllers use exact assumed FIR paths; this is an optimistic calibration condition. The mismatch profile adds 20% actuator gain and 0.5 ms unmodelled delay.
- FxNLMS additionally observes a simulated error microphone and adapts throughout the stream, including test. It uses the same nominal path/delay and transport jitter, but has extra sensing.
- The oracle sees future reference samples and is explicitly noncausal. It is a diagnostic bound for this controller family, not an attainable algorithm or a guaranteed global optimum.
- Prediction NRMSE measures future reference-microphone error; attenuation measures simulated ear residual. They are different quantities.
- Jitter is an illustrative smooth delay process. Delays are chosen stress cases, not measured specifications of wired/Bluetooth products. No codec, AGC, clock drift, dropouts, microphone feedback, music mixing, bilateral fit or head movement is emulated.
- The model has a dimensionless output clamp; no physical SPL or safe playback volume follows from it. No playback occurs.
- The MLP is a small fully trained tanh network, not evidence about the best possible ML architecture. Optimization warnings are preserved in results.json.

## Artifacts

- `results.json`: full per-seed metrics, training details, versions, source hashes and timing sweep.
- `metrics.csv`: machine-readable control and prediction comparison, including clipping fractions.
- `example_signals.npz`: reference, simulated ear disturbance and residuals for the first steady/replay seed; no WAV playback assets.
- PNG figures and `report.html`: plots and comparison table.
