# Physical validation protocol — future work

Nothing in the initial build plays audio. Its completed results are synthetic pressure calculations. The optional recorder is input-only and was not run against hardware during setup.

## Required measurements

The existing laptop/phone microphone remains the proposed operational reference. A separate calibrated near-ear measurement microphone is required to validate the claim, identify acoustic paths, and expose amplification. It can be test equipment without being part of a future end-user product.

Start with a fixture/coupler or suitable ear simulator. A microphone outside the ear or a laptop microphone can show cancellation at its own location without showing the same result at the ear. A probe near an actual ear does not automatically measure eardrum pressure; document its location, coupling, frequency response, uncertainty and limitations.

Use synchronized reference and near-ear channels where possible. If clocks differ, estimate offset and drift rather than aligning by a single arbitrary time shift. Record the clock and sample-rate mapping. Disable or document automatic gain control, noise suppression, echo cancellation, spatial effects, equalizers, headset mode switching, and sample-rate conversion.

## Measure first on a fixture

1. Fix source, microphone, earphone and target position. Record at least 30 seconds of original hum with zero actuator command and the earphone already in its test fit. This baseline accounts for passive isolation.
2. Use low calibrated test output to identify the secondary path from digital command to near-ear pressure. Record gain, phase, delay and estimation uncertainty over the control band. The script does not choose test-signal level.
3. Identify the reference-to-ear transfer and coherence for the disturbance tones. Test source-off conditions too; independent reference noise should not trigger substantial actuator output.
4. Repeat path and delay measurements across reseating and separate sessions. Include drift, OS buffering, callback overruns, and the actual earphone output route.
5. Replay controllers offline using the measured data and predeclared partitions. Require improvement in the intended bands before enabling output.

## Bound the first real-time prototype

- Establish the acoustic output limit using calibrated measurement on the fixture. A WAV peak, OS volume percentage or ±1.2 software clamp does not bound ear SPL across devices.
- Restrict output to the validated narrow bands; apply a gain ramp and a limiter. Retain immediate stop and mute on loss of timing/path confidence, callback failure or growing residual.
- Run with no human exposure initially. Ensure unpredictable sounds, mic disconnection and source-off periods do not produce sustained high output.
- Log command, reference, residual, timestamps, underruns, clipping and calibration identity. Check whether actuator leakage enters the reference microphone and destabilizes prediction/control.
- Do not use the experiment as hearing protection or for sudden hazardous noise. No safety certification or acoustic exposure threshold is established by this project.

## Declare physical success carefully

Compare matched baseline and controlled conditions at the same near-ear sensor with the same fit and calibrated measurement gain. Report target-band and outside-band spectra, broadband RMS, per-tone reduction, time traces, uncertainty and repeatability. Do not independently normalize before and after audio. Include failed runs and source/fit perturbations.

The proposed first target is at least 6 dB reduction in predeclared stable-hum bands across three independent stationary fixture sessions, without unexplained growth elsewhere. This is an engineering milestone, not a safe exposure level or a guaranteed result. Assess overall acoustic exposure separately before any listening trial.

For wireless, repeat after reconnections and mode changes and report the measured time-varying latency distribution. A successful simulation with fixed delay is insufficient. A practical open-loop consumer system must explain how it maintains path/timing confidence without a permanent near-ear error sensor.
