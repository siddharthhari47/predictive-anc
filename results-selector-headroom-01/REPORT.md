# Is choosing between predictors worth building?

21 October 2026 · Seen-data development audit

**Stop this selector design; diagnose the bank predictors' loss on strong hums.**

The hindsight window benchmark offers **0.28 dB** median paired tone improvement over v2 at 20 ms. The prespecified threshold was **1.00 dB**. The three causal rules offer **0.00, 0.00, and 0.00 dB** for 2, 4 and 8 second histories respectively.

Scored 39 public recordings, four personal recordings separately, and 52 existing synthetic scenes. The primary statistic uses 30 acoustic public recordings with tones (26 credited-author groups). One known malformed public file remains disclosed below. All data were already seen. This is neither fresh generalization evidence nor measured ANC.

![Audit comparison](C:/Users/talk2.000/Documents/Codex/2026-10-15/referenced-chatgpt-conversation-this-is-an/outputs/selector-headroom-20261021/selector-headroom.png)

## Source-level evidence

| Method | Tone median at 20 ms | Paired gain vs v2 | Paired gain at 120 ms | Band boosts | Whole-band boosts | Strong-source losses >1 dB |
|---|---:|---:|---:|---:|---:|---:|
| Zero output | 0.00 | -2.59 | -2.91 | 0 | 0 | 14 |
| v2 | 2.59 | 0.00 | 0.00 | 23 | 0 | 0 |
| Joint check | 2.90 | 0.06 | 0.18 | 10 | 0 | 5 |
| Per-tone fade | 3.53 | 0.03 | 0.15 | 10 | 0 | 5 |
| Prefix AR | 3.85 | 2.18 | 1.22 | 66 | 12 | 7 |
| Past errors: 2 s | 4.75 | 0.00 | 0.00 | 17 | 0 | 0 |
| Past errors: 4 s | 4.64 | 0.00 | 0.00 | 18 | 0 | 0 |
| Past errors: 8 s | 4.05 | 0.00 | 0.00 | 19 | 0 | 0 |
| Hindsight: static | 5.14 | 0.03 | 0.15 | 12 | 0 | 0 |
| Hindsight: windows | 5.18 | 0.28 | 0.26 | 13 | 0 | 0 |

All gain columns are dB of reference-waveform prediction. The paired metric subtracts v2's score on each recording before taking the median. Boosts count public recording-by-horizon cases (78 total), including electrical/unknown-acoustic captures. Band boosts mean at least 1 dB amplification in any third-octave band; whole-band boosts mean more than 0.5 dB amplification. Strong sources have v2 tone gain at least 3 dB at 20 ms.

## Fixed causal rules

- **Past errors: 2 s:** Fails: paired median at least half db, half oracle headroom kept.
- **Past errors: 4 s:** Fails: paired median at least half db, half oracle headroom kept.
- **Past errors: 8 s:** Fails: paired median at least half db, half oracle headroom kept.

No hyperparameter was tuned after this protocol was written. AR and joint check are reported as comparisons and were never options in the selector. The practical rules use only fully arrived target errors, and all crossfades are scored.

## The strong sources Claude highlighted

| Source | v2 | Per-tone fade | Hindsight window | Causal 2 / 4 / 8 s |
|---|---:|---:|---:|---:|
| Mobile_lift_stage.ogg | 9.75 | 4.65 | 9.75 | 9.75 / 9.75 / 9.75 |
| Wiki_Motor_lancha.wav | 20.03 | 11.19 | 20.03 | 20.03 / 20.03 / 20.03 |
| Mil_Mi-8MTV-1_helicopter_starting_up.ogg | 5.59 | 2.14 | 5.59 | 5.59 / 5.59 / 5.59 |
| Photocopie.ogg | 7.33 | 6.75 | 7.33 | 7.33 / 7.33 / 7.33 |

## Cohorts and uncertainty

