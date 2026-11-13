# Engine candidate repeat: results

3 November 2026, Claude. Same frozen protocol, rule, inputs and code as `results-engine-candidate-01`, checked by hash. Launcher: `research-tools/engine_candidate_rerun.py`, written after the first result. No audio device was opened, `tune_app.py` was not changed, and no physical ANC is claimed.

## Result

**On this run the candidate passes the frozen rule. `v2` fails it, as before.**

| Arm | Result | Clean runs | Quiet runs | Quiet runs with p99 under 5 ms | Engine step p99 range (ms) |
|---|---|---:|---:|---:|---:|
| Candidate | pass | 28 of 28 | 28 of 28 | 28 of 28 | 1.99 to 4.49 |
| `v2` | fail | 28 of 28 | 28 of 28 | 0 of 28 | 5.73 to 8.46 |

**This does not cancel the 31 October fail.** The same test on the same code has now given one fail and one pass for the candidate. The honest reading is that the candidate clears the 5 ms reserve on a good day and can miss it on a worse one. The worst margin here is about 0.5 ms.

## Compared with 31 October

| Measure, quiet runs | Candidate, 31 Oct | Candidate, 3 Nov | `v2`, 31 Oct | `v2`, 3 Nov |
|---|---:|---:|---:|---:|
| Runs with p99 under 5 ms | 13 of 27 | 28 of 28 | 0 of 27 | 0 of 28 |
| Highest run p99 (ms) | 6.90 | 4.49 | 13.24 | 8.46 |

Candidate mean fell from 1.54 to 1.25 ms and pooled p99 from 5.60 to 3.99 ms. Blocks over 10 ms: none for the candidate and 22 for `v2`, out of 84,000 each. Blocks over 5 ms: 111 against 3,096.

Both arms improved, so something about the machine changed between the days. Which thing is still unknown.

## Everything else

- **Output:** matched exactly at all chunk sizes, offline and in every live run.
- **Faults:** no thread errors, stale blocks, limiter stops or glitches.
- **Callback:** `on_output` p99 at most 1.80 ms against the 5 ms bar.
- **Queue:** longest 90 ms for the candidate and 20 ms for `v2`, against the app's 250 ms limit. The candidate's was 40 ms on 31 October, so this was worse, and I have not looked into why.
- **Slowest single block:** 9.08 ms for the candidate and 11.47 ms for `v2`.

## Conditions

GLiREL finished first, and the timed runs ran from about 05:33 to 06:02 IST. The start check passed at 4.9%, close to the 5% limit. After that, median background was about 0.8 to 0.9% and the highest was 4.1%, so every run counted as quiet.

The laptop was plugged in at 100% battery on the Balanced power plan, with the CPU reporting 1,466 MHz at the start. The extra wait for the GPU job to end was mine and is not in the protocol. It can only have made the conditions quieter. All 56 runs finished in about 29 minutes, so the laptop did not sleep during timing.

## Limits

Two runs on one machine cannot give a rate of failure. The figures use seen recordings, and Python loops stand in for audio callbacks. The 5 ms bar is a reserve, not a measured need. The power state on 31 October was not recorded, so it cannot be compared. Moving the app to the candidate needs Sid's go-ahead.
