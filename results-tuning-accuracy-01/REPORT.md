# Tuning accuracy and final-check diagnosis

26 October 2026 · Completed response to Claude review #55

**The simulation identifies two problems: finding a useful setting, and judging it against changing sound.** Six of 40 kept tones made their own auditory band louder during the tuning portion. Ten of 38 muted tones had at least 1 dB of potential band reduction at a better setting; only three had already reached that benefit before the final check. This supports improving tuning, but does not establish that extra button presses alone will solve it.

All results are **simulated-ear diagnostics on already-seen recordings**. The live app remains on v2. No new candidate, physical noise cancellation or measured human judgement accuracy is claimed.

![Tuning diagnosis](C:/Users/talk2.000/Desktop/Claude/predictive-anc/results-tuning-accuracy-01/tuning-diagnosis.png)

## What was evaluated

Every eligible tone from the original primary 30 ms v2 runs: **78 tones in 37 simulated rooms, representing 14 source recordings**. The remaining 35 of 72 rooms had no eligible menu and remain in the inventory. The existing 1 dB listener model, settings, random draws and time intervals were preserved. All 37 original tuning runs reproduce: **1,681 saved summary/setting fields agree**.

The best-setting reference fits two native phase bases to known simulated-ear pressure in each tone's auditory band, using only the tuning prefix after the 1.5-second warm-up. It is a signal-aware linear oracle, not information available from the laptop microphone. Performance after the prefix is evaluated without refitting; that later audio is already development data from earlier studies, not an untouched test.

## Search accuracy

| Quantity | All 78 | Kept 40 | Muted 38 |
|---|---:|---:|---:|
| Median absolute phase error | 26.7° | 9.5° | 46.0° |
| Median absolute gain error | 4.43 dB | 2.12 dB | 9.80 dB |
| Phase error above 60° | 21 | 6 | 15 |
| Median single-tone band reduction before final check | +0.20 dB | +1.41 dB | +0.001 dB |

The compressor is a bad tail case; the typical kept setting is substantially closer than its phase error suggests. Short prefixes allow one sweep turn each way for 21 tones; 57 allow three turns each way. Their median phase errors are 31.6° and 24.9° respectively. These different source groups do **not** establish a causal benefit from extra presses. Presses are also missed by the model; the observed count ranges from one to six.

A phase error above 60° is not a universal harm rule. An ideal sinusoid's residual power factor is `1 + a² − 2a cos(θ)`, where `a` is the relative amplitude. Here a 73.4° setting still improves its band by 0.14 dB, while a 59.4° setting makes its band louder. The actual rendered result determines harm.

## Kept settings that made their band louder

Each row evaluates that one tone through the native output cap and simulated path; positive means attenuation, negative means amplification. These effects cannot be summed into a whole-room result.

| Room / tone | Phase error | Tuning portion, dB | Later portion, dB |
|---|---:|---:|---:|
| fresh-021-r2 / 195.0 Hz | 59.4° | -0.209 | -0.046 |
| old-001-r0 / 164.1 Hz | 89.5° | -0.321 | +0.000 |
| old-003-r1 / 196.6 Hz | 169.4° | -0.705 | -0.066 |
| old-004-r0 / 173.1 Hz | 92.9° | -0.159 | -0.143 |
| old-013-r2 / 193.9 Hz | 152.6° | -1.835 | -0.469 |
| old-014-r2 / 86.1 Hz | 157.5° | -0.112 | -0.113 |

All six worsen their tuning band by more than 0.1 dB; two exceed 0.5 dB and one exceeds 1 dB. Five remain harmful later, three by more than 0.1 dB. A different kept tone becomes slightly harmful only later: six later harms overall, none above 0.5 dB. The original whole-band compressor crossing remains unchanged; it uses a different outcome than this per-tone auditory-band diagnostic.

## Muted tones: missed search opportunities versus rejected good settings

The grid was written down before this diagnostic ran. A "best-setting candidate" applies the original gain bounds and digital cap to the prefix oracle. It is a feasible benchmark, not a claim that a listener can find it.

| Band reduction threshold, dB | Muted: best candidate reaches it in prefix | Also reaches it later | Muted: setting already found reaches it in prefix | Also reaches it later |
|---|---:|---:|---:|---:|
| 0.1 | 30 | 25 | 12 | 7 |
| 0.5 | 21 | 13 | 4 | 2 |
| 1 | 10 | 6 | 3 | 2 |
| 3 | 3 | 1 | 1 | 1 |
| 6 | 1 | 0 | 0 | 0 |

At 1 dB, the ten potential opportunities span nine rooms and five sources; six persist into later audio across six rooms and four sources. Seven of those ten never reached a 1 dB setting during search. Three did reach it but were rejected, and two of those still provide at least 1 dB later. Calling all ten final-check errors would conflate search with acceptance.

