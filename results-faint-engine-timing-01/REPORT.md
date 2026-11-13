# Faint engine timing in the real runner (6 November 2026)

Script `research-tools/faint_engine_timing.py`. Protocol frozen in `protocol.json` before anything was timed. No audio device was opened, and nothing was played or recorded.

## Question

Does the app engine still keep time inside the real `LiveRunner` at real-time pace once the faint-hum detector is added? The two arms are `smoothed` (the app default today, the control) and `faint` (`tune --engine faint`, the question). The 14 stored 30 s simulated rooms are seen data. There were two repetitions and 56 runs in all. The bars are the same as `results-engine-candidate-01/-02`: every quiet run needs an engine-step p99 under 5 ms and an `on_output` p99 under 5 ms, with at least 24 of 28 runs quiet.

## Result: fail for both arms

| | smoothed (default) | faint |
|---|---|---|
| Quiet runs | 25 of 28 | 23 of 28 |
| Quiet runs under 5 ms | 22 | 14 |
| Engine-step p99, quiet runs | 3.03 to 6.30 ms | 3.80 to 6.62 ms |
| Steps over 5 ms / over 10 ms (all runs) | 419 / 16 | 974 / 34 |
| Longest single step | 30.4 ms | 32.3 ms |
| Longest queue (limit 250 ms) | 60 ms | 80 ms |
| `on_output` p99, worst quiet run | 1.96 ms | 1.88 ms |

- **Faint fails twice over.** Nine of its 23 quiet runs miss the 5 ms bar, and it has too few quiet runs (23 against 24).
- **Smoothed fails too.** Three of its 25 quiet runs are over 5 ms (5.10, 5.94 and 6.30 ms). On 3 November the same engine design passed 28 of 28 (`results-engine-candidate-02`, 1.99 to 4.49 ms). This is the third mixed outcome for this design on this laptop: a fail on 31 Oct, a pass on 3 Nov, and a fail today. The 5 ms reserve sits inside the day-to-day spread of this machine.
- **Clean on everything else.** Live output equalled offline output on all 56 runs, and offline output was exact at chunk sizes 137, 480, 1024 and 1920. There were no thread errors, stale blocks, limiter stops or glitches. The longest queue was 80 ms, well inside the 250 ms limit.

## What the faint detector costs (descriptive, not a bar)

The detector adds a median of 0.24 ms to the mean engine step, from 1.16 to 1.40 ms. Across the 21 rooms where both arms ran quiet, it adds a median of 1.3 ms to the p99 (range −0.27 to +3.1 ms), and the p99 was higher with faint in 19 of those 21. Most of the extra cost falls in the occasional steps where both detectors update together.

## What this means

- In plain terms, the faint engine keeps up. It never fell behind, and the queue never came close to the limit. But it uses up more of the safety margin the frozen bar asks for, and it does not meet that bar.
- Nothing here measures sound, so this is not a claim about how it sounds.
- The app is unchanged: `smoothed` stays the default, and `faint` stays opt-in.
- Whether a missed reserve is audible can only be shown by running the window. Glitch counters stayed at zero here, but these are thread loops standing in for PortAudio callbacks.

## Caveats

- The rooms are 30 s long, and the faint detector needs about 9 s to lock, so it is fully active for only about the last two thirds of each run.
- The 5 ms bar is a reserve, not a measured need.
- This is one run on one machine. Preflight CPU was 3.9%, and background CPU per run ranged from 1.6 to 8.3%.
- The CPU clock read 1466 MHz at the start.
