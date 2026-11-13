# A better real-tone forecaster

Claude, 18 Oct 2026. Report: [results-tone-forecaster-01/REPORT.md](../results-tone-forecaster-01/REPORT.md).

**Reference-signal prediction only.** Every score is how well the recording microphone's own signal is predicted 20 ms or 120 ms ahead. Nothing is played, there is no acoustic path and no ear measurement, and no real cancellation is claimed.

## Why

On the real hum recordings (`results-real-hums-01`), the frozen v2 forecaster reached a median 2.9 dB at the tones. A ridge AR model adapted on each file's first 40% reached 6.3 dB. Tune-by-ear needs a separate forecast for each tone, because the listener sets each tone's anti-hum level and shift. AR predicts the whole waveform and cannot give that. The aim was a per-tone forecaster that closes some of that gap without making any part of the band louder.

## Candidates

All of them are block-causal: 10 ms blocks at 2000 samples/s, and a forecast at a block end uses only samples up to that point (`anc_lab/tone_forecasters.py`).

- **v2 with a longer fit** (0.6 s, 1.2 s instead of 0.3 s). This is the simplest change.
- **Observer bank** (`ToneObserverBank`). Each tone gets seven trackers with memories from 25 ms to 1.6 s. Every sample, the gap between the microphone and the sum of all tracked tones nudges each tracker. This is the steady form of a Kalman tracker for a tone whose phase wanders, and each tracker also follows small frequency changes. When a forecast's target time has passed, its error near each tone is measured. Each tone then uses the memory with the lowest recent error, and is switched off when no memory beats predicting nothing. The v2 fast release and the v2 realized-error gate still apply.
  - *Narrow, mid or wide check.* The error can be measured only within about ±1.5 Hz of the tone (narrow) or across the block's ±44 Hz (wide). A narrow check rewards short memories, because the noise they add outside that small band goes uncounted. In development this showed up as third-octave boosts, so the wide check was added.
  - *Lines.* Tones come from the v2 selector, or from the v2 selector plus a looser causal line finder (`ProminentLines`). The line finder takes a 4 s spectrum every 0.5 s and keeps peaks standing 10 dB above the median of the surrounding ±10 Hz, with acquire/release hysteresis. The v2 selector's statistical line test rejects lines whose amplitude or phase wanders within a second. Real machine hum often does that.
- **Comparators** (not candidates): predict nothing; v2 with and without its gate; ridge AR adapted on each file's first 40% (prefix AR); the same ridge AR refitted every second on the latest 20 s of past samples (online AR). The AR models are adapted models and are reported separately. They give no per-tone output.

## Protocol

1. **Split first** (`results-tone-forecaster-01/split.json`). The recordings were grouped by author, the groups shuffled with a stated seed, and groups assigned to development until it held five files with tones. Development: 3 stephan files, 3 Work With Sounds files and the 2 electrical mains clips. Test: the other 10 files from 7 authors. Checksums are recorded.
2. **Not independent.** Every file, development and test, was analysed in `results-real-hums-01` before this study, and its v2 and AR scores were read. The test files were untouched by forecaster development here, but the gap this study tries to close was measured on them.
3. **Development** used the development recordings plus synthetic scenes: the release study's 36 development scenes and 8 new scenes whose tones wander in phase and amplitude, all in even 10 Hz bands. The choice rule was written before the first development run. Among gated candidates, pick the highest median tone-bin gain, but only if it has no more whole-band or third-octave boosts than v2 + gate, keeps the whole-band median within 0.1 dB, keeps the synthetic objective within 0.5 dB, and adds under 5 ms per block at the 99th percentile.
4. **Freeze** (`protocol.json`). This records the chosen forecaster, the comparators, the code checksums and fresh synthetic test seeds. The test run refuses to start if any code file has changed since.
5. **Test once**: the 10 test recordings and 48 fresh synthetic scenes in odd 10 Hz bands.

## Development

- **dev-01.** The two line-finder variants beat everything at the tones: median 7.4 dB (narrow check) and 6.3 dB (wide), against about 3.2 dB for v2 + gate. The whole band improved too, 2.1 and 2.3 dB against 0.9. Both failed the time check: one median step in the line finder cost about 2.6 ms, and the 99th-percentile block took 8–9 ms. The narrow variant also had more third-octave boosts than v2 (15 against 9). Under the rule, the pick was v2 with a 0.6 s fit, a 0.3 dB gain.
- **dev-02.** The line finder's median now uses a routine that gives bit-identical values about 30 times faster. Every development score matched dev-01 exactly (8 recordings, 44 scenes). The wide line-finder variant passed every check (p99 4.1 ms) and became the pick. The rule did not change. dev-02 also added one secondary comparison for the test: the same bank without the line finder.

Both development folders are kept.

## Test

