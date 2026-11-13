"""Study 03 diagnosis (development only): for recordings where the fallback let a boosting setting through,
compare the check's view (worst band of the active setting) with the study-02 dev-01 scores of joint.
Args: project path, trace json."""
import json
import sys
from pathlib import Path

import numpy as np

root = Path(sys.argv[1])
trace = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
dev = json.loads((root/'results-tone-forecaster-02'/'development'/'dev-01'/'development.json').read_text(encoding='utf-8'))
bands = np.round(1000*2**(np.arange(-14, -4)/3), 1)
for r in trace:
    if r['kind'] != 'recording':
        continue
    print(f"\n== {r['name']}  scored from {r['scored_from']:.1f} s; histogram {r['histogram']}")
    for g, ms in ((0, 20), (1, 120)):
        tr = [d for d in r['trace'] if d['g'] == g and d['t'] >= r['scored_from']]
        if not tr:
            print(f"  g{g}: no decision in the scored part (file too short)"); continue
        acts = [d['active'] for d in tr]
        wb = [bands[d['worst_band'][d['active']]] if d['active'] else None for d in tr]
        lv = [d['louder'][d['active']] for d in tr]
        print(f"  g{g}: active settings {sorted(set(acts))}; active worst-band level median {np.median(lv):.2f} max {max(lv):.2f};"
              f" worst bands {sorted(set(w for w in wb if w is not None))}")
        mins = [min(d['louder'][1:]) for d in tr]
        print(f"      least-boosting setting median {np.median(mins):.2f}, settings louder median by setting "
              f"{np.round(np.median([d['louder'] for d in tr], axis=0), 2).tolist()}")
        rec = next(x for x in dev['recordings'] if x['file'] == r['name'])
        for m in ('joint_ungated', 'joint_gated', 'v2_gated', 'zero'):
            s = next(s for s in rec['scores'] if s['method'] == m and s['horizon_start_ms'] == ms)
            print(f"      score {m:14s} bands {np.round(s['third_octave_change_db'], 2).tolist()}  tone {s['tone_band_gain_db']}")
