# Runner slowdown diagnostic: results

2 November 2026, Claude. Tool: `research-tools/runner_slowdown.py`, written after `results-engine-candidate-01`. A descriptive check with no pass or fail, and no frozen rule. No audio device was opened, `tune_app.py` was not changed, and no physical ANC is claimed.

## Finding

**Most of the slowdown I could reproduce comes from waiting between blocks, not from the threads.** Giving the engine a 10 ms gap between blocks adds about 0.32 ms to each step, higher in 13 of 14 rooms. Adding the app's other two threads then adds about 0.05 ms. Limiting numerical threads and shortening Python's lock handover change nothing that matters.

**The "3 times slower" figure did not hold up.** Today the same three-thread setup averaged 1.04 ms, against 1.54 ms on 31 October, on a machine that was busier today. So the slowdown from the single-thread timing is about 1.6 times here, and an unexplained day-to-day difference is about as large as the effects measured.

## Load

GLiREL training started 9 minutes in and overlapped most of the run. Median background was 5.9 to 8.3% per setup, with peaks up to 32.9%. These are figures under load, not quiet-machine figures. The setup order rotated room by room, so comparisons between setups are fairer than the absolute numbers.

## Results

The candidate engine (smoother and taper cache) on the same 14 rooms, 3,000 blocks per room, 42,000 per setup. Times are ms per engine step.

| Setup | Mean | p99 | Blocks over 5 ms | Blocks over 10 ms | Runs with p99 under 5 ms |
|---|---:|---:|---:|---:|---:|
| One thread, no gap | 0.67 | 2.95 | 26 | 3 | 14 of 14 |
| Same, numerical threads limited to 1 | 0.64 | 2.57 | 16 | 1 | 14 of 14 |
| One thread, 10 ms gaps | 0.95 | 3.88 | 98 | 4 | 13 of 14 |
| Same, limited to 1 | 0.92 | 3.86 | 128 | 3 | 12 of 14 |
| Real runner, three threads | 1.04 | 4.00 | 131 | 3 | 14 of 14 |
| Same, limited to 1 | 0.97 | 3.69 | 95 | 2 | 14 of 14 |
| Same, lock handover 0.5 ms | 0.99 | 4.12 | 160 | 2 | 12 of 14 |

Paired change in each room's mean:

| Change | Median change (ms) | Slower in |
|---|---:|---:|
| Add 10 ms gaps | +0.32 | 13 of 14 |
| Add the other two threads | +0.05 | 10 of 14 |
| Limit numerical threads, no gaps | −0.02 | 3 of 14 |
| Limit numerical threads, in the runner | −0.04 | 4 of 14 |
| Shorten lock handover | +0.02 | 8 of 14 |

## What this means

- **The likely cause of the gap effect is that the code starts from an idle state each block,** with its core asleep and its caches cold. This run shows that the gap matters, not that mechanism.
- **My earlier guess was mostly wrong.** I suggested thread competition and numerical threads as the likely reasons. Neither moved the mean by more than 0.05 ms.
- **The 31 October verdict stands, but it looks less settled.** The frozen candidate result is still a fail. All 14 three-thread runs here were under 5 ms, yet one rule-based run on another day missed in 14 of 27. The two days are not directly comparable, because this run had no quiet rule and no `v2` runs in between.

## Not established

- **The cause of the day-to-day difference.** The laptop was plugged in today at a reported fixed 2.2 GHz. Its power state on 31 October was not recorded.
- **Waiting against extra work.** The tool logged the worker's CPU time, but Windows counts that too coarsely for short bursts, so those figures are not used.
- **Slowest blocks.** Maxima of 10 to 38 ms appear in all setups, with no pattern.

## Limits

One machine, one sitting, 30 s of seen recordings, under load. Python loops stand in for audio callbacks.