**One amendment before any score.** The first test attempt (`test/`) stopped while drawing the synthetic scenes' frequencies. The frozen protocol kept fresh tones at least 2 Hz from every frequency used before, and the release study's own test draws filled almost all of the room left in the odd bands. No forecaster had run and no score existed. `protocol-amendment-01.json` drops only the release study's test draws from the excluded list: they scored v2 in an earlier study, and nothing here was developed on them. Every development frequency is still excluded. Seeds, candidate, comparators, recordings and code are unchanged. The stopped attempt is written up in `test/FAILED_ATTEMPT.md`, and the scored run is `test-02/`.

**Answer to the frozen question: no.** The question asked for a higher median at the tones with no more boosts than v2 + gate. The tones improved, but the boost count did not hold:

| On the 10 test recordings | v2 + gate (today) | Frozen candidate (bank with line finder, wide check, gate) | AR adapted on prefix | AR refitted online |
|---|---:|---:|---:|---:|
| Tone bins, median of 8 files with tones, 20 ms | 3.3 dB | **4.7 dB** | 7.2 dB | 7.8 dB |
| Tone bins, 120 ms | 3.2 dB | 4.2 dB | 3.7 dB | 4.6 dB |
| Whole band 35–350 Hz, median, 20 ms | 0.27 dB | 0.49 dB | 0.37 dB | 0.79 dB |
| Whole-band boosts | 0 | 0 | 1 | 0 |
| Third-octave boosts (file and horizon cases) | 4 | **6** | 17 | 15 |

- **At the tones.** The candidate beat v2 + gate on all 8 files that have tones, by 0.8 to 3.1 dB (sign test p = 0.008). That closes 35% of the gap to prefix AR at 20 ms. At 120 ms it passes prefix AR, which loses most of its lead at the longer horizon.
- **Whole band.** It was ahead of v2 + gate on 9 of 10 files and never dropped the whole band below −0.5 dB. This score does not depend on how the reference tones were picked, so it is the fairer check. The tone-bin reference tones use the same 10 dB prominence idea as the line finder, so the tone-bin score flatters it.
- **Boosts.** v2 + gate's 4 are on the two air-conditioner files (up to +1.9 dB). The candidate has none there. Its 6 are elsewhere: 1 band on the server room (+1.0 dB), 1 on the tram converter at 120 ms (+1.7 dB; this file has no reference tones), 1 at each horizon on the Gravity Sound fan (+1.1, +1.6 dB), and 2 at each horizon on the ventilation system (+1.5 dB). All are small next to the AR models' (up to +10 dB). The frozen rule counts boosts, and 6 is more than 4.
- **Where the gain comes from.** The same bank without the line finder scored 3.0 dB at the tones, below v2, with 1 boost. The line finder, which follows lines v2's statistical test rejects, gives the improvement. The per-tone memory choice on its own does not.
- **Synthetic test scenes (48, fresh).** Objective 7.46 dB against 7.07 for v2 + gate. Windows below −0.5 dB: 6 against 7. On wandering tones: 5.68 against 4.56 dB.
- **Time.** In a quiet single-thread run on a 126 s recording, the candidate's own work averaged 0.28 ms per 10 ms block. Its 99th percentile was 1.6 ms and its worst block 4.8 ms. With the tone-selector update that v2 also runs, 7 of 12,490 blocks went over 10 ms; the selector causes those. Under the parallel test pool, the worst file's own 99th percentile was 5.5 ms.

**What this means.** On these files, a line finder plus per-tone trackers predicts real hum better than v2: at the tones, on the whole band, and on synthetic wandering tones. It still falls well short of an adapted AR model at the tones at 20 ms. It also makes some third-octave bands a little louder on files where v2 did not. Under the rule set before the test, v2 stays in the anti-hum engine. No setting was changed after the test to make the candidate pass. A fix for the boosts would need a fresh development round and fresh test material.

**Limits.** Ten test files from seven authors, all from Wikimedia Commons, and all analysed before this study (see Protocol, step 2). Medians over 8 files are coarse; the per-file tables in the report are the evidence. Everything here is reference-signal prediction. Nothing was played, and no ear or cancellation was measured.

## Rerun

```powershell
.\.venv\Scripts\python.exe -m anc_lab tone-forecaster develop --out results-tone-forecaster-01\development\dev-03
.\.venv\Scripts\python.exe -m anc_lab tone-forecaster freeze --development results-tone-forecaster-01\development\dev-03
.\.venv\Scripts\python.exe -m anc_lab tone-forecaster test --out results-tone-forecaster-01\test-03 --protocol results-tone-forecaster-01\protocol-amendment-01.json
```

Development and test both refuse an existing output folder, and freezing refuses an existing `protocol.json`. A real rerun therefore needs a new study folder (change `STUDY` in `anc_lab/forecaster_study.py`). Run from the project folder. The recordings are read as data and never executed.
