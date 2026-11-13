# Input timestamp diagnostic

The first recording contains 3,000 callbacks and 30 seconds of samples, with no PortAudio stream status errors and no near-full-scale samples.

The driver-reported input latency is 22 ms. The recorded callback timestamp minus ADC timestamp is approximately **negative 10 ms**. The 99th percentile absolute discrepancy between adjacent ADC timestamp intervals and their sample-count intervals is approximately 4.94 ms. The timestamps are monotonic, but their ordering relative to the callback time is unsuitable for treating them as verified physical sample-age measurements.

These are observations of the host API's reported times, not acoustic measurements. The input sequence can still be evaluated in sample order for forecasting; its end-to-end acoustic timing has not been established. Do not use these reported values as a calibrated future playback schedule. Near-ear/synchronized loopback measurements remain required before a real-time ANC prototype.

The causal resampler retains a further 5 ms FIR group delay. The prediction assessment scores the resampled digital reference; its 20/120 ms forecast horizons are not claims of available physical cancellation lead time.
