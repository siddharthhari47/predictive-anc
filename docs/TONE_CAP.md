# Capping the joint check's tie fallback

Claude, 19 Oct 2026. Study folder: [results-tone-forecaster-03](../results-tone-forecaster-03/REPORT.md). Status: **stopped at development; no candidate, no test.** A ceiling on the fallback doesn't remove the joint check's remaining boosts on development material, and every cap low enough to act costs tone gain. Nothing was downloaded.

**Reference-signal prediction only.** Every score is how well the recording microphone's own signal is predicted 20 ms or 120 ms ahead. Nothing is played, there is no acoustic path and no ear measurement, and no real cancellation is claimed.

## Why

The joint band check from study 02 ([TONE_BOOSTS.md](TONE_BOOSTS.md)) passed its frozen test narrowly. Two boosts were left, both on Buzzing_Speakers.ogg, in two nearly empty low bands. The post-test notes named the check's tie fallback as the likely cause. When every output setting makes some band louder, the fallback keeps the least-boosting one, and nothing limits how loud that can be. This study asked whether a ceiling on the fallback removes the boosts and keeps the tone gain over v2.

Buzzing_Speakers.ogg and the other study-02 fresh files are seen now, as are the study-01 test files, so none of them was used. Everything here ran on the study-01 development recordings, the 44 development synthetic scenes, and 8 new development scenes. Those 8 copy the shape of the study-02 failure from its written description: a wandering buzz above 100 Hz over nearly empty low bands.

## The cap

`anc_lab/tone_cap.py`, `CappedCheckBank`. It is the joint check with one change: the fallback can loosen the limit only up to `cap_db`. Above that only no output is allowed. With no cap it gives exactly the joint check's output (a check confirms this). With the cap at 0.5 dB the fallback is off. `tone_floors.py` is frozen by study 02's protocol, so it was not edited.

## What the trials showed

The trials ran before the rule was written. They're in [results-tone-forecaster-03/diagnosis](../results-tone-forecaster-03/diagnosis/README.md).

- **A trace of every decision** on the development recordings showed the fallback in force often. On the air compressor the setting in use was up to 2.9 dB louder in some band in the check's own view, because even the best setting was 2.7 dB. Yet the scored output on that file was fine: worst band +0.9 dB against v2's +2.5 dB, and tones 8.1 / 7.1 dB against v2's 2.9 / 3.4 dB.
- **Caps of 0.5 to 2 dB** removed no boost on the recordings or the original scenes, and the low ones cut the air compressor's tones to 2 dB or less.
- **On the buzz scenes** the joint check had 2 boosts without the gate and 7 with it. The cap didn't change that.

## Development

The rule, written after the trials and before the formal run, needed a cap to have fewer boosts than the joint check (counting both development recordings and late synthetic windows). It also had to keep at least half of the joint check's tone lead over v2 and stay level on near-boosts, whole-band boosts, the whole band, the synthetic objective and compute time.

| Development material | v2 + gate | Joint + gate | Cap 0.5 | Cap 1 | Cap 2 | Cap 3 |
|---|---:|---:|---:|---:|---:|---:|
| Boosts, 1 dB (recordings + late synthetic) | 54 | 25 | 24 | 25 | 25 | 25 |
| Near-boosts, 0.5 dB | 74 | 40 | 36 | 38 | 40 | 40 |
| Tone bins, median of both horizons (needed 4.35) | 3.15 | 5.56 | 2.50 | 2.50 | 3.69 | 5.56 |
| Synthetic objective (dB) | 7.02 | 7.05 | 5.85 | 6.58 | 7.05 | 7.05 |

No cap met the rule. Caps 1, 2 and 3 removed no boost. Cap 3 never set the limit at all. Cap 0.5 removed one boost: 4 on the buzz scenes went, and 3 came back on drifting, harmonic and single-tone scenes. But it lost most of the tone gain and the synthetic objective. The protocol was frozen with no candidate (`results-tone-forecaster-03/protocol.json`), so there was nothing to test and no fresh recordings were chosen or downloaded.

## Where the remaining boosts come from

Of the joint check's 25 development boosts:

- **14 are sudden changes** (a source switching, a tone appearing or stopping at 9 s). The check takes medians over 8 s of history, which is too slow for these. v2 + gate has exactly the same counts on these scenes.
- **5 come from the gate.** The check judges each setting before the gate. It can't see what the gate's hard on/off switching adds.
- **3 are on drifting tones**, with or without a cap.
- **1 is before the first decision** (+1.4 dB on the 60 Hz mains clip, about 6.5 s in, while the check still uses its start setting).

So the fallback isn't the problem on this material. It mostly keeps the air compressor's tones and drifting tones alive. Whether it caused the Buzzing_Speakers boosts is still open. That file is seen, and the buzz scenes built to resemble it point at the gate instead.

## Timing

Worst-run compute time at the 99th percentile was 11 to 15 ms per 10 ms block for every check variant, against 4.1 ms in study 02. A training job from another project was using the processor during the run. The rule compared caps with the joint check in the same run, so the comparison holds, but the absolute numbers aren't usable. The joint check needs a quiet-machine timing run before anything goes near the live engine.

## What it means

The joint check (study 02) and v2 are unchanged, and the engine still uses v2. Replacing v2 is Sid's decision. Two fixes look more promising than a cap, and both need their own development round and fresh test recordings:

- **Soften the gate**: fade it in and out over a few blocks instead of switching, or have the band check judge the gated output.
- **Speed up the check's reaction** to sudden changes and to the start of a recording.

## Checks

Twelve new checks in `tests/test_tone_cap.py`:

- no cap matching the joint check exactly;
- the limit formula;
- a cap leaving only no output where the joint check keeps a 3 dB setting, while a 0.7 dB setting survives;
- a cap at the margin never keeping a loud setting;
- block causality;
- the reported settings;
- the buzz draws avoiding every test frequency and repeating;
- method names;
- the rule's boost and tone checks;
- the freeze refusing to run twice, to freeze a pick without a test stage, or to freeze after a code change;
- development refusing to overwrite;
- the frozen file list covering study 02's.

All 92 checks pass.

## Limits

The development recordings are eight files: six by two authors and two mains clips, and the mains clips never reach a decision. Boost counts move in steps of one, and the 25 against 24 that separates cap 0.5 from the joint check is one boost. The buzz scenes are synthetic and modelled on a written description, not the real file. Everything is reference-signal prediction.
