# Faster tone release, with repeats (second study)

Added 16 October 2026 by Claude. Results: [results-release-study-01/REPORT.md](../results-release-study-01/REPORT.md). Code: `anc_lab/release_study.py`, `anc_lab/release_report.py`; fast-release option in `anc_lab/tone_selection.py`. Command: `python -m anc_lab release-study --out <new folder>`.

Everything here is **synthetic reference-signal prediction**. There is no acoustic path, playback or ear measurement, and no claim of physical noise cancellation.

## Why

In the first study ([TONE_SELECTION.md](TONE_SELECTION.md)) the tracker kept forecasting for about a second after tones stopped, which was worse than predicting nothing. That weakness was seen on study-01 *test* scenes, so those scenes cannot be used to judge a fix. Study 01 also had one seed per scene.

## What changed

Two new options, both off by default (the defaults reproduce study 01 bit for bit):

1. **Fast amplitude release** (`SelectedToneForecaster(release_ratio=..., release_window_seconds=...)`). At each forecast origin, each active tone's amplitude is fitted over the last 0.1 s and over the full tracker window, using past samples only. If the short-window amplitude has fallen below the ratio times the long one, that tone is left out of the forecast at that origin. The detector keeps its slower hysteresis, so a brief dip does not throw away the track.
2. **Shared, shorter mute gate** (`realized_gate(..., shared_group=0)`). The 20 ms forecast matures first, so its realized error can mute the 120 ms forecast as well.

## How settings were chosen (development only)

- Development scenes: the 12 study-01 scene types on 3 frequency draws (the fixed development groups plus 2 random draws inside even-numbered 10 Hz bands), new seeds. 36 scenes.
- Objective: mean band gain (capped at 20 dB so steady scenes do not dominate) over the whole 2.5–11.8 s span plus each 1.5 s window after a tone starts or stops, both horizons.
- Stage A, no gate: selector release {1, 2, 4} × fast-release ratio {off, 0.3, 0.5} × short window {0.1, 0.2 s} × tracker window {0.6, 0.3 s}. Stage B: gate threshold {none, −1, 0, 1, 3 dB} × lookback {5, 10, 25 blocks} × shared {no, yes} on the stage-A winner.
- **Chosen (v2):** tracker window 0.3 s; fast release at 0.5× over 0.1 s; selector release unchanged (4; 1 and 2 tied); gate −1 dB over the last 5 matured blocks, shared from the 20 ms horizon. Development objective 7.90 vs 7.35 for the study-01 settings (v1). The gate added only 0.04 of that.
- Settings were written to `release_protocol.json`; test frequencies were drawn only afterwards.

## Test (5 random draws in odd 10 Hz bands × 12 scenes = 60 fresh scenes)

Every test frequency is more than 2 Hz from every development, earlier held-out and study-01 test frequency (checked in code). Mean [lowest, highest] over the 5 repeats, 35–350 Hz band, test window 8–12 s.

- **Tones stop at 9 s:** v2 + gate 8.2 [8.0, 8.5] dB at 20 ms and 3.7 at 120 ms. v1 scored 4.8 / 2.1 and the old top-3 tracker 3.0 / 0.8. That ties prefix AR (8.1 / 3.7), which had been the best method here. Forecast output dies away 0.03 s after the stop (v1: 0.15 s; both gated).
  In the 1.5 s right after the stop, every method is still worse than predicting nothing: v2 −5.3, v1 −10.4, AR −5.4, old top-3 −12.5 dB. Forecasts issued just before or at the stop still predict a tone, and the background left behind is quiet, so a few tens of milliseconds of wrong output cost several dB in that window. **The release problem is smaller, not gone.**
- **Drift:** 27.4 / 19.2 dB vs 18.4 / 12.5 for v1. This comes from the shorter 0.3 s tracker window, not from the release logic.
- **Source change:** 4.0 / 3.4 vs 3.7 / 3.1 (v1); old top-3 0.4 / −0.1.
- **Tone appears:** unchanged (3.5 / 3.3). Acquisition still takes about 1.25 s.
- **Noise only** (silence, white, rumble): 0.0 dB on every repeat for v1 and v2. The old top-3 detector reported 3 false tones at every update; adapted MLP −0.8 to −2.5 dB; frozen MLP −1.6 to −3.2 dB.
- **Costs of v2:**
  - Steady tones lose 0.1–0.5 dB (e.g. harmonic 34.0 vs 34.5 dB at 120 ms), because the shorter window averages less noise.
  - **Tones in rumble lose 1.2 dB with the gate** (4.0 vs 5.2 ungated). The 5-block gate sometimes mutes in rumble when it should not. On development the gate's benefit was only 0.04, so this is a real trade, not a free improvement.
- **Weak tones in strong noise:** still out of reach for every method (±0.2 dB).
- **Frozen pooled MLP:** negative or near zero almost everywhere. That is a frozen-weight result, reported separately from per-source adaptation.

Spread across repeats is small (usually under 1 dB). For the tracker-based methods on the drift, appear and stop scenes it is under 0.1 dB, because model error (lag, acquisition delay) dominates, not noise.

Compute: v2 selector update 7.7 ms mean / 11.7 ms max; forecast 0.97 ms per 10 ms block. Offline Python, one thread; not a real-time measurement.

## Limits

- The idea of fixing release came from study-01 test results. This study's test data is new, but its question is not independent of study 01.
- Same 12 scene types, only frequencies and seeds vary. The repeats measure spread over seeds and frequencies, not coverage of real sources.
- Random drift draws cluster around 92, 212 and 292 Hz. Few bands allow a 6 Hz drift path that avoids all earlier frequencies.
- Only abrupt stops are tested. A slowly fading real source would sit between "steady" and "stop", and the 0.5 ratio could drop a tone that only dips briefly. Nothing tested here measures that.

## Next

1. Decide whether v2 should keep the gate, or use v2 without it (rumble cost vs a small development gain). Any change has to be chosen on development data or with a new test set.
2. A fresh real recording session with the user's readiness, analysed with frozen v2 (and v1 for comparison).
3. Faster acquisition (1.25 s now) is the remaining transition weakness.
4. Broader grouped training before any frozen-ML transfer claim.
