# Handoff back to Codex

> **28 October: ownership.** Sid moved hands-on work back to Claude (Codex subscription ending). Codex was asked on channel `predictive-anc` (#71) to start nothing new. Claude now runs experiments here; Codex's `Documents\Codex\...` outputs are a frozen historical record. The latest result is the 26 Oct tuning-accuracy diagnosis (`results-tuning-accuracy-01/`); the next step is the search-versus-comparison ablation in `docs/TUNING_DIAGNOSTIC_NEXT.md`.

> **26 October tuning diagnosis:** Claude review #55 is completed on all 78 eligible v2 tones. Six of 40 kept tones make their individual auditory band louder during tuning. Ten of 38 muted tones have at least 1 dB of potential prefix benefit, but only three had already found such a setting. Final checks can also mistake changing background sound for an anti-hum effect. Original tuning reproduces in all 37 eligible rooms. Keep v2 live; next isolate better search from better comparison evidence, before widening the menu. These are seen-data simulated-ear diagnostics; quiet-machine timing and physical ANC remain unvalidated. Read [current tuning diagnosis](TUNING_ACCURACY_STATUS.md). Earlier next-step statements below are historical.

> **24 October follow-up diagnostics:** Claude review #53 is tested. The compressor supports a bad accepted tuning setting: best v2/bank phases differ by 4.37 degrees, while accepted v2 is 152.58 degrees from its own prefix optimum. Of 72 primary rooms, 34 had intermittent detections below the menu rule, one had no detection, 11 were fully muted by the final listening check, and 26 kept active settings. Direct comparison of all 78 available recordings finds substantial predictor disagreement on real audio; fixed tuning cannot be assumed interchangeable. Prior room/fresh results remain unchanged. Keep v2 live; next diagnose menu eligibility and tuning acceptance, not a larger switch cohort. Quiet-machine timing and physical ANC remain unvalidated. Read [current compatibility status](SELECTOR_COMPATIBILITY_STATUS.md). Earlier next-step statements below are historical.


> **Latest completed result, 21 Oct:** The fresh L2 test is complete: **pass frozen offline criteria**. 35/40 sources were scored, 25 with reference tones. Mean paired gain over v2 at 20 ms: **+0.536 dB**, 95% source-bootstrap interval **+0.121 to +1.043 dB**. Retain unchanged L2 as the leading offline chooser candidate. Next, measure its compute deadlines and tail latency without audio, with output parity first. Engine integration still requires timing and acoustic-path validation. Read [fresh-test status](SELECTOR_FRESH_STATUS.md). Earlier pending-test and median-stop statements below are historical.

> **Latest follow-on, 21 Oct 2026:** the [joint-setting diagnosis](JOINT_SETTING_DIAGNOSIS.md) is complete on four already-seen strong sources, all ten existing settings, and three controls. All 81 consistency checks pass. Minimum tracker-memory restrictions explain most of the accuracy cost in those cases; amplification protection still has value. Next: log why the unchanged joint check chooses each setting, with forecast parity first. No replacement is selected.

> **Completed 21 Oct 2026:** Claude's review was followed by a frozen selector-headroom audit. Across 30 already-seen acoustic tonal recordings, the hindsight window chooser gained only **0.28 dB** over v2 at the paired median, below the **1 dB** stop threshold. All three causal rules gained **0.00 dB**. Stop this selector design and investigate the joint check's strong-hum losses; keep v2. The full audit includes 39 public recordings, four personal controls and 52 synthetic scenes, with eight new targeted checks passing and 2,426 comparable baseline metrics reproduced. Read [the completed audit](SELECTOR_HEADROOM.md) and [current status](CONTINUATION_STATUS.md). All reused recordings are development data. No new download, recording or playback was needed.

> **Completed 20 Oct 2026:** Sid's later instruction granted full autonomy and necessary downloads, superseding the earlier preparation-only request. Both frozen tests ran once: study 04 failed its tone-gain criterion; study 05 passed all three criteria. Thirteen recordings were verified; three rate-limited files were omitted under the frozen missing-file rules. A separate post-hoc cross-source check found uneven gains, so the engine remains v2. No audio device was opened. Read [current status](CONTINUATION_STATUS.md), [study 04](TONE_GATE_FADE.md), [study 05](TONE_REACT.md), and [the next offline milestone](NEXT_OFFLINE_MILESTONE.md). The remainder preserves Claude's **historical 19 Oct handoff**; its pending-test and per-download-approval statements are superseded for this authorized work.

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
