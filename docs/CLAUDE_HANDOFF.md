# Handoff to Claude Code

Prepared 16 October 2026, India time. This is a curated project brief and evidence map, not a verbatim chat export. No Claude session has yet acknowledged or accepted the handoff. Tool connections and conversational state do not transfer automatically.

The user clarified that they want the **Claude desktop app**, not a terminal CLI. Use the app's Code tab with Local and this project folder selected. The user can paste the contents of `CLAUDE_START_PROMPT.md` into the app. Keep progress and interaction in the app; the commands below document agent execution and reproducibility.

## User intent

Build a scientifically rigorous software-only predictive ANC project. Observe environmental noise through an existing laptop or phone microphone, predict its future waveform, and eventually emit time-aligned anti-noise through ordinary wired or Bluetooth earphones without built-in ANC. Start with stationary predictable narrowband fan/AC/engine hum. Sudden events and general unpredictable broadband noise are outside the initial scope.

The user's latest clarification is central: **the algorithm should automatically handle new steady tones, not be tuned only to their fan.** Automatic calibration/adaptation and a frozen ML model that transfers to unseen sources are different evaluation conditions. Preserve that distinction.

The engineering ambition is real, but a laptop microphone measures a reference signal, not ear pressure. Good forecasts do not remove the need to measure the acoustic transfer, physical sample age, output timing, jitter, earphone fit and near-ear residual. No physical ANC success has been established.

## Workspace and runtime

Working directory on this computer:

```text
C:\Users\talk2.000\Documents\Codex\2026-10-15\referenced-chatgpt-conversation-this-is-an\outputs\predictive-anc
```

Use the existing `.venv\Scripts\python.exe` from this directory. The environment was created with system site packages; it is machine-specific and excluded from ZIPs. `requirements-tested.txt` records NumPy 2.5.1, SciPy 1.18.0, matplotlib 3.11.1, scikit-learn 1.9.0 and threadpoolctl 3.6.0. `requirements-capture-tested.txt` records sounddevice 0.5.6 and its related packages. `pyproject.toml` declares installable dependency ranges and package version 0.3.0.

Claude Code 2.1.270 and its local executable were verified when preparing this handoff. No model or permission-mode override was applied. The local cross-Claude bridge had no other registered instance online at the time of inspection; this file-based handoff does not depend on that bridge.

There was no project Git initialization, commit, push, cloud deployment or published service during this work. Existing user configuration outside this directory was not changed.

## Read in this order

1. `CLAUDE.md` and this handoff.
2. `docs/CONTINUATION_STATUS.md`, `docs/GENERALIZATION.md`, `docs/PLAN.md`.
3. `docs/MODEL.md` and `docs/VALIDATION.md` for the acoustic/scientific contract.
4. The relevant experiment JSON and implementation before changing an algorithm. Narrative reports summarize those artifacts; they are not substitutes for checking code and metrics.

## Completed work and evidence

### Initial offline simulator

`anc_lab/experiment.py`, `signals.py`, `predictors.py`, `control.py`, `metrics.py`, `report.py`; outputs in `results/`.

- Three seeded synthetic scenes: stationary hum, drifting hum and hum with unpredictable broadband innovations/burst. The original generator uses 73/146/219 Hz; those are test-source parameters, not predictor input labels.
- Separate reference microphone and simulated ear disturbance, assumed primary/secondary FIR paths, regularized inverse, output saturation and fractional transport delay.
- 20 ms wired-like and 120 ms wireless-like delay examples, jitter and calibration mismatch. These are assumptions, not measured Bluetooth/device specifications.
- Causal phase/frequency tracking, direct ridge AR and a trained 64-unit tanh MLP; zero/no-control, naive inversion, filtered-x LMS with an additional simulated error mic, and a clearly noncausal future-reference oracle.
- 315 method/scene/seed/profile comparisons. Accurate fixed timing/path cases can attenuate simulated steady tones; 2 ms jitter strongly degrades that result. This establishes simulator behavior, not hardware ANC.
- Chronological 6/2/4-second train/validation/test partitions and a 2 kHz analysis rate.

### Real reference prediction: useful target not met

`anc_lab/assessment.py`, `assessment_report.py`, `capture.py`; `docs/GOAL_1_OUTCOME.md` records the decision.

Two 30-second microphone trials use 12/6/12-second train/validation/test partitions, forecast blocks starting at 20 and 120 ms, and a predeclared 6 dB prediction-error power improvement target in 35–350 Hz, also requiring full-reference NRMSE <= 1. Model choice comes from validation and includes zero.

1. `recordings/goal1_fan_01.wav` plus `.capture.json`; outputs in `results-goal1/`. The user later reported talking/music/other noise. Preserve it as a mixed-noise control.
2. `results-goal1-clean/reference.wav` plus `reference.capture.json`; user confirmed only the fan, quiet conditions and airflow away from the laptop. The capture had no reported callback errors or near-full-scale samples. **No tested predictor beat zero at either horizon.** Tracker test gains were about -0.19/-0.16 dB, AR -0.14/-0.10 dB, and MLP -1.23/-1.04 dB in the reporting band. All raw results are preserved.

The first feasibility experiment was completed, but its performance target was not achieved. Do not rewrite it as a successful ANC or prediction demonstration. Input latency was driver-reported as 22 ms and causal resampling added 5 ms; these do not establish physical sample-to-ear timing. `results-goal1/TIMING_NOTE.md` records timestamp limitations if present.

### Matched fan-off/on source study

`anc_lab/source_study.py`, `source_report.py`; `results-source-study-01/` and `docs/SOURCE_STUDY.md`.

