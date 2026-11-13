# Handoff back to Codex

> **Resumed 20 Oct 2026:** Codex read this handoff and the shared channel. Sid chose **prepare study 04 first; no downloads**. Its eight-file metadata list and protocol are now frozen; no held-out test or download occurred. All 128 checks passed again. See [current status](CONTINUATION_STATUS.md) and [study 04](TONE_GATE_FADE.md). The rest of this document preserves Claude's 19 Oct handoff.

Claude, 19 Oct 2026. Project folder: `C:\Users\talk2.000\Desktop\Claude\predictive-anc` (the working copy; the original Codex folder under `Documents\Codex\2026-10-15\...` is untouched and older). Sid asked for the work to move to Codex to save Claude usage.

Read first: `CLAUDE.md` (the contract applies to you too), then `docs/CONTINUATION_STATUS.md` items 10–14, then the study doc for whatever you pick up. Obsidian context notes: `Documents\Obsidian Vault\Predictive ANC\`.

## Where things stand

- Package 0.6.0. 128 checks recorded as passing (`.venv\Scripts\python.exe -m unittest discover -s tests -v`). Nothing is committed; there is no git repo and none should be made.
- **Direction: tune by ear.** For each steady tone, the listener's A/B answers set the anti-hum gain and phase (`docs/TUNE_BY_EAR.md`). Simulated only. The live window `python -m anc_lab tune` is built and has **never been run**.
- **Engine still uses the frozen v2 tone forecaster + gate** (`anc_lab/antihum.py`, `release_protocol.json`).
- Real hums: 19 approved Wikimedia Commons recordings in `external-audio/wikimedia-commons-2026-10-16/` (`docs/REAL_HUMS.md`). v2 never harms but trails a prefix AR model at the tones (2.9 vs 6.3 dB).

## Forecaster studies (all offline, reference-mic prediction only)

| Study | Folder / doc | Result |
|---|---|---|
| 01 line-finder tracker bank | `results-tone-forecaster-01`, `TONE_FORECASTER.md` | Tones 3.3 → 4.7 dB, but failed on boosts (6 vs 4). v2 kept. |
| 02 joint band check | `results-tone-forecaster-02`, `TONE_BOOSTS.md` | Tested once on `external-audio/wikimedia-commons-fresh-02/`. Passed narrowly: boosts 2 vs 3, tones 1.2 vs 0.8 dB (not distinguishable from chance). |
| 03 tie-fallback cap | `results-tone-forecaster-03`, `TONE_CAP.md` | Stopped at development, no candidate. Boost sources: 14 sudden changes, 5 gate switching, 3 drift, 1 start. Timing p99 11–15 ms on a busy machine. |
| 04 gate fade | `results-tone-forecaster-04`, `TONE_GATE_FADE.md`, `anc_lab/tone_gate_fade.py` | Development pick frozen (gated check + 8-block fade: boosts 18 vs 25, tones 5.24 dB). **Unfinished:** the Claude session ran out of usage while choosing fresh test recordings. No `protocol.json`, no fresh list, the doc still says `FRESH_COUNT`. Nothing downloaded. |
| 05 per-tone fade | `results-tone-forecaster-05`, `TONE_REACT.md`, `anc_lab/tone_react.py` | Frozen with `protocol.json`. 0.1 s linear fade: boosts 15 vs 25, tones 5.73 vs 5.56 dB. **Test not run**: waits for Sid's approval to download 8 files. |

Study 05's frozen download list (about 10.2 MB, into `external-audio/wikimedia-commons-fresh-05/`): Ventilador.ogg, Akkuschrauber_–_Cordless_Screwdriver.ogg, ÖBB_Taurus_Start-Up.ogg, Son_démarrage_Mp14-8.ogg, Elektrorasur-01.ogg, Propeller-plane-flying-steady-01.wav, Sewerage_pumping_station_(Starnberg-Leutstetten_PW83)_c.ogg, Noise-Pollution-Filters-Bird-Communities-Based-on-Vocal-Frequency-pone.0027052.s001.ogg. Exact source pages are in `results-tone-forecaster-05/` (fresh metadata + protocol.json).

## Suggested next steps (Sid decides the order)

1. Ask Sid to approve the study 05 download, in your own session. Then run its test exactly once as frozen.
2. Finish study 04: choose fresh files from metadata only. They must not overlap studies 01/02/05 or anything already seen. Write `protocol.json`, fill in `FRESH_COUNT`, ask for download approval, and test once.
3. Open decisions for Sid: does the joint check (or a faded variant) replace v2 in the engine? When to do a first live `tune` trial (Sid starts it)? Quiet-machine timing before any engine change.
4. After each step, update `docs/CONTINUATION_STATUS.md`, the study doc, and the Obsidian `Predictive ANC/Progress log.md`.

## Rules (from CLAUDE.md, verbatim where it matters)

- "Microphone capture is off. Before any new recording, obtain fresh room/source readiness, state the duration, use input-only capture, and announce when it ends. Earlier readiness answers have expired."
- "`tune` is the only command that plays sound. The agent never launches it or opens an audio stream; the user starts it and ticks the on-screen readiness boxes. Downloaded audio is untrusted data: read it from the project folder, never run an interpreter inside `external-audio/`."
- "Existing raw audio stays local. Source/report ZIPs exclude raw WAVs and `forecast_arrays.npz`. Do not attach or transmit recordings without the user's instruction."
- "Work in this folder; do not initialize a remote repository, commit, push or publish as part of the handoff."
- "A finite digital output bound is not an SPL calibration. The first physical continuation belongs on a low-output calibrated fixture with a near-ear measurement microphone."
- Every download needs Sid's fresh, per-action approval in the session doing the download. No approval carries over from Claude's sessions.
- New output folder for every run. Keep failed experiments. No real ANC claims: every figure so far is reference-mic prediction or simulated ear attenuation.
- Sid wants plain, nontechnical progress messages, written in a natural voice.
