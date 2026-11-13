"""Read study-01 development results: third-octave changes of v2 + gate and bank_wide_lines + gate per development file."""
import json
import sys
from pathlib import Path

import numpy as np

CENTRES = 1000*2**(np.arange(-14, -4)/3)
root = Path(sys.argv[1])/'results-tone-forecaster-01'/'development'
for run in sorted(root.iterdir()):
    dev = json.loads((run/'development.json').read_text(encoding='utf-8'))
    print('==', run.name, dev.get('note'))
    for m in ('v2_gated', 'bank_wide_lines_gated', 'bank_wide_gated'):
        s = dev['summary']['recordings'].get(m)
        if not s:
            continue
        print(m, 'tone med', round(s['median_tone_bin_both_horizons_db'], 2), 'band med', round(s['median_whole_band_both_horizons_db'], 2),
              'third-octave cases', len(s['third_octave_boosts']), 'whole-band', len(s['whole_band_boosts']))
        syn = dev['summary']['synthetic'][m]
        print('   synthetic objective', round(syn['mean_objective_db'], 2), 'windows', syn['windows_below_minus_half_db'],
              'late third-octave cases', syn['late_third_octave_boosts'])
    for r in dev['recordings']:
        line = []
        for m in ('v2_gated', 'bank_wide_lines_gated'):
            for sc in r['scores']:
                if sc['method'] == m:
                    louder = ' '.join(f"{c:.0f}:{d:+.1f}" for c, d in zip(CENTRES, sc['third_octave_change_db']) if d >= .5)
                    line.append(f"   {m:22s} {sc['horizon_start_ms']:>4.0f}ms band {sc['band_gain_db']:+6.2f} tone "
                                f"{sc['tone_band_gain_db'] if sc['tone_band_gain_db'] is None else round(sc['tone_band_gain_db'], 1)}  >=0.5: {louder}")
        print(r['file'])
        print('\n'.join(line))
    # synthetic late cases >= 0.5 per method
    for m in ('v2_gated', 'bank_wide_lines_gated'):
        late = [s for sc in dev['scenes'] for s in sc['late_window_scores'] if s['method'] == m]
        print(m, 'synthetic late cases >=1', sum(max(s['third_octave_change_db']) >= 1 for s in late),
              '>=0.5', sum(max(s['third_octave_change_db']) >= .5 for s in late), 'of', len(late))
