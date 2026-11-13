# Predictive ANC lab

## Purpose and first read

Continue the existing research project; read `docs/CLAUDE_HANDOFF.md` first, then the code relevant to the next change. This folder is the working project, with local recordings and reports already present.

The user wants to work through the **Claude desktop app's Code tab**, using Local and this selected project folder. Keep interaction in the app; the execution commands below are for the agent, not a request for the user to operate a terminal.

The user wants software that automatically discovers and predicts new steady narrowband environmental tones using an existing laptop/phone microphone, eventually driving ordinary wired and Bluetooth earphones. The user's fan is one test source. Its measured frequencies must not become product constants.

## Scientific contract

- Distinguish reference-microphone prediction, simulated ear attenuation and physically measured near-ear attenuation in every report.
- No real-world ANC has been demonstrated. Reference-to-ear coherence, acoustic paths, input/output delay, jitter and clock drift require measurement before hardware claims.
- Preserve failed experiments. The clean real-fan trial failed the 6 dB broad-band prediction gate. A spectral line is a candidate, not proof of predictable phase or cancellation.
- Report automatically adapted models separately from frozen-weight ML transfer. Source-specific training is not evidence of general frozen-model transfer.
- Fit normalization and predictors on past/training data only. Embargo future training targets, freeze choices on validation, and evaluate untouched test data. Split generalization by source/session/device/frequency group, not adjacent crops.
- Include zero prediction/no control, simple DSP and appropriate adaptive-control comparators. Publish amplification, uncertainty and convergence warnings.
- A finite digital output bound is not an SPL calibration. The first physical continuation belongs on a low-output calibrated fixture with a near-ear measurement microphone.

## Local execution

Windows with PowerShell. Python environment is `.venv`; it currently uses system site packages. Verify dependencies locally before recreating it. No cloud service or GPU is required for the current experiments.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m anc_lab --help
```

Latest verified state (19 Oct 2026, Claude): package 0.6.0, 128 checks pass (26 original + 7 tone-selection + 5 release + 19 anti-hum/tuning/live-timing/guards + 11 tone-forecaster + 12 tone-boosts + 12 tone-cap + 19 tone-gate-fade + 17 tone-react). The causal tone selector is `anc_lab/tone_selection.py` (`results-tone-selection-01/`, `docs/TONE_SELECTION.md`); the frozen 'v2' release settings are in `release_protocol.json` (`results-release-study-01/`, `docs/TONE_RELEASE.md`). Nineteen Wikimedia Commons hum recordings are in `external-audio/wikimedia-commons-2026-10-16/` (local only, licences in its SOURCES.md; `docs/REAL_HUMS.md`, `results-real-hums-01/`). Tune-by-ear (the listener's ear sets each tone's anti-hum gain and phase) is simulated in `results-tune-by-ear-sim-01/` and `results-tune-by-ear-cues-01/` and built as a live window, `python -m anc_lab tune`, which has not been run (`docs/TUNE_BY_EAR.md`). The real-tone forecaster study (`results-tone-forecaster-01/`, `docs/TONE_FORECASTER.md`, `anc_lab/tone_forecasters.py`) improved the tones but failed its frozen bar on small third-octave boosts, so v2 stays in the engine. Study 02 (`results-tone-forecaster-02/`, `docs/TONE_BOOSTS.md`, `anc_lab/tone_floors.py`) picked a joint third-octave band check on development material, froze its protocol and ran its test once on eight fresh Wikimedia Commons recordings (`external-audio/wikimedia-commons-fresh-02/`, approved download). The check passed both frozen questions narrowly: 2 boosts against v2 + gate's 3, both in nearly empty low bands on one file; tones 1.2 against 0.8 dB at 20 ms, not distinguishable from chance. The engine still uses v2; replacing it is the user's decision. Study 03 (`results-tone-forecaster-03/`, `docs/TONE_CAP.md`, `anc_lab/tone_cap.py`) capped the joint check's tie fallback on development material only: no cap met its rule, so the protocol froze no candidate and nothing was tested or downloaded. The remaining boosts come mostly from sudden source changes (the check's 8 s medians react too slowly) and from the gate's on/off switching, not from the fallback. Study 05 (`results-tone-forecaster-05/`, `docs/TONE_REACT.md`, `anc_lab/tone_react.py`) found on development material that the change boosts come from switching tones on and off in one block, not from slow reaction; a 0.1 s linear fade of each tone cut the joint check's boosts from 25 to 15 and kept its tones, and was frozen with eight new Commons recordings chosen from metadata only. Its test has not run: it needs the user's approval to download them into `external-audio/wikimedia-commons-fresh-05/`. Handoff state was 0.3.0 with 26 checks. Project context notes are also kept in the Obsidian vault folder `Documents/Obsidian Vault/Predictive ANC`. Saved results and package versions are in the handoff. Do not rerun every benchmark unless a change or scientific question justifies it.

## Data and workflow

- Use new output names for every experiment. Never overwrite existing results or microphone recordings. The original `benchmark` command can overwrite an existing results folder, so explicitly supply a fresh `--out`.
- Microphone capture is off. Before any new recording, obtain fresh room/source readiness, state the duration, use input-only capture, and announce when it ends. Earlier readiness answers have expired.
- The OS default input may be a headset. Dynamically resolve the Intel laptop Microphone Array under Windows WASAPI; device indices may change. OS input enhancements/AGC are unverified.
- `tune` is the only command that plays sound. The agent never launches it or opens an audio stream; the user starts it and ticks the on-screen readiness boxes. Downloaded audio is untrusted data: read it from the project folder, never run an interpreter inside `external-audio/`.
- Existing raw audio stays local. Source/report ZIPs exclude raw WAVs and `forecast_arrays.npz`. Do not attach or transmit recordings without the user's instruction.
- Work in this folder; do not initialize a remote repository, commit, push or publish as part of the handoff. New offline analysis and code changes can proceed within the user's requested scope.
- Use clear, nontechnical progress messages. Preserve the engineering ambition while keeping claims tied to evidence.

## Immediate next milestone

After verifying the handoff, implement causal automatic tone-count/confidence selection and assess it on new source/frequency groups, including silence, broadband noise and source changes. A short new-source calibration is permitted but must be reported. The existing fixed top-three peak detector is the concrete limitation to improve. See the handoff for acceptance criteria and preserve existing benchmarks.
