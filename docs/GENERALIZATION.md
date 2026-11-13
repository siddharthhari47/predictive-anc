# General-purpose tone prediction, not a fan-specific model

The intended system automatically discovers and follows predictable tones from new sources. The user's fan is an experimental source, not a product requirement. Neither its name nor its measured frequencies should be hard-coded into the deployed predictor. The current research band is 35–350 Hz; successful performance across every frequency, device and room has not been established.

## Two distinct ways to handle a new source

**Automatic adaptation:** observe a short calibration prefix, identify spectral components, estimate their frequency/phase/amplitude or fit a predictor, then forecast later samples. A reusable algorithm can adapt to new tones without a human typing their frequencies. The calibration time and observations are part of its operating requirements.

**Frozen-ML transfer:** train model weights on a development corpus, freeze them, then forecast recordings from withheld sources. Any new-source normalization, context, online updates or calibration must be reported. A model fitted separately to each fan recording has not demonstrated this kind of transfer.

Both are legitimate research directions. ML must earn its role against simple DSP with the same available history and forecast deadlines. A hybrid of automatic tone tracking, uncertainty estimation and learned prediction may be useful, but that architecture remains an experiment.

## First frequency-group diagnostic: completed

[The new benchmark](../results-generalization-01/REPORT.md) trains a pooled MLP on three synthetic source groups and evaluates different frequencies, including a single tone, unrelated tones, a harmonic mixture and a broadband negative control. Frequencies are not supplied to predictors; the tracker detects peaks from each new source's initial six seconds. The adapted AR and MLP fit that prefix. The frozen pooled MLP only calibrates input scaling on the prefix and does not update its weights.

The evaluation uses a chronological 6/2/4-second split and forecast blocks starting at 20 and 120 ms. Model selection uses validation only and includes zero prediction. Pooled training examples never cross source boundaries. Frequency groups and settings were saved before training/evaluation. There are 40 method/source/horizon comparisons.

| Method | Test band prediction gain across the three tonal cases and two horizons |
|---|---:|
| Automatic tone tracker | 33.38 to 34.83 dB |
| AR adapted to each new source | 33.25 to 34.45 dB |
| MLP adapted to each new source | 32.24 to 33.03 dB |
| Frozen pooled MLP | −5.58 to −1.37 dB |

The tracker was selected on validation for all tonal cases. Zero was selected for the broadband negative control at both horizons. Negative prediction gain means worse error than zero prediction. These values measure synthetic reference-waveform prediction, **not physical noise cancellation**.

All MLP fits reached their configured 180-iteration limit. The pooled model had only three development source groups. Its failure is evidence about this first comparator and training set, not a general limitation of ML. There is one random seed per source, stationary synthetic tones and a low noise floor; this is a diagnostic, not a distribution-wide performance claim. The original benchmark separately tests assumed acoustic paths and timing jitter.

## Why freeze bands for one real recording experiment?

The matched fan study identified candidate bands near 41, 124, 165 and 330 Hz. Freezing those bands before evaluating an independent recording prevents selecting favorable frequencies after seeing forecast errors. They are measurement choices for that experiment. A deployed algorithm must select bands automatically from past observations, assess confidence, track changes and stop predicting when the reference no longer supports a reliable forecast.

The original 35–350 Hz real-fan prediction failure remains a failure. A later narrowband result must be separately named and reported; it cannot replace the earlier score. No further microphone capture or playback is needed to reproduce the synthetic generalization diagnostic.

## Next validation gates

1. **Automatic selection:** implement a causal tone-count and confidence rule. The current tracker takes up to three strongest peaks, including weak noise peaks when fewer true tones exist. The offline zero baseline prevents unsupported selection in this diagnostic, but this is not yet a real-time confidence controller.
2. **New real data:** automatically discover candidate tones from a prefix and freeze evaluation bands before later validation/test data. Confirm any source-study bands on a fresh recording. Require repeated sessions and retain negative results.
3. **Broader training:** generate varied frequencies, mixtures, phases, amplitudes, frequency drift, signal-to-noise ratios and discontinuities; then add real recordings with documented microphone processing. Freeze architectures and settings on development validation data.
4. **Group-held-out evaluation:** withhold entire frequency ranges, source units, sessions, microphones and environments. Report adapted and frozen-weight models separately, including their calibration data, worst cases, failures and uncertainty. Do not random-split adjacent waveform windows to claim generalization.
5. **Acoustic validation:** prediction must still pass reference-to-ear coherence, path calibration, measured sample-to-ear timing and near-ear residual measurements. An algorithm that accepts new frequencies cannot infer an unknown earphone path or future playback jitter solely from reference audio.

The product ambition stays broad; each experiment has a defined and falsifiable scope.
