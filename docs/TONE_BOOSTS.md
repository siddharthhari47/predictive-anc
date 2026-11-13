# Removing the line finder's third-octave boosts

Claude, 18 Oct 2026. Study folder: [results-tone-forecaster-02](../results-tone-forecaster-02/). Status: **test done**. The joint band check passed both frozen questions. It had fewer boosts than v2 + gate on fresh recordings, but they are not all gone, and its tone gain over v2 is small. See [the result](#the-test-result) below.

**Reference-signal prediction only.** Every score is how well the recording microphone's own signal is predicted 20 ms or 120 ms ahead. Nothing is played, there is no acoustic path and no ear measurement, and no real cancellation is claimed.

## Why

In the first forecaster study ([TONE_FORECASTER.md](TONE_FORECASTER.md)) the observer bank with the line finder beat v2 at the tones on every test file with tones. It still failed its frozen bar. It made a third-octave band 1 dB or more louder in 6 (file, horizon) cases, against 4 for v2 + gate, so v2 stayed in the engine. This study asks whether the bank can keep its tone gain without those boosts.

The study-01 test files where the boosts showed up (the server room, the tram converter, the Gravity Sound fan and the ventilation system) were not used to design anything here. All diagnosis and design used the study-01 development recordings and the development synthetic scenes.

## What causes the boosts

On the development recordings the same bank had 4 boost cases at 1 dB and 12 at 0.5 dB, out of 16. Tracing it showed two causes.

- **Short memories spread noise.** A tone tracker with a 25 or 50 ms memory follows the tone closely but adds noise over a wide band. That noise lands in the neighbouring third-octave bands. The bank's own check measures each tone's error over about ±44 Hz. On a strong tone the tone bins win that check, so the short memory is kept.
- **Spurious lines.** On the compressor recording the harmonics are 9 Hz apart (36, 54, 63, 72, 81, 90 Hz). The line finder also tracked lines near 60 and 75 Hz between them, and their forecasts made the 50 Hz band louder. Lines 9 Hz apart sit inside one ±44 Hz check, so the per-tone check cannot pick them apart.

## What was tried

All on development material, kept in [results-tone-forecaster-02/diagnosis](../results-tone-forecaster-02/diagnosis/README.md).

- **Single settings** (a stricter switch-off margin, memory floors, checking at 120 ms, a 13 dB prominence threshold). None removed the boosts; the best went from 4 to 3 cases.
- **A per-band guard** (`anc_lab/tone_guard.py`) that drops a tone whose forecast makes its band louder. **Failed.** The tones are fitted jointly, so dropping one changes the others, and switching tones on and off makes its own noise. The synthetic objective fell from 7.7 to 0.8 dB, and on the 60 Hz mains recording one band rose by about 27 dB. It is kept as a failed experiment.
- **A lean towards longer memories.** Fewer near-boosts, but one band on the 60 Hz mains recording rose 18.5 dB.
- **Memory floors** (`FloorToneBank` in `anc_lab/tone_floors.py`): line-finder tones never use a memory shorter than 0.2 s. Taken forward as a candidate.
- **A joint band check** (`JointCheckBank`, same file). Taken forward as a candidate.

## The joint band check

The bank keeps all its trackers as before. What changes is what it outputs. For each horizon group (20 ms and 120 ms) it prepares ten output settings: every tone's memory raised to at least 0, 0.05, 0.1, 0.2 or 0.4 s, each with and without the line finder's tones. It also has the option of outputting nothing.

Every setting's forecast is kept until its target time passes. Every 0.5 s, the last 4 s of each setting's error is split into the same ten third-octave bands the bar uses (39 to 315 Hz). The check then compares each band with the signal itself. A setting is allowed when no band is more than 0.5 dB louder than outputting nothing. The decision uses the median over the last 16 checks, so one odd window cannot decide. Among allowed settings it picks the one with the lowest total error, and it only switches when the gain is at least 0.2 dB.

Drifting tones make every setting a little louder somewhere, and v2 does the same. In that case the settings within 0.25 dB of the least-boosting one stay allowed, rather than falling back to silence. Until the first decision, at about 6.5 s, it outputs v2's own tones with a memory of at least 0.1 s.

It only looks at the past. A forecast's error is measured after its target time, and the switch acts on later blocks.

## Development

The choice rule was written after the trials and before the formal run (`development/dev-01`). A candidate had to:

- have no more whole-band or third-octave boosts than v2 + gate and fewer than the study-01 bank;
- have **fewer near-boosts (0.5 dB) than both**, a margin added because study 01 passed its boost check in development and failed it on test;
- have fewer boosts in the synthetic scenes than both;
- keep at least half of the study-01 bank's tone lead over v2;
- hold the whole band within 0.1 dB and the synthetic objective within 0.5 dB of v2;
- stay under 5 ms per block at the 99th percentile.

| Development material | v2 + gate | Study-01 bank + gate | Memory floor + gate | **Joint check + gate** |
|---|---:|---:|---:|---:|
| Tone bins, median of both horizons (5 files) | 3.15 dB | 6.29 dB | 6.15 dB | **5.56 dB** (needed 4.72) |
| Whole band, median of both horizons | 0.98 dB | 2.32 dB | 2.33 dB | 1.59 dB |
| Third-octave boosts, 1 dB (16 cases) | 9 | 4 | 3 | **1** |
| Near-boosts, 0.5 dB | 11 | 12 | 11 | **8** |
| Synthetic late windows with a boost, 1 / 0.5 dB | 35 / 49 | 34 / 44 | 30 / 43 | **17 / 23** |
| Synthetic objective | 7.26 dB | 7.66 dB | 7.65 dB | 7.27 dB |
| Own p99 time per block, worst run | | 2.75 ms | 2.82 ms | 4.08 ms |

The memory floor failed the near-boost check (11, not fewer than v2's 11). The joint check passed every check and was frozen. Its one remaining boost is +1.4 dB on the 60 Hz mains clip at 20 ms.

**The cost.** The joint check keeps about three quarters of the study-01 bank's tone lead over v2. The rest is lost on two files. On the microwave, the tones drop from 14.8 to 9.1 dB at 20 ms. On the compressor with the 9 Hz harmonics, they drop from 6.5 to 1.5 dB. It also gives up part of the whole-band gain, and its own compute time is higher (worst run 4.1 ms per 10 ms block at the 99th percentile, measured under the parallel pool).

## The frozen test

`results-tone-forecaster-02/protocol.json`, frozen before any test material was read, holds the candidate, the comparators, code checksums for twelve files and the questions.

**Fresh recordings (primary).** Eight Wikimedia Commons files, chosen by title, description, length, licence and author only. None had been downloaded or heard when the protocol was frozen. No author also made a recording used before. Each file's SHA-1 and size are frozen. A file that cannot be downloaded is reported as missing and is not replaced:

| File | Author | Licence | Length |
|---|---|---|---:|
| Pump.ogg | ezwa | Public domain | 32 s |
| The Sound of MOXIE at Work on Mars (PIA26041).wav | NASA/JPL-Caltech/CNES/IRAP | Public domain | 75 s |
| Montreal Clock Tower clock mechanism.flac | Andy Mabbett | CC BY-SA 4.0 | 41 s |
| Siemens Combino Engine Sound.wav | Dawidpl4553 | CC BY-SA 4.0 | 120 s |
| Lille subway noise.wav | Dazhoid | CC BY-SA 4.0 | 18 s |
| Stirling marble engine 000.ogg | Nkim5706 | CC BY-SA 3.0 | 28 s |
| Buzzing Speakers.ogg | buzzingspeakers.com | CC BY-SA 3.0 | 17 s |
| 60-hz.wav | Rayo v.2.0 | CC BY-SA 4.0 | 20 s |

The page does not say how 60-hz.wav was captured; it may be a generated tone. It is kept out of the medians, but its boosts still count.

**Questions, answered separately.**

1. Are the boosts gone? On the fresh files, does the joint check + gate have no more third-octave boosts and no more whole-band boosts than v2 + gate?
2. Is the tone gain kept? Is its median tone-bin gain at 20 ms, on the fresh acoustic files with tones, above v2 + gate's?

The study-01 bank + gate is reported alongside, with the share of its lead that survives.

**Secondary.** The ten study-01 test recordings are scored again but labelled seen: their boosts started this study, so they are not independent. There are also 48 fresh synthetic scenes in odd 10 Hz bands, more than 2 Hz from every development frequency. The study-01 test frequencies are not excluded. Excluding them as well leaves no room in either band parity, and no study-02 choice used them.

**Running it.** After the download, `forecaster_study_02.run_test()` runs once. It refuses to start if `test/` exists, if any frozen code file has changed, or if a downloaded file's SHA-1 differs. It writes `test/test.json` and `REPORT.md`.

## The test result

With Sid's approval, the eight files were downloaded on 18 Oct 2026 into `external-audio/wikimedia-commons-fresh-02/`. Licences are in its SOURCES.md. All eight matched their frozen size and SHA-1, so none was missing. The test ran once and took 1.3 minutes. The frozen answer is in [REPORT.md](../results-tone-forecaster-02/REPORT.md). A note written after the test, [POST_TEST_NOTES.md](../results-tone-forecaster-02/POST_TEST_NOTES.md), explains the parts the answer leaves out. No setting was changed after the test.

| Fresh recordings | v2 + gate | Study-01 bank + gate | **Joint check + gate** |
|---|---:|---:|---:|
| Third-octave boosts, 1 dB (16 cases) | 3 | 4 | **2** |
| Near-boosts, 0.5 dB | 4 | 6 | **2** |
| Whole-band boosts | 0 | 0 | 0 |
| Tone bins at 20 ms, median of 5 acoustic files | 0.8 dB | 3.2 dB | **1.2 dB** |
| Whole band at 20 ms, median of 7 acoustic files | 0.01 dB | 0.01 dB | 0.00 dB |

1. **Are the boosts gone? Fewer than v2 + gate, which is what the frozen question asked, but not gone.** Both of the joint check's boosts are on the buzzing speakers recording, in the 39 and 50 Hz bands, at +7.3 dB (20 ms) and +5.6 dB (120 ms). v2 + gate boosts the same bands on the same file by up to 11.5 dB. The buzz is above 100 Hz, so those two bands are nearly empty: they hold about −50 dB of the band's power before the boost. The most likely cause is the fallback for drifting tones. It keeps the least-boosting setting even when that setting boosts by several dB, and it has no ceiling. The joint check never chose "no output" on this file.
2. **Is the tone gain kept? Yes, but it is small.** Joint 1.2 dB, v2 0.8 dB. It was ahead on two files (pump +0.4 dB, clock mechanism +0.6 dB), tied on two where no tone method gained (Mars, Lille subway) and 0.1 dB behind on the buzzing speakers. Two wins and one loss out of five is not distinguishable from chance. It keeps 18% of the study-01 bank's lead over v2, against 77% in development.

**The study-01 bank blew up on the Mars recording.** That recording has almost no sound below 300 Hz. The bank made nine nearly empty bands 28 to 54 dB louder at both horizons. The gate missed it because the whole band barely moved. v2 and the joint check output nothing there. The boost count shows this as only 2 cases.

**Secondary results**, which agree with the fresh files:

- On the study-01 test recordings, which are seen and so not independent, the joint check had 0 boosts against v2's 4 and the bank's 6. It also had 2 near-boosts against 10 and 11. Its tones were 4.1 dB at 20 ms against 3.3 and 4.7 dB.
- On 48 fresh synthetic scenes it had 19 late windows with a boost, against 29 and 35. Its objective was 6.97 dB against 6.98 and 7.45 dB.
- Its own compute time stayed under the limit: worst run 3.8 ms per 10 ms block at the 99th percentile.

**Adapted AR models**, reported separately, were again best at the tones: medians of 3.0 and 3.7 dB at 20 ms. They also made bands louder in 13 and 10 cases, including about +70 dB on the near-empty Mars bands, and made the whole band worse on the Lille subway.

**What this means.** The joint check is the first line-finder forecaster to pass a frozen test against v2. Its case rests on safety more than on tones: fewer boosts than v2 on every set it was tested on, and no blow-up where the study-01 bank had one. On fresh sounds, its tone gain over v2 is small and uncertain. Nothing in the anti-hum engine was changed; whether the joint check replaces v2 is Sid's decision. A ceiling on the fallback is the obvious next fix. It needs a new development round and new test recordings, because the buzzing speakers file has now been examined.

## Checks

Twelve new checks in `tests/test_tone_floors.py`. They cover:

- the floor bank with no floors matching the plain bank exactly;
- floors being respected;
- the joint check being block-causal, tracking steady tones and staying silent on noise;
- its switch to no output when every setting boosts;
- the fresh files being new files by new authors;
- the SHA-1 check;
- the synthetic draws avoiding development frequencies and matching the frozen ones;
- every stage refusing to overwrite.

All 80 checks pass.

## Limits

The development numbers come from eight recordings by two authors plus two mains clips. A boost count over 16 cases moves in steps of one. The test rests on eight recordings. Only five of them have reference tones, and on two of those no tone method gained anything. The per-band boost score is relative, so a band that is nearly empty can show a large boost from very little output. Everything here is reference-signal prediction.