| Cohort | Tonal files | Window-oracle paired median | Causal 2 / 4 / 8 s paired median |
|---|---:|---:|---:|
| 2026-10-16 | 13 | 1.25 | 0.11 / 0.00 / 0.00 |
| former-test-02 | 5 | 0.00 | 0.00 / 0.00 / 0.00 |
| former-test-04 | 6 | 0.00 | 0.00 / 0.00 / 0.00 |
| former-test-05 | 6 | 0.11 | 0.00 / 0.00 / 0.00 |

The JSON includes both per-recording and credited-author-cluster bootstrap intervals. They describe this purposively collected, already-seen pool; they do not certify generalization. Author metadata also cannot establish independent acoustic capture conditions.

## Secondary controls

| Synthetic method | Late band-boost cases | Late whole-band boosts |
|---|---:|---:|
| Zero output | 0 | 0 |
| v2 | 45 | 0 |
| Joint check | 24 | 0 |
| Per-tone fade | 14 | 0 |
| Prefix AR | 75 | 7 |
| Past errors: 2 s | 32 | 0 |
| Past errors: 4 s | 34 | 0 |
| Past errors: 8 s | 37 | 0 |
| Hindsight: static | 31 | 0 |
| Hindsight: windows | 31 | 0 |

Synthetic counts are scene-by-horizon cases in the existing final-four-second windows. For the stochastic wandering/buzz scenes this diagnostic uses whole-band oracle loss and does not assign fixed reference tone bins. Earlier reports scored their nominal center frequencies; those tone-bin values are intentionally not compared as identical. Whole-band and third-octave baseline comparisons remain available.

Personal recordings (secondary, not pooled into the primary statistic):

- recordings/goal1_fan_01.wav: whole-band gains at 20 ms, v2 / causal 2 / 4 / 8 s = -0.00 / -0.00 / -0.00 / -0.00 dB.
- results-goal1-clean/reference.wav: whole-band gains at 20 ms, v2 / causal 2 / 4 / 8 s = 0.00 / 0.00 / 0.00 / 0.00 dB.
- results-source-study-01/fan_on.wav: whole-band gains at 20 ms, v2 / causal 2 / 4 / 8 s = 0.16 / 0.16 / 0.16 / 0.16 dB.
- results-source-study-01/fan_off.wav: whole-band gains at 20 ms, v2 / causal 2 / 4 / 8 s = 0.00 / 0.00 / 0.00 / 0.00 dB.

## Limits of the oracle

The static oracle sees the whole scored recording. The window oracle sees future errors, optimizes an additive two-second spectral objective, and includes actual 100 ms transitions. Its static fallback prevents a worse whole-file score than the best fixed arm. It is deliberately privileged, but is not a proof that no other architecture could exceed it. The 1 dB stop is a scoped development decision for this family, not an impossibility claim.

The practical rules minimize causal low-band energy; the hindsight benchmarks can also use the hindsight tone labels defining the primary metric. That information advantage is explicit.

## Integrity and next action

- 2426 available frozen-baseline metric comparisons match within numerical tolerance.
- Eight targeted checks passed before freezing: future-data invariance, complete-target accounting, cold start, hysteresis, sample ramps, oracle optimization and static fallback.
- All input, forecast-array, diagnostic-code, protocol and prior-result hashes were verified.
- Excluded in advance: Resident_air-conditioned_out_door_unit.ogg, already documented as malformed.
- Run time: 7.19 minutes. Parallel offline timing is not real-time qualification.
- **Next action:** Stop this selector design; diagnose the bank predictors' loss on strong hums.
- Keep v2. No downloads, recording, playback or engine changes occurred.
- Physical continuation still requires measured paths, timing and low calibrated fixture output.

[Protocol](C:/Users/talk2.000/Desktop/Claude/predictive-anc/results-selector-headroom-01/protocol.json) · [Full local evidence](C:/Users/talk2.000/Desktop/Claude/predictive-anc/results-selector-headroom-01/audit/results.json) · [Summary and uncertainty](C:/Users/talk2.000/Documents/Codex/2026-10-15/referenced-chatgpt-conversation-this-is-an/outputs/selector-headroom-20261021/summary.json) · [Claude's review](C:/Users/talk2.000/Desktop/Claude/predictive-anc/docs/CLAUDE_REVIEW_20261020.md)
