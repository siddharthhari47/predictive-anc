# Tuning ablation: better search or better evidence?

28 October 2026, Claude. Frozen protocol `protocol.json` (sha256 `9dbeda5e…`), design in `docs/TUNING_ABLATION.md`. Seen development data, simulated ear, simulated listener. No sound was played or recorded, and no physical ANC is claimed.

## Answer

**No arm meets the frozen "helps" rule.** The search change gives better settings, but the final keep-or-mute decision throws much of that away. Neither check rule (the original or the new microphone-validated one) decides well. The bottleneck is now the decision, not the search.

## Primary result (listener noise 1 dB, 37 rooms × 5 seeds, 14 sources)

| Arm | Room band gain over O, dB (95% CI) | Helps? | Harmful keeps | Harmed rooms | Listening time per tone |
|---|---|---|---|---|---|
| O original | — (mean 0.63 dB vs no control) | — | 27 | 18 | 90 s |
| S search | −0.01 (−0.10 to +0.04) | no | 23 | 20 | 166 s |
| C check | −0.05 (−0.17 to +0.01) | no | **4** | 19 | 96 s |
| SC both | −0.05 (−0.16 to +0.01) | no | 5 | 17 | 173 s |

The two changes do not interact: SC − S − C + O = +0.02 dB (−0.03 to +0.11).

## What each change did, tone by tone (390 tone tunings per arm)

| | O | S | C | SC |
|---|---|---|---|---|
| Median phase error vs oracle | 37.6° | **26.3°** | 35.8° | 29.7° |
| Median gain error | 5.3 dB | 4.4 dB | 5.0 dB | 4.4 dB |
| Useful setting found before the check (≥1 dB) | 109 | **133** | 112 | 132 |
| Kept | 171 | 198 | 112 | 123 |
| Useful keeps (≥1 dB) | 86 | **108** | 84 | 96 |
| Harmful keeps | 27 | 23 | **4** | 5 |
| Missed opportunities (oracle ≥1 dB, muted) | 77 | 64 | 104 | 93 |
| Muted as inconclusive | 0 | 0 | 87 | 81 |

- **The recorded seed was lucky.** On it, O's median phase error is 26.7°, which reproduces the 26 Oct diagnosis. On the four new seeds it is 35.7–41.5°, so the earlier diagnosis understated the search error. S is better on every seed: 20.9, 27.8, 33.6, 20.7 and 29.0° against 26.7, 41.1, 41.5, 35.7 and 40.6°.
- **The search change works at the tone level.** Phase error falls by a third, 24 more tunings reach a useful setting, 22 more useful settings are kept and harmful keeps fall slightly. The cost is about 76 s of extra listening per tone.
- **The microphone-validated check is too strict.** It almost removes harmful keeps (27 → 4), but only 57.5% of on/off pairs pass the stability test (median microphone change 0.77 dB). 22% of tones end up "inconclusive" and are muted, including good ones.

## Why the room measure does not move

The whole-room measure is dominated by a single room, `old-004-r0`. One strong tone there is worth up to 9.8 dB in the scored part:

- **O** happened to keep it on the recorded seed: 5.8 dB for the room.
- **S** found an even better setting on that seed (5° from the oracle against O's 8°), but the unchanged original check then muted it.
- **C** and **SC** muted it as inconclusive, because the background in that room is unstable.

Without this room, S is ahead in 4 rooms by more than 0.1 dB and behind in none. That observation is post hoc and does not change the frozen verdict.

## Sensitivity (descriptive)

- **Listener noise 0.5 dB and 2 dB.** The pattern is the same: S cuts phase error and adds useful keeps, C cuts harmful keeps and adds inconclusive mutes.
- **C at 2 dB noise.** C is significantly worse than O: −0.09 dB (−0.24 to −0.01).
- **Every noise level.** No arm helps.

## Verification

Details are in `verification.json`.

- **Frozen code.** The code hashes match the frozen protocol.
- **Parity.** Arm O reproduces the saved v2 tuning in all 37 rooms (780 parity fields) and the saved room scores exactly.
- **Recomputation.** An independent recomputation reproduces every paired mean.
- **Tests.** The unit tests pass (8/8).

## What this means for next steps

- **Keep the search change** as the leading candidate. It is the only change that improved the settings themselves.
- **Next: a better keep-or-mute decision.** It should keep more of the useful settings without bringing back the harmful keeps. Its design should come from what this run showed:
  - a strict all-or-nothing stability gate wastes too many pairs;
  - one noisy pair-based veto loses whole rooms;
  - candidate ideas, none frozen or tested yet:
    - weight each pair by how stable its background was;
    - use shorter, interleaved on/off intervals so the background has less time to change;
    - keep tones whose sweeps showed a strong, consistent quiet point.
- **Fresh data.** Any winner still needs fresh source recordings before it is believed.

## Limits

- **Development data.** These are seen rooms; the result chooses where to spend effort, not what works.
- **Simulated listener.** Listener noise, "same" threshold and press model are assumptions, not measured hearing.
- **Simulated microphone.** It hears no earphone leakage, and its background follows the same source as the ear's.
- **Unvalidated.** Quiet-machine timing and physical ANC remain unvalidated. The live app stays on v2 with the original tuner.
