# Engine candidate test: results

31 October 2026, Claude. Design: `docs/ENGINE_CANDIDATE.md`. Protocol: `protocol.json`, frozen with the code before any time was measured. Offline test on stored simulated room microphones, played at real-time pace through the app's own `LiveRunner`. No audio device was opened, `tune_app.py` was not changed, and no physical ANC is claimed.

## Verdict

**Fail by the frozen rule, for both the candidate and today's v2.** The candidate works correctly and is much faster than v2, but its engine step missed the 5 ms bar: only 13 of 27 quiet runs had p99 under 5 ms, and the worst was 6.90 ms. For v2, none of the 27 did (8.20 to 13.24 ms).

Everything except that bar came through clean. The machine was quiet this time, with 27 of 28 runs per arm qualifying, so load does not explain the miss.

## Output

The candidate's raw log and gate matched plain `AntiHumEngine`, and its smoothed log matched the offline smoother, on all 14 rooms at 4 chunk sizes (largest phasor difference 1.4e-16). After every paced run, the logs of both arms matched their offline references too.

## Paced runs

28 runs per arm, 84,000 blocks each, on 3 threads.

| Measure (ms) | `v2` (today) | `candidate` |
|---|---:|---:|
| Thread errors, stale blocks, limiter stops, glitches | 0 | 0 |
| Engine step p99 per quiet run, range | 8.20–13.24 | 3.54–6.90 |
| Quiet runs under 5 ms | 0 of 27 | 13 of 27 |
| Engine step median, all blocks | 1.24 | 1.27 |
| Engine step mean | 1.75 | 1.54 |
| Blocks over 5 ms | 4,224 | 1,716 |
| Blocks over 10 ms | 1,806 | 15 |
| Slowest engine step | 18.6 | 37.9 |
| `on_output` p99 per quiet run, worst | 2.02 | 1.96 |
| `on_output` slowest | 30.4 | 32.5 |
| Longest microphone queue | 20 | 40 |
| Forecast lead range | 50–90 | 50–90 |
| Decision | fail | fail |

`on_input` never took more than 2.2 ms. Anti-hum was being synthesized in about 75% of blocks in both arms; the output was discarded.

## What this means

- **The combination is correct.** It runs in the real runner on three threads with no error, and the app's own freshness check never fired. At no point did a forecast get near the 250 ms limit.
- **The app's real engine step is slower than the earlier single-thread timings.** The candidate's mean is 1.54 ms here against 0.55 ms pinned to one processor. The likely reasons are the three threads competing for Python's lock and the numerical threads no longer being limited, and the decimator is not part of this figure. This run did not separate them.
- **The candidate removes nearly all the over-10 ms blocks** (1,806 to 15). Its slowest single block and longest queue are worse than v2's (37.9 against 18.6 ms, 40 against 20 ms). That is the worst of 84,000 blocks, and it is not shown to be caused by the candidate.
- **The bar is a reserve, not a measured need.** This failure means the candidate does not meet the margin set in advance. It does not show that the app would break.

## Deviations

None to the frozen procedure. The minimum of 24 quiet runs was set after the earlier rerun, before any data here, and it did not affect the result.

## Limits

- **Stand-ins.** Python loops replaced PortAudio callbacks, and the 50 ms output latency is assumed, so the lead range is not a device measurement.
- **Scope.** One machine, one schedule, 30 s of seen recordings.
- **Live app.** Unchanged. v2 and the original tuner stay live. By this rule the candidate does not go in as it stands.
