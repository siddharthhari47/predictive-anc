# Fixed tuning through chooser switches: frozen development experiment

22 October 2026. Implements Claude review #50. All signals are computed offline; the live v2 engine is unchanged. This is an integration check on seen recordings in modal rooms, not new-source validation, a listening test or physical ANC.

The original 48 rooms (16 recordings, three draws each) have been reproduced exactly: 59,939 compared numbers, maximum difference zero. A separate, prewritten alignment check passed on four synthetic frequencies from 47.3 to 343.7 Hz, steady and drifting 0.01 Hz/s, at both room leads: maximum inter-predictor phase difference 0.658 degrees, level difference 0.0128 dB. These are bounded controls; agreement on them is not a general bound on prediction bias.

## Timing, decisions and output

Both predictors consume the same samples starting at x[0], and their phasors refer to newest sample `seen-1`. Native live block origins are 19,39,... rather than the older reference-study grid 20,40,... . The numerical chooser rule is unchanged and separately checked against the original batch rule on this native grid. A future-tail perturbation check confirms prefix decisions and forecasts remain identical.

The primary chooser still uses completed, hard-gated **20 ms** errors: two-second window, 1 dB margin, 100 ms sample crossfade, 3 s start floor. It uses the original bank's 20 ms group components. Output is synthesized at the actual **30 ms** lead: horizons 60..79 after each newest sample. The exploratory **200 ms** output uses the existing 120 ms decision stream and that bank group's components, extrapolated at horizons 400..419. No 20 ms waveform block is moved to stand in for a 30 ms prediction. The 200 ms extrapolation has no inherited accuracy claim.

Primary output uses the native live renderer separately for each predictor: per-tone settings, no DC, and block-ramped gates, followed by L2's sample weights. The chooser continues to select on hard-gated errors while its emitted output is ramped. This difference is the integration under test. Secondary reference diagnostics retain hard gates and DC, with output recomputed at the actual room lead; those are microphone prediction metrics, not simulated-ear benefits.

## Coverage before ear outcomes

Prepare all 48 original rooms and store causal traces, but do not score candidate ear attenuation yet. Count every scored-suffix decision and whether a prefix-menu tone has nonzero command during the transition. A qualifying source needs a command-exposed transition with a complete 200 ms window. The primary coverage floor is six distinct sources at 30 ms.

If fewer than six qualify, append all three seeded rooms for each fixed, already-seen fresh-01 source: 005,010,018,021,023,025,026,035. This includes the previously observed switching sources and all four accuracy gain carriers. Use their saved reference arrays as dry sources, no new downloads or favorable crops. These 24 additions are deliberately enriched development examples, not a representative sample. There is one conditional expansion only. Report the original48 group separately. Seal source inclusion and coverage receipts before ear scoring. If coverage remains below six, the result is inconclusive even if all numerical scores tie.

## Comparisons and pass rule

Use the original first 40% prefix, warm-up, seed stream, tone menu and simulated listener (judgement noise 1 dB). Keep the same prefix-selected frequencies in all arms; bank tones outside that menu remain untuned and silent. This controls the switch/tuning question, not the later new-tone user experience. Settings remain fixed throughout the suffix.

Arms: zero; v2 tuned on v2; chooser reusing v2 tuning (**primary**); chooser tuned on itself; and a separate noncausal retuning bound. The bound fits unconstrained per-tone complex coefficients after each suffix switch using future ear errors, retains filter transients and ignores the output cap. It is an upper bound only for that specified unclipped linear family and cannot support a pass.

First average paired tone-attenuation differences over rooms within each source; then weight sources equally. Keep no-tone rooms in all amplification and switching reports. Primary 30 ms criteria:

- Mean paired difference at least -0.5 dB, with a source-bootstrap 95% lower bound at least -0.5 dB (20,000 draws, seed 20261022). An interval crossing the margin is inconclusive when the point/harm checks otherwise pass.
- No source's mean difference below -1 dB.
- No new room/source/third-octave amplification over 1 dB where v2 is at or below 1 dB; no new whole 35–350 Hz amplification over 0.5 dB. List all band levels, including already-amplified baseline bands.
- In every complete +/-100 ms window around the first arriving command of each suffix switch, candidate 35–350 Hz residual power no more than 3 dB above simultaneous v2. Include modeled extra earphone delay. List every switch and incomplete/boundary window. This engineering energy criterion **does not establish inaudibility** or calibrated sound pressure.
- No clipped-fraction increase over v2 exceeding 1e-6.

Report own-tuning and 200 ms outcomes separately under the same descriptive checks; 200 ms remains exploratory. Log all prefix switches, muted settings, extra clipping, source aggregation and the original cohort separately. Failure or inconclusive coverage cannot be relabelled safe. No promotion to the live engine follows automatically.

## Timing limitation

The preceding timing run remains a contended diagnostic. Slow v2 under load supports caution but does not identify how much delay was caused by contention. Alternating cached-v2/cached-chooser pairs can give a better interim comparison; they do not guarantee equal background load or replace the quiet-machine p99 gate. No new performance claim is made during room computation.
