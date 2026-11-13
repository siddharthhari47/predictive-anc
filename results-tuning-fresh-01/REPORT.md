# Fresh-recording test of SD-s30: results

30 October 2026, Claude. Design: `docs/TUNING_FRESH_TEST.md`. Protocol: `protocol.json` (sha256 `561c2307…`), frozen with the code before any new media byte was read.

**What this is.** A simulation on recordings no earlier study used: 18 rooms (32 tones, 7 sources), 10 seeds, and 3 simulated listener noise levels. No sound was played or recorded. This is not a physical ANC result.

## Verdict

**Inconclusive. SD-s30 did not pass this test, and it did not fail it.**

The frozen rule needs at least 12 sources and 25 eligible rooms. The test reached 7 sources and 18 rooms, so the result is inconclusive whatever the scores say. No recordings were added afterwards.

The four performance conditions all point the right way at 1 dB listener noise. That is encouraging but it is not a pass. Seven sources is too few for a source bootstrap to be trusted, so the intervals below are likely too narrow.

## Main table (listener noise 1 dB)

Differences are against O, the original tuner on the v2 engine. Brackets are 95% source-bootstrap intervals.

| Measure | O | SD-s30 | Condition |
|---|---|---|---|
| Tone-level gain | 0.67 dB | 0.81 dB; +0.141 [+0.054, +0.243] | met |
| Harmful keeps (prefix) | 12 | 1 | met |
| Harmed rooms (of 180 runs) | 26 | 15 | met |
| Whole-room change | — | +0.033 [+0.007, +0.068] | met |
| Useful keeps | 108 | 121 | not in the rule |
| Enough sources (12) | | 7 | **not met** |
| Enough rooms (25) | | 18 | **not met** |

The tone-level gain is close to the development figure (+0.134). The whole-room gain is much smaller than development (+0.113).

## Other noise levels (descriptive)

| Listener noise | Tone-level gain | Harmful keeps O → SD-s30 | Harmed rooms O → SD-s30 |
|---|---|---|---|
| 0.5 dB | +0.092 [+0.020, +0.172] | 16 → 3 | 25 → 18 |
| 1 dB | +0.141 [+0.054, +0.243] | 12 → 1 | 26 → 15 |
| 2 dB | +0.054 [−0.044, +0.190] | 16 → 14 | 17 → **22** |

At 2 dB the gain's interval crosses zero, the harmful-keep advantage almost disappears, and SD-s30 harms more rooms than O. A noisier listener loses most of the benefit, and the sequential check is the likely reason, though this test does not isolate it.

## Recordings

- 40 candidates chosen from metadata; 7 dropped at freeze because the uploader or author had appeared before, leaving 33.
- 33 downloaded with identities verified.
- 30 decoded. Two had a silent start (tf-024, tf-025), and one had no audio track (tf-030). These were reported, not replaced.
- 7 had a tone the engine holds: TTC subway, Foveaux Strait ferry, TransJakarta bus, coffee machine, Moscow bus, wind turbine, airplane wheel.

## What went wrong

1. **The test was undersized, and that was my mistake.** The design note records that only 8 of the previous 40 recordings entered tuning rooms. At that yield 33 recordings gives about 7 sources, which is what happened. I should have sized the list for the 12-source minimum before freezing.
2. **Rate limiting.** The first download got 9 of 33 before Wikimedia returned HTTP 429, because my pacing was too fast. I then built rooms before reading the download result. Nothing was scored. Those outputs are kept as `download-attempt-1/`, `rooms-attempt-1.json` and `decoded-attempt-1/`.
3. **Deviation from the frozen plan.** `research-tools/tuning-fresh-01/resume_download_tuning_fresh.py` finished the same frozen list with the same identity checks. It is not in the frozen code hash because it was written afterwards. No recording was added or replaced, and all 9 sources from the first attempt rebuilt to identical rooms (`check_room_rebuild.py`).

## Limits

- **Selection.** A purposive public collection, and eligibility depends on the v2 engine.
- **Simulation.** The listener, rooms and microphone are simulated, with no earphone leakage.
- **Timing.** The smoother's compute timing in the live engine is unmeasured.
- **Live app.** Unchanged. v2 and the original tuner stay live.
