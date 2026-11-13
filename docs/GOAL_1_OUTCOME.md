# Goal 1 outcome: clean fan trial

The first controlled microphone feasibility experiment is complete. **Useful prediction at the predeclared 6 dB threshold has not been demonstrated.** No earphone output or acoustic cancellation was attempted.

## Evidence

After the mixed-noise first recording, the user confirmed: only the fan was running, no talking/music, and airflow away from the laptop. A new 30-second mono recording was captured from the laptop's Intel Smart Sound microphone array through Windows WASAPI at 48 kHz. Source isolation is based on the user's report, not independent acoustic verification.

The repeat contains no reported stream errors and no near-full-scale samples. Peak digital amplitude is 0.0351 and RMS is 0.00283. These are recording levels, not calibrated pressure or SPL. The capture sidecar's WAV hash matches the assessment's input hash.

The assessment and predictor source files are unchanged from the mixed-noise trial. Training uses 0–12 s, validation 12–18 s, and test 18–30 s. Selection was frozen from validation before test metrics were computed. No model was retuned after seeing the clean test data.

| Method | 20 ms validation gain | 20 ms test gain | 120 ms validation gain | 120 ms test gain |
|---|---:|---:|---:|---:|
| Zero forecast | 0.00 dB | 0.00 dB | 0.00 dB | 0.00 dB |
| Tone tracker | −0.19 dB | −0.19 dB | −0.28 dB | −0.16 dB |
| Direct linear AR | −0.10 dB | −0.14 dB | −0.07 dB | −0.10 dB |
| Neural MLP | −0.85 dB | −1.23 dB | −0.76 dB | −1.04 dB |

Values are prediction-error power improvement over zero prediction in the predefined 35–350 Hz band. Negative values mean more prediction error. The 20/120 ms labels refer to the start of each following 10 ms forecast block. Persistence and repeated-cycle baselines are also included in the full report and performed worse.

The clean spectrum is broadly distributed, with weak training-selected peaks near 41.0, 80.4 and 129.2 Hz. It does not resemble the strong, coherent three-tone source used by the synthetic positive control. That observation is consistent with the failed prediction result, but it does not distinguish fan turbulence, room noise, microphone self-noise or input processing. A fan-off measurement is needed for that separation.

The MLP reached its configured iteration limit. This result therefore describes the tested first models, not the best achievable neural predictor. One source/position and one clean session do not establish general feasibility or impossibility.

## Decision

Do not advance this recording to live anti-noise playback. The first target for further work is **source characterization**: determine whether the microphone is receiving a sufficiently strong, coherent periodic component that is actually attributable to the fan.

The next useful experiment is a matched fan-off / fan-on pair with fixed microphone position and input settings. Compare absolute digital spectra without independently normalizing the two recordings. Document the OS microphone enhancement settings, which are currently unknown. If a stable fan-attributable tone exists, predeclare its control band and evaluate a new held-out recording; retain the failed 35–350 Hz result. If it does not, use a more tonal steady source for the predictive-ANC proof of concept.

The driver reports 22 ms of input latency and the causal resampler adds 5 ms of filter delay. Those values do not establish physical end-to-end latency. Measuring the acoustic path and actual sample-to-ear timing remains a later gate.

## Deliverables

- `results-goal1-clean/report.html`: visual report and full comparison.
- `results-goal1-clean/assessment.json` and `metrics.csv`: per-model validation/test results.
- `results-goal1-clean/reference.wav` and `reference.capture.json`: local raw capture and provenance/timing metadata.
- `results-goal1-clean/trial_notes.json`: user-reported experimental conditions.

Raw microphone audio stays in the local project and is excluded from the source/report ZIP.
