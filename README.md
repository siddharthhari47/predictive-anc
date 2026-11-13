# Predictive ANC lab

**A working offline research project, not a validated ANC product.** The engineering goal is software prediction of stationary fan/AC/engine tones using an existing reference microphone and ordinary earphones. The idea is that a steady hum repeats, so a program hearing it through a microphone could predict it a little ahead and play the opposite sound early enough to cover the earphones' output delay. The first deliverable tests whether prediction can survive output delay, timing uncertainty, and acoustic paths.

**Where it stands, 13 November 2026:** No real-world ANC has been demonstrated. All the gains so far are offline, scored on recordings and in simulated rooms built from real hum recordings, and even there the tuning sometimes makes the band around a hum louder instead of quieter. Live tries on 6 November against a room fan gave no quieting. That fan's 200 Hz hum sat only 2.5 dB above the noise in its band and wandered, so the best linear predictor removed just 1.9 dB of the band at a 50 ms look-ahead ([fan predictability](results-fan-predictability-02/REPORT.md)). The fan in the current room is a broadband whoosh with no hum the laptop microphone can find. The next test uses a steady 200 Hz tone from a phone as a stand-in hum: first an input-only recording through both microphones, then a `tune` session on it. A pure tone is the easiest case, so a failure there would point at playback or stability rather than prediction. The dated status notes that used to open this page are in [the README history](docs/README_HISTORY.md).

Open [the generated visual report](results/report.html), [initial findings and verification](docs/INITIAL_FINDINGS.md), [full experiment notes](results/REPORT.md), or [the project plan](docs/PLAN.md).

**The intended system adapts to new steady tones; it is not specific to this fan.** See [automatic adaptation versus frozen-ML transfer](docs/GENERALIZATION.md) and the [new frequency-group benchmark](results-generalization-01/REPORT.md). A short source-specific calibration and a model that transfers without weight updates are evaluated separately. No arbitrary-tone or hardware-ANC claim is made.

## Tune by ear: the current direction

A laptop microphone hears the hum, not what reaches your ear. For one steady tone, the difference comes down to two numbers, how loud and how shifted the anti-hum must be, and a listener can find both by answering "which is quieter?" questions. [TUNE_BY_EAR.md](docs/TUNE_BY_EAR.md) describes the procedure, its test in simulated rooms using [19 real hum recordings](docs/REAL_HUMS.md), and a live window for wired earphones:

```powershell
.\.venv\Scripts\python.exe -m anc_lab tune
```

It plays nothing until every readiness box is ticked and Start is pressed, caps the output, and stores no audio. It runs the smoothed engine by default; add `--engine v2` for the earlier one, or `--engine faint` (or `tune-faint.bat`) to also listen for weak, slightly wobbly hums such as a fan heard by a laptop mic. That option takes about 9 s to lock on and did not pass its frozen test (`results-faint-tones-02/REPORT.md`). Live tries with it on 6 November made a room fan no quieter. In simulation it helped only where one tone clearly stands out (13 dB at the tones on a ventilation recording, about nothing on most others), and its final check switches off any tone it cannot show to help. All quieting figures are simulated; nothing has been measured at an ear.

`tune --mic earbuds` (or `tune-earbud-mic.bat`, which also adds the faint detector) listens through the earbuds' own microphone, the input Windows calls "Headset Microphone (...)", instead of the laptop's. It is the earbuds' call microphone, not one inside the ear; it may filter out steady noise the way call microphones do, and it does not shorten the delay. Bluetooth hands-free microphones are never used. `tune` has not been run with it yet. Two input-only recordings through it on 12 November (`results-live-listen-03`, taken before the listener was ready, and `results-live-listen-04`) never showed a hum, though the fan in that room had none to show. In the first, 62% of the samples were exact digital silence, which looks like call noise reduction at work.

`tune --mask` (or `mask-hum.bat`) opens a hum masker instead. It plays soft noise one hearing band wide around each hum it finds, so the hum stands out less, with a level slider and the same readiness boxes, output cap and time limit. It adds sound rather than cancelling anything, so earphone delay and pitch wander do not matter. Tested offline only; nobody has listened to it yet.

## Notes for the AI agents

The hands-on work is done by AI coding agents (Codex and Claude Code). [CLAUDE.md](CLAUDE.md) and the handoff, status and review files in `docs/` are their working notes. CLAUDE.md also sets the project's rules: choices are frozen before untouched test data is scored, failed experiments are kept, the microphone is opened only after the listener says they are ready, and only `tune` plays sound, started by the listener.

## Goal 1: a real microphone experiment

The [first goal](docs/GOAL_1.md) was to establish a held-out prediction result on a 30-second fan recording. The [controlled fan-only repeat](results-goal1-clean/report.html) is now complete, after the [first trial](results-goal1/report.html) was identified as a mixed-noise control. Both trials are preserved. The clean trial did not meet the 6 dB prediction target at either horizon. The subsequent [matched source study](results-source-study-01/report.html) found four persistent spectral candidates near 41, 124, 165 and 330 Hz. These require a fresh prediction trial; they do not replace the earlier failed result or establish physical cancellation. Read [the source study](docs/SOURCE_STUDY.md) for provenance and limits.

Capture and evaluate a new trial with no playback:

```powershell
.\.venv\Scripts\python.exe -m anc_lab devices
.\.venv\Scripts\python.exe -m anc_lab trial --out results-new-trial --device "input device name" --source "fan, quiet room, no direct airflow"
```

