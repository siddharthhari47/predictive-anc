# Chooser components: reconstruction check complete

22 October 2026. Offline reference-waveform reconstruction only. No new simulated-ear or physical ANC result.

The component adapter passed all **36 method/source comparisons** on 12 fixed, already-seen recordings and reproduced all 12 decision arrays exactly. Largest waveform difference: **3.35e-13** in normalized reference units, below the frozen 1e-9 absolute / 1e-8 relative tolerance. The unity-gain tone renderer, with DC explicitly removed, differed by at most 1.33e-15.

The fixed first-30-second inputs contain **10 / 7 chooser transitions** at the 20/120 ms groups, **100 / 70 mixed blocks**, and **1560 bank ghost-tone frames**. The minimum exercised-state coverage rule was **met**. Ghost counts describe bank state, including times its output may be muted; they do not assert audible ghost tones.

## What the adapter preserves

- Original causal v2 local frequency/phase/amplitude fits, fast release and DC term; original faded-bank per-horizon components, including fading-out ghosts.
- Independent matured-error gates and the exact sample-level three-arm chooser fade. No new fit to the mixed waveform and no changed chooser decisions.
- Component phasors are referenced to the newest input sample. Tested horizon indices are 41–60 and 241–260: first samples 20.5 and 120.5 ms after the origin. Arbitrary leads are rejected.
- A separate negative tone renderer applies each matched tone setting before summing predictor contributions. It excludes DC, retains separate frequencies, and explicitly selects hard gates or per-block ramps.

## Checks and their limits

Four targeted unit checks passed. They cover v2 fit/DC/release, deliberate gate differences and DC removal, distinct-frequency crossfades plus the zero arm, and a deliberately phase-reversed predictor switch. In that artificial last check, a setting that cancels the first predictor gives +6.02 dB amplification after switching to an opposite-phase predictor. This demonstrates that fixed tuning can be invalidated in principle and that the test detects it; it is not an observed L2 failure.

The adapter intentionally repeats a least-squares fit to expose v2 components. It is a diagnostic, not the measured timing implementation or a proposed production engine. The comparison uses already-seen clips and supports representation fidelity only. It does not establish tuning robustness, new-source accuracy, room generalization or real-time performance.

| Source | 20 ms transitions | 120 ms transitions | Ghost frames | Maximum reference error |
|---|---:|---:|---:|---:|
| fresh-001 | 0 | 0 | 26 | 2.12e-14 |
| fresh-002 | 0 | 0 | 28 | 1.38e-14 |
| fresh-004 | 0 | 0 | 326 | 5.48e-14 |
| fresh-005 | 4 | 2 | 115 | 3.29e-14 |
| fresh-010 | 1 | 1 | 120 | 3.35e-13 |
| fresh-021 | 1 | 1 | 90 | 2.38e-14 |
| fresh-018 | 1 | 1 | 17 | 3.44e-14 |
| fresh-025 | 1 | 0 | 63 | 1.72e-13 |
| fresh-026 | 0 | 0 | 86 | 2.1e-14 |
| fresh-035 | 1 | 1 | 350 | 4.52e-14 |
| fresh-007 | 0 | 0 | 17 | 0 |
| fresh-023 | 1 | 1 | 322 | 2.32e-14 |

## Remaining integration experiment

1. Reproduce the stored original v2 results for the 48 existing room/source draws, with their original 30/200 ms leads, seeds and prefix/suffix split. Keep this as a baseline reproduction, separate from the new 20.5/120.5 ms component mapping.
2. Freeze the new room runner, exact rendering convention and lead comparison before any candidate ear scores. Make hard-gated reference-preserving tone output and block-ramped integration output explicit separate conditions; neither silently inherits the fresh waveform pass.
3. Tune each method using only the calibration prefix, keep settings fixed for the scored suffix, and include v2 settings reused on the chooser as a diagnostic. Freeze source-group aggregation, switch-coverage requirements and harm limits first. Preserve no-tone/muted rooms and include deliberately biased/no-switch controls.
4. Report simulated-ear tone and whole-band attenuation, every amplification/clipping case and windows around switches. No retuning per switch. The study must disclose inadequate switching coverage rather than claiming safety from ties.

The new room experiment has **not run**. The original room simulator and live v2 engine are unchanged. The quiet-machine timing gate also remains unresolved; no engine promotion is proposed.

## Receipts

- Protocol SHA256: `07b7378160aa583b599cbd95604372423b1a5d49c8ad915fb1118d422b47a8ad`.
- Results SHA256: `27a776a2c62cdf6db8824788348ca8291b9b0694817d881fa4539e4e7bd0808d`.
- 75 saved-result/frozen-dependency checks passed. No full test-suite rerun is claimed.
- Reports contain only summaries; original media and waveform arrays remain local.
