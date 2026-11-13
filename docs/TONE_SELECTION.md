# Automatic tone count and confidence (first study)

Added 16 October 2026 by Claude. Results: [results-tone-selection-01/REPORT.md](../results-tone-selection-01/REPORT.md). Code: `anc_lab/tone_selection.py`, `anc_lab/selection_study.py`, `anc_lab/selection_report.py`. Command: `python -m anc_lab select-tones --out <new folder> [--real <wav> ...]`.

Everything here is **synthetic reference-signal prediction** plus a re-analysis of earlier recordings. There is no acoustic path, playback or ear measurement, and no claim of physical noise cancellation.

## What changed

The old detector (`estimate_tones`, kept unchanged) always returns up to three of the strongest peaks from a 6 s prefix and then keeps them. With fewer true tones it locks onto noise, and it cannot follow tones that drift, appear, stop or change.

The new selector decides, every 0.25 s, how many tones are present using only the most recent 1 s of samples:

1. **Line test.** A Thomson multitaper harmonic F-test (NW = 4, 7 tapers) asks, at each frequency in 35–350 Hz, whether a steady sinusoid explains the window better than local noise. Under the no-tone hypothesis the statistic has a known F(2, 12) distribution. The threshold is therefore a stated false-alarm level, corrected for the number of independent frequencies in the band. It is not a tuned peak height, and it is unaffected by overall level or by how steeply the noise spectrum slopes.
2. **Confidence over time.** A line becomes active after passing in 2 of the last 3 updates and is released after 4 consecutive misses. Reported confidence is the pass fraction.
3. **Prediction.** The existing causal tone tracker runs on whatever set is currently active. With no active tones, the forecast is zero.
4. **Mute gate (controller side, separate object).** At each origin, the gate checks forecasts whose whole target block has already happened (no future samples). If those recent forecasts did not beat zero by the threshold, output is muted.

Warm-up is 1.25 s before the first possible detection. No prefix fit and no frequency labels are used. The fan's measured frequencies appear nowhere in the code.

## How settings were chosen

The development scenes use the earlier development frequency groups and new seeds. The detector grid (false-alarm level 1e-2 to 1e-5; acquire/history 1/1, 2/3, 3/4; release 1/2/4) was scored by total false plus missed tone-updates. The winner was 1e-2, 2-of-3, release 4: 14 false and 63 missed, out of 704 true tone-updates. The gate threshold was then chosen by best worst-case, then best mean, development gain. All gate thresholds tied on worst case (about 0 dB), and −1 dB won on mean. On development data the gate mattered little, because the selector already outputs zero when it finds no tones. Settings and test-scene definitions were written to `selection_protocol.json` before any test scene was synthesized.

Test scenes use fresh frequencies, more than 2 Hz from every development and earlier held-out frequency (a code check enforces this), and fresh seeds. One test frequency (74.1 → 77.0 Hz) was moved *before* the run, because the freshness check found it within 0.3 Hz of the end of a development drift.

## Findings (fresh synthetic scenes; test window 8–12 s)

- **No tone present** (silence floor, white noise, rumble): the new selector reports zero tones in 49 of 51 test updates. Its 3 false activations all came from rumble, 151.7 Hz in one scene. Prediction gain is 0.00 to −0.01 dB, so it is effectively muted. The old top-3 detector reports 3 false tones at every update and loses up to 0.5 dB. The adapted MLP loses up to 3.2 dB, and the frozen MLP up to 3.4 dB.
- **Steady tones** (single, unrelated, harmonic): correct count and frequency within 0.03 Hz. Gain is the same as the old tracker (33.3–34.8 dB), because the old tracker was already good when exactly three or more tones existed.
- **Drift** (+0.5 Hz/s): the new tracker gains 18.4 dB (20 ms) and 12.5 dB (120 ms). The old fixed-frequency tracker scores −0.4/−0.6 dB, and prefix AR scores 5.0/−10.3 dB.
- **Tone appears at 9 s**: picked up after 1.25 s. Gain +3.5/+3.3 dB, versus about 0 for prefix methods. Validation (6–8 s, before the tone existed) correctly chose zero. That shows validation-time selection cannot anticipate a later source.
- **Tones stop at 9 s**: released after 1.0 s. For about a second after the stop, both trackers are slightly worse than zero (about −0.9 dB in 9–10.5 s). The gate improves the totals (2.9 → 4.8 dB at 20 ms), but prefix AR does best here (8.2 dB) because its forecasts decay on their own. **The release delay is a real weakness.**
- **Source change at 9 s**: overall the old tracker scores higher (5.1 vs 3.5–3.7 dB). This is luck: its prefix grabbed a noise peak at 208.3 Hz, which happened to be 0.6 Hz from the later 208.9 Hz tone. After acquisition (10.5–12 s) the new tracker scores 19.8 dB and the old one 6.7 dB.
- **Weak tones in strong noise** (per-tone level about 15–18 dB below the broadband noise): the 66 Hz tone is found, but the 247 Hz tone is missed throughout. All methods are within ±0.6 dB of zero, so this case is out of reach for every method tested.
- **Tones in rumble**: both tones found, 4.8–5.1 dB, similar to the old tracker.
- **Frozen pooled MLP** is negative or about zero in every scene, consistent with the earlier transfer failure. It is a frozen-weight result and is reported separately from per-source adaptation.

Compute: about 4.5 ms mean and under 11 ms max per selector update (1 s window, laptop CPU, one thread). The tracker forecast costs 0.5–1.2 ms per 10 ms block for 1–3 tones. This is offline Python timing, not a real-time callback measurement.

## Re-analysis of earlier recordings (not independent evidence)

These are the same files, and test segments (18–30 s), as earlier reports. Settings came from synthetic development only.

- `results-goal1-clean/reference.wav` (the failed clean fan trial): **no line passed the test in any update**. The output is zero, gain 0.00 dB, compared with −0.1 to −1.2 dB for the earlier methods. The selector does not make the failed trial a success. It declines to predict and so avoids making things worse.
- `fan_off.wav`: no tones, as expected.
- `fan_on.wav`: a line near 41 Hz is active in 95% of updates, and 330/124/165 Hz appear intermittently (11–20%). This independently matches the source-study candidates without using them. The prediction gain is only +0.17/+0.18 dB, because those lines carry a tiny share of the 35–350 Hz power. A real spectral line is not the same as useful broadband prediction.
- `goal1_fan_01.wav` (mixed noise with talking/music): intermittent lines near 105–106 and 318 Hz. Gain is 0.00 dB.

## Limits and next steps

- One seed per scene. Development and test share scene types but not frequencies or seeds. Twelve scene types do not represent the world.
- Release latency (about 1 s) and acquisition latency (1.25 s) are set by the 1 s window and the hysteresis. Shortening them trades against false alarms, and that trade should be chosen on development data, not on this test.
- Tones closer than about 4 Hz are reported as one line.
- The 6 dB broad-band target is unchanged. Real-world value now depends on whether real sources have enough power in steady lines. In the fan recordings they do not.
- Next: (1) a faster release path, for example letting the gate react to realized error on a shorter horizon, tuned on development scenes only; (2) several seeds per scene type with confidence intervals; (3) a fresh real recording session with user readiness, analysed with these frozen settings; (4) broader grouped training before any frozen-ML transfer claim.
