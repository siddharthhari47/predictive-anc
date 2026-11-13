# Selector headroom audit

> **Latest completed result, 21 Oct:** The fresh L2 test is complete: **pass frozen offline criteria**. 35/40 sources were scored, 25 with reference tones. Mean paired gain over v2 at 20 ms: **+0.536 dB**, 95% source-bootstrap interval **+0.121 to +1.043 dB**. Retain unchanged L2 as the leading offline chooser candidate. Next, measure its compute deadlines and tail latency without audio, with output parity first. Engine integration still requires timing and acoustic-path validation. Read [fresh-test status](SELECTOR_FRESH_STATUS.md). Earlier pending-test and median-stop statements below are historical.

21 October 2026. Status: completed once; the prespecified stop rule was triggered.

The hindsight window benchmark gained **0.28 dB** over v2 at the median of paired recording differences at 20 ms, below the **1 dB** threshold. The causal 2/4/8-second rules each gained **0.00 dB** at the paired median. Keep v2; stop this selector design and investigate the joint check's accuracy cost on strong hums.

The primary analysis contains 30 acoustic public recordings with tones, grouped into 26 credited authors. The full audit scored 39 public recordings, four personal recordings separately and 52 existing synthetic scenes. The 2-second rule reduced public recording-by-horizon band-boost cases from 23 to 17, but did not meet the accuracy criterion. This is useful protection evidence, not grounds for claiming no possible value in selection.

Eight targeted checks passed, and 2,426 comparable baseline metrics reproduced the saved results. The synthetic wandering/buzz scenes have no fixed tone-bin labels in this audit; their 160 former nominal-center tone metrics are disclosed as non-comparable, while their whole-band and third-octave metrics still match. The original frozen studies and model code remain unchanged.

Read the [completed report](../results-selector-headroom-01/REPORT.md) and [summary with uncertainty](../results-selector-headroom-01/SUMMARY.json). The sections below preserve the experiment's fixed design.

A [completed follow-on diagnosis](JOINT_SETTING_DIAGNOSIS.md) held all ten existing joint-check settings fixed on four strong sources. It points to minimum tracker-memory restrictions as the main accuracy cost in those cases. The next bounded step is to log why the existing check chooses those settings; no replacement has been selected.

This follows [Claude's review](CLAUDE_REVIEW_20261020.md). Before building a selector for the engine, measure whether choosing between the existing forecasts offers enough benefit. Keep v2 in the live engine.

## Fixed experiment

The audit lists all 40 previously downloaded public recordings from the original collection and studies 02, 04 and 05. One original file was previously documented as malformed and is excluded in advance, with its identity retained. The four earlier personal recordings are separate secondary controls. The 44 original development synthetic scenes and eight buzz scenes are also included. Nothing is downloaded, played or recorded.

Every recording is explicitly **seen/development data**. Earlier tests can inform this new development question; they cannot serve as independent validation of a new method. The primary statistic uses decoded acoustic public recordings with reference tones. Electrical/unknown-acoustic captures, non-tonal files, personal recordings and synthetic scenes still appear in the relevant secondary or amplification results.

Existing frozen arms: v2 + gate, joint check + gate, 100 ms per-tone fade + gate, zero output, and prefix-adapted AR as an accuracy comparator. Only **v2, per-tone fade and zero** are options for the selectors.

Three fixed causal rules use lookbacks of 2, 4 or 8 seconds. Each chooses the lowest past residual energy in 35–350 Hz, after a causal fourth-order Butterworth filter. A target block contributes only after its final sample has arrived; each prediction horizon keeps its own maturity accounting. A full lookback must be available. Before three seconds, the output is v2. Switching needs a 1 dB advantage and takes a 100 ms linear crossfade; no new choice is made during that transition. The final output is scored after both its inherited gate and the crossfade.

The recording prefix remains the first 40% for calibration and normalization, with scoring on the suffix, as in the earlier studies. Prefix processing is calibration replay, not a claim of deployable causal output before calibration completes. AR sees only its training prefix. Synthetic scoring uses the same final four seconds as earlier development. Reference tones are found with hindsight for scoring and the oracles only; causal choices never receive those labels.

## Hindsight benchmarks and the stop rule

The static oracle chooses the best single arm per recording and horizon using the scored error. The window oracle uses two-second windows and explicitly renders each 100 ms crossfade. Dynamic programming finds the minimum additive spectral error for that sequence of windows. A final tail shorter than half a second is merged into the preceding window.

There is a necessary qualification to the word “oracle”: two-second window losses are not identical to the overlapping whole-file Welch score. The window benchmark therefore also includes the best static arm as a predeclared fallback. It is a privileged reference for this particular family of selectors, **not a mathematical bound on every possible future selector**.

Primary statistic: median of the per-recording paired tone-gain differences against v2 at 20 ms, over acoustic public recordings with reference tones. Windows are not independent sources.

- If window-oracle headroom is **below 1 dB**, stop work on this selector design and diagnose the loss of the bank predictors on strong hums. This is an engineering decision for the tested choices, not proof that all selection is impossible.
- If headroom reaches **1 dB**, assess each fixed causal lookback. A plausible candidate needs at least 0.5 dB median paired gain, at least half the oracle headroom, no loss exceeding 1 dB on sources where v2 gains at least 3 dB, no additional recording band-boost cases, and no whole-band boosts.
- Report every lookback. This audit does not automatically promote a method or launch another download.

The 120 ms horizon, whole-band error, source-level losses, credited-author grouping, source cohorts, no-tone cases and synthetic changes are secondary evidence. Any later candidate still needs a newly frozen independent test. Neither “30 recordings” nor “20 tonal sources” alone guarantees statistical power.

## Integrity

The existing source/protocol files are unchanged. The new diagnostic lives in `anc_lab/selector_headroom.py`; it has eight targeted checks for completed-target accounting, future-data invariance, cold start, hysteresis, transitions and oracle optimization. Those checks passed before the protocol was written.

The new [protocol](../results-selector-headroom-01/protocol.json) freezes the diagnostic code hashes, all file identities, synthetic waveform hashes, metrics and decision rules. Per-case results and forecasts remain local. No original frozen test is being overwritten or reclassified as a new independent test.

All numbers are reference-waveform prediction metrics. Physical continuation still requires measured acoustic paths and low calibrated output with a near-ear measurement microphone; this audit does not authorize or launch a listening trial.
