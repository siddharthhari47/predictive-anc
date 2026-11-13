"""Consolidate completed evidence and current continuation notes without modifying frozen artifacts."""
from pathlib import Path
import shutil

ROOT = Path(r"C:\Users\talk2.000\Desktop\Claude\predictive-anc")
OUT = Path(r"C:\Users\talk2.000\Documents\Codex\2026-10-15\referenced-chatgpt-conversation-this-is-an\outputs\anc-studies-20261020")
BACKUP = ROOT / "research-tools/codex-20261020/docs-before-finalization"
BACKUP.mkdir(exist_ok=False)


def edit(path, transform):
    old = path.read_text(encoding="utf-8")
    new = transform(old)
    assert old != new, f"No update for {path}"
    shutil.copyfile(path, BACKUP / path.name)
    path.write_text(new, encoding="utf-8", newline="\n")


def replace_once(text, old, new):
    assert text.count(old) == 1, (old[:100], text.count(old))
    return text.replace(old, new, 1)


def status(text):
    old = next(line for line in text.splitlines() if line.startswith("Current direction (20 Oct):"))
    new = (
        "Current direction (20 Oct): Sid granted full autonomy and authorized necessary downloads. Both frozen "
        "tests completed once: study 04 failed its tone-gain criterion; study 05 passed all three criteria. "
        "Thirteen recordings were downloaded and verified (20.07 MB); three were unavailable after bounded "
        "HTTP 429 retries and were not replaced. A separate post-hoc check of study 05 on study 04's now-seen "
        "recordings showed source-dependent accuracy. The engine remains v2 because a broadly better replacement "
        "has not been demonstrated. The next offline research plan is "
        "[preserving accuracy across new sources](NEXT_OFFLINE_MILESTONE.md)."
    )
    text = replace_once(text, old, new)
    text = replace_once(text, "Completed evidence:", "Milestone history (dated preparation states are superseded by the completed results below):")
    text = replace_once(text, "**Fading tones in and out of the joint check (Claude, 19 Oct 2026; frozen, test waiting for the download).**",
                        "**Fading tones in and out of the joint check (Claude, 19 Oct 2026 development; tested 20 Oct below).**")
    text = replace_once(text, "The test runs once, after Sid approves the download into `external-audio/wikimedia-commons-fresh-05/`.",
                        "That was the 19 Oct frozen development state. After Sid's later download authorization, the test ran once on 20 Oct; its result is recorded below.")
    text = replace_once(text, "**Gate fade: fresh test prepared (Codex, 20 Oct 2026).**",
                        "**Gate fade: preparation record (Codex, 20 Oct 2026; subsequently tested below).**")
    text = replace_once(text, "Sid's instruction was **Prepare study 04 first; no downloads**. Neither study 04 nor 05 has download approval in this session. The v2 live engine is unchanged.",
                        "At this preparation stage Sid's instruction was **Prepare study 04 first; no downloads**. Sid subsequently granted full autonomy and necessary-download authorization; both tests are now complete. The v2 live engine is unchanged.")
    text = replace_once(text, "Next: complete the running study-05 frozen test and audit its saved scores, then publish the two-study summary locally. No playback or microphone stream is being opened; engine promotion depends on the results.",
                        "Next: develop and evaluate a causal predictor-selection hypothesis under [the next offline milestone](NEXT_OFFLINE_MILESTONE.md). "
                        "Studies 04/05 are complete and all their audio is now seen data. Do not rerun either frozen test or reuse its files as independent validation for a newly chosen method. "
                        "Physical continuation remains at the measured-path/fixture stage described in PLAN.md.")
    text += (
        "\n### 20 Oct: source-consistency diagnostic and current decision\n\n"
        "The unchanged study-05 per-tone fade was evaluated on the six already-scored study-04 recordings in a separate, "
        "explicitly post-hoc run. Median tone-bin gain at 20 ms was 3.39 dB, joint check 3.26 dB, and v2 6.46 dB. "
        "The fade beat v2 on two files and lost on four; band-boost cases were 5 for each method. All 30 baseline score "
        "comparisons reproduced the original study-04 values within numerical tolerance. This diagnostic does not "
        "alter either frozen primary outcome. See [cross-source report](../results-tone-crosscheck-20261020/REPORT.md).\n\n"
        "Study 05's higher fresh-set median (2.20 versus 0.85 dB) also corresponds to two paired wins and four losses, "
        "so it is not evidence of consistent improvement across sources. Fades reduce switching-related errors; "
        "source-general prediction is still the next problem. The engine stays v2 for that reason, not because "
        "download approval is pending. No playback or microphone capture occurred.\n\n"
        "Verification: both protocols and their 18 code hashes remained unchanged; the 13 input size/SHA-1/SHA-256 "
        "checks and saved-result receipts were audited. Three affected freshness/draw unit checks passed after the "
        "downloads (0.222 s). The full 128-check suite had passed earlier in this continuation (51.607 s); predictor "
        "source did not change afterward.\n\n"
        f"[Combined results and figure]({(OUT/'RESULTS.md').as_posix()}) · "
        "[Next offline research plan](NEXT_OFFLINE_MILESTONE.md).\n"
    )
    return text


