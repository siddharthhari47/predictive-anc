# Could the simulated listener hear the tone being tuned?

After-the-fact diagnostic of `results-tune-by-ear-sim-01` (simulated ear, 30 ms lead, tuning part only). Nothing in the run was changed.

Cue: how much quieter the listener's auditory band around the tone gets when that tone alone is cancelled with the exact path setting, the best that tuning could ever find. The simulated listener answers "same" below 1 dB.

| Cue (dB) | Tones | Predicted quieting after tuning, typical listener (median) | Kept after check: ±0.5 dB listener, ±1 dB listener, ±2 dB listener |
|---|---:|---:|---|
| below 0 | 5 | 0.3 dB | 0%, 20%, 20% |
| 0 to 1 | 19 | 0.8 dB | 26%, 32%, 37% |
| 1 to 3 | 18 | 1.4 dB | 33%, 50%, 22% |
| 3 to 10 | 12 | 6.2 dB | 58%, 75%, 67% |
| 10 or more | 3 | 24.2 dB | 100%, 100%, 100% |

Tones: 57. Cue below 1 dB: 24, of which 5 negative (even the exact setting makes that band louder, because the forecast error is larger than the tone). Median cue 1.4 dB.
