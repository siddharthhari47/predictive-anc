"""Study-01 dev-02 (development material only): boost counts at 1 and 0.5 dB for v2 + gate and bwl + gate. Args: project path."""
import json
import sys
from pathlib import Path

import numpy as np

root = Path(sys.argv[1])
dev = json.loads((root/'results-tone-forecaster-01'/'development'/'dev-02'/'development.json').read_text(encoding='utf-8'))
for m in ('v2_gated', 'bank_wide_lines_gated', 'bank_wide_gated'):
    rec = [(r['file'], s['horizon_start_ms'], max(s['third_octave_change_db'])) for r in dev['recordings'] for s in r['scores'] if s['method'] == m]
    syn = [max(s['third_octave_change_db']) for sc in dev['scenes'] for s in sc['late_window_scores'] if s['method'] == m]
    print(m, 'recordings >=1:', sum(v >= 1 for *_, v in rec), '>=0.5:', sum(v >= .5 for *_, v in rec),
          '| synthetic late >=1:', sum(v >= 1 for v in syn), '>=0.5:', sum(v >= .5 for v in syn))
    print('   ', [(f[:14], ms, round(v, 1)) for f, ms, v in rec if v >= .5])
    print('   ', {k:dev['summary']['recordings'][m][k] for k in ('median_tone_bin_both_horizons_db', 'median_whole_band_both_horizons_db')},
          {k:dev['summary']['synthetic'][m][k] for k in ('mean_objective_db', 'windows_below_minus_half_db')})
