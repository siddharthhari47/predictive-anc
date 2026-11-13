# Initial findings — offline only

Completed 15 October 2026. The default run contains 315 rows: three noise conditions × three seeds × five transport/calibration profiles × seven methods. Run time was about 56 seconds on this machine, including baseline adaptation-step comparisons. This is batch execution time, not a verified real-time latency budget.

## What the first experiment says

With steady hum and exact assumed path calibration, the causal tracker achieved a mean 21.36 dB reduction in simulated broadband ear residual for the 20 ms fixed-delay profile. At a fixed 120 ms delay, it achieved 21.35 dB. The source is predictable enough that stable delay alone is not the limiting factor in this idealized case.

With the same steady source and 2 ms RMS unknown jitter on the 120 ms profile, the tracker fell to 0.58 dB mean attenuation. The future-reference oracle also loses nearly all its benefit under these timing conditions. The test therefore isolates playback-time uncertainty as a limiting factor even when waveform prediction is excellent.

Adding 20% secondary-path gain mismatch and 0.5 ms unknown fixed delay reduced the tracker's steady-hum result to 8.19 dB. The error-microphone FxNLMS baseline recovered about 21.26 dB because its additional sensor permits adaptation. That comparison illustrates the value of ear-level feedback; it does not show that a remote reference-only system can self-calibrate its target pressure.

There is no universal ML winner. On steady fixed-delay hum, the tracker, direct AR and small neural model are all close to the simulated noise floor. On the long fixed-delay drifting case, the neural model averaged 14.78 dB compared with 11.65 dB for direct AR and 12.04 dB for the tracker. This is one synthetic drift family with three realizations, not proof of general neural superiority.

The unpredictable-noise case still contains hum. Its approximately 3 dB reduction under accurate timing is largely compatible with removing tones while leaving unpredictable energy. It should not be read as successful prediction or cancellation of the broadband burst.

Six of nine neural fits hit the configured 180-epoch limit without meeting the optimizer's stopping criterion. The predictions and metrics are valid outputs of those fits, but this limits conclusions about the neural model's best achievable performance. These warnings are preserved per fit in `results/results.json`.

Some control conditions amplify the disturbance. For example, naive inversion worsens the steady wired fixed-delay residual by roughly 4.6 dB, and the adaptive baseline loses stability/performance under some unknown-jitter conditions. Negative results remain in the report; no algorithm is assumed safe simply because it emits an inverted waveform.

## Recommended next experiment

Use the optional input-only recorder to collect several stationary fan/AC sessions with the existing microphone. Then measure synchronized reference and near-ear signals on a wired fixture, including the secondary acoustic path and the full latency/jitter distribution. Replace the assumed paths and timing with those measurements before implementing live output. Keep the simple tracker and direct AR as the first contenders; the current results do not justify committing to a large neural architecture.

## Verification completed

- Nine regression checks passed: future-data invariance, training-label embargo, positive/fractional delay direction, analytic timing sensitivity, path-compensated oracle cancellation, delayed FxNLMS adaptation/renderer agreement, deterministic distinct reference/ear signals, replay intake checks, and causal resampling/train-prefix normalization.
- A full 16 kHz generated mono WAV was replayed end-to-end into the 2 kHz analysis pipeline. Its generated recording and temporary report stay outside the delivered project.
- A Python wheel built successfully from `pyproject.toml` without installing or changing global dependencies.
- The three scientific figures were rendered and visually inspected for readable labels, legends and unclipped content.
- No microphone capture, acoustic playback, ear-level hardware measurement or Bluetooth device measurement occurred.
