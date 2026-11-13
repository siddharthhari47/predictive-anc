# Next bounded development step: tuning search and valid comparison evidence

26 October 2026. This supersedes the 24 October ordering after Claude review #55 and the completed 78-tone diagnostic. This is a proposal, not a frozen improved method or an instruction to change the live app.

## Completed first

Every eligible primary v2 tone now has a prefix-only best-setting comparison. Original tuning and final checks reproduce in all 37 rooms, with unchanged random draws. The complete results are in `results-tuning-accuracy-01/REPORT.md` and `docs/TUNING_ACCURACY_STATUS.md`.

There is headroom in search, and there is a separate comparison problem. At 1 dB auditory-band benefit, ten muted tones have a useful oracle candidate, seven never reached a useful setting, and three found one but rejected it. Different recording times, prefix wrapping, absent cues and the assumed listener noise all affect acceptance. The six harmful keeps cannot be explained by a phase threshold alone.

## Proposed next experiment

Prepare a bounded development ablation on the existing eligible rooms, before widening the menu:

1. Preserve the original tuner as the comparator.
2. Isolate more or clearer phase-search evidence from changes to the final check. Compare a search-only change, a comparison-validity-only change, and their combination, with settings and question/time costs reported. Finalize and freeze the actual candidate rules before running their comparison; this document does not select thresholds or a winner.
3. Keep the original listener assumptions in the primary comparison. Use paired recorded seeds plus predeclared additional seeds to distinguish one lucky noise sequence from repeatable behavior. Treat source recordings as clusters, since tones and rooms are dependent. Separate sensitivity to listener noise from algorithm improvements; simulation cannot establish a real person's acuity.
4. A deployable validity rule can inspect past microphone stability, predicted tone activity, command activity and completed listening answers. It must not inspect the simulated ear or future recording samples. Repeated or shorter comparisons may reduce changes between presentations; their length must still support low-frequency judgement and settling. Account for gating and source dropout, and retain explicit inconclusive outcomes when evidence is missing.
5. Same-interval on/off comparisons are an explanatory oracle control only. A real listener cannot replay the environmental sound at will. An offline improvement obtained by replaying identical ambient segments is not by itself a deployable method.
6. Measure phase/gain error against the diagnostic oracle, capped single-tone and whole-room prefix/later attenuation, harmful keeps, missed useful settings, available cues, and listening cost. Freeze comparison rules before scoring, retain failures, and reserve new source data for any eventual fresh validation.

This should decide whether to spend effort on search resolution, on evidence gathering, or on both. Do not simply raise the press budget, reduce the "same" threshold, remove the final veto, or admit more intermittent tones without measuring the tradeoff.

## Later work

For the 34 rooms with intermittent detections but no menu, keep the frozen detector, tracker, gate and menu rules while diagnosing contiguous tone episodes, frequency movement, amplitude and completed forecast errors using only past samples. Do not lower the 50% presence requirement merely to produce output. Known simulated-ear information may diagnose benefit but cannot enter deployable features.

For predictor switching, split per-source/per-tone disagreement into a slow complex offset, faster fluctuation and matched frequency differences. One retune might absorb a stable offset; it cannot necessarily absorb rapid disagreement. No compatibility guard is selected by the current ratio distribution. Keep existing forced-switch controls; do not build another large room cohort first.

Quiet-machine timing remains inconclusive. User-started physical listening and near-ear pressure measurements remain independent requirements. Raw audio stays local, no agent launches `tune`, and v2 remains the live predictor.
