"""Recount the frozen summary from the raw tone table and case files, then look at how much it leans on any one source.
Descriptive only: the verdict stays in summary.json. Written after the verdict was known."""
import csv, json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
sys.path.insert(0, r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
from anc_lab import tuning_fresh_02  # noqa: F401
from anc_lab import tuning_fresh as tf
from anc_lab import tuning_decision as td
from anc_lab import tuning_ablation as ab

S = tf.STUDY
out = {}
summary = json.load(open(S/'summary.json', encoding='utf-8'))
built = json.load(open(S/'rooms.json', encoding='utf-8'))
cases = [json.load(open(S/'cases'/(c['case_id']+'.json'), encoding='utf-8')) for c in built['eligible_cases']]
titles = {s['source_id']: s['title'] for s in built['sources']}
for sigma in (.5, 1., 2.):
    key = f'{sigma:g}'
    row = {}
    level = defaultdict(lambda: defaultdict(dict))
    band = defaultdict(lambda: defaultdict(dict))
    for arm in ('O', 'SD-s30'):
        harms = harmful = useful = kept = tones = 0
        for c in cases:
            for r in c['runs']:
                if r['sigma'] != sigma or r['arm'] != arm:
                    continue
                harms += bool(ab.room_harm(r['room']))
                level[c['source_id']][(c['case_id'], r['seed_index'])][arm] = td.tone_level(r)
                band[c['source_id']][(c['case_id'], r['seed_index'])][arm] = r['room']['band_db']
                for t in r['tones']:
                    tones += 1
                    kept += t['kept']
                    harmful += t['kept'] and t['final_effect']['prefix_erb_db'] < -1e-9
                    useful += t['kept'] and t['final_effect']['prefix_erb_db'] >= td.USEFUL_DB
        row[arm] = dict(room_harms=harms, harmful_keeps_prefix=harmful, useful_keeps=useful, kept=kept, tones=tones)
        saved = summary['by_sigma'][key][arm]['counts']
        assert all(saved[k] == v for k, v in row[arm].items()), (key, arm, row[arm], saved)
    # seeds -> rooms -> sources
    def per_source(d):
        res = {}
        for src, runs in d.items():
            rooms = defaultdict(list)
            for (case, _), v in runs.items():
                rooms[case].append(v['SD-s30']-v['O'])
            res[src] = float(np.mean([np.mean(x) for x in rooms.values()]))
        return res
    t, b = per_source(level), per_source(band)
    sm = summary['by_sigma'][key]['SD-s30']
    assert abs(np.mean(list(t.values()))-sm['tone_level_minus_O']['mean']) < 1e-9, 'tone mean'
    assert abs(np.mean(list(b.values()))-sm['band_db_minus_O']['mean']) < 1e-9, 'band mean'
    loo = {s: round(float(np.mean([v for k, v in t.items() if k != s])), 3) for s in t}
    row.update(tone=sm['tone_level_minus_O'], band=sm['band_db_minus_O'], verdict=sm['verdict'], sources_better=sum(v > 0 for v in t.values()), sources_worse=sum(v < 0 for v in t.values()),
               sources_tied=sum(v == 0 for v in t.values()), per_source={k: round(v, 3) for k, v in sorted(t.items(), key=lambda kv: -kv[1])},
               median=round(float(np.median(list(t.values()))), 3), leave_one_out_min=min(loo.values()), leave_one_out_max=max(loo.values()))
    if sigma == 1.:
        # same frozen bootstrap shape, each source removed in turn
        vals = np.array(list(t.values()))
        rng = np.random.default_rng(20261031)
        low = {}
        for i, s in enumerate(t):
            rest = np.delete(vals, i)
            boots = rest[rng.integers(0, len(rest), (10000, len(rest)))].mean(1)
            low[s] = round(float(np.quantile(boots, .025)), 3)
        row['leave_one_out_lower_bound'] = low
    out[key] = row
out['titles'] = {s: titles[s] for s in sorted({c['source_id'] for c in cases})}
(S/'recheck.json').open('x', encoding='utf-8').write(json.dumps(out, indent=1, ensure_ascii=False))
sys.stdout.reconfigure(encoding='utf-8')
print(json.dumps(out, indent=0, ensure_ascii=False))
