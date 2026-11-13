# Signal, timing and evaluation contract

All signals in v0.1 are dimensionless. There is one reference, one actuator and one simulated ear target.

## Signals and acoustics

Let the latent reference-position noise be `v[n]`. The measured reference is `x[n] = v[n] + sensor_noise[n]`. The ear's original disturbance is `d[n] = (P * v)[n] + ear_local_noise[n]`. The ear-local term is independent of `x`, so even perfect reference prediction leaves a residual floor.

The issued digital command is `u[n]`. The receiver sees `r[n] = interpolate(u, n - D_actual - jitter[n])`. The ear's anti-noise pressure is `a[n] = (S_actual * r)[n]`. The residual is `e[n] = d[n] + a[n]`.

`P` and `S` are separate causal FIRs. Defaults:

- Primary: 0.85 at 1 ms and 0.18 at 4 ms.
- Secondary: 0.70 at 3 ms and 0.12 at 5 ms.
- Independent reference sensor noise RMS 0.008 and ear-local noise RMS 0.025.
- Main tone amplitudes 0.45, 0.22 and 0.12, plus latent broadband noise RMS 0.012.

These are deliberately simple, assumed coherent paths. They are not headphone measurements. A real reference microphone observes a sound field, not a privileged latent source waveform; this model is an optimistic case. Multiple independent sources, nonminimum-phase paths, microphone-to-ear spatial decorrelation, nonlinear drivers, seal changes and feedback from the earphone into the reference are absent.

For WAV replay, the captured reference is treated as `v` and passed through the same synthetic primary path with a new independent ear-local term. No measured residual or physical pressure can be inferred from that operation. Training-prefix normalization is dimensionless. Causal anti-alias resampling retains its FIR group delay.

## Timing and command construction

At decision origin `t`, each deployable predictor receives only reference samples through `x[t]`. It forecasts a set of positive horizons. The next 20 command samples (10 ms at 2 kHz) occupy `u[t+1:t+21]`. Thus blocks are committed from the last known sample; there is no centered analysis window or later-sample block lookahead.

Nominal transport `D` is 40 or 240 samples (20 or 120 ms), in addition to the explicit secondary FIR delay. It represents an assumed sample-to-output transport budget after command scheduling. Input-sample age and real compute time are not dynamically simulated. A hardware implementation must measure and include acquisition age, computation, buffering and clock alignment in the effective horizon.

To account for the primary and secondary paths, a regularized least-squares FIR `q` solves:

`min_q || convolution(S_hat, q) - delay(P_hat, A) ||² + lambda ||q||²`

with `A = 16` samples (8 ms), 40 taps and `lambda = 0.0001`. The advance makes this particular inversion causal as a filter design. Prediction supplies the corresponding future samples:

`u[t+j] = -sum_k q[k] * predicted_x[t + D + A + j - k | x[:t+1]]`

for `j = 1..20`. The forecast horizon set includes every index needed by this sum. `inverse_relative_error` records the remaining FIR fit error. This advance is not a general solution to arbitrary ill-conditioned/nonminimum-phase acoustic inverses.

The command is clipped to ±1.2 dimensionless units; all algorithms use that numerical bound. It is **not an acoustic safety limit**. Simulation inputs are not calibrated in Pa or dB SPL.

Jitter is an unknown zero-mean smooth delay process: independent Gaussian values on a 10 ms grid are linearly interpolated and scaled to the specified RMS. Receiver-time interpolation approximates a time-varying fractional delay. It is not a packet scheduler. Large negative total delays are rejected. Linear interpolation introduces high-frequency amplitude error; this finite-sample transport is an approximation, especially for large time warps. It omits codec quantization, packet loss, hard buffer jumps, clock drift and reference-channel acoustic feedback.

## Predictors and controls

