# Proposed next offline diagnostic

24 October 2026. Development proposal following the completed room test; **not a frozen benchmark, acceptance result or engine change**. Claude is being asked to challenge this scope. No new recordings or downloads are required for the first step.

## Question

Why does one air-compressor room become louder when the chooser uses a better microphone predictor with the old tuning, and how can the next test ensure that real output switches are exercised?

## 1. Diagnose existing evidence before changing anything

Use all three existing WWS_Aircompressor rooms, not only the harmful one. Read their saved traces, fixed settings and ear paths. Reconstruct parity with the frozen outcomes first. At the exact 30 ms lead, log each tuned tone's frequency, relative level, relative phase, gate state and availability for v2 and the bank, plus the emitted component and ear residual. Use common-time phasors and explicitly matched frequencies; do not compare phase when the relevant component is absent.

Cover the tuning prefix, the actual switch and the entire scored suffix. In the harmful room the switch is near 5.63 s and scoring begins at 25.44 s, so this is not solely a switch-edge question. Separate forecast bias from a tone disappearing, gate changes and frequency/menu mismatch. Use existing zero, v2-tuned/v2-output, v2-tuned/chooser-output and chooser-own-tuning outcomes. Any further intervention is labelled post-hoc development and saved separately.

Do not change predictor settings, selector thresholds, source inclusion or the completed benchmark. The diagnosis should yield a specific measured mechanism or an explicit unresolved finding, not a new winner selected from many retries.

## 2. Prepare an active-output stress test

Write a new protocol before generating or scoring its suffixes. Use automatically discovered random steady tones plus separately labelled drift cases through known source/mic/ear paths. Choose frequency ranges and seeds independently of the observed compressor frequencies. Ensure the prefix establishes useful nonzero tuning; count actual emitted-command exposure before suffix ear scores. Fix failure/exclusion reporting in advance so unsuccessful tuning is not silently discarded.

Keep two questions separate: forced switches exercise the renderer and fixed calibration under controlled phase/level mismatch; natural chooser switches exercise the decision rule. Forced transitions must never be counted as natural selector coverage. Include equal-predictor null controls, known phase-bias harm controls, v2-only and zero output. Keep the actual 30 ms/no-DC/ramped output convention and disclose whether decisions remain on 20 ms errors. Defer the exploratory 200 ms branch unless it answers a distinct question.

Report per-tone and whole-band changes, all amplification and clipping, and every switch window. A digital energy threshold is not an audibility or SPL claim. Do not keep adding cases until the completed experiment's six-source floor is reached; this must be a separate development experiment. A later fresh source test will still be needed.

## Timing and physical work

The quiet-machine compute gate remains pending. An alternating cached-v2/cached-chooser measurement is an optional contended diagnostic, not a substitute. Keep live v2 unchanged. Physical continuation needs the existing user-started procedure and calibrated near-ear measurement; this proposal opens no audio device.

## Review questions for Claude

Is the compressor diagnosis the cheapest next useful step, or is the prefix-tone menu the dominant integration obstacle? Does a two-part forced/natural switch stress test answer fixed-tuning compatibility without overstating real coverage? What single intervention would the diagnosis justify testing next, if any?
