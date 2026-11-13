# Second fresh-recording test of SD-s30: results

30 October 2026, Claude. Design: `docs/TUNING_FRESH_TEST_02.md`. Protocol: `protocol.json` (sha256 `3455b068…`), frozen with the code before any new media byte was read.

**What this is.** A simulation on recordings no earlier study used: 36 rooms (55 tones, 14 sources), 10 seeds, and 3 simulated listener noise levels. No sound was played or recorded. This is not a physical ANC result.

## Verdict

**Pass. SD-s30 meets the frozen rule on fresh recordings at 1 dB listener noise.**

This is the first fresh-data pass for a tune-by-ear configuration. It is a simulated result, and the gain is small and uneven across recordings (see "How much to trust this").

## Main table (listener noise 1 dB)

Differences are against O, the original tuner on the v2 engine. Brackets are 95% source-bootstrap intervals.

| Measure | O | SD-s30 | Condition |
|---|---|---|---|
| Tone-level gain | 0.82 dB | 1.02 dB; +0.198 [+0.050, +0.389] | met |
| Harmful keeps (prefix) | 36 | 13 | met |
| Harmed rooms (of 360 runs) | 54 | 49 | met |
| Whole-room change | — | +0.107 [+0.015, +0.257] | met |
| Useful keeps | 161 | 201 | not in the rule |
| Enough sources (12) | | 14 | met |
| Enough rooms (25) | | 36 | met |

## Other noise levels (descriptive)

| Listener noise | Tone-level gain | Harmful keeps O → SD-s30 | Harmed rooms O → SD-s30 |
|---|---|---|---|
| 0.5 dB | +0.195 [+0.049, +0.374] | 19 → 9 | 53 → 45 |
| 1 dB | +0.198 [+0.050, +0.389] | 36 → 13 | 54 → 49 |
| 2 dB | +0.131 [+0.001, +0.257] | 33 → 21 | 47 → 45 |

The first test's warning at 2 dB, where harmed rooms rose 17 to 22, did not repeat here. Its 7 sources were too few to settle this, and the lower bound here is barely above zero, so a noisier listener should still be treated as the weak case.

## How much to trust this

- **Recounted.** A separate script (`research-tools/tuning-fresh-02/recheck_summary.py`, output `recheck.json`) rebuilt every count and both mean differences from the raw case files at all three noise levels. All matched `summary.json`.
- **No single recording decides it.** Twelve of 14 sources improved at 1 dB. Removing any one source leaves a mean gain of +0.12 to +0.23 dB and a lower bound above zero, the lowest being +0.024 without tg-006. That check was chosen after the verdict and is descriptive.
- **The typical gain is small.** The median source gains +0.06 dB against the +0.20 dB mean. Six sources (tg-006, tg-021, tg-071, tg-058, tg-063, tg-062) gain about +0.25 dB or more, and tg-006 alone gains +1.2 dB. The other six that improved gain under +0.07 dB. Two got worse: tg-011 (−0.21 dB) and tg-067 (−0.04 dB).
- **Harm remains.** The rule compares arms. SD-s30 still harms 49 of 360 room runs (14%), only slightly fewer than O, and keeps 13 harmful settings. The clear change is harmful keeps, not harmed rooms.
- **The two tests are separate.** The first test was inconclusive, not failed, and its outcome was known when this one was designed. Its rule was copied unchanged and the two are not pooled. Its recordings, uploaders and authors were excluded.

## Recordings

- 71 frozen from metadata, none dropped at freeze; all 71 downloaded with identities verified.
- 8 excluded mechanically and not replaced: 6 had no audio track (tg-002, 022, 025, 029, 059, 068), 1 had an unreadable format (tg-024), 1 had a silent start (tg-042).
- 63 decoded. 14 had a tone the engine holds, close to the 1 in 5 yield the list was sized for: Masada cable car, Lagos bus park, a steam locomotive, a cockpit at night, a Boeing 747 taxiing, the Lisbon ferry, a borehole drill, foundation drilling, a fan, a landing at Batumi, an airliner cabin, a residential noise recording, an inclined elevator, and airport boarding bridges.
- Four of these are aircraft recordings (tg-012, 013, 058, 062) and two are drilling, so the set is not an even spread of everyday hum.

## Deviations from the frozen plan

1. `research-tools/tuning-fresh-02/run_stage.py` is not in the frozen code hash. `anc_lab/tuning_fresh_02.py` has no command line, so this small launcher applies its frozen paths and seed and calls the frozen stages. It contains no scoring logic.
2. `check_rooms.py` was written after the rooms were built and before scoring. It only reads. Zero room seeds mismatched.
3. `recheck_summary.py` was written after the verdict. It does not change the verdict.

The frozen code and protocol hashes were checked at each stage. Wikimedia rate-limited 4 downloads (tg-011, 025, 039, 050) even at 45 s spacing. Each was retried after a 10 minute wait and verified, and the rooms were built only after the manifest was read.

## Limits

- **Selection.** A purposive public collection, and eligibility depends on the v2 engine.
- **Simulation.** The listener, rooms and microphone are simulated, with no earphone leakage.
- **Timing.** The smoother's compute timing in the live engine is unmeasured.
- **Live app.** Unchanged. v2 and the original tuner stay live. Moving to SD-s30 changes v2 and needs Sid's go-ahead.
