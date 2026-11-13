# Softening the gate on the joint check

Claude's 19 Oct development work was tested by Codex on 20 Oct 2026. Status: **did not pass all frozen questions; the frozen test is complete.** Study folder: [results-tone-forecaster-04](../results-tone-forecaster-04/). The development history below is retained; the fresh test result is recorded separately.

**Reference-signal prediction only.** Every score is how well the recording microphone's own signal is predicted 20 ms or 120 ms ahead. Nothing is played, there is no acoustic path and no ear measurement, and no real cancellation is claimed.

## Why

Study 03 ([TONE_CAP.md](TONE_CAP.md)) traced 5 of the joint check's 25 development boosts to the v2 gate. The gate passes or zeros a whole 10 ms block, so each switch is a step in the output, and a step spreads tone energy into the nearly empty bands below 100 Hz. The band check judges each output setting before the gate, so it can't see this. This study asked whether a softer gate removes those boosts without losing the check's tone gain over v2.

Buzzing_Speakers.ogg and the other study-02 fresh files are seen, as are the study-01 test files, so none of them was used. Everything below ran on the study-01 development recordings, the 44 development synthetic scenes, and study 03's 8 buzz scenes.

## The remedy

`anc_lab/tone_gate_fade.py`. Two parts, tried alone and together:

- **A fade.** The gate decides exactly as before, but its decision moves a gain up or down by a fixed step per block instead of switching it. A cosine fade over 8 blocks takes 80 ms each way. A one-block fade is the v2 gate (a check confirms this).
- **A gated check** (`GatedCheckBank`). The joint band check, but it judges each setting after its own copy of the gate and fade, so it sees what the switching adds.

`tone_floors.py` and the other study-02 and study-03 files are frozen by their protocols, so none was edited. The gated check is added as one extra bank kind when study 04 loads.

## What the trials showed

The trials ran before the rule was written. They're in [results-tone-forecaster-04/diagnosis](../results-tone-forecaster-04/diagnosis/README.md).

- **On the buzz scenes** an 8-block fade brought the joint check back to its no-gate count (2 late boosts, against 7 with the hard gate). Fades of 3 blocks or less barely helped. v2's boosts there are its own, not the gate's.
- **On all development material** the fade removed exactly those 5 buzz boosts and nothing else. The other 15 synthetic boosts are the same under every fade. Most are on the sudden-change scenes.
- **The hard gate does help in one place.** When tones stop, it cuts the forecast sooner (2.2 dB at 20 ms, against 3.6 dB with the 8-block fade).
- **The gated check** removed one more buzz boost and one on fast-wandering tones, for about 0.3 dB of tone median.

## Development

The rule, written after the trials and before the formal run, needed a candidate to have fewer boosts than joint + gate (development recordings, either horizon, plus late synthetic windows), and no more late boosts on the buzz scenes than the joint check with no gate at all. It also had to stay level on near-boosts, whole-band boosts, the whole band, the synthetic objective and windows, keep at least half of the joint check's tone lead over v2, and add at most 1 ms to the 99th-percentile compute time per block. The pick is the eligible candidate with the fewest boosts.

| Development material | v2 + gate | Joint + gate | Joint, no gate | Joint, fade 8 | Joint, fade 8 in / 3 out | Gated check | **Gated check, fade 8** | Gated check, fade 8 in / 3 out |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Boosts, 1 dB (recordings + late synthetic) | 9 + 45 = 54 | 1 + 24 = 25 | 1 + 20 = 21 | 1 + 19 = 20 | 1 + 19 = 20 | 1 + 21 = 22 | **1 + 17 = 18** | 1 + 18 = 19 |
| Buzz scenes, late boosts | 10 | 7 | 2 | 2 | 2 | 5 | **1** | 2 |
| Near-boosts, 0.5 dB | 74 | 40 | 35 | 35 | 35 | 38 | **36** | 33 |
| Tone bins, median of both horizons (needed 4.35) | 3.15 | 5.56 | 5.48 | 5.50 | 5.55 | 5.31 | **5.24** | 5.36 |
| Whole band, median (dB) | 0.98 | 1.59 | 1.58 | 1.59 | 1.60 | 1.57 | **1.56** | 1.58 |
| Synthetic objective (dB) | 7.02 | 7.05 | 6.95 | 6.98 | 7.02 | 7.06 | **6.97** | 7.02 |
| Added p99 time per block over joint (ms) | | | | +0.02 | +0.08 | +0.21 | **+0.48** | +0.27 |
| Meets the rule | | | | yes | yes | no | **yes (pick)** | yes |

