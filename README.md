# Predictive ANC lab

> **26 October tuning diagnosis:** Claude review #55 is completed on all 78 eligible v2 tones. Six of 40 kept tones make their individual auditory band louder during tuning. Ten of 38 muted tones have at least 1 dB of potential prefix benefit, but only three had already found such a setting. Final checks can also mistake changing background sound for an anti-hum effect. Original tuning reproduces in all 37 eligible rooms. Keep v2 live; next isolate better search from better comparison evidence, before widening the menu. These are seen-data simulated-ear diagnostics; quiet-machine timing and physical ANC remain unvalidated. Read [current tuning diagnosis](docs/TUNING_ACCURACY_STATUS.md). Earlier next-step statements below are historical.

**24 October follow-up diagnostics:** Claude review #53 is tested. The compressor supports a bad accepted tuning setting: best v2/bank phases differ by 4.37 degrees, while accepted v2 is 152.58 degrees from its own prefix optimum. Of 72 primary rooms, 34 had intermittent detections below the menu rule, one had no detection, 11 were fully muted by the final listening check, and 26 kept active settings. Direct comparison of all 78 available recordings finds substantial predictor disagreement on real audio; fixed tuning cannot be assumed interchangeable. Prior room/fresh results remain unchanged. Keep v2 live; next diagnose menu eligibility and tuning acceptance, not a larger switch cohort. Quiet-machine timing and physical ANC remain unvalidated. See [the compatibility checkpoint](docs/SELECTOR_COMPATIBILITY_STATUS.md).


**Latest research, 21 October 2026:** The fresh L2 test is complete: **pass frozen offline criteria**. 35/40 sources were scored, 25 with reference tones. Mean paired gain over v2 at 20 ms: **+0.536 dB**, 95% source-bootstrap interval **+0.121 to +1.043 dB**. See [fresh-test report](results-selector-fresh-01/REPORT.md).

**A working offline research project, not a validated ANC product.** The engineering goal is software prediction of stationary fan/AC/engine tones using an existing reference microphone and ordinary earphones. The first deliverable tests whether prediction can survive output delay, timing uncertainty, and acoustic paths.

Open [the generated visual report](results/report.html), [initial findings and verification](docs/INITIAL_FINDINGS.md), [full experiment notes](results/REPORT.md), or [the project plan](docs/PLAN.md).

**The intended system adapts to new steady tones; it is not specific to this fan.** See [automatic adaptation versus frozen-ML transfer](docs/GENERALIZATION.md) and the [new frequency-group benchmark](results-generalization-01/REPORT.md). A short source-specific calibration and a model that transfers without weight updates are evaluated separately. No arbitrary-tone or hardware-ANC claim is made.

## Tune by ear: the current direction

A laptop microphone hears the hum, not what reaches your ear. For one steady tone, the difference comes down to two numbers, how loud and how shifted the anti-hum must be, and a listener can find both by answering "which is quieter?" questions. [TUNE_BY_EAR.md](docs/TUNE_BY_EAR.md) describes the procedure, its test in simulated rooms using [19 real hum recordings](docs/REAL_HUMS.md), and a live window for wired earphones:

```powershell
.\.venv\Scripts\python.exe -m anc_lab tune
```

It plays nothing until every readiness box is ticked and Start is pressed, caps the output, and stores no audio. It runs the smoothed engine by default; add `--engine v2` for the earlier one, or `--engine faint` (or `tune-faint.bat`) to also listen for weak, slightly wobbly hums such as a fan heard by a laptop mic. That option takes about 9 s to lock on and did not pass its frozen test (`results-faint-tones-02/REPORT.md`). It has not been tried by anyone yet. In simulation it helped only where one tone clearly stands out (13 dB at the tones on a ventilation recording, about nothing on most others), and its final check switches off any tone it cannot show to help. All quieting figures are simulated; nothing has been measured at an ear.

`tune --mic earbuds` (or `tune-earbud-mic.bat`, which also adds the faint detector) listens through the earbuds' own microphone, the input Windows calls "Headset Microphone (...)", instead of the laptop's. It is the earbuds' call microphone, not one inside the ear; it may filter out steady noise the way call microphones do, and it does not shorten the delay. Bluetooth hands-free microphones are never used. Nobody has listened through it yet.

`tune --mask` (or `mask-hum.bat`) opens a hum masker instead. It plays soft noise one hearing band wide around each hum it finds, so the hum stands out less, with a level slider and the same readiness boxes, output cap and time limit. It adds sound rather than cancelling anything, so earphone delay and pitch wander do not matter. Tested offline only; nobody has listened to it yet.

## Continue in the Claude desktop app

The user prefers the desktop app. Open Claude, choose **Code**, select **Local**, then **Select folder** and choose this project directory. Paste this into the app's prompt box:

> Read CLAUDE.md, docs/SELECTOR_COMPATIBILITY_STATUS.md and docs/CONTINUATION_STATUS.md. Continue the existing project from the latest completed result and its stated next step. Keep the continuation offline.

Read [the handoff](docs/CLAUDE_HANDOFF.md) for context. The app session uses the existing code, reports, local recordings and environment. The user does not need to start a terminal session. Preparing the handoff does not itself start Claude or record audio. See the [official desktop guide](https://code.claude.com/docs/en/desktop-quickstart).

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

A matching capture sidecar is required for the report's live-capture quality flag. Imported recordings without it still receive numerical metrics, with unverified provenance clearly marked. A local `.venv` with access to this machine's existing scientific packages and the optional capture dependency has been prepared; it is excluded from the downloadable source archive.

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

To regenerate just the report: `python -m anc_lab report --out results`.

## Research context

The brief continues the user's “DSP sound quality improvement” conversation: predict repeatable environmental noise and play synchronized anti-noise through existing earphones, eventually including Bluetooth. Only the prior user messages were readable in the imported preview; this project's explicit brief supplies the detailed scope. Prior assistant output was unavailable, so no technical claims from it were assumed.

Primary implementation references and their implications are recorded in [SOURCES.md](docs/SOURCES.md). This repository deliberately starts with stationary, narrowband conditions. Sudden events, general broadband cancellation, moving listeners, music mixing, phone deployment and wireless calibration remain future work.
