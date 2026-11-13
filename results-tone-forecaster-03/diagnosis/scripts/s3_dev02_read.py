"""Study 03 diagnosis, step 0 (development material only): read study-02 dev-01 for joint gated vs ungated,
v2 and bwl. Boost lists per recording and synthetic late counts. Args: project path."""
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
dev = json.loads((root/'results-tone-forecaster-02'/'development'/'dev-01'/'development.json').read_text(encoding='utf-8'))
print('development files', dev['development_files'])
print('scenes', len(dev['scenes']), 'families', sorted({s['family'] for s in dev['scenes']}))
for m in ('v2_gated', 'v2_ungated', 'bank_wide_lines_gated', 'joint_ungated', 'joint_gated'):
    rec = [(r['file'], s['horizon_start_ms'], max(s['third_octave_change_db'])) for r in dev['recordings'] for s in r['scores'] if s['method'] == m]
    syn = [(sc['scene'], s['horizon_start_ms'], max(s['third_octave_change_db'])) for sc in dev['scenes'] for s in sc['late_window_scores'] if s['method'] == m]
    sm, ss = dev['summary']['recordings'][m], dev['summary']['synthetic'][m]
    print(f"\n{m}: rec >=1 {sum(v >= 1 for *_, v in rec)} >=.5 {sum(v >= .5 for *_, v in rec)} | syn late >=1 {sum(v >= 1 for *_, v in syn)} >=.5 {sum(v >= .5 for *_, v in syn)}"
          f" | tone med {sm['median_tone_bin_both_horizons_db']:.2f} whole med {sm['median_whole_band_both_horizons_db']:.2f}"
          f" | objective {ss['mean_objective_db']:.2f} windows<-.5 {ss['windows_below_minus_half_db']}")
    print('   rec >= .5:', [(f[:16], ms, round(v, 2)) for f, ms, v in rec if v >= .5])
    print('   syn >= 1 :', sorted([(n.split('#')[0][:18], ms, round(v, 1)) for n, ms, v in syn if v >= 1], key=lambda t: -t[2])[:30])
