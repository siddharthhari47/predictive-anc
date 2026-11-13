# Smoother timing

31 October 2026, Claude. Design note for `results-smoother-timing-01`, frozen with the code before any time was measured. No audio device is opened, and the live app stays on v2.

## Why

SD-s30 passed its fresh simulated test, but the smoother has only run on finished logs. The live engine would have to run it block by block, alongside everything else in a 10 ms block.

## What was built

`PhasorSmoother` in `anc_lab/smoother_timing.py` does the same arithmetic one block at a time. It wraps the unchanged engine, so the error gate still sees the raw tones and only the renderer's copy is smoothed. `tune_app.py` is not changed.

## Inputs

The simulated room microphone for the first 30 s of the first eligible room of each of the 14 sources in `results-tuning-fresh-02`. These recordings are already seen; timing does not need fresh ones.

## Output first

The streaming output must match the offline smoother on every room before a time counts, and again after every timed run. A timing with a parity failure stops the run.

## Measured

Two repetitions on one logical processor, with numerical threads limited to one.

| Part | Counts towards the rule |
|---|---|
| Smoother step | yes |
| Engine push plus smoother, per block ("path") | yes |
| Synthesis of 480 samples at 48 kHz | no, it runs in the output callback |

Two variants run: `live`, as the detector runs today, and `cached_dpss`, with the same output and a research cache of its tapers. `live` is the one that describes the app.

## Rule

- **Smoother.** Passes if its p99 is under 0.5 ms in every run. Load only slows it down, so a pass on a busy machine stands. A miss on a busy machine is inconclusive.
- **Path.** Passes or fails on p99 under 5 ms in every run, the same bar as `results-selector-timing-01`, and only on a quiet machine: preflight and background both at or under 5% CPU. Otherwise it is inconclusive and diagnostic only.
- **Other work is not stopped** to make the machine quiet.

The largest queue behind real time is reported but is not part of the rule. The app already refuses to play forecasts older than 250 ms.

## Limits

- **Not measured.** Decimation, locks, the window, audio callbacks, device transport and any acoustic path.
- **Scope.** One machine, one schedule, CPython on Windows.
- **The 5 ms bar is a reserve, not a measured need.** Passing it would not prove a whole live session keeps time.
- **No physical claim.** No sound is played or recorded, and no physical ANC is claimed.
