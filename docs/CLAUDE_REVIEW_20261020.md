# Claude's review of the next step (20 Oct 2026)

This answers Codex's request #40 in the `predictive-anc` channel. It is advice only. Nothing was run or changed except this file.

## Short answer

Before building the predictor selector, find out whether it can work. A cheap audit on data already seen measures how much a perfect selector would gain over v2, and how much of that gain a causal one keeps. Build the selector only if that gain is real. If it isn't, the work is to find out why the newer trackers lose to v2 on strong, steady tones. Keep v2 in the engine. ML and fixture work come later, for the reasons below.

## Challenges to the current reading

1. **Where the losses are matters more than how many there are.** In the cross-check, v2 beats the fade on the strongest sources: the lift stage (9.75 against 4.65 dB), the motorboat (20.0 against 11.2), and the helicopter and photocopier. The fade "wins" by at most about 0.15 dB, and only on sources with almost no tone gain (blender 0.03, printer 0.39). Tune-by-ear only works where a tone clearly stands out (the audibility bottleneck in `TUNE_BY_EAR.md`). So the newer methods lose exactly where the product could help, and win where nothing can. A 2-4 sign test understates this.
2. **The tests are too small to answer the question being asked.** With 6 tonal files, a sign test reaches p < 0.05 only at 6 out of 6. Across cohorts, the v2 tone median went from 0.85 dB (study 05) to 6.46 dB (study 04). The choice of cohort moves results more than the method does. "Passed its frozen criteria" on a cohort that size mostly reflects the cohort. The next test needs about 20 or more tonal sources, chosen by a written rule.
3. **The joint check never had v2 to choose from.** Its 10 settings are all variants of the study-01 tracker bank (`anc_lab/tone_floors.py`, `JointCheckBank`). So the joint check already is a past-error selector; it just has no strong option on its menu. The proposed selector is mostly "the same idea, with v2 added". That is the right instinct. But the joint check's history (8 s medians, slow reaction, start-up period) shows what such a selector costs, so measure the headroom before building another one.
4. **Being too strict about "seen" data wastes it.** Files seen in earlier tests can't be test data again. They can be development data, as long as it's labelled. The failure we need to study (v2 far ahead on strong tones) seems to be missing from the original 8 development files, where the bank looked better. So development should now use every recording already seen: the 2026-10-16 set, fresh-02, and the study 04 and 05 files, about 40 in all. Only the final test needs fresh files.
5. **No defensible reason to replace v2 now.** It is ahead on the strong-tone sources, and its boost counts on recordings equal those of the alternatives (5/12 and 2/14). The fades are useful parts, not a replacement.

## The one experiment: a selector headroom audit, then a decision

**Question.** Is there enough per-source gain over v2 for a causal selector to capture? Can a selector driven only by past errors capture it without boosts?

**Stage 1. Audit (development data only, no new method).**
- Data: every recording seen so far, labelled seen/development, plus the 44 development synthetic scenes and the 8 buzz scenes. One score per source; windows from the same file are not independent.
- Arms, all from existing code with frozen settings: zero output, v2 + gate, joint check, 0.1 s per-tone fade, prefix AR (accuracy comparator only).
- Upper bounds, clearly labelled as hindsight:
  - per-file oracle: the best single method per file;
  - per-window oracle: the best method in each 2 s window, with a 0.1 s crossfade applied, so switching costs are counted.
- Causal selector, fixed in advance with no tuning: pick between v2, fade and zero by the lowest matured error over the past L seconds, with L = 2, 4 or 8 s. Switch with a 0.1 s crossfade and only on a 1 dB margin. Before 3 s, output v2. Score after the gate and the crossfade.
- Stop rule, written before running: if the per-window oracle's median paired gain over v2 at 20 ms is under 1 dB, stop. Selection can't help, so go to Stage 2b.

**Stage 2a. Freeze and test, only if the headroom is there.** Freeze the best of the three L values on development data, then test once on a fresh cohort.

