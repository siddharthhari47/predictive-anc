# Project plan and decision gates

## Objective

Investigate software-only predictive cancellation of a few repeatable noise tones, using an existing laptop/phone microphone as reference and ordinary wired/Bluetooth earphones as actuator. Preserve the long-term engineering goal while requiring measured ear-level evidence before claiming real ANC.

The first viable setting is a stationary source, stationary listener/fixture, stable earphone fit, and narrowband low-frequency hum. Prediction may compensate stable latency. It cannot determine an unknown acoustic path or an unknown future playback time from waveform history alone.

The algorithm must automatically adapt to previously unseen steady tones; this is not a fan-specific product. Evaluate automatic source calibration separately from frozen-ML transfer across sources. [GENERALIZATION.md](GENERALIZATION.md) defines the distinction, the completed frequency-group diagnostic and the next group-held-out tests. Experimental bands may be frozen for honest evaluation without hard-coding those bands into the product.

## Phase 0 — offline feasibility (implemented)

Deliverables: reproducible Python package; deterministic noise sources; optional recording/replay; distinct microphone/ear signals; path compensation; 20/120 ms assumed transport delay; fractional jitter and gain/delay mismatch; causal tracker, direct AR and trained neural comparator; meaningful controls; machine-readable metrics; static figures and local visual report; scientific regression checks.

Evaluate three seeds for each of steady, slowly drifting, and unpredictable noise. Report complete results, including amplification. Use a chronological 6/2/4 second split. Do not pick a winner on the test partition. Use validation ear error to choose the FxNLMS adaptation step because long transport delays constrain adaptation stability.

Exit gate: causal bookkeeping and forward-model tests pass; steady tones can be cancelled under accurate assumed paths; jitter and mismatch visibly degrade results; unpredictable innovations remain a negative control. This gate establishes simulator consistency, not hardware feasibility.

## Phase 1 — reference capture and device characterization

Current first experiment: see [GOAL_1.md](GOAL_1.md) and [the outcome](GOAL_1_OUTCOME.md). A mixed-noise recording and a user-confirmed quiet fan-only repeat have been captured and evaluated with no playback. The clean trial did not meet the useful-prediction target. The subsequent [matched fan-off/fan-on study](SOURCE_STUDY.md) found four persistent spectral candidates; useful prediction of those candidates still requires fresh independent data. Acoustic calibration and near-ear measurements remain pending.

1. Capture repeated fan/AC recordings with the existing microphone, on stationary geometry. Log source distance, microphone, sample rate, input processing, and OS settings. Gather at least three independent sessions, not three crops of one capture.
2. Measure reference-to-ear coherence at each candidate tone with a synchronized near-ear measurement microphone. Estimate whether the reference actually observes the disturbance at the target location. A desk microphone may not observe ear-local or spatially incoherent noise.
3. Measure input/processing/output latency and clock drift for the intended wired setup on a fixture. Separate software buffering, driver delay, DAC delay and acoustic travel. Use an electrical loopback for timing where appropriate plus acoustic measurements for the full path.
4. Estimate the secondary path at a low calibrated output. Also estimate reference-to-ear primary transfer over the control tones. Save raw simultaneous channels, timestamps, calibration units and repeated fits. Repeat after earphone removal/reseating.

Exit gate: stable coherent tones, usable synchronized reference/ear data, repeatable path estimates and a measured latency/jitter distribution. If those fail, narrow the geometry or frequency set before adding ML.

## Phase 2 — offline replay of measured paths

Replace assumed FIRs and delays with measured distributions. Keep session-level train/validation/test separation. Include model mismatch and held-out earphone fits. Track changes in residual outside target bands, clipping, prediction uncertainty and sensitivity to timing error. Add capture-clock offset/drift, reference leakage from the earphone, packet discontinuities and gain changes as separate ablations.

Exit gate: on held-out fixture recordings, target at least 6 dB reduction in predefined hum bands relative to the same earphone fit with zero actuator output. This is a proposed engineering target, not a promised result. Require stable performance and no unexplained residual growth before hardware playback. Predeclare bands and comparison windows; publish failures.

## Phase 3 — real-time wired fixture prototype

Implement a dedicated full-duplex audio callback, preallocated buffers, timestamp accounting and a ring buffer. Start with the simplest successful predictor. Measure worst-case callback time, not only average inference time. Account for capture age, block deadlines, resampling delay and output queue depth in the actual forecast horizon. Never silently read future samples to fill a missed block.

Add a narrow control band, gain ramps, output bounds, an immediate stop, watchdog mute on underrun/path-confidence loss, and error-mic residual monitoring. The software clamp is not SPL calibration. Verify all behavior on a fixture with no human ear exposed first.

Exit gate: simultaneous physical baseline/controller measurements at the near-ear mic demonstrate repeatable reduction over at least three independent runs with measured low acoustic output. Include latency traces, residual spectra, held-out fit/position perturbations and any amplification. Consumer listening is a separate safety decision after fixture validation.

## Phase 4 — calibrated wireless fixture prototype

Characterize the specific phone/laptop, headset, profile, codec, sample rate and operating mode. Do not substitute advertised codec latency for measured microphone-to-ear timing. Measure reconnects, buffer changes, dropouts, resampling drift and microphone mode changes. Determine whether the future playback schedule is predictable enough at the chosen tones.

Rerun the wired protocol using the measured wireless timing distribution. If unknown timing exceeds the derived phase-error budget, restrict frequencies, improve timestamp/calibration access, or reject that operating condition. More accurate waveform prediction cannot repair independent playback-time uncertainty.

Exit gate: measured near-ear reduction with the actual wireless device, at a known low output, over repeated sessions and reconnections. “Works on Bluetooth” requires this evidence; a fixed 120 ms simulation does not establish it.

## Initial decisions and boundaries

- Python/NumPy/SciPy for signal/control work; scikit-learn for the first trained MLP; no mandatory GPU or cloud service.
- 2 kHz analysis rate and 35–350 Hz reporting band are a scoped low-frequency simulation, not a production audio engine. Harmonics are selected from training data only.
- Predictor/controller/source interfaces stay separate so future measured paths and better ML models can be added without changing evaluation definitions.
- Benchmark nonlinear ML against a strong simple tracker before investing in neural complexity. The first network is a comparator, not a product architecture commitment.
- Stereo ears require separate ear transfer functions and potentially different cancellation commands. The current model is one target point and one actuator.
- No microphone capture occurred in the initial v0.1 setup. Goal 1 now includes input-only microphone capture. No physical ANC playback, cloud deployment, commits or remote repository creation has occurred.
