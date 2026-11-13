# Fresh-recording test of the SD-s30 tuner

30 October 2026, Claude. Design note for `results-tuning-fresh-01`, frozen with the code and the recording list before any new media was downloaded.

## Question

`results-engine-smoothing-01` picked SD-s30 on rooms it had already seen: improved search, sequential keep-or-mute check, and an engine that smooths each tone's estimate. Does it still beat the original tuner on recordings no earlier study used?

Nothing about the candidate changes. This is a one-shot test.

## Arms

| Arm | Tuner | Engine |
|---|---|---|
| O | original | v2 |
| SD-s30 | improved search + sequential check | smoothed, alpha 0.3 |

Same 10 seeds per room for both arms, at listener noise 1, 0.5 and 2 dB.

## Recordings

- **Selected from Commons metadata only.** No new media byte is touched before the protocol is frozen.
- **Forty candidates** of machinery, appliances and vehicles, chosen by title and description (`research-tools/tuning-fresh-01/picks.txt`). At most one per uploader and one per credited author, and none from an uploader or author used earlier. Candidates failing that check are dropped at freeze, and `protocol.json` lists them.
- **Excluded:** every recording in `external-audio/` by SHA-1, every earlier title, including the 40 recordings of `results-selector-fresh-01`, of which only 8 entered tuning rooms; also music, speech-led material, synthetic tone demos and compilations.
- **Length:** at least 51 s of metadata duration. Only the first 90 s are used, with no looping or chosen crops.
- **Audio-bearing video is allowed.** The first audio track, channel zero, is decoded.
- **Failures stay failures.** Missing, undecodable or short files are reported and never replaced.

## Rooms

Three simulated rooms per recording, drawn from a seed fixed by the recording id. The room, listener and earphone models are unchanged. As in earlier studies, only rooms where the engine holds at least one tone in the tuning part enter the test. That eligibility is read from the v2 engine before any tuning. Rooms are built and counted before tuning, and the list is sealed.

A room rebuilt by this code matches a saved development room exactly, and both arms reproduce their saved development runs on it (`tests/test_tuning_fresh.py`).

## Rule

Measures and aggregation are the same as decision-01: seeds to rooms to sources, 10,000 source-bootstrap resamples.

**SD-s30 passes** at 1 dB listener noise only if all four hold against O:

1. the lower 95% bound of its tone-level gain is above 0;
2. it has no more harmful keeps;
3. it has no more harmed rooms;
4. its whole-room change is at least -0.05 dB.

**Adequacy.** At least 12 sources and 25 eligible rooms, or the result is inconclusive whatever the scores. No recordings are added after that.

Noise levels 0.5 and 2 dB are descriptive. The per-tone oracle is not computed, so phase and gain errors are not reported. They were secondary measures and the rule does not use them.

## Limits

- **Selection.** The recordings are a purposive public collection, and metadata cannot prove independence or steadiness.
- **Simulation.** The listener, rooms and microphone are simulated, with no earphone leakage.
- **Timing.** The smoother's compute timing in the live engine is unmeasured.
- **No physical claim.** No sound is played or recorded, and no physical ANC is claimed.
