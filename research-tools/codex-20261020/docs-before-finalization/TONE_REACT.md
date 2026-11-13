# Fading tones in and out of the joint check

Claude's 19 Oct development work was tested by Codex on 20 Oct 2026. Status: **passed all frozen questions; the frozen test is complete.** Study folder: [results-tone-forecaster-05](../results-tone-forecaster-05/). The development history below is retained; the fresh test result is recorded separately.

**Reference-signal prediction only.** Every score is how well the recording microphone's own signal is predicted 20 ms or 120 ms ahead. Nothing is played, there is no acoustic path and no ear measurement, and no real cancellation is claimed.

## Why

Study 03 ([TONE_CAP.md](TONE_CAP.md)) found that 14 of the joint check's 25 development boosts were on scenes where the sound changes suddenly at 9 s: a tone appears, the tones stop, or one source gives way to another. One more was on the 5 s mains clip, before the check's first decision. Its guess was that the check's 8 s of medians react too slowly. This study asked whether the check can react faster to a change and to the start of a recording without losing its tone gain over v2.

Buzzing_Speakers.ogg and the other study-02 fresh files are seen now, as are the study-01 test files, so none of them was used. Everything up to the freeze ran on the study-01 development recordings, the 44 development synthetic scenes and study 03's 8 buzz scenes.

## What the diagnosis showed

The trials ran before the rule was written. They're in [results-tone-forecaster-05/diagnosis](../results-tone-forecaster-05/diagnosis/README.md).

- **A faster check can't fix the change boosts.** Holding any one of the check's ten settings for the whole scene gives 15 to 17 boosts on the 9 change scenes, against the joint check's 14, so no choice made sooner helps. An oracle that silences the output the instant the sound changes, which no causal method can do, still leaves 9.
- **A perfect tracker has them too.** The clean synthesized tones themselves, switched on and off with no delay, give 15. With a 0.1 s fade at each switch they give 5.
- **So the boosts come from switching.** The signal has one edge where a tone starts or stops. An output that switches a strong tone in one block puts a second edge into the error, and that spreads into the next third-octave band.
- **The start case is the start setting, not speed.** On the 60 Hz mains clip the start setting boosts one band by 1.35 dB. A 0.2 s start floor removes it there but costs about 3 dB of tone on that clip, and more on the synthetic scenes.

## The fades

`anc_lab/tone_react.py`, `FadeCheckBank`. It is the joint check with each tone's output level moved by a slew limit instead of a switch. In each output setting a tone's level climbs from 0 to 1 over the fade-in time while that setting outputs it, and falls back over the fade-out time when it stops. A tone the selector drops while it is still fading out runs on from its last phasor until it is silent. The band check judges each setting as it would be heard, fades included. With one-block fades it gives exactly the joint check's output (a check confirms this). `tone_floors.py` is frozen by study 02's protocol, so it was not edited.

After the trials the output step was rewritten as one array step, the way the joint check does it. Side by side, the forecasts were identical; only the compute time changed.

## Development

The rule, written after the trials and before the formal run, needed a candidate to have fewer boosts than the joint check overall and on the change scenes, and no more near-boosts or whole-band boosts. It also had to keep at least half of the joint check's tone lead over v2, stay level on the whole band and the synthetic objective, and keep its 99th-percentile compute time (median over runs) within 0.5 ms of the joint check's in the same run. All counts are gated.

| Development material | v2 + gate | Joint + gate | Fade 0.05 s | Fade 0.1 s | Fade 0.2 s | **0.1 s linear** | 0.1 s + 0.3 s switch | 0.1 s + 0.2 s start |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Boosts, 1 dB (recordings + late synthetic) | 54 | 25 | 18 | 15 | 16 | **15** | 15 | 14 |
| On the change scenes | 14 | 14 | 10 | 7 | 7 | **7** | 7 | 7 |
| Near-boosts, 0.5 dB | 74 | 40 | 33 | 28 | 25 | **26** | 27 | 27 |
| Tone bins, median of both horizons (needed 4.35) | 3.15 | 5.56 | 5.68 | 5.67 | 5.59 | **5.73** | 5.66 | 5.67 |
| Whole band, median (dB) | 0.98 | 1.59 | 2.33 | 2.36 | 2.36 | **2.35** | 2.35 | 2.36 |
| Synthetic objective (dB, needed 6.55) | 7.02 | 7.05 | 7.04 | 7.03 | 7.03 | **7.04** | 7.03 | 6.45 |
| p99 ms per block, median over runs | — | 3.72 | 3.81 | 3.84 | 3.90 | **3.97** | 3.89 | 3.92 |

Five candidates met the rule. The start-floor variant failed on the synthetic objective. The 0.1 s fade, the linear fade and the switch fade tied at 15 boosts, and the linear fade had the fewest near-boosts of the three, so it was picked: [DEVELOPMENT.md](../results-tone-forecaster-05/development/dev-01/DEVELOPMENT.md).