The gated check with the hard gate failed one part: it left 5 buzz boosts. The other four met the rule, and the gated check with the 8-block fade has the fewest boosts, so it is frozen for the test. It keeps 87% of the joint check's tone lead over v2 (5.24 against 5.56 and 3.15 dB). The tone cost is at 120 ms (4.6 against 5.1 dB); at 20 ms it ties the joint check (5.9 dB).

The gate also switched less: 165 times on the recordings and 120 on the scenes, against 169 and 132 for the joint check and 609 and 416 for v2.

## Where the remaining boosts come from

Of the pick's 18 development boosts:

- **14 are sudden changes** (6 at a source change, 5 when a tone appears, 3 when tones stop). No gate fade changes these. Study 05 ([TONE_REACT.md](TONE_REACT.md)) found they come from the check switching each tone on or off within one block, not from slow reaction.
- **1 is on a buzz scene** (buzz_am), one fewer than the joint check with no gate.
- **1 is on drifting tones** and **1 on fast-wandering tones**.
- **1 is before the first decision**: +1.4 dB on the 60 Hz mains clip at 20 ms, the same boost every check variant has.

So the gate's share is gone on development material. Study 05's per-tone fade works on the change boosts and leaves the gate's buzz boosts; this study's gate fade does the reverse. The two have not been tried together.

## The frozen test

`results-tone-forecaster-04/protocol.json` holds the code hashes, the rule's table, the fresh synthetic draws (3 repeats each of the standard, drifting and buzz scenes, in odd 10 Hz bands, avoiding every frequency a development scene used) and the fresh recording list with each file's SHA-1 and size. The test runs once and refuses to run if any of that changed.

The primary question has two parts, answered separately, on material no study-04 choice used:

1. **Are the gate's boosts gone, with none added?** Fewer boosts than joint + gate over the late windows of the fresh synthetic scenes, and no more than joint + gate over the fresh recordings (either horizon).
2. **Is the tone gain kept?** A median tone-bin gain at 20 ms, over the fresh acoustic recordings with reference tones, above v2 + gate's.

The other candidates, v2 with the fade, and the seen recordings are reported for information and answer nothing.

### Fresh recordings

Eight files, **19,336,652 bytes (19.34 MB)** total, selected on 20 Oct from the already-local Commons metadata gathered on 19 Oct. No new web request was needed. The selection uses titles, descriptions, duration, licence labels and credited authors only. It covers appliances, a lift and transport machinery; a helicopter start-up and a car engine with birds are stress cases. Their in-band tonality and usable steady intervals remain unknown. No audio was downloaded, played, decoded or scored.

