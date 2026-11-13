# Tuning ablation: better search or better evidence?

28 October 2026, Claude. Design note for `results-tuning-ablation-01`, frozen with the code before any arm was scored. It answers the question in `docs/TUNING_DIAGNOSTIC_NEXT.md`: is the tune-by-ear layer losing cancellation because it searches badly, or because its final on/off check believes the wrong evidence?

## Why these two changes

The 26 October diagnosis found two separate faults.

- **Search.** The median phase error for the 78 tones is 26.7°. Most tones had only two sweeps, one in each direction, and each fine step asked a single question. One noisy answer moves the phase in the wrong direction and nothing corrects it.
- **Evidence.** The final check compares "on" and "off" in two intervals heard one after the other. The background changes between them by a median of 0.69 dB, and by 3.9 dB at the 90th percentile. The anti-hum effect is often smaller than that change. A tone with no effect at all passes the original check 30.7% of the time.

Each arm changes one fault so that the two can be told apart.

## Arms

| Arm | Search | Final check |
|---|---|---|
| O | original | original |
| S | 4 alternating sweeps; first fine phase step 60°; best of 3 at every fine step | original |
| C | original | microphone-validated pairs, 3 valid pairs needed |
| SC | as S | as C |

**Search (S).**
- **Sweeps.** Four phase sweeps run in alternating directions (+, −, +, −). The two directions are averaged separately, then combined, so reaction delay still cancels even if one sweep is lost.
- **Fine phase.** The fine phase search starts at ±60° and then follows 30/15/8/4°. A 60° step can correct a sweep that landed far from the right phase.
- **Voting.** Every fine phase and gain step asks up to three times. The setting moves half a step once A or B has two votes. It stays put once "same" has two votes, or after a three-way split.
- **Unchanged.** The level staircase, the gain steps and the gain limits.

**Check (C).**
- **Valid pairs.** An on/off pair counts only if the laptop microphone heard the same background in both intervals: its auditory-band level around the tone may differ by at most 1 dB.
- **Decision.** Any valid "louder with anti-hum" answer switches the tone off at once. Three valid pairs with at least two "on" answers keep it.
- **Inconclusive.** After six pairs without three valid ones, the tone is switched off and marked inconclusive.
- **Effect on false keeps.** A tone that does nothing is kept about 10% of the time under the simulated listener, against 30.7% for the original check.

The rule reads only the microphone, over sound the listener has already heard, so the live app could apply it. It never reads the simulated ear.

## What is measured

**Rooms, seeds and listener.**
- All 37 eligible rooms (78 tones, 14 source recordings).
- Five listener seeds per room: the recorded one plus four fixed in advance from the room name. Every arm uses the same seeds.
- Listener noise of 1 dB is primary. 0.5 and 2 dB are sensitivity checks only.

**Parity first.** Before anything is summarised, arm O at 1 dB with the recorded seed must reproduce the saved v2 tuning in every room.

**Primary measure.** Whole-room attenuation in the 35–350 Hz band over the scored part of the recording, paired against O.

**Secondary measures.**
- Tone attenuation, third-octave boosts and clipping.
- Phase and gain error against the prefix oracle.
- Single-tone harm in the tuning and scored parts.
- Useful keeps and missed opportunities (the oracle offered at least 1 dB, but the tone was muted).
- Listening time, questions and check pairs.

**Statistics.** Rooms from the same recording are not independent, so averages are taken per recording first, with a 95% interval from resampling the 14 recordings.

## Decision rule

At 1 dB listener noise, an arm **helps** only if all three hold:

1. the lower 95% bound of its mean paired gain over O is above zero;
2. it has no more harmful keeps than O;
3. it has no more harmed rooms than O.

Its extra listening time is reported beside it. Every arm is reported whatever happens. The interaction SC − S − C + O shows whether the two changes add up.

## Limits

- **Development data.** This is seen data. The result chooses where to spend effort; it is not a fresh validation.
- **Simulated listener.** The listener is an assumption, not measured hearing.
- **Simulated microphone.** It hears no earphone leakage, and its background comes from the same simulated source as the ear's. A real laptop microphone may track the ear's background less well.
- **No physical claim.** No sound is played or recorded, and no physical ANC is claimed.
