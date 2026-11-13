# Fresh selector test status

> The fresh accuracy result below is unchanged. Its timing follow-on and component reconstruction are now complete; quiet-machine timing remains inconclusive and room tuning remains untested. Read [the current integration checkpoint](SELECTOR_TIMING_STATUS.md).


The fresh L2 test is complete: **pass frozen offline criteria**. 35/40 sources were scored, 25 with reference tones. Mean paired gain over v2 at 20 ms: **+0.536 dB**, 95% source-bootstrap interval **+0.121 to +1.043 dB**.

Retain unchanged L2 as the leading offline chooser candidate. Next, measure its compute deadlines and tail latency without audio, with output parity first. Engine integration still requires timing and acoustic-path validation.

[Completed report](../results-selector-fresh-01/REPORT.md) · [Saved numerical summary](../results-selector-fresh-01/SUMMARY.json) · [Verification](../results-selector-fresh-01/VERIFICATION.json).

The original protocol and two operational amendments preceded scoring. The unchanged chooser was tested once. All raw media and arrays remain local; no physical ANC claim.

## Acquisition preparation history

21 October 2026. **Protocol frozen; fixed-source acquisition underway. No fresh scores yet.**

Claude's correction in message #43 was verified against the raw saved source scores. The L2 rule gives +0.74956 dB mean paired gain at 20 ms, against +1.02734 dB for the window benchmark. Its paired median is zero. Both the reported marginal medians and paired median are correct; the latter is an insensitive decision statistic when most source differences are exact ties. The old outcome remains preserved.

The new interpretation is post-hoc development evidence, not a retrospective pass. The subgroup of longer clips also changes source identity, so it does not prove that short duration caused ties. Counts use two explicit tolerances: 1e-8 dB for numerical differences and 0.01 dB for practically negligible differences.

## Frozen test

- Exactly unchanged L2; v2/fade/zero arms, completed targets only, 1 dB margin, 100 ms fade. Keep v2 in the live engine.
- Forty files, forty uploaders and forty distinct credited-author strings; 1,162,424,776 bytes. Metadata-only freshness checks rejected two previously used identities before freeze; the draft list is retained.
- Two fan/ventilation files, fifteen other machinery files and twenty-three transport-engine files. Several are explicit onset, moving-source, mixed-background or changing-machinery stress cases. This purposive cohort is not representative of all steady hums, and one author/uploader per file does not establish independence of all capture conditions.
- Use the first 90 seconds at most, first audio track/channel zero, unchanged causal resampler and first-40% calibration. Require at least 30 seconds of actual scored target blocks per horizon; no looping, concatenation or favorable crop selection.
- At least 30 usable sources and 20 with reference tones, otherwise inconclusive. No replacement or enlargement after any waveform access.
- Mean paired tone gain at 20 ms: source-bootstrap two-sided 95% lower endpoint >0 (50,000 resamples; seed 20261021). No >1 dB loss on v2 >=3 dB sources at 20 ms; no more recording-by-horizon band boosts across 20/120 ms than v2; no whole-band boosts at either horizon. Report the horizons separately as well.
- Eight new study checks plus eight existing causal-selector checks pass (16 total, 0.753 s), including source-score parity on seen cached data, aggregation, actual duration and harm vetoes. No full-suite claim is made.

Protocol SHA-256: `f395e6a2b9b20dfc4ac5d9d2b33f07e6f9b4c8ed4ead0240fb333e5b8b974308`.

## Pre-scoring operational amendments

The original protocol stays intact. Commons rejected larger originals with HTTP 429 and explicitly requested smaller copies. The first acquisition stopped after ten completed receipts; all receipts and partial files remain. Before any decoding or scoring, `acquisition-amendment-01.json` uniformly nominated one official smaller representation for each fixed source (or an original <=25 MB when none exists). Thirty-eight are available by metadata, approximately 205 MB total; two are exclusions. Requests are serial with ten-second gaps and one retry after a ninety-second backoff. No alternative representation is tried after failure. Derivative identity is supported by its frozen official API URL and parent identity; saved SHA-256/ETag values are local receipts, not externally published checksums.

A subsequent metadata-only code inspection found six Ogg videos labelled `application/ogg`, which the original runner would have sent to the audio-only loader. `decoder-amendment-02.json` corrects video-container routing to the already specified first-audio-track decoder and adds amendment integrity checks. The original runner is preserved. All candidate, comparator, score, crop, normalization and decision code is unchanged. Eighteen targeted checks pass (0.510 s), including saved-score parity and causal-selector invariants. Both amendments were frozen before any fresh media decoding or score access.

- Acquisition amendment SHA-256: `c77ec958c0b8c07856e9997589ed973afcd51f9b65498dc83eded7f22fefea26`.
- Decoder amendment SHA-256: `d4a400d1242f25ce7be08847a711cdd2808d261bda26cb9fcc75f6cfd5e1b426`.

These are disclosed implementation deviations from the original freeze, not changes to the source set or scientific endpoints. Reports must cite both alongside the original protocol.

[Immutable protocol](../results-selector-fresh-01/protocol.json) · [Freeze receipt](../results-selector-fresh-01/frozen.json) · [Seen-data reassessment](../results-selector-fresh-01/REASSESSMENT.md) · [Original design text frozen with the protocol](SELECTOR_FRESH_TEST.md).

All processing is offline reference prediction. No listening, capture, engine promotion or physical ANC claim. Necessary project downloads are already authorized by Sid's direct full-autonomy instruction. Original frozen studies, audit results and predictor code remain unchanged.

