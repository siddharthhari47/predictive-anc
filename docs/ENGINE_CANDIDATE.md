# Engine candidate test

31 October 2026, Claude. Design note for `results-engine-candidate-01`, frozen with the code before any time was measured. No audio device is opened, and `tune_app.py` is not changed.

## Why

The smoother has passed on its own, and on quiet runs the taper cache kept the loop under its 5 ms bar. Neither has run inside the app's own code, and decimation, locks and the callbacks have never been timed.

## What was built

`SmoothedEngine` in `anc_lab/engine_candidate.py` goes in through `LiveRunner`'s existing `engine` argument. The renderer gets smoothed tones. The gate, the tone list and the raw components stay as they are. The smoother steps once per origin, including when one push holds several.

The taper cache is the same scoped `cached_dpss` used in the timing runs. It holds one window length, and only the worker thread reads it. It replaces a shared SciPy function for the length of a run, so an app version should cache the tapers inside `tone_selection.py` instead.

## Output first

At chunk sizes of 137, 480, 1024 and 1920 samples, the raw log must equal plain `AntiHumEngine` and the smoothed log must equal `smooth_arrays`, on all 14 rooms. A mismatch stops the study.

## Live stage

Each stored 30 s microphone is resampled to 48 kHz and played at real-time pace through the real `on_input`, `on_output` and `pump`, on three threads. Tones are set on both ears, so `on_output` really synthesizes. Its output is thrown away. There are two arms, `v2` and `candidate`, 28 runs each. Threads are not pinned, as in the app.

## Rule

- **Clean, on every run.** No thread error, stale block, limiter stop or glitch, and logs equal the offline reference.
- **Timing, on every quiet run.** Engine push p99 under 5 ms and `on_output` p99 under 5 ms.
- **Result.** Fail if either misses. Pass needs both and at least 24 of 28 quiet runs. Otherwise inconclusive.
- **Quiet.** Preflight and background at or under 5%. The earlier every-run rule was spoiled by 3 brief spikes; this minimum of 24 was set after seeing that, before any data here. Not-quiet runs are still reported.
- **Other work is not stopped.**

## Limits

- **Stand-ins.** Python loops replace PortAudio callbacks, and the 50 ms output latency is assumed.
- **Scope.** One machine, one schedule, seen recordings.
- **The 5 ms bars are reserves, not measured needs.**
- **No physical claim.** No sound is played or recorded, and no physical ANC is claimed.
