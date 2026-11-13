# Fresh-sound results: studies 04 and 05

20 October 2026 · Predictive ANC lab

Both studies used frozen code, fixed comparison rules and fresh recording lists. The tests ran once. All gains below describe prediction of the recording microphone waveform, not physical ANC.

| Study | Frozen outcome | Fresh recordings | Synthetic scenes | Tone gain: candidate / joint / v2 at 20 ms |
|---|---|---:|---:|---:|
| 04: gate fade | Not all questions passed | 6 | 60 | 3.25 / 3.26 / 6.46 dB |
| 05: per-tone fade | All questions passed | 7 | 84 | 2.20 / 2.05 / 0.85 dB |

![Frozen study comparison](C:/Users/talk2.000/Documents/Codex/2026-10-15/referenced-chatgpt-conversation-this-is-an/outputs/anc-studies-20261020/frozen-study-comparison.png)

## What the tests decide

### Study 04

- fewer synthetic late boosts and no more recording boosts: **yes**.
- tone gain above v2: **no**.
- Missing recordings: Paisaje_sonoro_-_Aves_y_motor_de_auto.wav, Cogwheel_loco_Rigi_vsb.ogg.
- [Detailed result and uncertainty](C:/Users/talk2.000/Documents/Codex/2026-10-15/referenced-chatgpt-conversation-this-is-an/outputs/anc-studies-20261020/study-04-review.md).

### Study 05

- fewer change boosts: **yes**.
- no more recording boosts: **yes**.
- tone gain above v2: **yes**.
- Missing recordings: Noise-Pollution-Filters-Bird-Communities-Based-on-Vocal-Frequency-pone.0027052.s001.ogg.
- [Detailed result and uncertainty](C:/Users/talk2.000/Documents/Codex/2026-10-15/referenced-chatgpt-conversation-this-is-an/outputs/anc-studies-20261020/study-05-review.md).

## Decision boundary

The current live engine remains v2. Passing a frozen reference-prediction rule is only one development step: quiet-machine processing time, measured output timing, acoustic transfer, and near-ear residual pressure remain necessary before a new controller can be described as real ANC. The two faded candidates were tested separately; their combination was not tested.

These small, purposive samples do not establish performance on every tone or sound. The models infer tones from past samples; no fan frequency was hard-coded for these tests. Sudden and mixed noises are stress cases for amplification, not a claim to predict arbitrary broadband sound.

## Reproducibility

Raw downloads stay local in the project. Each batch has current Commons metadata, licence attribution, the user authorization, and the frozen-size/SHA-1 checks. Reports have SHA-256 receipts. A separate review recounted boosts and recomputed medians from the stored scores; it did not rerun or retune the models.