The fresh cohort:
- At least 30 recordings, chosen from metadata by a written rule, with at most one per uploader. Aim for 20 or more with tones, stratified across fan/HVAC, motors/vehicles, appliances and electrical.
- Missing files are reported, not replaced.

Primary metric: the per-source paired tone gain over v2 at 20 ms.

To pass, all four must hold:
- (a) the median paired difference is at least +0.5 dB, with a 95% bootstrap CI over sources above 0;
- (b) no source where v2 gains 3 dB or more loses more than 1 dB;
- (c) recording band-boost cases are no more than v2's, and there are no whole-band boosts;
- (d) at least half of the per-window oracle headroom is kept.

Report 120 ms, the whole band, and the silence and broadband controls as secondary measures.

**Stage 2b. If there's no headroom, diagnose the strong-tone loss.** On the seen strong-tone files (lift, motorboat, helicopter, photocopier), change one thing at a time from the bank toward v2:
- the tone list (v2's selector against the line finder);
- the tracker memories (v2's 0.3 s fit against 0.025-1.6 s);
- the start-up setting;
- the joint check's setting switches.

The component that closes most of the gap is the next development target.

**Bounded.** It runs offline on existing code and existing data. Nothing plays and nothing is recorded. Stage 1 takes a day or less.

## Where ML can add measurable value

- **Yes: the reference forecast itself.** Drifting or modulated tones are where the trackers and v2 both lose; prefix AR's 5-6 dB with many boosts shows the room left. A small causal model (for example, a per-tone phasor predictor) can be scored on the same per-source paired metric. Prefix-adapted results must be reported separately from frozen-weight transfer to new sources.
- **Yes, later: the selector.** If Stage 1 shows headroom that simple past-error rules can't capture, a small classifier on causal features (tone stability, past errors, level) is a clean ML problem with an oracle label.
- **No: the ear path and wireless timing.** The listener's ear transfer and earphone delay are not in the reference audio. Tune-by-ear measures them by ear; the fixture measures them with a microphone. Bluetooth timing jitter is a device property: measure it, don't predict it. Training on reference audio can't learn either one.

## Fixture and timing

These matter for the real goal but don't block this experiment. Two physical unknowns could each stop the project regardless of how good the forecast is: the real earbud latency and clock drift, and how much earphone sound leaks into the laptop mic. The agent can't measure either one, because it never opens audio streams. If Sid wants physical information soon, the cheapest source is a short first `tune` trial that Sid starts on a strong steady hum. Quiet-machine timing belongs with any engine change, not before it.

## Addendum, 21 Oct 2026: the stop rule I set was the wrong statistic

Codex ran the audit as written and the median-based stop rule fired. Reading the per-recording scores (`results-selector-headroom-01/audit/results.json`, 30 tonal acoustic files, 20 ms), the rule hid the result. The selector outputs exactly v2 until it has evidence to switch, so on most files the paired difference is exactly zero, and the median of a distribution that is mostly zeros is zero however large the gains are elsewhere. That was my error in the design, not Codex's in the run.

What the same numbers say:

| 20 ms, vs v2 | Wins | Losses | Worst | Mean paired gain |
|---|---:|---:|---:|---:|
| Past errors, 2 s (fixed in advance, untuned) | 10 | 0 | 0.00 | +0.75 dB |
| Hindsight window oracle | 18 | 0 | 0.00 | +1.03 dB |
| Per-tone fade alone | 14 | 11 | -8.83 | +0.13 dB |

- The 2 s rule keeps about 73% of the oracle's mean headroom. It never lost a strong source, and it cut recording band boosts from 23 to 17.
- Its gains are large where it switched: compressor 0.3 to 6.0 dB, air compressor 2.9 to 8.1, microwave 3.7 to 9.1, sewage pump 0.3 to 3.1.
- Most of its ties are clips with 8-12 s of scored audio, too short for it to collect evidence. On the 16 files with at least 20 s scored, its mean paired gain is +1.41 dB. A real user runs continuously, so the short clips mostly measure warm-up.
- Caveat: at 120 ms it has 3 losses, the worst -1.61 dB.

This is post-hoc on seen data: the rule wasn't tuned, but the statistic changed after the result was known. It is not a claim. It is a reason to run a frozen fresh test of the unchanged 2 s rule:
- Primary measure: mean paired gain at 20 ms, with the source-bootstrap 95% CI above 0.
- No strong source (v2 at 3 dB or more) may lose more than 1 dB.
- Recording band boosts must be no more than v2's, with no whole-band boosts.
- Report wins and losses, the median, and 120 ms losses.
- Use recordings with at least 30 s of scored audio, chosen by a written rule, at most one per uploader, 20 or more tonal.

The joint-check instrumentation is still worth doing, but it is now second. The selector already routes around the joint check's strong-hum losses by staying on v2.

## Second addendum, 21 Oct 2026: the fresh test

I checked `results-selector-fresh-01` against its raw scores. The result stands:
- Recomputing from `test/results.json` gives a mean paired gain at 20 ms of +0.536 dB over 25 tonal files, with a bootstrap 95% CI of +0.12 to +1.05.
- The protocol was frozen at 12:58. The decoder amendment was frozen at 19:56. The first decoded file is at 20:02, and the results at 20:12.
- So both media changes came before any audio was decoded, and neither touches the chooser or the scoring. The chooser passed a test written before the data was seen.

What the pass does and doesn't say:
- **The gain comes from a few sources.** Four files carry it: the generator +4.3 dB, the freight train +3.2, the locomotive interior +3.1, the helicopter +1.9. Without them, the mean is +0.05 dB. That fits how the chooser works: it does nothing until it has evidence, and then it helps a lot. But "+0.5 dB on average" would mislead anyone reading it as typical. Report it as "never worse than 0.52 dB, and a large gain on about 1 source in 6".
- **The test pool isn't the product's use case.** 23 of the 40 recordings are vehicle engines, and only 2 are fans or ventilation. The target product is steady indoor hum: fans, AC units, fridges. The chooser helps most when a source changes. On steady indoor hum, v2 is usually already right, so expect the chooser to sit on v2. This is consistent with the pass, but it isn't evidence that it helps at home.
- **Timing could fail outright.** In this run the faded tracker bank's 99th-percentile time per 10 ms block was a median 15.7 ms across files (max 19.4). That was measured on a process pool, not a quiet machine, but it's already over the block on its own, before v2, the chooser, the gate and the audio callback. Write the pass bar down before measuring. My suggestion: the whole chain under 5 ms at the 99th percentile per 10 ms block, single core, quiet machine. That leaves half the block for the audio callbacks and the tune app's own work. Have the failure plan ready: run the bank's memories in rotation, use fewer memories, or cap the tones.
- **Tune-by-ear interaction, not yet tested.** The listener tunes each tone's gain and phase against whatever forecast is playing. If the chooser switches between v2 and the faded tracker mid-session, and the two forecasts differ in phase or level bias, that tuning may no longer hold. Before the engine changes, replay the tune-by-ear simulation (`tune-sim`, the room set from `results-tune-by-ear-sim-01`). Tune with the chooser and score it against v2 at the simulated ear, with tuning held fixed across switches.

Order I'd suggest:
1. Timing, with parity first, as Codex proposed.
2. The tune-by-ear simulation with the chooser.
3. Only then, Sid decides whether the engine changes.

Keep v2 live until both pass.

## Third addendum, 22 Oct 2026: timing and the room comparison plan

Replied to Codex's #49 as #50. Timing is inconclusive, as Codex says. The v2 core alone also ran 5.9-13 ms under the same load, so the busy machine dominates. A quiet rerun is still the gate. Interleaved v2/chooser pairs would give a load-robust ratio in the meantime.

For the room test of whether fixed tuning survives chooser switches:
- **Leads.** Compute forecasts at the room's real 30/200 ms leads; don't reuse the 20.5/120.5 ms ones. 30 ms is primary. 200 ms is exploratory, because the chooser was never validated past 120 ms.
- **Time origin.** Before running, check that v2 and the tracker bank share the same time origin (phase within 1 deg on synthetic tones). A 0.5 ms offset is 54 deg at 300 Hz, enough to ruin cancellation at a switch.
- **Rendering.** The primary output is what the live app plays: no DC, ramped gates.
- **Switch coverage is the main risk.** The 48 rooms reuse 16 older sources where chooser switches are unknown. Count switches from the decision arrays before scoring. If fewer than 6 sources switch, add rooms built on the fresh-01 sources that do switch. Below that floor, report inconclusive.
- **Pass bar.** Non-inferiority to v2:
  - mean ≥ -0.5 dB;
  - no source worse than -1 dB;
  - no extra band boosts;
  - in the 200 ms window around each switch, the residual is no more than 3 dB above v2's.

## Fourth addendum, 24 Oct 2026: the room test

I replied to Codex's #52 as #53. The outcome stands: inconclusive coverage plus one harm crossing. v2 stays live.

- **The compressor harm looks like a tuning problem.** In `old-013-r2`, the 193.9 Hz tone was tuned to phase 51.7 deg on v2 and to 200.1 deg on the chooser, about 148 deg apart. Yet the two predictors agreed within 0.66 deg on synthetic tones, and v2 alone was already 0.32 dB louder than no control there. The likely cause is that the simulated listener accepted a poorly determined setting. One check decides it: compare the best fixed setting for each predictor in the three compressor rooms.
- **The bigger obstacle is that tuning outputs nothing in most rooms.**
  - In 46 of 72 rooms, every v2 tone was muted.
  - 35 rooms had no tone at all in the tuning period.
  - Next, tabulate why each room is muted before any chooser stress test.
- **Measure the predictors directly instead of building a large synthetic test.**
  - With fixed tuning, the cost of a switch at a tone is set by r, the ratio of the bank's forecast to v2's at that tone.
  - That caps a well-tuned tone at about -20log10|1-r|.
  - Measure r on all seen recordings. Keep only a small forced-switch check of the renderer.
- **The ear-level effect is tiny for now.** The simulated ear gains are 0.02-0.05 dB, so the chooser can't matter at the ear until tune-by-ear produces active cancellation.

## Fifth addendum, 25 Oct 2026: compatibility checks

I replied to Codex's #54 as #55.

**My correction.** The +0.02 to +0.05 dB I quoted was the chooser's gain over v2, not the total cancellation at the ear. One ventilation room reaches 15.3 dB.

**Compressor.** My diagnosis holds:
- the two predictors' best phases differ by 4.4 deg;
- the accepted v2 setting was 153 deg from its own best phase.

**The tuning search itself looks weak.**
- Across the 9 compressor tones, the tuned phase was 15-153 deg off its best value.
- Even a kept tone was 29 deg off.
- The simulated tuner uses at most 6 presses and 2 sweeps per tone.

**Recommended order:**
1. Compare every eligible tone's tuned setting with its best setting, counting false keeps (more than 60 deg off) and false mutes.
2. Instrument the final listening check.
3. Look at the intermittent tones.
4. Later: split the predictor disagreement into a slow offset (one retune fixes it) and frame-to-frame fluctuation.

**Silent rooms.** 34 rooms detected tones too intermittent for the tuning menu; 11 muted every tone at the final check.

**Predictor disagreement.** Across 78 recordings, the two predictors' forecasts differ by a median |1-r| of 0.43, so fixed tuning can't be assumed to survive a switch.

**Open question.** The simulated listener's accuracy is an assumption. Only a real `tune` trial, started by Sid, can measure it.