edit(ROOT / "docs/CONTINUATION_STATUS.md", status)


def handoff(text):
    old = next(line for line in text.splitlines() if line.startswith("> **Resumed 20 Oct"))
    return replace_once(text, old,
        "> **Completed 20 Oct 2026:** Sid's later instruction granted full autonomy and necessary downloads, "
        "superseding the earlier preparation-only request. Both frozen tests ran once: study 04 failed its tone-gain "
        "criterion; study 05 passed all three criteria. Thirteen recordings were verified; three rate-limited files "
        "were omitted under the frozen missing-file rules. A separate post-hoc cross-source check found uneven gains, "
        "so the engine remains v2. No audio device was opened. Read [current status](CONTINUATION_STATUS.md), "
        "[study 04](TONE_GATE_FADE.md), [study 05](TONE_REACT.md), and "
        "[the next offline milestone](NEXT_OFFLINE_MILESTONE.md). The remainder preserves Claude's **historical "
        "19 Oct handoff**; its pending-test and per-download-approval statements are superseded for this authorized work.")


edit(ROOT / "docs/CODEX_HANDOFF.md", handoff)


def contract(text):
    text = replace_once(text,
        "Continue the existing research project; read `docs/CLAUDE_HANDOFF.md` first, then the code relevant to the next change. This folder is the working project, with local recordings and reports already present.",
        "Continue the existing research project; read `docs/CONTINUATION_STATUS.md` for current evidence and "
        "`docs/CLAUDE_HANDOFF.md` for the original brief, then the code relevant to the next change. "
        "This folder is the working project, with local recordings and reports already present.")
    old = "Latest verified state (19 Oct 2026, Claude):"
    new = (
        "Latest verified state (20 Oct 2026, Codex): studies 04 and 05 completed their frozen tests once. Study 04 "
        "failed the tone-gain criterion; study 05 passed its three criteria on seven fresh recordings and 84 synthetic "
        "scenes. Thirteen Commons recordings were downloaded with the user's explicit full-autonomy authorization; "
        "three rate-limited entries remain missing, without replacement. Both protocols and all frozen code hashes "
        "are unchanged. The full 128-check suite passed earlier in this continuation; three affected freshness/draw "
        "checks passed after downloading. A post-hoc cross-source check found the per-tone fade still behind v2 on "
        "four of six earlier sources, so the engine remains v2. No audio stream was opened. Read "
        "`docs/NEXT_OFFLINE_MILESTONE.md`, `results-tone-crosscheck-20261020/REPORT.md`, and the two `CODEX_REVIEW.md` "
        "files. Download permission is not a pending blocker for this authorized continuation; new microphone or "
        "physical playback steps retain the explicit workflow below.\n\n"
        "Historical verified state (19 Oct 2026, Claude; later outcomes above supersede pending-test statements):"
    )
    text = replace_once(text, old, new)
    text = replace_once(text,
        "After verifying the handoff, implement causal automatic tone-count/confidence selection and assess it on new source/frequency groups, including silence, broadband noise and source changes. A short new-source calibration is permitted but must be reported. The existing fixed top-three peak detector is the concrete limitation to improve. See the handoff for acceptance criteria and preserve existing benchmarks.",
        "Automatic tone-count/confidence selection is implemented. The next offline milestone is to preserve "
        "prediction accuracy across unfamiliar sources, using a causal predictor-selection hypothesis as described "
        "in `docs/NEXT_OFFLINE_MILESTONE.md`. It is a plan, not a frozen protocol. Studies 04/05 and the cross-source "
        "diagnostic are complete; keep their test data marked seen. Freeze new choices and use untouched sources "
        "before claiming improvement. A short source calibration is permitted but must be reported separately "
        "from frozen-model transfer. Preserve existing benchmarks and failed experiments.")
    return text


