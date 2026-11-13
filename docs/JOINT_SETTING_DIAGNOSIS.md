# Joint-check accuracy diagnosis

> **Latest completed result, 21 Oct:** The fresh L2 test is complete: **pass frozen offline criteria**. 35/40 sources were scored, 25 with reference tones. Mean paired gain over v2 at 20 ms: **+0.536 dB**, 95% source-bootstrap interval **+0.121 to +1.043 dB**. Retain unchanged L2 as the leading offline chooser candidate. Next, measure its compute deadlines and tail latency without audio, with output parity first. Engine integration still requires timing and acoustic-path validation. Read [fresh-test status](SELECTOR_FRESH_STATUS.md). Earlier pending-test and median-stop statements below are historical.

21 October 2026. Completed offline follow-on to the [selector-headroom stop](SELECTOR_HEADROOM.md).

The underlying tracker bank retains most of v2's accuracy on the four strong sources examined. The large losses enter when the joint band check restricts the available tracker memories. This localizes the problem; it does not establish a replacement or prove why each past-error decision was made.

## Intervention and results

On the already-seen lift, motorboat, helicopter and copier recordings, hold each of the joint check's ten existing output settings fixed: minimum memory of 0, 0.05, 0.1, 0.2 or 0.4 seconds, each with extra line-finder tones allowed or excluded. All underlying tracking, internal per-tone choices, calibration prefixes and output gates remain unchanged. Compare with v2, the unrestricted bank and the adaptive joint check. This is a complete existing setting menu, not a search over new settings.

Tone-prediction gains at 20 ms, in dB:

| Output | Lift | Motorboat | Helicopter | Copier |
|---|---:|---:|---:|---:|
| v2 + gate | 9.75 | 20.03 | 5.59 | 7.33 |
| Unrestricted bank + gate | 10.16 | 20.33 | 5.49 | 6.96 |
| Adaptive joint check + gate | 4.90 | 8.61 | 1.61 | 6.82 |
| Fixed 0.1 s minimum, lines allowed | 7.84 | 16.60 | 5.19 | 7.03 |
| Fixed 0.4 s minimum, lines allowed | 3.72 | 2.84 | 1.61 | 6.32 |

Within each fixed memory setting, excluding extra line-finder tones changes tone gain by less than 0.42 dB on these four sources at 20 ms. The much larger losses come from restricting tracker memory. The helicopter's fixed 0.4-second setting exactly reproduces the joint check's 1.61 dB scored tone gain. These comparisons make memory restrictions the immediate investigation target.

The amplification tradeoff is real. With extra lines allowed, increasing the minimum from 0 to 0.4 seconds reduces the largest third-octave increase from 4.86 to 1.49 dB on the lift and 6.87 to 3.31 dB on the helicopter. On the motorboat it changes only from 6.12 to 6.08 dB while tone accuracy drops by 17.48 dB. This is reason to inspect the decisions, not to remove protection globally. Some boosted bands contain little reference energy; their relative dB changes are not ear-level SPL or perceived loudness.

All ten settings, both 20/120 ms horizons, tone error, whole-band error and per-band amplification are saved in [the full results](../results-joint-setting-diagnosis-01/results.json). The [tabulated report](../results-joint-setting-diagnosis-01/REPORT.md) includes every setting at 20 ms.

## What this establishes

- All 81 baseline/intervention consistency checks pass. The three original comparators reproduce saved study-04 metrics; the unrestricted fixed setting reproduces the original bank.
- The protocol was written before the diagnostic scores. The four sources were deliberately selected from earlier failures, so this is post-hoc development evidence.
- Holding a setting fixed removes the joint decision process and its setting transitions together. It does not isolate transition transients.
- A static winner chosen here would be hindsight tuning. No setting is promoted, no frozen result is overwritten, and the engine remains v2.
- No new downloads, recording or playback occurred. These are reference-microphone prediction metrics, not physical ANC.

## Next bounded experiment

Instrument the existing joint decision without changing its output. For each completed-target band check, log the candidate settings, their allowed/disallowed status, worst band, absolute reference and residual band powers in normalized digital units, total error, current setting and selected setting. Preserve the exact history/median and tie rules. Log enough history to explain a decision, rather than inferring it from a final histogram.

First require instrumented and original forecasts, settings and scores to match on these four cases. Then use the other already-seen recordings and synthetic change/negative controls to determine whether the strong-source losses are associated with nearly empty bands, stale history, genuinely increased error, or a combination. Do not call a relative-band test an SPL limit.

Only after that attribution should a changed guard be proposed with a small, explicit development menu and fixed accuracy/amplification criteria. Evaluate the actual transitioned and gated output, preserve v2 as a comparator, and require a newly frozen independent source test before claiming generalization. Source counts alone do not establish statistical power. Timing and measured acoustic-path work remain separate requirements for physical ANC.

Reproducibility: [diagnostic plan](../results-joint-setting-diagnosis-01/plan.json), [receipt](../results-joint-setting-diagnosis-01/receipt.json), and local runner copy under `research-tools/selector-headroom-01/`.
