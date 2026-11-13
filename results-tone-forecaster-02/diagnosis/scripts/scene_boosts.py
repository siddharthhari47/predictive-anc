"""Per synthetic development scene: late max third-octave change for v2 + gate (study-01 dev-02) and the trial variants."""
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
dev = json.loads((root/'results-tone-forecaster-01'/'development'/'dev-02'/'development.json').read_text(encoding='utf-8'))
trial = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
v2 = {sc['scene']:{s['horizon_start_ms']:max(s['third_octave_change_db']) for s in sc['late_window_scores'] if s['method'] == 'v2_gated'}
      for sc in dev['scenes']}
bwl = {sc['scene']:{s['horizon_start_ms']:max(s['third_octave_change_db']) for s in sc['late_window_scores']
                    if s['method'] == 'bank_wide_lines_gated'} for sc in dev['scenes']}
names = list(trial['scenes'][0]['variants'])
print(f"{'scene':28s} {'v2':>11s} {'bwl01':>11s} " + ' '.join(f'{n:>14s}' for n in names))
for sc in trial['scenes']:
    s = sc['scene']
    cells = [f"{v2[s][20.]:+5.1f}/{v2[s][120.]:+5.1f}", f"{bwl[s][20.]:+5.1f}/{bwl[s][120.]:+5.1f}"]
    for n in names:
        late = {l['ms']:l['max_third'] for l in sc['variants'][n]['late']}
        cells.append(f"{late[20.]:+6.1f}/{late[120.]:+6.1f}")
    print(f"{s:28s} " + ' '.join(f'{c:>11s}' for c in cells[:2]) + ' ' + ' '.join(f'{c:>14s}' for c in cells[2:]))
print('objective per scene (v2, floors, base):')
for sc in trial['scenes']:
    s = sc['scene']
    o = next(x for x in dev['scenes'] if x['scene'] == s)['objective']
    print(f"  {s:28s} v2 {o['v2_gated']['objective_db']:6.2f}  bwl {o['bank_wide_lines_gated']['objective_db']:6.2f}  "
          f"base {sc['variants']['base']['objective_db']:6.2f}  floors {sc['variants']['floors']['objective_db']:6.2f}")