edit(ROOT / "CLAUDE.md", contract)

cross_note = (
    "\n## Post-hoc source consistency, 20 Oct\n\n"
    "The unchanged study-05 candidate was also run on study 04's six already-scored recordings in a separate "
    "diagnostic. Its 20 ms tone median was 3.39 dB versus joint check 3.26 dB and v2 6.46 dB; it beat v2 on two files "
    "and lost on four. All three methods had five recording-horizon band-boost cases. This was planned after the "
    "primary results and is not a new held-out test. No tuning occurred and the primary outcomes are unchanged. "
    "See [the diagnostic](../results-tone-crosscheck-20261020/REPORT.md).\n\n"
    "On study 05's own fresh set, the higher median likewise hides two paired wins and four losses against v2. "
    "Keep the engine at v2 while developing a source-general improvement; "
    "[next offline milestone](NEXT_OFFLINE_MILESTONE.md).\n"
)
edit(ROOT / "docs/TONE_REACT.md", lambda text: text + cross_note)

progress = Path(r"C:\Users\talk2.000\Documents\Obsidian Vault\Predictive ANC\Progress log.md")
edit(progress, lambda text: text + (
    "\n\n## 2026-10-20 — cross-source diagnostic and completed continuation\n"
    "- Both frozen studies are complete. 13 Commons recordings downloaded and verified (20,068,308 bytes); three "
    "HTTP-429 failures disclosed without replacements. Frozen protocols and predictor code are unchanged.\n"
    "- The unchanged 100 ms per-tone fade was tested on the already-seen six study-04 recordings, explicitly "
    "post-hoc: tone median 3.39 dB versus v2 6.46 dB, two paired wins/four losses, five band-boost cases each. "
    "All 30 comparator checks match the original scores. It does not change study 05's primary pass.\n"
    "- Keep v2. Fades help switching but do not yet improve accuracy consistently across sources. Prepared "
    "`docs/NEXT_OFFLINE_MILESTONE.md` for causal predictor selection; no new candidate or protocol frozen.\n"
    "- Three affected freshness/draw checks passed after downloads (0.222 s). The full 128-check suite had "
    "already passed before these runs; no predictor source changed. No playback, capture or physical ANC claim.\n"
    "- Combined report: `" + str(OUT / "RESULTS.md") + "`.\n"
))