| Recording | Seconds | MB | Credited author | Cached licence |
|---|---:|---:|---|---|
| [Het_vermalen_van_fruit_in_een_blender_-_SoundCloud_-_marloeskunst.ogg](https://commons.wikimedia.org/wiki/File:Het_vermalen_van_fruit_in_een_blender_-_SoundCloud_-_marloeskunst.ogg) | 30.7 | 1.47 | marloeskunst | CC BY 3.0 |
| [Laser_printer,_2015-01-23.ogg](https://commons.wikimedia.org/wiki/File:Laser_printer%2C_2015-01-23.ogg) | 80.5 | 2.72 | Finn Årup Nielsen | CC BY-SA 3.0 |
| [Photocopie.ogg](https://commons.wikimedia.org/wiki/File:Photocopie.ogg) | 18.5 | 0.33 | Luk | CC BY-SA 3.0 |
| [Mobile_lift_stage.ogg](https://commons.wikimedia.org/wiki/File:Mobile_lift_stage.ogg) | 34.0 | 0.56 | T.Voekler | CC BY-SA 3.0 |
| [Mil_Mi-8MTV-1_helicopter_starting_up.ogg](https://commons.wikimedia.org/wiki/File:Mil_Mi-8MTV-1_helicopter_starting_up.ogg) | 19.2 | 0.62 | H.dav.are | CC BY-SA 4.0 |
| [Wiki_Motor_lancha.wav](https://commons.wikimedia.org/wiki/File:Wiki_Motor_lancha.wav) | 15.0 | 4.33 | Vega16 | CC BY-SA 4.0 |
| [Paisaje_sonoro_-_Aves_y_motor_de_auto.wav](https://commons.wikimedia.org/wiki/File:Paisaje_sonoro_-_Aves_y_motor_de_auto.wav) | 51.9 | 9.16 | Luis Alvaz | CC BY-SA 4.0 |
| [Cogwheel_loco_Rigi_vsb.ogg](https://commons.wikimedia.org/wiki/File:Cogwheel_loco_Rigi_vsb.ogg) | 21.7 | 0.14 | Audrius Meskauskas | Public domain |

The filenames and SHA-1s were checked against 28 local audio files and study 05's reserved list. Credited authors are distinct, absent from the earlier source credits and study 02, and different from study 05's authors. Work With Sounds was excluded. This establishes the documented provenance checks; it does not prove independent capture events or a representative sample. Non-tonal files still count for boosts and whole-band scores, as the frozen scoring code requires. Full reasons and cached source metadata are in [the selection record](../results-tone-forecaster-04/fresh-metadata/README.md).

The existing study-04 and study-05 helpers expect different JSON shapes at the default fresh-list path. To keep both frozen code sets unchanged, the object [fresh_protocol_input.json](../results-tone-forecaster-04/fresh-metadata/fresh_protocol_input.json) was passed explicitly to study 04's one-time freeze. The bare-list [fresh_recordings.json](../results-tone-forecaster-04/fresh-metadata/fresh_recordings.json) is an identical mirror used by study 05's overlap guard. The protocol names and hashes the object; the audit verifies that the two lists and embedded protocol entries agree. Both native freshness checks pass. Do not attempt to freeze again or pass the bare list to the study-04 freeze helper.

All 18 study-04 code hashes match the development run. The 60 frozen synthetic scene specifications reproduce without synthesizing or scoring their waveforms. Study 05's 18 code hashes and its protocol remain unchanged. Before a later approved download, recheck source metadata and then verify frozen bytes and SHA-1s; unavailable files are reported without replacement, and any present-file mismatch stops the test. This was the preparation state. Sid subsequently authorized necessary downloads; see the completed test below.

## Test result, 20 Oct 2026

Study 04 did not pass all frozen questions on 6 fresh recordings and 60 fresh synthetic scenes. At 20 ms, median tone-bin prediction gain was 3.25 dB for the candidate, 3.26 dB for joint + gate, and 6.46 dB for v2 + gate. Recording band-boost cases: 5, 5 and 5, respectively.

The unchanged protocol was executed once after Sid granted full autonomy and authorized necessary downloads. Current Commons sizes and SHA-1s were checked against the frozen list; the downloaded bytes were then verified. No substitutes were used.

Missing recordings: Paisaje_sonoro_-_Aves_y_motor_de_auto.wav, Cogwheel_loco_Rigi_vsb.ogg. Any missing entries remain in the protocol and are disclosed rather than replaced.

- fewer synthetic late boosts and no more recording boosts: **yes**.
- tone gain above v2: **no**.

Full frozen report: [REPORT.md](../results-tone-forecaster-04/REPORT.md). Independent recount of the saved scores and paired uncertainty: [CODEX_REVIEW.md](../results-tone-forecaster-04/CODEX_REVIEW.md). This audit did not rerun or retune the models.

These are reference-signal prediction results only. The test clips are now seen data and must not be reused as fresh evidence for a later chosen improvement. The live engine remains v2; multiprocessing timings are not quiet-machine qualification.

## Timing

Under load (another project's training job and a study-05 check shared the processor), the pick's 99th-percentile compute time was 5.87 ms per 10 ms block, median over runs, against 5.67 ms for the joint check in the same runs. The fade on its own is under 0.1 ms. A timing run on a quiet machine is still to do; `forecaster_study_04.run_timing` does it one run at a time and records what else the processor was doing.

## What it means so far

The frozen result above supersedes the development-only expectation. The development result did not satisfy every frozen fresh-test requirement, so this candidate is not promoted. The engine still uses v2. The two studies address different transitions; their combination has not been validated and needs its own development and fresh test. Quiet-machine timing and near-ear validation remain separate from reference-prediction accuracy.

## Checks

Nineteen new checks in `tests/test_tone_gate_fade.py`:

- a one-block fade being the v2 gate;
- gains moving only between 0 and 1, a fixed step per block;
- a faded output with no steps;
- the live fade matching the offline one;
- one timing entry per block;
- a gate that never shuts giving exactly the joint check;
- the check's own gate being the v2 gate;
- block causality;
- the reported settings;
- method names;
- the output gate reaching the check;
- only the output being faded in a run;
- the rule's checks, and its pick of the fewest boosts;
- the fresh list refusing seen files and repeat authors;
- the synthetic test draws avoiding development frequencies and repeating;
- the freeze recording no candidate and running once;
- every stage refusing to overwrite;
- the frozen file list covering study 03's.

With study 05's 17 checks, all 128 passed again on 20 Oct (51.607 s). After the metadata was written, the three affected freshness/draw checks passed (0.221 s), and the manifest, compatibility mirror and frozen input checksum were verified. No performance test was run.

## Limits

The development recordings are eight files: six by two authors and two mains clips, and the mains clips never reach a decision. The buzz scenes are synthetic, modelled on a written description of the study-02 failure. Boost counts move in steps of one; the pick's 18 against 19 and 20 for the next candidates is one or two boosts. Compute times were measured on a busy machine. Everything is reference-signal prediction.