Use a new output directory for each trial. Select the laptop microphone explicitly if the default input is a headset. The command records 30 seconds, saves raw audio and capture metadata, trains on 12 seconds, chooses the model on the next 6 seconds, and scores the last 12 seconds. Reported prediction-error improvement is not ear-level attenuation. Device indices can change after reconnecting hardware.

To evaluate an existing 30-second mono recording:

```powershell
python -m anc_lab assess --input recordings/fan.wav --out results-new-assessment
```

A matching capture sidecar is required for the report's live-capture quality flag. Imported recordings without it still receive numerical metrics, with unverified provenance clearly marked.

## Run it

From this project directory in PowerShell, with Python 3.10 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m anc_lab benchmark --out results
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

For a quick single-seed steady-hum run:

```powershell
python -m anc_lab benchmark --seeds 7 --scenes steady --out results-quick
```

For the separate automatic-adaptation / frozen-ML diagnostic on new synthetic frequencies:

```powershell
python -m anc_lab generalize --out results-new-generalization
```

For a matched real-source comparison with no independent level normalization:

```powershell
python -m anc_lab compare-sources --off path/to/fan_off.wav --on path/to/fan_on.wav --out results-new-source-study
```

Both source WAVs require matching live-capture sidecars. The comparison identifies candidate spectral lines, not forecast success or acoustic attenuation.

The supplied `results/` contains a completed default benchmark; `requirements-tested.txt` records the package versions used. No virtual environment is bundled. All commands are local. There are no service credentials or cloud dependencies.

## What is implemented

- Seeded 73/146/219 Hz hum, slow frequency/amplitude drift, and a negative control with strong broadband innovations and a surprise burst.
- Separate noisy reference microphone and simulated ear disturbance, including independent ear-local noise.
- Assumed primary and secondary acoustic FIRs, regularized path compensation, output saturation, fractional latency, correlated unknown jitter, and a calibration-mismatch case.
- A causal sinusoid phase/frequency tracker; direct multi-horizon ridge autoregression; and a fully trained, causal feed-forward neural MLP with 128 past samples and 64 tanh hidden units.
- No-control, delayed naive polarity inversion, normalized filtered-x LMS with an extra simulated near-ear error mic, and a clearly marked noncausal future-reference oracle.
- Chronological 6 s training / 2 s validation / 4 s test partitions, training-label embargo, train-only normalization, validation-only FxNLMS step selection, test prediction error and ear-level attenuation, per-tone metrics, clipping counts, seed ranges and a timing sweep.
- Input-only microphone recording and mono WAV replay. A replay recording is treated as a reference, then routed through **synthetic** ear paths; it cannot establish physical attenuation.

## Optional recording, with no playback

The initial v0.1 simulation uses generated noise. Goal 1 adds explicit real microphone capture; its separate reports are described above. To deliberately record locally:

```powershell
python -m pip install -e ".[capture]"
python -m anc_lab devices
python -m anc_lab record --out recordings/fan.wav --seconds 12 --rate 16000
python -m anc_lab benchmark --input recordings/fan.wav --out results-recording
```

Select a particular input with `--device 2` or `--device "device name"`. Use a new recording path; existing recordings are never overwritten. Do not assume the device named by the OS is the laptop microphone if a Bluetooth headset is connected. Capture is mono, has no speaker output, and records only when this command is run.

Replay requires at least 12 seconds of mono audio. It does not loop short recordings across train/test boundaries. Anti-alias resampling uses a causal FIR with its group delay retained. Offline normalization uses the training prefix only. If AGC, noise suppression or echo cancellation was enabled during capture, document it: these can alter phase, dynamics and predictability.

## Read the numbers correctly

`attenuation_db = 10 log10(mean(disturbance²) / mean(residual²))`. Positive values mean reduction; negative values mean amplification. Both arrays are dimensionless **simulated ear** pressures. This is neither calibrated SPL nor the reference microphone's noise reduction.

Prediction NRMSE compares future reference samples to predictions, independently of acoustic control. A better predictor may still produce worse ear residual if the playback time, path, gain, seal or position is wrong. The supplied 20/120 ms delays and 0.25/2 ms jitter cases are illustrative assumptions, not measured specifications of any device.

The baseline with an error microphone has additional sensing and adapts online. The oracle reads future reference data. These distinctions are shown in the report. The neural predictor is an initial comparator; no ML superiority is claimed.

**The benchmark and recording commands never play sound.** Only `tune` (0.6.0) does, after on-screen confirmation, with a hard digital cap. Neither that cap nor the benchmark's dimensionless saturation limit is a loudness calibration, and neither can set a safe earphone level. Any hardware continuation starts on a fixture, at low calibrated acoustic output, using a near-ear measurement microphone. See [the validation protocol](docs/VALIDATION.md).

## Project layout

```text
anc_lab/        generators, causal predictors, acoustic control, metrics, CLI, report
tests/          causality, timing, path, adaptation and replay checks
docs/           plan, mathematical contract, validation protocol, sources
results/        completed benchmark, JSON/CSV metrics, figures, local HTML report
```

To regenerate just the report after a benchmark run: `python -m anc_lab report --out results`. It reads `results/example_signals.npz`, which the benchmark writes and the repository leaves out.

## Research context

The project continues an earlier conversation titled “DSP sound quality improvement”: predict repeatable environmental noise and play synchronized anti-noise through existing earphones, eventually including Bluetooth. Only the questions in that conversation could be read, not the replies, so this project's own brief sets the detailed scope and no technical claims from the replies were assumed.

Primary implementation references and their implications are recorded in [SOURCES.md](docs/SOURCES.md). This repository deliberately starts with stationary, narrowband conditions. Sudden events, general broadband cancellation, moving listeners, music mixing, phone deployment and wireless calibration remain future work.
