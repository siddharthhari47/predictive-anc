# Goal 1: first real-microphone prediction result

Status: the first controlled real-microphone feasibility experiment is complete, 15 October 2026. **The 6 dB prediction-performance target was not met.** This closes the initial capture-and-evaluate experiment, not the technical gate for useful predictive cancellation.

Two 30-second live captures are preserved. The first included other sounds and remains a mixed-noise control in `recordings/goal1_fan_01.wav` and `results-goal1/`. After the user confirmed that only the fan was running and airflow was away from the laptop, a controlled repeat was captured in `results-goal1-clean/reference.wav`. Both passed basic digital quality checks. The unchanged evaluation selected zero prediction at both horizons on the clean trial; the prediction threshold was not met. See [the controlled-trial finding](GOAL_1_OUTCOME.md).

## Deliverable

Capture one 30-second stationary fan recording using the laptop microphone. Establish whether its repeating components can be forecast 20 ms ahead, with 120 ms as a wireless-oriented stress case. Produce a reproducible, held-out prediction report and an explicit decision about the next experiment. This is the first real-data feasibility result; it does not complete acoustic ANC validation.

## Predeclared evaluation

- Record locally with no playback; retain the device identity, raw WAV hash, input quality and callback timing metadata.
- Use the first 12 seconds for model fitting, the next 6 seconds for selection, and the last 12 seconds for untouched evaluation. No test-based frequency selection, model tuning or normalization.
- Compare the causal tone tracker, direct linear AR and neural MLP against zero prediction, persistence and a repeating-cycle baseline.
- Freeze the selected model using validation error before reading its test score. Report all methods, not only the selection.
- Report full-reference waveform error and 35–350 Hz prediction-error power separately. A narrowband result does not imply broadband noise cancellation.
- A useful first prediction result targets at least 6 dB reduction in low-band prediction-error power relative to zero prediction at 20 ms, with no worse full-reference MSE than the zero predictor. Report the same criteria at 120 ms separately.
- Quality gate: no capture overflow/underflow status, no near-full-scale samples, non-silent recording and valid training/validation/test coverage. Quality problems invalidate the success flag rather than being hidden by normalization.
- A failed threshold is a useful feasibility result, not a reason to relabel the result as successful cancellation. Preserve the data, identify the limiting factor, and choose the next experiment from evidence.

## Completion evidence

A real input recording with provenance and quality metadata; tested causal evaluation code; the report with predeclared pass/fail metrics and selected model; and a concrete next step supported by that result. One trial establishes a first finding only. Independent-session reproducibility, near-ear pressure, acoustic paths, measured output timing and safe physical playback remain the next gates in PLAN.md.
