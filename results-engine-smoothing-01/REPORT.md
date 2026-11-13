# In-band engine output study: results

29 October 2026, Claude. Design: `docs/ENGINE_SMOOTHING.md`. Protocol: `protocol.json` (sha256 `510bf091…`), frozen with the code before any room was re-tuned on the new engine.

**What this is.** A simulation on seen development data: 37 rooms (78 tones, 14 sources), 10 seeds, and 3 simulated listener noise levels. No sound was played or recorded. This is not a physical ANC result, and it is not a fresh validation.

## Verdict

**SD-s30 meets the frozen "helps" rule at 1 dB listener noise. It is the frozen candidate.**

SD-s30 combines three changes:
- the improved search;
- the sequential keep-or-mute check;
- an engine that smooths each tone's estimate with a 5.7 Hz half-bandwidth.

This is the first tune-by-ear configuration in this line of studies to pass all four conditions. The stronger smoother, s10, removes more band boosts but costs too much tone cut and fails condition 1.

## Main table (listener noise 1 dB)

All differences are against O: the original tuner on the v2 engine. Brackets are 95% source-bootstrap intervals.

| Arm | Tone-level gain | Whole-room gain | Harmful keeps | Harmed rooms | Useful keeps | Helps |
|---|---|---|---|---|---|---|
| O (v2) | — (0.84 dB absolute) | — | 62 | 36 | 182 | — |
| SD (v2) | +0.146 [+0.051, +0.285] | +0.116 [+0.011, +0.306] | 21 | 38 | 240 | no (harmed rooms) |
| O-s30 | −0.006 [−0.047, +0.023] | −0.009 | 63 | 26 | 188 | no |
| **SD-s30** | **+0.134 [+0.017, +0.281]** | **+0.113 [+0.001, +0.304]** | **14** | **22** | **250** | **yes** |
| O-s10 | −0.057 [−0.167, +0.015] | −0.031 | 64 | 23 | 180 | no |
| SD-s10 | +0.093 [−0.064, +0.253] | +0.088 [−0.043, +0.292] | 16 | 14 | 239 | no (interval) |

**Engine effect alone** (same tuner, smoothed engine minus v2):

| Engine | Tone level | Harmed rooms |
|---|---|---|
| s30 | −0.01 dB, inside noise (SD-s30 minus SD: −0.012 [−0.058, +0.024]) | 38 → 22 (SD), 36 → 26 (O) |
| s10 | about −0.05 dB | 38 → 14 (SD) |

**Other listener noise levels** (descriptive only):
- **0.5 dB.** SD-s30 also passes:
  - tone +0.151 [+0.022, +0.326];
  - harmful keeps 6 vs 52;
  - harmed rooms 19 vs 34.
- **2 dB.** SD-s30 fails the interval: tone +0.082 [−0.015, +0.212]. It still halves the harmed rooms, 30 vs 42.

## Verification (`verification.json`)

- **Hashes.** The protocol hash, the code hashes and all 37 decision-01 case-file hashes match.
- **Parity.** O and SD were recomputed on two seeds at 1 dB noise and match decision-01 exactly: 1792 fields, settings and room scores. The 4440 copied v2 runs are identical to decision-01.
- **Independent recount.** A recount from the case files reproduces the tone-level means, room-harm counts and harmful-keep counts in `summary.json` for every arm and noise level.
- **Tests.** All 21 unit checks pass.

## What to keep in mind

- **The cost is concentrated.** It falls on the strongest rooms. Room by room, the s30 engine costs most in old-007-r1 (−0.35 dB tone level), old-000-r2 (−0.29) and old-007-r2 (−0.25). It gains most in fresh-018-r2 (+0.24) and old-001-r1 (+0.22).
- **Some harms remain.** SD-s30 still harms 22 runs, all in five rooms: old-001-r2, old-013-r1, old-013-r2, old-014-r0 and old-014-r1.
- **The bandwidths were set from the lead, but data was seen.** A six-room fixed-setting probe was looked at before freezing, and the whole study is on seen rooms.
- **Not yet deployable.** The smoother changes the live renderer, and its compute timing has not been measured. The live app still runs v2 with the original tuner.

## Next

1. **Fresh-data test** of the frozen SD-s30 on rooms built from recordings this line of studies has not used. Arms: O vs SD-s30, same four conditions, protocol frozen before download.
2. **Timing.** Measure the timing of the smoothed renderer in the live engine, offline and without audio.
3. **Live use.** Only then could the live app's default change, and that is Sid's decision.

## Limits

- Seen development data.
- Simulated listener and microphone, with no earphone leakage.
- Phase and gain errors are measured against the v2 oracle.
- No physical ANC is claimed.