| Method | Available information | Adaptation |
|---|---|---|
| No control | None | Zero actuator output |
| Naive polarity | Current reference sample | `u[n] = -x[n]`, no delay/path compensation |
| Tone tracker | Training frequency peaks; rolling 0.6 s reference history | Causal sinusoidal least squares, four bounded local frequency corrections |
| Ridge AR | 128 reference samples ending at origin | Direct linear ridge forecast per requested horizon; trained once |
| Neural MLP | Same 128 samples and target horizons | 64 tanh hidden units; all weights trained, then frozen |
| FxNLMS | Current/past reference and a simulated near-ear error mic | Samplewise normalized filtered-x LMS; secondary model includes nominal transport; online through test |
| Future-reference oracle | Actual future reference samples | Explicitly noncausal diagnostic for the same path-compensated controller |

The AR is direct multi-horizon linear prediction rather than iterative one-step rollout. It is a data-driven FIR forecast, not a frequency-aware controller. Ridge regularization is fixed at 3. The MLP uses Adam, alpha 0.03, 180 maximum epochs, no random early-stopping validation, seed-controlled initialization and train-only standardization. Optimization warnings are retained in `results.json`; absence of a warning is not evidence of a global optimum.

The tracker gets initial peaks (35–350 Hz, at most three separated by 12 Hz) from the training prefix only. Its rolling fits use time relative to the current origin. It estimates local constant frequency and extrapolates; it is not given the source's drift law, true frequencies or future phase. At each origin it refits from causal history independently. It can still be weak on rapid drift or broad spectra.

FxNLMS has a richer sensor set. It uses current residual `e[n]` to update future coefficients and a reference filtered by nominal `D + S_hat`. Three step sizes, 0.001/0.005/0.015, are evaluated; selection minimizes validation ear-error power only. The selected controller's test performance is reported without test-based tuning. Adaptation is frozen while the command saturates, with a small weight leak. This is a basic delayed-gradient control baseline, not an optimized long-delay adaptive ANC implementation. It starts adapting at the beginning of the stream, before the open-loop controllers start at the training boundary; the common score interval follows both warmups.

The oracle is not a universal lower bound on residual: it uses the same approximate inverse, unknown jitter and command clamp, and it includes future reference sensor noise. A denoising tracker can occasionally beat it. It demonstrates that known future waveforms alone cannot solve unknown output timing.

## Leakage prevention and scoring

Training: samples `[0, 12000)`. Validation: `[12000, 16000)`. Test: `[16000, 24000)`. Training origins are spaced every five samples, and their **latest forecast target is strictly before sample 12000**. This embargo includes all compensation horizons. All transformations and frequency estimates fit the training prefix only. There is no shuffled split or test-selected model.

Predictions are computed from training end onward in 20-sample steps. Physical residual scoring begins at validation end plus the largest nominal delay, advance, inverse taps and one output block; it ends at the final committed origin. This conservative common interval avoids startup, transport flush and missing-future-target artifacts across profiles. Its exact bounds are in each result row. Both physical before/after signals use identical indices and units, with no separate normalization.

Reference forecast metrics use horizons `D+1..D+20`, before path compensation, with targets strictly inside the validation/test partitions. Compensation may require somewhat longer forecasts; those extra output dimensions train under the same embargo. Validation and test metrics are reported separately. Predictions may use recent test history as it becomes available, which is causal online operation; model weights do not retrain on test.

- Broadband attenuation: `10 log10(mean(d²) / mean(e²))`.
- Band attenuation: same ratio of Welch spectral power integrated from 35 to 350 Hz.
- Per-tone attenuation: same spectral ratio within ±3 Hz of each **training-detected** peak.
- Prediction MSE, NRMSE and NMSE dB: future reference forecast error divided by future reference power where appropriate.
- Clipping fraction: fraction of issued samples clipped; the open-loop methods' denominator is their committed blocks, and naive/FxNLMS use the full stream. This is a numerical diagnostic, not a directly comparable time-normalized safety measure.
- Seed aggregation: mean and min/max; three realizations are not a population confidence interval. The scene families all share the tone set; this is not broad generalization evidence.

For a perfect equal-amplitude single tone with frequency `f` and timing error `delta`, residual amplitude is `2 |sin(pi f delta)|` times the original. Attenuation is therefore `-20 log10(2 |sin(pi f delta)|)`. This describes a timing-only idealization, not the noisy multipath floor. Gain error and phase error combine: relative residual amplitude is `|1 - g exp(-j 2 pi f delta)|`.
