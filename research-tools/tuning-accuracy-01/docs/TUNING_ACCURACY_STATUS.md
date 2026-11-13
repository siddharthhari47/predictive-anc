# Tuning accuracy status — 26 October 2026

Claude review #55 is completed: every primary v2 menu tone has a prefix oracle, and the final checks are instrumented with original-run parity. This is development diagnosis on previously inspected audio, not a new acceptance test.

- Scope: 78 tones, 37 rooms, 14 sources; all 72 original rooms retained in the inventory. Thirty-five have no eligible menu.
- Forty tones were kept and 38 muted. Six keeps make their single-tone auditory band louder in the tuning portion, from 0.11 to 1.83 dB. Five of those remain harmful later; one different tone becomes slightly harmful later. No single-tone later harm exceeds 0.5 dB. These are not the historical whole-band harm metric.
- At a descriptive 1 dB band-benefit level, ten muted tones have a useful gain-bounded prefix-oracle candidate; six also meet that level later. Only three muted tones had already found a 1 dB setting; two also work later. Thus seven of ten are missed search opportunities, not simply mistaken final rejections.
- Median phase error: 26.7 degrees overall, 9.5 kept, 46.0 muted. Six kept settings exceed 60 degrees, but that flag does not identify exactly the same six harms: relative amplitude matters.
- Final checks compare successive recording segments. The compressor's bad setting passed through simulated judgement noise; its second check had no modeled on/off level difference. A useful microwave tone was rejected when a 6.90 dB background rise outweighed 2.21 dB of local reduction. A locomotive example shows the problem without a loop boundary.
- Difference noise is sqrt(2) dB, because each presentation has 1 dB noise. The unchanged two-check rule passes a true null with 30.7% probability under those assumptions. This is not measured human performance.

Verification: ten targeted tests passed; 1,681 original tuning fields agree; 2,803 independent numerical comparisons agree to 5.68e-14. All 78 fits are identifiable. One oracle violates tuner gain bounds, five clip somewhere; capped and bounded scores are explicit. Eight tiny negative probability tails were corrected only in a separate reporting table (maximum keep-probability change 3.33e-16), with original logs preserved.

[Full report](../results-tuning-accuracy-01/REPORT.md) · [Tone diagnostics](../results-tuning-accuracy-01/tone-diagnostics.csv) · [Final checks](../results-tuning-accuracy-01/check-trials.csv) · [Verification](../results-tuning-accuracy-01/verification.json) · [Next development proposal](TUNING_DIAGNOSTIC_NEXT.md)

Keep v2 live. No physical playback, recording, model change, new downloads or fresh-validation claim. The next question is how much better search and valid comparison evidence each contribute. Do not widen the menu or assume more clicks alone will fix this.
