# Smoother timing: results

31 October 2026, Claude. Design: `docs/SMOOTHER_TIMING.md`. Protocol: `protocol.json` (sha256 `2d09de19…`), frozen with the code before any time was measured. Offline engineering timing on simulated room microphones. No audio device was opened, and no physical ANC is claimed.

## Verdict

**Smoother: pass. Whole engine loop: inconclusive, because the machine was busy.**

The smoother is not a timing problem. Its p99 is about 0.03 ms against a bar of 0.5 ms, and it takes under 1% of the loop's time. Whether the whole loop meets the 5 ms bar on a quiet machine is still unknown, as it has been since the 22 October timing study.

All three quiet checks failed, at 29.7%, 13.4% and 12.3% whole-machine CPU against a limit of 5%. Other work was not stopped, so no run qualifies as quiet.

## Output first

The streaming smoother matched the offline one on all 14 rooms and both variants (largest phasor difference 1.8e-16), and again after every timed run.

## Timing (ms per 10 ms block)

28 runs per variant, 84,000 blocks each. A p99 means 99% of blocks finished within that time; it is not a limit on the slowest block.

| Measure | `live` (as the app runs today) | `cached_dpss` (same output) |
|---|---:|---:|
| Smoother p99, worst run | 0.030 | 0.028 |
| Smoother mean | 0.004 | 0.005 |
| Smoother slowest block | 1.3 | 8.0 |
| Smoother share of loop time | 0.6% | 0.8% |
| Loop p99 per run, range | 4.53–6.86 | 1.23–3.84 |
| Runs under 5 ms | 8 of 28 | 28 of 28 |
| Loop median block | 0.37 | 0.38 |
| Loop mean block | 0.70 | 0.57 |
| Blocks over 5 ms | 1,562 | 51 |
| Blocks over 10 ms | 25 | 17 |
| Slowest block | 85.0 | 34.1 |
| Largest queue behind real time | 75 | 24 |
| Smoother decision | pass | pass |
| Loop decision | inconclusive | inconclusive |

Synthesis of 480 samples, which belongs to the output callback, had a worst run p99 of 0.23 ms.

## What this means

- **The smoother adds almost nothing.** Over all `live` blocks the engine alone has p99 5.38 ms and 1,551 blocks over 5 ms; with the smoother it is 5.39 ms and 1,562. The 11 extra blocks were already just under the line.
- **The slow blocks are the tone detector, as in the earlier study.** The taper cache removes most of them, with identical output. Under the same load it brought every run under 5 ms. That is an observation on a busy machine, not a pass. These sequential runs share changing load, and the cache is a research implementation that would need its own thread-safety check.
- **The worst queue stayed under the app's limit.** At 75 ms it is under the 250 ms at which the app stops playing old forecasts. This was one busy run, not a guarantee, and it does not cover decimation, locks or the audio callbacks.
- **Rare long stalls remain in both variants.** The slowest smoother blocks (1.3 and 8.0 ms) are about 300 and 1,700 times the mean. The likely cause is the system pausing the process, but this run cannot establish that.

## Deviations

`research-tools/smoother_timing_recheck.py` was written after the result. It recomputes the figures above from the raw per-block times, adds the engine-alone comparison and changes no decision. All frozen decisions match `SUMMARY.json`. Before the freeze, a test-data mistake in `tests/test_smoother_timing.py` was corrected; the smoother code did not change.

## Limits

- **Not measured.** Decimation, locks, the window, audio callbacks, device transport and any acoustic path.
- **Scope.** One machine, one schedule, CPython on Windows, 30 s of seen recordings.
- **The 5 ms bar is a reserve, not a measured need.**
- **Live app.** Unchanged. `PhasorSmoother` is not connected to `tune_app.py`, and v2 and the original tuner stay live.