def final_report(text):
    text = replace_once(text,
        "Both studies used frozen code, fixed comparison rules and fresh recording lists. The tests ran once. All gains below describe prediction of the recording microphone waveform, not physical ANC.",
        "Both studies used frozen code, fixed comparison rules and fresh recording lists. Each primary test ran once. "
        "**Per-tone fading passed study 05, but gains varied by source, so v2 remains the engine default.** "
        "All gains below describe prediction of the recording microphone waveform, not physical ANC.\n\n"
        "Downloaded and verified 13 of the 16 planned recordings (20,068,308 bytes, about 20.07 MB). Three "
        "remained unavailable after bounded Wikimedia HTTP-429 retries. The existing missing-file rules allowed "
        "omission; none was replaced or removed from the frozen protocol.")
    text = replace_once(text, "## Decision boundary",
        "## Why we are keeping v2\n\n"
        "Study 05's 100 ms per-tone fade reduced amplification cases on fresh synthetic sudden-change scenes "
        "from **25 to 14** compared with the joint check (36 scene-by-horizon cases). Recording band-boost cases "
        "stayed at **2 of 14**. Median tone gain rose to **2.20 dB**, compared with joint check **2.05 dB** and v2 "
        "**0.85 dB**. Yet on paired tonal files it beat v2 only twice and lost four times. A difference between "
        "aggregate medians is not the median improvement on individual sources; the small sample does not "
        "establish broad superiority.\n\n"
        "Study 04's gate fade reduced late synthetic amplification cases from **27 to 14** versus joint check "
        "(120 scene-by-horizon cases), but failed to retain v2's tone accuracy: **3.25 versus 6.46 dB**. "
        "Recording band-boost cases stayed at **5 of 12**. The parent joint check already had almost the same "
        "tone shortfall, so smoothing the gate alone did not solve it.\n\n"
        "A separate post-hoc diagnostic then evaluated the unchanged study-05 candidate on the six already-seen "
        "study-04 recordings. Its tone median was **3.39 dB**, versus v2 **6.46 dB**, with two paired wins and "
        "four losses. Both had five band-boost cases. This supports the source-dependence concern but is **not "
        "a new held-out test**. All 30 comparator checks reproduced the original score rows. "
        f"[Cross-source details]({(OUT/'cross-source-review.md').as_posix()}).\n\n"
        "Both AR baselines are reported in the detailed reviews. They sometimes predict tones better, but "
        "their higher amplification counts prevent choosing them on accuracy alone.\n\n"
        "## What the numbers mean\n\n"
        "Positive prediction gain means lower reference-waveform error relative to predicting zero. Tone figures "
        "are medians over recordings with reference tones; whole-band figures cover 35–350 Hz. Reference tones "
        "are identified with hindsight for scoring only. The causal predictors do not receive those future labels. "
        "The 20/120 ms values are forecast-horizon starts, not measured device latency or Bluetooth performance. "
        "A band-boost case has at least 1 dB amplification in any scored third-octave band. Large relative boosts "
        "can occur in nearly empty bands; neither dBFS nor these gains establishes ear-level SPL.\n\n"
        "## Decision boundary")
    text += (
        "\n## Next offline step\n\n"
        "Test whether causal selection between predictors, based only on already-observed forecast errors, can "
        "retain v2's strong sources while using the fade where it helps. The next experiment must emphasize "
        "paired source gains and amplification, with a new frozen test set. The plan also retains AR and "
        "causal ML comparisons and the path/timing steps needed to return to the ANC objective. "
        f"[Next milestone]({(ROOT/'docs/NEXT_OFFLINE_MILESTONE.md').as_posix()}).\n\n"
        "The current batch is complete. No predictor settings were retuned from these test results, no live engine "
        "change was made, and no microphone or playback stream was opened.\n\n"
        "## Verification\n\n"
        "- All 18 frozen code hashes per study and both protocol checksums match their pre-test records.\n"
        "- The 13 downloaded inputs match their frozen sizes/SHA-1 values, download SHA-256 receipts and test input hashes.\n"
        "- Saved-result medians and amplification counts were recomputed without rerunning the primary models.\n"
        "- Three affected freshness/draw unit checks passed after the downloads. The full 128-check suite passed "
        "earlier in this continuation; the predictor code has not changed since.\n"
        "- The comparison figure was visually inspected. The complete input/result integrity audit is in "
        f"[verification.json]({(OUT/'verification.json').as_posix()}).\n"
    )
    return text


edit(OUT / "RESULTS.md", final_report)
print("Current status, handoff, contract, study note, Obsidian log and final report updated.")
