---
tags: [anc, log]
---
# Progress log

Back to [[Predictive ANC]].

## 2026-10-16 — Claude takes over from Codex
- Read `CLAUDE.md`, the handoff and the start prompt.
- Copied the project into `Desktop\Claude\predictive-anc`; checked every file's hash against the original (all 88 identical). Original left in place.
- Built a fresh Python environment there; all **26 scientific checks pass**.
- Found the Obsidian vault empty, so started these notes as the project's running context.
- Started the [[Tone selector milestone]] (offline only).
- Built the automatic tone counter + mute switch; 7 new checks added (**33 pass**).
- Ran the first study → `results-tone-selection-01/`. Summary in [[Tone selector milestone]].
- Package version now 0.4.0 (it had been inconsistent: 0.2.0 vs 0.3.0).
- Built the faster tone-release path and a repeat study → `results-release-study-01/` (5 new checks, **38 pass**, version 0.5.0). Summary in [[Release milestone]].

## 2026-10-16/17 — real hums and tune-by-ear
- Sid asked for cancellation of what reaches the ear, usable by anyone with ordinary earphones. Agreed approach: **tune by ear** (the listener's answers set each tone's anti-hum). See [[Tune by ear milestone]].
- Downloaded 19 real hum recordings from Wikimedia Commons (approved; kept local) plus `soundfile` and `sounddevice`.
- Study 03 → `results-real-hums-01/`: frozen settings are safe on real hums but weak; AR predicts the tones better.
- Built the capped anti-hum engine, the tune-by-ear question sequence, and simulated rooms. Study 04 → `results-tune-by-ear-sim-01/` and `results-tune-by-ear-cues-01/`: helps only where one tone stands out.
- Built the live tuner window (`python -m anc_lab tune`). Found that the USB earbuds' clock drifts against the laptop mic's; added clock tracking (fixes it in simulation). **Not run on real devices.**
- 19 new checks (**57 pass**). Version 0.6.0. Docs: `docs/REAL_HUMS.md`, `docs/TUNE_BY_EAR.md`.

