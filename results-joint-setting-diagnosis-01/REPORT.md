# Why the joint check loses on strong hums

21 October 2026 · Post-hoc diagnosis on four already-seen sources

All figures are reference prediction, not measured ANC. These sources were selected because earlier results showed losses. The experiment is diagnostic and cannot establish generalization.

Each existing output setting was held fixed. This separates the available settings from the joint check's past-error decisions. The bank's own tracking and existing output gate were unchanged.

## Tone accuracy at 20 ms

| Method | Lift | Motorboat | Helicopter | Copier |
|---|---:|---:|---:|---:|
| v2_gated | 9.75 | 20.03 | 5.59 | 7.33 |
| bank_wide_lines_gated | 10.16 | 20.33 | 5.49 | 6.96 |
| joint_gated | 4.90 | 8.61 | 1.61 | 6.82 |
| fixed_0_lines_gated | 10.16 | 20.33 | 5.49 | 6.96 |
| fixed_0.05_lines_gated | 9.59 | 20.33 | 5.49 | 6.96 |
| fixed_0.1_lines_gated | 7.84 | 16.60 | 5.19 | 7.03 |
| fixed_0.2_lines_gated | 6.09 | 10.09 | 3.31 | 6.95 |
| fixed_0.4_lines_gated | 3.72 | 2.84 | 1.61 | 6.32 |
| fixed_0_selector_gated | 10.06 | 20.27 | 5.45 | 6.81 |
| fixed_0.05_selector_gated | 9.17 | 20.27 | 5.45 | 6.81 |
| fixed_0.1_selector_gated | 7.57 | 16.63 | 5.18 | 6.82 |
| fixed_0.2_selector_gated | 6.03 | 10.13 | 3.35 | 6.71 |
| fixed_0.4_selector_gated | 3.73 | 2.88 | 1.63 | 6.21 |

## Largest third-octave amplification at 20 ms

Positive values are increased residual energy in a band; 1 dB or more is a boost case. Some bands have very little reference power. This is not ear-level SPL.

| Method | Lift | Motorboat | Helicopter | Copier |
|---|---:|---:|---:|---:|
| v2_gated | 1.67 | 6.18 | 6.38 | 0.40 |
| bank_wide_lines_gated | 4.86 | 6.12 | 6.87 | 0.35 |
| joint_gated | 1.72 | 6.20 | 3.31 | 0.21 |
| fixed_0_lines_gated | 4.86 | 6.12 | 6.87 | 0.35 |
| fixed_0.05_lines_gated | 2.54 | 6.12 | 5.88 | 0.35 |
| fixed_0.1_lines_gated | 2.13 | 5.82 | 5.43 | 0.24 |
| fixed_0.2_lines_gated | 1.79 | 5.94 | 5.17 | 0.17 |
| fixed_0.4_lines_gated | 1.49 | 6.08 | 3.31 | 0.12 |
| fixed_0_selector_gated | 3.92 | 6.06 | 6.29 | 0.30 |
| fixed_0.05_selector_gated | 2.41 | 6.06 | 5.14 | 0.30 |
| fixed_0.1_selector_gated | 1.93 | 5.72 | 4.60 | 0.21 |
| fixed_0.2_selector_gated | 1.67 | 5.83 | 4.91 | 0.14 |
| fixed_0.4_selector_gated | 1.11 | 5.84 | 3.26 | 0.09 |

## Interpretation limits

- `fixed_0_lines` is the unrestricted setting. Its score matches the original bank, verifying the intervention.
- `selector` excludes extra line-finder tones; `lines` permits them. The number is the minimum allowed tracker memory in seconds.
- Fixing a setting removes the joint check's adaptation and its setting transitions together. It does not isolate transition transients alone.
- All static settings and both horizons are retained in the JSON. Choosing a winning static setting here would be hindsight tuning.
- The protective check cannot simply be removed: compare the amplification table as well as tone accuracy.
- All 81 baseline/intervention consistency checks pass. No frozen model code changed.

[Plan](C:/Users/talk2.000/Desktop/Claude/predictive-anc/results-joint-setting-diagnosis-01/plan.json) · [All scores](C:/Users/talk2.000/Desktop/Claude/predictive-anc/results-joint-setting-diagnosis-01/results.json)