Where its 15 boosts are: one is the start case on the 60 Hz mains clip (unchanged), seven are on the change scenes (4 source change, 3 tones stopping; tone appearing went from 5 to 0), five are on the buzz scenes and only with the gate on, and two are on drifting and fast-wandering tones. The seven left on the change scenes are split over the horizons (4 at 20 ms, 3 at 120 ms), all where tones stop or one source gives way to another. Fading in fixes an appearing tone; fading out can't stop forecasts made just before a stop from running past it.

The fades also raised the whole-band gain, from 1.59 to 2.35 dB. That was not designed for. Most of it is on WWS_Compressor (0.8 / 0.0 dB to 2.5 / 2.4 dB at 20 / 120 ms), where the trackers drop and re-acquire tones often; with fades the check then holds different settings. That this is the reason is likely, not proven.

## The frozen protocol

`results-tone-forecaster-05/protocol.json` froze the linear fade, the code hashes, and the test material before anything was downloaded:

- eight Wikimedia Commons recordings chosen from metadata only: four whose descriptions say the sound starts, stops or changes speed (a fan switched on and off, a cordless screwdriver, an electric locomotive and a metro train starting up), and an electric razor, a propeller plane, a sewage pumping station and a gas compressor exhaust ([fresh-metadata](../results-tone-forecaster-05/fresh-metadata/README.md));
- 84 fresh synthetic scenes (18 of them change scenes) from new seeds, in odd 10 Hz bands, more than 2 Hz from every development frequency and study 03's buzz draws.

The primary question has three parts, answered separately: fewer boosts than the joint check on the fresh change scenes; no more third-octave or whole-band boosts on the fresh recordings; and a tone gain at 20 ms still above v2's. The whole-band gain is reported as a secondary result.

## Test result, 20 Oct 2026

Study 05 passed all frozen questions on 7 fresh recordings and 84 fresh synthetic scenes. At 20 ms, median tone-bin prediction gain was 2.20 dB for the candidate, 2.05 dB for joint + gate, and 0.85 dB for v2 + gate. Recording band-boost cases: 2, 2 and 2, respectively.

The unchanged protocol was executed once after Sid granted full autonomy and authorized necessary downloads. Current Commons sizes and SHA-1s were checked against the frozen list; the downloaded bytes were then verified. No substitutes were used.

Missing recordings: Noise-Pollution-Filters-Bird-Communities-Based-on-Vocal-Frequency-pone.0027052.s001.ogg. Any missing entries remain in the protocol and are disclosed rather than replaced.

- fewer change boosts: **yes**.
- no more recording boosts: **yes**.
- tone gain above v2: **yes**.

Full frozen report: [REPORT.md](../results-tone-forecaster-05/REPORT.md). Independent recount of the saved scores and paired uncertainty: [CODEX_REVIEW.md](../results-tone-forecaster-05/CODEX_REVIEW.md). This audit did not rerun or retune the models.

These are reference-signal prediction results only. The test clips are now seen data and must not be reused as fresh evidence for a later chosen improvement. The live engine remains v2; multiprocessing timings are not quiet-machine qualification.

## Timing

Under the parallel pool the linear fade's 99th-percentile time was 3.97 ms per 10 ms block against the joint check's 3.72 ms (median over runs), and its mean 1.42 against 1.48 ms. In the trial the worst run had swung by 2.5 ms with the machine's load. Timed side by side in one process, the fade code is about 0.1 ms per block slower on average.

## What it means so far

The frozen result above supersedes the development-only expectation. The frozen bar was met on this small sample; this does not establish universal benefit or physical ANC. The engine still uses v2. The two studies address different transitions; their combination has not been validated and needs its own development and fresh test. Quiet-machine timing and near-ear validation remain separate from reference-prediction accuracy.

## Checks

Seventeen new checks in `tests/test_tone_react.py`:

- one-block fades matching the joint check exactly;
- the fade shapes;
- a new tone fading in, and a dropped tone fading out free-running;
- tone matching across selector updates, as the bank does it;
- the switch fade;
- block causality;
- the reported fade counts;
- change-scene boosts counting only the change scenes, and the rule needing fewer of them;
- method names;
- the synthetic test draws avoiding development and buzz frequencies;
- the fresh list being new;
- the freeze recording no candidate and running once, the test stage running once, and development refusing to overwrite;
- the frozen file list covering study 03's.

All 128 checks pass, counting study 04's 19.

## Limits

The development recordings are eight files: six by two authors and two mains clips, and the mains clips never reach a decision. Boost counts move in steps of one, and the three tied candidates differ only in near-boosts. The change scenes are synthetic, with one switch each at 9 s. The whole-band rise was found on development material and isn't explained for certain. Everything is reference-signal prediction.
