# Fresh test of the unchanged two-second selector

21 October 2026. Preparation only; no fresh audio has been inspected or scored.

Claude withdrew the audit's median-based development stop in message #43. Recomputing the saved 30-source results confirms +0.74956 dB mean paired gain for L2 and +1.02734 dB for the window benchmark, despite L2's zero median. Both the marginal method medians and paired median in the original report are arithmetically correct. The new interpretation changes the endpoint after results were seen; the original protocol, outcome and results remain intact.

At a 0.01 dB practical tie tolerance, L2 has ten wins and no losses at 20 ms, and three losses at 120 ms (worst -1.61318 dB). At a numerical tolerance of 1e-8 dB there are eleven wins at 20 ms and five losses at 120 ms; the extra changes are smaller than 0.01 dB. Report both tolerances. The 16 longer sources have +1.40541 dB mean gain, but this is a post-hoc association with source duration, not proof that short clips cause ties. L2 already has a two-second completed-error history and calibration replay before scoring.

## Frozen design to implement before new audio

- Candidate: exactly the existing `causal_mix` with L=2 seconds, a 1 dB switch margin, a 100 ms sample-linear crossfade, v2 before three seconds, and only fully matured target blocks. Its arms remain v2 + gate, the unchanged per-tone fade + gate, and zero. No new model tuning.
- Primary: mean of per-recording paired tone-prediction gain against v2 at 20 ms. A two-sided percentile source-bootstrap 95% interval (50,000 resamples, seed 20261021) must have its lower endpoint strictly above zero. Treat recordings, not windows, as sampling units.
- Require at least 30 usable fresh acoustic recordings, including at least 20 with reference tones. If either minimum is missed, the test is inconclusive regardless of score; do not add or replace files after inspecting audio or results.
- No strong source (v2 tone gain at least 3 dB at 20 ms) may lose more than 1 dB. Public recording-by-horizon band-boost cases across 20 and 120 ms must be no more than v2's, and there must be no whole-band boost cases. Existing thresholds remain >=1 dB in any third-octave band and >0.5 dB whole-band amplification.
- Report both horizons separately, mean and median, both win/loss tolerances, all per-source scores and worst losses. Passing the 20 ms primary test does not validate wireless use or guarantee non-regression at 120 ms.
- Preserve all no-tone and negative controls. Tone labels are derived only from the reference waveform for scoring, with the unchanged detector; they never enter the candidate. A label is not proof of temporal stationarity.

## Source selection before downloading

Seek 40 public, freely licensed acoustic machinery/vehicle/appliance recordings from metadata only, at most one per uploader and one per credited recording author where identifiable. Exclude filenames, hashes and obvious source/capture duplicates from all previously used or reserved recordings. Prefer different credited recording sources from the old pool; disclose any collection-wide overlap. Metadata cannot prove independent acoustic captures.

Use at least 51 seconds of source audio, capped at the first 90 seconds. The first 40% is the existing calibration/normalization prefix and only the suffix is scored; after horizon trimming require at least 30 seconds of actual scored samples for each horizon. Do not loop, concatenate, select a favorable crop or choose intervals after listening. Audio-bearing video containers are eligible only when their metadata describes the target machinery; decode the first audio track and keep channel zero with the same causal resampler. Report absent/short/undecodable audio rather than replacing it.

Aim for fan/HVAC, other stationary machinery/appliances and transport engines. Exclude music, speech-led material, synthetic tone demos and compilations on metadata. Search may broaden before any audio is downloaded. Freeze the complete identities, URLs, sizes, checksums, licences, uploader/author groups, source rationales, acquisition limits, runner/test hashes and all analysis rules in `results-selector-fresh-01/protocol.json` before acquisition or scoring. Metadata refreshes are permitted; a changed file identity after freeze is missing, not a substituted input.

This document is the written preparation rule; it is not the final hashed protocol. Do not relax eligibility silently if a suitable cohort cannot be assembled. Existing raw audio stays local. No live engine change, audio playback, capture or physical ANC claim is part of this test.
