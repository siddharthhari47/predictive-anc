# Keep-or-mute decision: a microphone-corrected sequential check

28 October 2026, Claude. Design note for `results-tuning-decision-01`, frozen with the code before the new rule was scored on any room.

## Why

The ablation (`results-tuning-ablation-01/REPORT.md`) showed that the improved search finds better settings, but the final decision throws much of that away.

- **The original check** compares on and off twice. The background changes between the two intervals, so it keeps a useless tone about 31% of the time. In the dominant room it also muted the best setting the search had found.
- **The microphone-gated check** threw away every pair whose background changed by more than 1 dB. That was 42% of pairs, and 22% of tones ended up muted as "inconclusive".

## The rule

**Don't discard unstable pairs. Correct for the background change instead.**

1. **The model.** For each on/off pair, the listener hears the anti-hum effect, plus the background change between the two intervals, plus judgement noise.
2. **The background estimate.** The laptop microphone measures the background change in the tone's auditory band over the two intervals the listener has just heard. The live app has the same signal.
3. **Weighing each answer.** Each answer ("on quieter", "off quieter", "same") is weighed as evidence for "the anti-hum helps by 2 dB" against "it does nothing", given that measured background change.
   - "On quieter" counts for less when the background itself fell during the "on" interval.
   - "Same" counts slightly *for* the anti-hum when the background rose during "on".
4. **Stopping.** Evidence is added up pair by pair (a Wald sequential test with 10% error rates on both sides).
   - At +2.20 the tone is kept.
   - At −2.20 it is muted.
   - After six pairs, the tone is kept only if the evidence leans towards helping.

**Assumptions built into the rule.**
- The rule assumes a 1 dB listener and 1 dB of microphone error.
- It keeps those assumptions when the simulated listener is actually 0.5 or 2 dB, so those runs test a wrong model.
- All constants were chosen from the listener model alone.

**Model-only operating points** (background change SD 1.5 dB, before any room was scored):

| True effect | Sequential keeps | Original check keeps |
|---|---|---|
| no effect | 16% | 33% |
| 1 dB louder (harmful) | 1.5% | 13% |
| 2 dB quieter (useful) | 91% | 81% |

The sequential check uses about 4 pairs on average, against 2 for the original.

## Arms

| Arm | Search | Decision |
|---|---|---|
| O | original | original |
| S | improved | original |
| D | original | new |
| SD | improved | new |

O and S must reproduce the ablation runs exactly.

## Seeds and measures

**Seeds.** Ten seeds per room: the ablation's five plus five new ones.

**Primary measure: tone-level decision quality.** For each room and seed, take the mean over its tones of each tone's own cancellation in the scored part of the recording. A muted tone counts as 0. This replaces the whole-room measure as primary because, in the ablation, one room's single strong tone dominated that measure. The whole-room measure stays as a guard.

**SD helps** (at 1 dB listener noise) only if all four hold:

1. the lower 95% bound of its tone-level gain over O is above 0;
2. it has no more harmful keeps than O;
3. it has no more harmed rooms than O;
4. its whole-room change is at least −0.05 dB.

## Limits

- **Development data.** These are seen rooms, so the result chooses a candidate; it is not a fresh validation.
- **Simulated listener.** The listener is an assumption.
- **Simulated microphone.** It has no earphone leakage, and its background comes from the same source as the ear's.
- **No physical claim.** No sound is played or recorded, and no physical ANC is claimed.
