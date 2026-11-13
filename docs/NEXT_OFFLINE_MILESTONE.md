# Next offline milestone: preserve accuracy across new sources

> **Latest completed result, 21 Oct:** The fresh L2 test is complete: **pass frozen offline criteria**. 35/40 sources were scored, 25 with reference tones. Mean paired gain over v2 at 20 ms: **+0.536 dB**, 95% source-bootstrap interval **+0.121 to +1.043 dB**. Retain unchanged L2 as the leading offline chooser candidate. Next, measure its compute deadlines and tail latency without audio, with output parity first. Engine integration still requires timing and acoustic-path validation. Read [fresh-test status](SELECTOR_FRESH_STATUS.md). Earlier pending-test and median-stop statements below are historical.

Prepared 20 October 2026 after studies 04 and 05. Historical proposal, superseded on 21 October by the completed [selector-headroom audit](SELECTOR_HEADROOM.md).

**Current decision:** do not build this selector into the engine. Its hindsight window benchmark achieved only 0.28 dB paired median improvement over v2, below the prespecified 1 dB threshold; the three causal rules each achieved 0.00 dB. Investigate why the joint check gives away strong-tone accuracy. All previously used recordings may support that development work, but a later candidate requires a newly frozen independent test. Keep v2.

The [first follow-on diagnosis](JOINT_SETTING_DIAGNOSIS.md) is also complete. Its ten-setting comparison points to minimum tracker-memory restrictions; the next bounded experiment is to log the unchanged joint check's band powers and reasons for choosing each setting.

The original proposal below is retained as research history. Its oracle is a privileged benchmark for the specified choices and transitions, not a universal upper bound on other architectures.

The goal remains automatic prediction of unfamiliar steady tones. No frequency from the user's fan becomes a product constant. The 35–350 Hz analysis band and 20/120 ms forecast horizons remain the current experimental scope.

## What the completed tests tell us

The 100 ms per-tone fade reduced switching-related amplification on study 05's fresh synthetic change scenes: 25 to 14 scene-by-horizon cases compared with the joint check. It passed that study's frozen rules. However, a higher aggregate tone median did not mean it improved most sources: at 20 ms it beat v2 on two of the six tonal recordings and lost on four.

On the already-seen study-04 recordings, the unchanged per-tone fade scored a median 3.39 dB at the tones against v2's 6.46 dB, again two wins and four losses. This post-hoc check is diagnostic evidence of source dependence, not an independent validation test. The gate-fade candidate also failed study 04's tone criterion.

Keep v2 as the engine default. The fades are useful research components; neither result establishes a generally better predictor.

## Research question

Can a causal choice between a small number of predictors retain v2's strong sources while benefiting from another predictor when its *already-observed* forecast errors are lower?

Start with a narrow comparison: v2, the unchanged per-tone fade and zero output. Use original development recordings and synthetic development scenes for design. Treat all previously tested recordings, including studies 04/05, as seen diagnostic data from now on. A new choice needs a separately frozen, untouched source test.

AR remains a strong accuracy comparator. Its higher amplification counts in both new studies mean that adding it to an automatic selector needs an explicit, tested output guard. Retain the project's causal ML comparator, and report prefix-adapted ML separately from frozen weights transferred to unfamiliar sources. Adding a larger network is a separate hypothesis, not a substitute for this comparison.

## Causal design requirements

At sample time t, a selector can score a forecast made at t−h only when its entire target block has arrived. Maintain separate accounting for the two forecast horizons; the 120 ms forecast cannot be judged using a target that has not arrived. Give the selector no hindsight tone labels and no actual future playback jitter.

Use an explicit cold-start rule and zero-output fallback. Compare stable selection and smoothly changing weights on development data, because changing predictors can create the same switching energy that the fade studies measured. Any selected output must be evaluated after those transitions and its gate, not as the best of independently scored predictors.

Keep an oracle selector that sees future errors only as a clearly labeled hindsight benchmark for the specified design. It must never enter the candidate or its tuning features. The completed audit documents why its window objective does not provide a universal mathematical upper bound.

## Evaluation before another frozen test

1. Write the development rule before the formal development run. Specify the small candidate set, error history length, transition rules, numeric acceptance thresholds and compute budget.
2. Report paired per-source gains against v2, their uncertainty, the fraction of sources improved, and worst regressions. A difference between two aggregate medians alone is insufficient. Do not treat multiple windows from the same recording as independent sources.
3. Report zero-output, v2, joint check, per-tone fade and AR separately. Include tone-bin and whole-band prediction error, amplification counts, onset/stop behavior, and silence/broadband negative controls. Preserve failures.
4. Freeze any eligible candidate, its code hashes, source list, seeds, exclusions, missing-file rule and analysis before inspecting new test audio. Use new credited sources/capture sessions where identifiable. Metadata alone does not prove independent acoustic captures.
5. Run the new test once. Report all prespecified recordings, including those with no detected tones, and all missing files without replacing them after results are known.
6. If accuracy and amplification criteria pass, measure the whole streaming pipeline on an otherwise quiet machine. Include selector, predictor, gate, resampling and scheduling time; a component's p99 under an offline pool is insufficient.

## Returning to the ANC objective

Reference prediction is only one part of the system. The original simulator already explores assumed acoustic paths, output delay, jitter and mismatch. Replay a successful predictor through that simulator before any fixture work, retaining separate reference-error and simulated ear-pressure metrics.

Physical continuation requires synchronized reference and near-ear measurements, measured wired latency/clock behavior, and low calibrated output on a fixture. An unknown ear transfer function or independent playback-time error cannot be repaired by predicting the microphone waveform. Wireless follows only after measuring the actual device's timing variability.

No new recording, playback, engine promotion, or physical ANC claim is part of this plan.

Evidence: [current status](CONTINUATION_STATUS.md), [study 04 review](../results-tone-forecaster-04/CODEX_REVIEW.md), [study 05 review](../results-tone-forecaster-05/CODEX_REVIEW.md), [post-hoc cross-source check](../results-tone-crosscheck-20261020/REPORT.md), and [overall project plan](PLAN.md).
