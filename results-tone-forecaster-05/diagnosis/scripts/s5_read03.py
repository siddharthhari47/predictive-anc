import json, sys
from pathlib import Path
root = Path(sys.argv[1])
d = json.loads((root/'results-tone-forecaster-03/development/dev-01/development.json').read_text())
print([c['name'] for c in d['comparators']])
ms = ['v2_gated','v2_ungated','joint_gated','joint_ungated','bank_wide_lines_gated']
from collections import Counter
for m in ms:
    cnt = Counter(); tot=0
    for sc in d['scenes']:
        for s in sc['late_window_scores']:
            if s['method']==m and s['third_octave_boosts_over_1db']>0:
                cnt[sc['scene'].split('#')[0]]+=1; tot+=1
    print(m, tot, dict(cnt))
print()
# details for change scenes
for sc in d['scenes']:
    n = sc['scene']
    if not any(k in n for k in ('source_change','tone_appears','tones_stop')): continue
    print(n, sc['seed'], [ (t['freq'],t['start'],t['stop']) for t in sc['spec']['tones']])
    for m in ['v2_gated','v2_ungated','joint_gated','joint_ungated']:
        for s in sc['late_window_scores']:
            if s['method']==m:
                ch = s['third_octave_change_db']
                print(f"   {m:16s} {s['horizon_start_ms']:5.0f} band {s['band_gain_db']:6.2f} max {s['max_third_octave_change_db']:6.2f} bands", ' '.join(f'{c:5.1f}' for c in ch))
    o = sc['objective']
    print('   obj', {m: round(o[m]['objective_db'],2) for m in ['v2_gated','joint_gated'] if m in o}, {m:[round(g,1) for g in o[m]['window_gains_db']] for m in ['v2_gated','joint_gated']})
