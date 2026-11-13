# Smoother timing, quiet rerun: results

31 October 2026, Claude. A repeat of `results-smoother-timing-01` on a quieter machine, with the same frozen protocol (sha256 `2d09de19…`), code hashes, inputs and rule. Offline engineering timing on simulated room microphones. No audio device was opened, and no physical ANC is claimed.

## Verdict

**Smoother: pass again. Whole engine loop: inconclusive again, because 3 of the 28 runs in each variant went over the 5% background limit.**

The start check passed this time at 2.1%, but the rule needs every run quiet, and the limit was crossed in brief spikes (5.1 to 14.3%). The frozen decision stands. The quiet runs still say a lot:

- **As the app runs today, the loop misses the 5 ms bar without any load to blame.** 10 of the 25 quiet runs had p99 over 5 ms, so a fully quiet repeat would be unlikely to pass.
- **With the taper cache, all 25 quiet runs were under 5 ms**, at 1.23 to 2.54 ms. So were the 3 runs that were not quiet.

## Timing (ms per 10 ms block)

28 runs per variant, 84,000 blocks each. Output matched after every run.

| Measure | `live` (as the app runs today) | `cached_dpss` (same output) |
|---|---:|---:|
| Quiet runs | 25 of 28 | 25 of 28 |
| Smoother p99, worst run | 0.023 | 0.020 |
| Smoother mean | 0.004 | 0.004 |
| Smoother slowest block | 5.1 | 0.5 |
| Smoother share of loop time | 0.7% | 0.8% |
| Loop p99 per run, range | 4.59–6.03 | 1.23–2.54 |
| Quiet runs under 5 ms | 15 of 25 | 25 of 25 |
| All runs under 5 ms | 17 of 28 | 28 of 28 |
| Loop median block | 0.35 | 0.35 |
| Loop mean block | 0.67 | 0.55 |
| Blocks over 5 ms | 1,011 | 14 |
| Blocks over 10 ms | 8 | 6 |
| Slowest block | 25.1 | 22.3 |
| Largest queue behind real time | 15 | 12 |
| Smoother decision | pass | pass |
| Loop decision | inconclusive | inconclusive |

Synthesis of 480 samples had a worst run p99 of 0.28 ms.

## What this means

- **The tone detector's taper work is the live engine's timing limit, not the machine's load.** Compared with the first run, the `live` p99 range barely moved at the low end (4.53 to 4.59 ms). Most runs sit just around the bar on a nearly idle machine, while the cache alone brings them well under it.
- **The smoother is not involved.** It added 19 of the 1,011 slow `live` blocks and none of the blocks over 10 ms.
- **The bar is a reserve, not a measured need.** A 5 ms miss does not mean the live app breaks. The worst queue was 15 ms against the app's 250 ms limit. Blocks of 22 to 25 ms still occur in both variants, more than twice the 10 ms block.
- **The cache would need its own check.** It is a research implementation, so its thread safety has not been tested.

## Deviations

`research-tools/smoother_timing_quiet_rerun.py` was written after `results-smoother-timing-01`. It only points the frozen benchmark at this folder and waits for quiet first. The frozen benchmark itself ran unchanged, so its hash checks still applied. `protocol.json`, `frozen.json`, `parity/` and `inputs/` are copies from the first run.

The first launcher asked for 2 quiet minutes in a row and was stopped because that was stricter than needed. It had timed nothing, and its folder was removed. The launcher that ran asks for 30 quiet seconds. The start was chosen for low load on purpose, and the split into quiet and not-quiet runs was made after the result. It changes no decision. This is the only rerun; it is not pooled with the first.

## Limits

- **Not measured.** Decimation, locks, the window, audio callbacks, device transport and any acoustic path.
- **Scope.** One machine, one schedule, CPython on Windows, 30 s of seen recordings.
- **Live app.** Unchanged. Neither `PhasorSmoother` nor the cache is connected to `tune_app.py`, and v2 and the original tuner stay live.
