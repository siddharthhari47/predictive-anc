# Goal 1 implementation verification

Verified on 15 October 2026:

- The explicit input-only recorder captured 30 seconds from the laptop's Intel Smart Sound microphone array through Windows WASAPI at 48 kHz. It did not use the headset, which was the system default input. The WAV and metadata SHA-256 agree.
- No speaker output was opened. The capture function uses an input stream only.
- The first recording has no reported stream errors or near-full-scale samples. The driver timestamp limitation is documented separately in `results-goal1/TIMING_NOTE.md`.
- The first real assessment uses 12/6/12-second chronological partitions, embargoes all training labels before the training boundary, freezes model selection on validation, then scores the held-out partition.
- Sixteen unit/regression checks pass, covering both the original simulator and new assessment causality, cycle wrapping, scoring signs, clipping visibility, training-only normalization, zero-baseline selection and quality gating. A rerun into an existing trial folder is rejected before the microphone opens, preserving the prior results.
- An end-to-end generated positive control returned over 41 dB low-band prediction-error improvement at both horizons. Its physical-provenance gate correctly remained false because it was not a live microphone recording. This run is stored under the workspace's `work/goal1-positive-control/` directory rather than presented as real-data success.
- The mixed-noise trial selected zero prediction at both horizons on validation. Its failed target remains in the report. User-reported conditions are preserved in `results-goal1/trial_notes.json`.

The controlled fan-only repeat is now complete in `results-goal1-clean/`. The user confirmed the required conditions before capture. It contains exactly 30 seconds at 48 kHz, with no reported stream errors or near-full-scale samples. WAV/capture/assessment hashes match, training targets remain inside the training partition, and predictor/assessment code hashes match the first trial. Both horizon selections chose zero prediction from validation. The performance target was not met.

The capture-and-evaluate experiment is complete; the useful-prediction gate remains unmet. See `GOAL_1_OUTCOME.md` for the decision and next source-characterization experiment. No new model changes were made, so the already-passing 16 regression checks were not repeated solely for a new data file.