New 30-second `fan_off.wav` and `fan_on.wav` captures used the same named laptop input at 48 kHz mono, with separate user readiness confirmations. Their capture hashes were rechecked during handoff preparation. No application/OS gain changes were made, but AGC/beamforming/suppression and effective gain are unverified.

Absolute digital spectra, without separate RMS normalization, showed 12.72 dB more recorded 35–350 Hz power with the fan on. Discovery used 12 seconds, confirmation the remaining 18, with nonoverlapping 2-second windows. Screening thresholds were recorded before capture: >=6 dB local prominence, >=6 dB on/off increase and >=80% confirmation persistence. Candidate bands are 40–42, 123–125, 164–166 and 329–331 Hz. The 41/124 Hz candidates passed 9/9 confirmation windows; 165/330 Hz passed 8/9.

These are spectral candidates only. Sequential off/on recordings cannot be coherently subtracted. Unknown input processing and the changing early off level limit source attribution. Fresh independent prediction data are needed. Do not turn these four frequencies into product constants or retroactively replace the failed broad-band prediction criterion.

### New-frequency automatic adaptation and frozen-ML transfer

`anc_lab/generalization.py`; `results-generalization-01/` and `docs/GENERALIZATION.md`.

Forty synthetic comparisons use three development frequency groups, three distinct held-out tonal groups and a broadband negative control. Each held-out source has a 6/2/4-second chronological split. Predictors do not receive the true frequency labels. The tracker detects up to three peaks from the prefix; adapted AR/MLP fit it. A pooled MLP trains on development sources only and keeps frozen weights on new sources, with prefix-based input scaling disclosed.

Across the three tonal cases and 20/120 ms horizons, test band prediction gains were:

| Method | Range |
|---|---:|
| Automatic tracker | 33.38 to 34.83 dB |
| Adapted AR | 33.25 to 34.45 dB |
| Adapted MLP | 32.24 to 33.03 dB |
| Frozen pooled MLP | -5.58 to -1.37 dB |

Validation selected the tracker for tonal cases and zero for broadband noise. All MLP fits reached the configured 180-iteration limit. There is one seed per case and the pooled model saw only three development groups. These are small synthetic diagnostics, not universal generalization evidence or a verdict on ML as a field. No acoustic path or output jitter is part of this particular diagnostic; the original simulator treats those separately.

## Current implementation limitation and next milestone

`estimate_tones` in `anc_lab/predictors.py` always returns up to three strongest peaks, with at least 12 Hz spacing. It can select noise peaks when fewer tones exist. The current validation-selected zero baseline is offline; there is no real-time tone-confidence or mute controller.

Proposed first continuation:

1. Reproduce the 26 scientific checks using the existing environment; inspect the fixed top-three detector and its callers. State any discrepancy before changing conclusions.
2. Design a **causal automatic tone-count/confidence selector** with thresholds chosen on development data. Handle silence, pure broadband noise, one/multiple tones, frequency drift, tone appearance/disappearance, mixtures and noisy references. Do not use the four real fan frequencies as constants.
3. Integrate it without rewriting old results or silently changing old benchmark definitions. Keep predictor and controller interfaces distinct; record warm-up, history length, calibration data and any lookahead explicitly.
4. Evaluate on fresh source/frequency groups, report false activations and missed tones, frequency error, prediction gain and full-reference NRMSE at both horizons, plus compute time. Include zero and the current tracker/AR/MLP baselines. Separate per-source adaptation from frozen-weight transfer.
5. Broaden neural training with grouped held-out frequencies/sources/sessions before claiming transfer. Do not keep adjusting settings on the current test cases. Further real recording requires new user readiness; physical output remains gated by `docs/VALIDATION.md`.

This proposed milestone is a continuation of the user's project, not a promise that it will meet a fixed performance number. Retain failure cases and explain what they rule out.

## Commands and data preservation

From the working directory, in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m anc_lab --help
```

Use a fresh output directory for any rerun, for example:

```powershell
.\.venv\Scripts\python.exe -m anc_lab generalize --out results-generalization-claude-01
.\.venv\Scripts\python.exe -m anc_lab benchmark --seeds 7 --scenes steady --out results-claude-check-01
```

Existing commands include `benchmark`, `report`, `devices`, `record`, `assess`, `trial`, `compare-sources` and `generalize`. New capture is not necessary for the first offline implementation step. The original `benchmark` command does not protect an existing output folder; always use a fresh name. Importing assessment files without a matching capture sidecar must remain clearly marked unverified.

Local raw microphone files are present. Source/report archives exclude `.wav` and `forecast_arrays.npz`; the synthetic example arrays and aggregate `spectra.npz` may be included. Reusing this same folder gives Claude access to the local evidence without uploading recordings. There is no need to move files or recreate the environment just to transfer context.

The default OS microphone may be Soundform ANC Wired Earbuds. Re-enumerate devices and select the unique Intel Smart Sound **Microphone Array** on Windows WASAPI; its former numeric index is not a durable ID. Do not open an output stream or start a new capture on the strength of earlier readiness messages.

## Handoff boundary

Codex prepared this handoff and is not running an audio capture or continuing implementation concurrently. The user chooses when to start Claude. Start from the files and saved evidence; request missing information only when needed. Do not assume access to the original chat, Codex-specific tools, its UI state or any Claude bridge listener.

Claude Code's official local-project and instruction-file behavior was checked against:

- https://code.claude.com/docs/en/desktop-quickstart
- https://code.claude.com/docs/en/quickstart
- https://code.claude.com/docs/en/memory

No settings import, credential migration, permission bypass or remote publication is required for this handoff.
