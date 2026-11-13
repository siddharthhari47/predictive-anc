# Matched fan-off / fan-on source characterization

Two new 30-second captures used the same laptop Intel Smart Sound microphone array through Windows WASAPI at 48 kHz mono. The user separately confirmed readiness for fan-off and steady fan-on captures, with otherwise quiet conditions, unchanged requested positions and airflow away from the microphone. No application or OS gain settings were changed by this project. Their effective gain and microphone enhancement state remain unverified.

The study is complete: [open the visual report](../results-source-study-01/report.html). Both captures have matching WAV provenance hashes, no near-full-scale samples and no reported stream errors. Audio remains local; no output stream was opened.

## Findings

- Recorded power in 35–350 Hz was **12.72 dB higher** with the fan on; the confirmation-only difference was 12.77 dB. These are digital recording comparisons, not SPL or cancellation measurements.
- Four bands passed the predefined spectral screen: **40–42, 123–125, 164–166 and 329–331 Hz**.
- The 41 and 124 Hz bands passed both prominence and on/off criteria in 9/9 confirmation windows; 165 and 330 Hz passed in 8/9.
- A peak near 308.5 Hz passed the confirmation criteria but failed discovery prominence, so it was not promoted to a candidate after seeing later data.
- The fan-off recording level declined over its first several seconds. The data alone do not identify whether that reflects room settling or input processing; this is an additional reason to avoid claiming calibrated source separation. Discovery and confirmation results are shown separately.

The difference is consistent with fan-related tonal energy but does not establish fan attribution, phase predictability, reference-to-ear coherence or achievable ANC. Sequential recordings cannot be coherently waveform-subtracted, and unknown AGC/beamforming/suppression may change their relative levels.

## Fixed analysis

The screening criteria were saved before the fan-off capture: 35–350 Hz, 12-second discovery / 18-second confirmation, 2-second windows, at least 6 dB local prominence, at least 6 dB on/off increase, and at least 80% confirmation persistence. Fan-on readiness was then added to the same protocol file before its capture. The implementation fixes its detailed peak-band convention before evaluating the pair: ±1 Hz around each discovery peak; local background is the median density 3–10 Hz away. Source-screen thresholds are engineering criteria, not statistical confidence levels.

Nonoverlapping Hann periodograms preserve absolute digital amplitude; no separate RMS normalization is applied. Each on confirmation window is compared with the mean off confirmation spectrum. Frequencies are chosen only on discovery. Analysis code and protocol hashes are stored in source_study.json.

The four bands characterize this experiment and are not product constants. The intended system discovers new tones automatically. See [generalization and automatic adaptation](GENERALIZATION.md).

## Reproduce

```powershell
python -m anc_lab compare-sources --off results-source-study-01/fan_off.wav --on results-source-study-01/fan_on.wav --out results-source-study-reproduction
```

Use a new result directory. Raw WAVs and their capture sidecars are required for numerical reanalysis. The source/report archive excludes raw microphone audio; it includes results and spectral aggregates for review.

## Verification and next step

The project now passes 26 scientific checks, including known level scaling, persistent-tone acceptance, broadband and shared-tone rejection, discovery/confirmation isolation, capture-hash verification and pooled-source training boundaries. The three study figures have been visually inspected. The original prediction results are retained.

Next: a fresh independent reference trial, with frozen evaluation bands and automatic source adaptation, followed by repeated source/session checks. Live anti-noise remains gated on measured acoustic paths, timing and near-ear pressure.
