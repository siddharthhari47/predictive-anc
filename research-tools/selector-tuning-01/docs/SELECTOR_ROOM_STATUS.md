# Fixed-tuning room checkpoint — 24 October 2026

**24 October continuation:** All 72 fixed-tuning rooms are scored. The result is **inconclusive for switch coverage**, with one observed primary whole-band harm-limit breach: the reused-tuning chooser makes an air-compressor room 0.570 dB louder than no control (v2: 0.324 dB). Five sources meet the frozen switch condition, below six; only three have nonzero tuned output during complete scored switches. Mean paired tone change is +0.017 dB, 95% interval -0.012 to +0.055. Keep v2 live. Next diagnose persistent tuning compatibility on the compressor, then prewrite an active-output switch stress test. The quiet-machine timing gate remains unresolved. The fresh +0.536 dB reference-prediction result is unchanged and is not an ear-attenuation claim.

The frozen experiment has ended. Preserve its 72 rooms and do not append cases until it passes. Original48 alone: four qualifying sources, mean -0.010 dB. The planned enrichment adds only one qualifying source. Post-hoc actual-command exposure is three sources at both leads; 46/72 primary v2 tuning sessions mute every tone.

Reusing settings at 30 ms introduces one new whole 35–350 Hz amplification crossing, no new third-octave crossing, no extra clipping and no switch-window energy violation. Own-prefix tuning is secondary and also lacks coverage. At 200 ms it adds one 100 Hz helicopter-band boost; all 200 ms results are exploratory.

The air-compressor switch occurs about 5.63 s into its prefix; scoring starts at 25.44 s. The loss is persistent, not a scored switch transient. Cause is not yet established. The phase/origin controls pass, so a gross shared-origin bug was not observed on the synthetic checks; this does not rule out source-dependent phase or level errors.

Read [full report](../results-selector-tuning-01/REPORT.md), [verification](../results-selector-tuning-01/VERIFICATION.md), [frozen design](SELECTOR_ROOM_TEST.md) and [next diagnostic proposal](SELECTOR_ROOM_NEXT.md). The original protocol and code are unchanged; [pre-scoring amendment](../results-selector-tuning-01/pre-scoring-amendment-01.json) only restores null for the worst band when output is muted.

Evidence: seven targeted checks, all 576 outcome rows and 80 suffix events audited, maximum numerical discrepancy about 1.1e-14. The frozen v2 control matches its earlier tuning/outcomes. No full-suite claim. The first 48-room baseline reproduced 59,939 numbers exactly; 16 alignment scene/lead controls pass within 0.658 degrees and 0.0128 dB.

Research helpers and a hash manifest are in `research-tools/selector-tuning-01/`. Raw audio and cached signal arrays remain local. No real-time engine was changed, no audio device opened, and no physical ear-level attenuation was measured.
