# Keep-or-mute decision study: results

29 October 2026, Claude. Design: `docs/TUNING_DECISION.md`. Protocol: `protocol.json` (sha256 `06690ce0…`), frozen with the code before the new rule was scored on any room.

**What this is.** A simulation on seen development data: 37 rooms (78 tones, 14 sources), 10 seeds, and 3 simulated listener noise levels. No sound was played or recorded, and nothing here is a physical ANC result.

## Verdict

**No arm meets the frozen "helps" rule at 1 dB listener noise.**

- **SD** (improved search plus the new sequential check) gives the largest gains and cuts harmful keeps by two thirds. It fails one guard: 38 harmed rooms against O's 36.
- **D** (new check alone) fails only because its confidence interval touches zero.
- Under the frozen rule, the original tuner and v2 stay live.

## Main table (listener noise 1 dB)

The values are mean paired differences from O over the 14 sources, with 95% source-bootstrap intervals in brackets.

| Arm | Tone-level gain | Whole-room gain | Harmful keeps | Harmed rooms | Useful keeps | Listening per tone | Verdict |
|---|---|---|---|---|---|---|---|
| O (original) | — (0.84 dB absolute) | — | 62 | 36 | 182 | 90 s | — |
| S (search) | +0.057 [+0.025, +0.10] | +0.003 | 50 | **47** | 217 | 166 s | fails guard 3 |
| D (check) | +0.060 [−0.012, +0.151] | +0.050 [−0.004, +0.146] | 18 | 36 | 218 | 98 s | fails criterion 1 |
| SD (both) | **+0.146 [+0.050, +0.284]** | **+0.116 [+0.011, +0.307]** | **21** | 38 | **240** | 174 s | fails guard 3 only |

**Effect of the check on top of the search (SD minus S):**
- tone level +0.089 [−0.00, +0.23];
- whole room +0.113 [−0.001, +0.33].

**Other listener noise levels** (descriptive only):
- **0.5 dB.** D passes all four conditions:
  - tone level +0.078 [+0.011, +0.165];
  - whole room +0.058 [+0.005, +0.153];
  - harmful keeps 6 vs 52;
  - harmed rooms 33 vs 34.

  SD gains more (+0.16 [+0.044, +0.335]) but has 38 harmed rooms vs 34.
- **2 dB.** No arm helps.
  - SD tone level is +0.086 [−0.012, +0.225].
  - D still cuts harmful keeps from 70 to 39.

The sequential check used 4.06 on/off pairs per tone on average, against 2 for the original check. This matches the model's prediction made before scoring.

## Verification (`verification.json`)

- **Hashes.** The protocol and code hashes match the frozen values.
- **Parity.** 3840 parity fields are exact: arms O and S reproduce ablation-01 for seeds 0–4 at every noise level, and O reproduces the saved v2 tuning.
- **Independent recount.** An independent re-aggregation from the per-room files reproduces the tone-level means and room-harm counts in `summary.json`.
- **Tests.** All 14 unit checks pass.

## Where the extra harmed rooms come from (post hoc, `posthoc-room-harms.json`)

This analysis was written after the frozen verdict and does not change it.

- **Which criterion fires.** Almost every room harm in every arm comes from the third-octave criterion, a band boosted by more than 0.5 dB, not from the whole room getting louder. In SD, 37 of 38 are third-octave only.
- **Which rooms.** The same few rooms account for most harms in every arm: old-007-r0, old-001-r2, old-014-r1 and fresh-035-r0.
- **old-007-r0 is a special case.** It is counted as harmed on all 10 seeds in every arm. Yet its whole-room band is about 6.8 dB *quieter* in each of those runs. The harm flag is a ~1.1 dB boost in one third-octave band that occurs with every setting, so the decision rule cannot affect it.
- **SD against O, run by run.** 12 runs are harmed in SD but not O, and 10 are harmed in O but not SD. The 2-room gap is a net of opposite changes spread over 8 rooms, not one systematic failure.
- **The search change carries the extra boosts.** S alone has 47 harmed rooms. Adding the sequential check brings that back to 38.

## What this means

1. **The sequential check works as designed.** It cuts harmful keeps by about two thirds (62 → 18–21). It no longer throws away useful settings (useful keeps 182 → 218–240), and it costs about 2 extra pairs per tone.
2. **The remaining blocker is the improved search.** It produces settings that occasionally lift one neighbouring third-octave band by more than 0.5 dB. The next design target is a boost-aware step in the search, for example a phase/gain step that is refused when the microphone shows a neighbouring band rising.
3. **Seen data only.** Even a passing candidate would need a fresh-data run before it could replace the original tuner.

## Limits

- Seen development data; the simulated listener and simulated microphone are assumptions.
- The microphone has no earphone leakage, and its background comes from the same source as the ear's.
- No physical ANC is claimed.

## Addendum, same night: the search is not the source of the boosts (post hoc, `posthoc-boost-source.json`)

Sid approved a boost-aware search as the next step. Before designing it, I checked whether the search really makes worse settings. It does not. This corrects point 2 of "What this means" above.

- **Same tones kept, same harm.** When the improved search and the original tuner end up keeping the same tones, they harm almost the same number of rooms: 16 vs 15 (162 paired runs). The search's extra harms all come from runs where it keeps more tones: 20 vs 10.
- **The harm is spill from the anti-hum renderer.** The boosted band is usually a near-silent neighbour of a kept tone, holding about 0.01–0.6% of the room's sound. The anti-hum puts a little energy there.
  - In old-007-r0 the band rises by about five times the anti-hum's own power in that band.
  - So the spill adds in step with sound already in the room, most likely the hum's own small side tones, reproduced with the wrong timing.
- **Why the tuner cannot fix it.** The spill grows and shrinks with the tone's gain, so no gain or phase choice removes it while the tone is kept. A tuner can avoid it only by muting a tone that is otherwise helping. In old-007-r0 that tone gives 12 dB.

**Result.** A boost-aware search is not built: under this guard it could only mute useful tones. The fix belongs in the anti-hum engine's output, by keeping its energy inside the tone's own band. That is an engine study, since it changes the frozen v2 output, and it needs a decision before it starts.

A side note on the guard. A "harm" here can be a 1 dB rise in a band holding under 1% of the room's sound, next to a tone that has just been cut by 12 dB. The guard stays frozen as written, but it is stricter than audibility.
