# Saved-signal verification

24 October 2026. **Passed**, with maximum numeric difference 1.06e-14.

Reconstructed all 576 metric rows and 78 complete switch-window powers (80 events total) from stored traces and saved settings. Independently rebuilt output placement, filtering, power ratios, per-source aggregation, bootstrap intervals and harm decisions. Reconstructed all 144 noncausal bound outcomes from their saved coefficients. Compared individual case JSON with the aggregate; checked source/cache/code/protocol receipts and the original v2 outcomes/tuning structures.

The verifier records 119,285 comparisons including nested values and structures; these are not that many independent experiments or unit tests. Seven targeted unit tests passed separately. The whole historical suite was not rerun. This verification shares the native tone renderer and SciPy primitives with the scorer; it is not an independent full predictor implementation.

Nothing was re-predicted or re-tuned. No frozen scores, settings, rules or original code were changed. Actual tuned-command exposure is an explicitly post-hoc diagnostic and does not alter the formal coverage decision.

Verifier SHA-256: `2970db3b351b1218aa3645fb93cecbd6ab179ed63080ac91c641ec50016c2332`.
Results SHA-256: `2c54bde410207e530c2effde621ea7b2d480fa96a33c19c15ac602b959865232`.
Full receipt: [verification.json](verification.json).
