"""List third-octave changes per file for selected methods in a development or test json.
Args: json path, then method names."""
import json
import sys

import numpy as np

CENTRES = 1000*2**(np.arange(-14, -4)/3)
data = json.loads(open(sys.argv[1], encoding='utf-8').read())
methods = sys.argv[2:]
for r in data['recordings']:
    print(f"\n{r['file']}  tones={[round(t,1) for t in r['reference_tones_hz']]}")
    for m in methods:
        for s in r['scores']:
            if s['method'] != m:
                continue
            ch = s['third_octave_change_db']
            flag = ' '.join(f"{c:.0f}Hz:{v:+.1f}" for c, v in zip(CENTRES, ch) if v > 0.3)
            print(f"  {m:28s} {s['horizon_start_ms']:>4} ms band {s['band_gain_db']:+.2f} tone {s['tone_band_gain_db'] if s['tone_band_gain_db'] is None else round(s['tone_band_gain_db'],1)}  louder>0.3: {flag}")
print()
for sc in data.get('scenes', []):
    for s in sc['late_window_scores']:
        if s['method'] in methods and s['third_octave_boosts_over_1db'] > 0:
            print('scene', sc['scene'], s['method'], s['horizon_start_ms'], round(s['max_third_octave_change_db'], 2))
