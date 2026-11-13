# Keeping the anti-hum inside each tone's band

29 October 2026, Claude. Design note for `results-engine-smoothing-01`, frozen with the code before any room was re-tuned on the new engine.

## Why

The keep-or-mute study (`results-tuning-decision-01/REPORT.md` and its post-hoc addendum) left one blocker: rooms flagged as harmed because a near-silent neighbouring third-octave band rose by more than 0.5 dB. The tuner turned out not to be the cause.

- **The cause is the v2 engine.** It re-estimates each tone every 10 ms, so it also copies the room's own sound a few hertz either side of the tone.
- **Why that copy harms.** The anti-hum arrives 30 ms ahead of its estimate, so that copy lands late. Beyond about 5.6 Hz from the tone (1/(6 × 30 ms)), the delay exceeds 60°, and the copy adds to the sound instead of cancelling it.
- **Why tuning cannot fix it.** The spill scales with the tone's gain. Only muting the tone or changing the engine output removes it.

## The change

Each tone's estimate is smoothed over the last few blocks, in a frame that turns with the tone, so a steady tone passes through unchanged.

- **What it filters out.** Rapid wobbles, which carry the off-tone sound, are filtered out.
- **Causal.** It uses only the current and past blocks, so the live engine could do the same.
- **Tracking rules.**
  - A tone's smoothing state follows the nearest tracked component within 2 Hz.
  - It survives gaps of up to 0.1 s.
  - It is cleared whenever the engine's gate was off.

**Two strengths, both set from the 30 ms lead:**

| Engine | Smoothing per 10 ms | Half-bandwidth | Reasoning |
|---|---|---|---|
| s30 | 0.3 | 5.7 Hz | edge where a late copy starts to add |
| s10 | 0.1 | 1.7 Hz | about a third of that edge |

**What was seen before freezing.** I looked at a fixed-setting probe on six rooms, keeping their v2-tuned settings. In old-007-r0 the worst band boost fell from 1.11 to 0.41 dB (s30) and 0.15 dB (s10), while its tone cut fell from 13.6 to 13.1 and 11.9 dB. No room has been re-tuned on the new engine.

## Arms

| Arm | Tuner | Engine |
|---|---|---|
| O | original | v2 (decision-01 runs reused) |
| SD | improved search + sequential check | v2 (decision-01 runs reused) |
| O-s30, SD-s30 | as above | s30, re-tuned |
| O-s10, SD-s10 | as above | s10, re-tuned |

**Parity.** O and SD are recomputed on two seeds at 1 dB listener noise. They must match decision-01 exactly, both settings and room scores. The decision-01 case files are hash-locked.

## Measures and rule

Measures, seeds and aggregation are the same as decision-01.

**SD-s30 or SD-s10 helps** (at 1 dB listener noise) only if all four hold against O on the v2 engine:

1. the lower 95% bound of its tone-level gain is above 0;
2. it has no more harmful keeps;
3. it has no more harmed rooms;
4. its whole-room change is at least −0.05 dB.

If both pass, the candidate is the one with the larger tone-level gain.

**Also reported:**
- the engine effect alone, X on the smoothed engine minus X on v2;
- the mean worst-band boost.

## Limits

- **Seen development data.** This picks a candidate; it is not a fresh validation.
- **Timing.** The new engine's compute timing is unmeasured.
- **Phase and gain errors** are still measured against the v2 oracle.
- **Simulation.** The listener and microphone are simulated.
- **No physical claim.** No sound is played or recorded, and no physical ANC is claimed.