All 78 linear fits are identifiable, with condition numbers 1.0000–1.0088. One unconstrained oracle lies outside the original gain range. Five oracle commands and three pre-check commands clip somewhere in the retained recording; the reported band scores include the native digital cap. The gain-bounded benchmark is not claimed to be the exact optimum of the nonlinear capped problem. All ≥1 dB muted-opportunity counts are unchanged by imposing the gain bounds.

## What the final checks actually compared

The observer logged all 156 final A/B pairs, including their actual noise draws, without changing choices. It also compared on/off at each identical recording interval with earlier kept tones present. This distinguishes the anti-hum's local effect from differences between successive recording segments.

- **Compressor false keep:** `old-013-r2`, 193.9 Hz. In the first check the noiseless sequential on-minus-off difference was **+1.481 dB** (on louder), but judgement noise changed it to **−0.266 dB**, recorded as "same". In the second check there was no modeled on/off level difference in either interval; background change produced +0.343 dB and noise changed that to **−1.052 dB**, recorded as "on". "Same" plus "on" passed. With these fixed settings and presentations, the existing noise model gives an **8.30%** keep probability.
- **Microwave false mute:** `old-004-r1`, 300 Hz. The setting already reduces the full-prefix auditory band by **3.71 dB**, and the later band by **4.88 dB**. One check wraps from 13.5–15.5 s back to 1.5–3.5 s. Anti-hum reduces the second interval by **2.21 dB**, but its background is **6.90 dB** louder than the earlier off interval. The comparison therefore says on is **4.69 dB louder**, before any judgement noise. The next check strongly prefers on, but one off answer vetoes it.
- **Locomotive false mute:** `old-014-r0`, 91.3 Hz. A setting providing +1.31/+1.54 dB prefix/later benefit is rejected when a **4.33 dB background rise** overwhelms its 1.86 dB local reduction. This pair does not wrap the recording, so wrapping is not the only issue.

Across all final pairs the median absolute background difference is **0.69 dB**, the 90th percentile **3.87 dB**, and the maximum **11.93 dB**. Eleven pairs wrap the tuning prefix. Nine pairs have no modeled on/off level difference in either interval; four belong to ultimately kept tones. These are hearing-metric nulls, not proof of zero physical output.

Seventeen of 40 kept settings average less than 1 dB of same-interval benefit in their final checks. With settings and intervals held fixed, removing only the final comparison noise would reject four actual keeps and retain three actual mutes. That is a conditional counterfactual, not a rerun of a noise-free tuner. Three of the six prefix-harmful keeps would still be kept by their noiseless sequential checks because background variation favors them.

The 1 dB noise is **per presentation**. Difference noise has a standard deviation of √2 dB; the "same" zone is ±1 dB. Even a true null has a **30.7%** probability of passing two checks under this model. These are consequences of assumed listener behavior, not measured human error rates. Sweep presses use a different reaction-delay/miss/window model.

## Verification and next work

Ten targeted unit checks passed, including complete synthetic-session parity, prefix isolation and RNG preservation. **2,803 numerical audit checks** reproduced normal-equation fits, direct native rendering, all capped scores and the nine earlier compressor fits; maximum difference **5.68e-14**. The observer reproduces all saved tuning settings and summaries. Cached traces, native rendering and filter primitives are shared; this is not an independent physical model.

Eight raw Gaussian "same" tail probabilities had tiny negative roundoff (at most 8.31e-24). A separate, saved reporting correction computes nonnegative tail differences; maximum change in any keep probability is 3.33e-16. No raw result, decision, setting or audio score was changed. See [stable probabilities](C:/Users/talk2.000/Desktop/Claude/predictive-anc/results-tuning-accuracy-01/check-probabilities-stable.csv) and [correction receipt](C:/Users/talk2.000/Desktop/Claude/predictive-anc/results-tuning-accuracy-01/probability-roundoff-correction.json).

**Next: isolate search accuracy and comparison validity in a bounded development experiment.** Use these logs to design an ablation of extra/clearer phase evidence versus checks that require active, sufficiently comparable tone evidence. A same-recording-segment oracle is a diagnostic control only; a real listener cannot replay the environment at will. A deployable check must use causal activity/stability evidence and repeated or shorter comparisons. Do not relax acceptance or widen the tone menu from these results alone. Intermittent detections and predictor-switch compatibility remain later work.

Quiet-machine timing and user-started physical validation remain separate open requirements. No audio was played or recorded, and the live engine and all previous frozen studies are unchanged.

Files: [protocol](C:/Users/talk2.000/Desktop/Claude/predictive-anc/results-tuning-accuracy-01/protocol.json) · [tone table](C:/Users/talk2.000/Desktop/Claude/predictive-anc/results-tuning-accuracy-01/tone-diagnostics.csv) · [all check trials](C:/Users/talk2.000/Desktop/Claude/predictive-anc/results-tuning-accuracy-01/check-trials.csv) · [verification](C:/Users/talk2.000/Desktop/Claude/predictive-anc/results-tuning-accuracy-01/verification.json) · [full logged tuning](C:/Users/talk2.000/Desktop/Claude/predictive-anc/results-tuning-accuracy-01/acceptance-results.json)
