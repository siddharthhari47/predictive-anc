# Run 01 crashed before scoring was written

The run froze `protocol.json`, then computed the synthetic seeds and the 14 stored rooms, then stopped with
`ValueError: Input rate must be an integer multiple of the analysis rate.` on the first real recording
(44.1 kHz; the decimator needs a multiple of 2 kHz). Nothing was saved or printed apart from progress lines,
so no score from this run was seen.

Fix: real recordings are resampled to 48 kHz before decimating. Detector settings, seeds and bars are
unchanged. The rerun is `results-faint-tones-02`.