## 2026-10-18 — a better real-tone forecaster (study 05)
- Split the recordings by author before anything ran: 8 development, 10 test. Wrote the choice rule first. Noted plainly that every file was already scored in study 03, so the test isn't independent.
- Built per-tone tracker banks and a looser causal line finder (`anc_lab/tone_forecasters.py`), plus a develop → freeze → test command (`python -m anc_lab tone-forecaster`).
- Development round 1: line-finder versions best but too slow. Round 2 with a faster median (identical numbers) picked the bank + line finder. Both kept.
- First test attempt stopped before any score (fresh synthetic tones couldn't be drawn); one written amendment, then the test ran once → `results-tone-forecaster-01/test-02/`.
- Result: tones 3.3 → 4.7 dB (AR 7.2), better on all 8 tonal files, whole band better too, but 6 small third-octave boosts against v2's 4, so it **failed the frozen bar**. v2 stays. See [[Tone forecaster milestone]].
- 11 new checks (**68 pass**). Version unchanged (0.6.0). Doc: `docs/TONE_FORECASTER.md`.

## 2026-10-18 — removing the forecaster's small boosts (study 06)
- Worked only on development files and synthetic scenes; the study-05 test files where the boosts showed up were left alone.
- Found two causes: short tracker memories spreading noise into nearby bands, and the line finder picking up false lines between closely spaced harmonics.
- A per-band guard failed badly and is kept as a failed experiment (`anc_lab/tone_guard.py`). Trials are in `results-tone-forecaster-02/diagnosis/`.
- Wrote the choice rule, then ran development once: the joint band check (`anc_lab/tone_floors.py`) passed, cutting boosts from 4 to 1 and keeping about three quarters of the tone gain. Protocol frozen → `results-tone-forecaster-02/protocol.json`.
- 12 new checks (**80 pass**). Version unchanged (0.6.0). Doc: `docs/TONE_BOOSTS.md`.
- Sid OK'd the download. The 8 fresh Commons recordings went into `external-audio/wikimedia-commons-fresh-02/`, and all matched their checksums. The test ran once.
- Result: **passed both questions, narrowly.** 2 boosts against v2's 3; both are on the buzzing speakers, in nearly empty low bands. Tones 1.2 against 0.8 dB, which could be chance. The study-05 bank blew up on the Mars recording; the joint check stayed silent there. Engine unchanged; replacing v2 is Sid's call. See [[Tone boosts milestone]].

## 2026-10-19 — capping the joint check's fallback (study 07)
- Tried a ceiling on the joint check's fallback (`anc_lab/tone_cap.py`), on development material only, plus 8 new synthetic buzz scenes shaped like the study-06 failure. Seen test files left alone.
- Wrote the rule, then ran development once. **No cap passed**: caps of 1–3 dB removed no boosts, and 0.5 dB removed one but lost the tone gain. Protocol frozen with no candidate → `results-tone-forecaster-03/protocol.json`. **No test, no download.**
- Found where the remaining boosts come from: mostly sudden sound changes (the check is too slow) and the gate's on/off switching, not the fallback.
- 12 new checks (**92 pass**). Version unchanged (0.6.0). Doc: `docs/TONE_CAP.md`. See [[Tone cap milestone]].

## 2026-10-19 — fading tones in and out of the joint check (study 09)
- Asked whether the joint check can react faster to sudden sound changes and to the start of a file. Development material only; seen test files left alone.
- Diagnosis: **speed isn't the problem.** A perfect tracker switched on and off instantly gets about as many boosts as the check; the same tracker with a 0.1 s fade gets a third as many. The boosts come from switching tones in one block. Trials in `results-tone-forecaster-05/diagnosis/`.
- Built the joint check with per-tone fades (`anc_lab/tone_react.py`). Wrote the rule, then ran development once: the 0.1 s linear fade passed, **25 → 15 boosts** (7 on the change scenes against 14), tones kept (5.7 against 5.6 dB). Protocol frozen → `results-tone-forecaster-05/protocol.json`.
- Picked 8 fresh Commons recordings from their descriptions only, four of them sounds that start, stop or change speed. **Not downloaded: the test is waiting for Sid's OK.**
- 17 new checks (**128 pass**, with study 08's 19). Version unchanged (0.6.0). Doc: `docs/TONE_REACT.md`. See [[Tone react milestone]].


## 2026-10-20 — Codex resumes; gate-fade test prepared (forecaster study 04)
- Read the `predictive-anc` cross-claude channel and `predictive-anc-handoff-20261019`, then verified the current Desktop working copy against the handoff.
- Sid chose **Prepare study 04 first; no downloads**. Both study-04 and study-05 downloads remain paused.
- Reused the existing 19 Oct Commons metadata cache to choose eight machinery recordings (19.34 MB), with distinct credited authors and no name, checksum or author overlap with earlier sources or study 05. Tonality is still unknown; some captures are deliberate mixed/changing stress cases.
- Froze `results-tone-forecaster-04/protocol.json` once for the unchanged gated check + 80 ms cosine gate fade. Its 18 code hashes match development; 60 synthetic scene specifications reproduce. **No held-out waveform was generated or scored; no audio download, playback or microphone capture.**
- Resolved a handoff metadata-format mismatch using an explicit object input for study 04 and an identical bare-list mirror for study 05's guard. Both frozen code sets and study 05's protocol are unchanged.
- All **128 checks passed** again (51.607 s); three affected freshness/draw checks passed after preparation (0.221 s). Updated `docs/TONE_GATE_FADE.md` and `docs/CONTINUATION_STATUS.md`.
- Engine still v2; no new performance or physical ANC claim. Next is a fresh approval for an exact download batch, followed by that frozen test once. Quiet-machine timing and engine promotion remain pending decisions.


## 2026-10-20 — frozen forecaster study 04 tested once
- Sid authorized full autonomy and necessary downloads, superseding the earlier preparation-only direction.
- Study 04 did not pass all frozen questions on 6 fresh recordings and 60 fresh synthetic scenes. At 20 ms, median tone-bin prediction gain was 3.25 dB for the candidate, 3.26 dB for joint + gate, and 6.46 dB for v2 + gate. Recording band-boost cases: 5, 5 and 5, respectively.
- Missing inputs: Paisaje_sonoro_-_Aves_y_motor_de_auto.wav, Cogwheel_loco_Rigi_vsb.ogg. The frozen missing-file rule was followed; none was replaced. Source metadata, authorization and hashes are saved.
- The frozen runner executed once. A review recomputed its medians and boost counts from saved scores; no model rerun or retuning.
- No physical ANC claim or engine change; v2 remains in use. Reports: `results-tone-forecaster-04/REPORT.md` and `CODEX_REVIEW.md`.


## 2026-10-20 — frozen forecaster study 05 tested once
- Sid authorized full autonomy and necessary downloads, superseding the earlier preparation-only direction.
- Study 05 passed all frozen questions on 7 fresh recordings and 84 fresh synthetic scenes. At 20 ms, median tone-bin prediction gain was 2.20 dB for the candidate, 2.05 dB for joint + gate, and 0.85 dB for v2 + gate. Recording band-boost cases: 2, 2 and 2, respectively.
- Missing inputs: Noise-Pollution-Filters-Bird-Communities-Based-on-Vocal-Frequency-pone.0027052.s001.ogg. The frozen missing-file rule was followed; none was replaced. Source metadata, authorization and hashes are saved.
- The frozen runner executed once. A review recomputed its medians and boost counts from saved scores; no model rerun or retuning.
- No physical ANC claim or engine change; v2 remains in use. Reports: `results-tone-forecaster-05/REPORT.md` and `CODEX_REVIEW.md`.
