"""Study 04 diagnosis, trial 3 (all development material): synthetic windows below -0.5 dB for the fades and the
gated check, and a gated check that judges an asymmetric fade (8 blocks in, 3 out). Args: project path, output json
[--read]."""
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, sys.argv[1])

import s4_lib as L

GATES = {'none':None, 'hard':None,
         'cos8':{'in_blocks':8, 'out_blocks':8, 'shape':'cosine'},
         'cos8in3out':{'in_blocks':8, 'out_blocks':3, 'shape':'cosine'},
         'cos12in4out':{'in_blocks':12, 'out_blocks':4, 'shape':'cosine'}}
METHODS = [{'name':'v2', 'kind':'v2', 'window_seconds':.3},
           {'name':'joint', 'kind':'joint', 'nb_tau':0., 'lines':True, 'options':{}},
           {'name':'gcheck_hard', 'kind':'gated_check', 'nb_tau':0., 'lines':True, 'options':{'gate':L.V2['gate']}},
           {'name':'gcheck_cos8', 'kind':'gated_check', 'nb_tau':0., 'lines':True,
            'options':{'gate':L.V2['gate'], 'fade':GATES['cos8']}},
           {'name':'gcheck_cos8in3out', 'kind':'gated_check', 'nb_tau':0., 'lines':True,
            'options':{'gate':L.V2['gate'], 'fade':GATES['cos8in3out']}}]


def report(d):
    print(f"runtime {d['runtime_seconds']/60:.1f} min")
    summary = L.summarize(d['records'], d['scenes'])
    for k, r in summary.items():
        if k == 'zero':
            continue
        w = sum(sc['windows_below_minus_half_db'][k] for sc in d['scenes'])
        fam = {f:len([b for b in L.summarize([], [s for s in d['scenes'] if s['family'] == f])[k]['syn_boosts']])
               for f in ('standard', 'wander', 'buzz')}
        print(f"{k:30s} boosts {len(r['rec_boosts'])}+{len(r['syn_boosts'])}={len(r['rec_boosts'])+len(r['syn_boosts']):2d} "
              f"near {r['rec_near']+r['syn_near']:2d} tone {r['tone_median']:.2f} band {r['band_median']:.2f} "
              f"obj {r['objective']:.2f} win<-0.5 {w} by family {fam}")
    runs = d['records']+d['scenes']
    for m in [m['name'] for m in d['methods'] if m['kind'] != 'v2']:
        diff = [r['methods'][m]['own_block_ms_p99']-r['methods']['joint']['own_block_ms_p99'] for r in runs]
        p = [r['methods'][m]['own_block_ms_p99'] for r in runs]
        print(f"{m:20s} own p99 median {np.median(p):.2f} worst {max(p):.2f}; paired difference from joint, median "
              f"{np.median(diff):+.2f} ms")


def main():
    elapsed = L.timer()
    tasks = L.development_tasks()
    paths = L.development_paths()
    with ProcessPoolExecutor(6) as pool:
        rec_jobs = [pool.submit(L.recording_task, (str(p), METHODS, GATES)) for p in paths]
        scene_jobs = [pool.submit(L.scene_task_windows, (*t, METHODS, GATES)) for t in tasks]
        records = [j.result() for j in rec_jobs]
        scenes = [j.result() for j in scene_jobs]
    d = {'gates':GATES, 'methods':METHODS, 'records':records, 'scenes':scenes, 'runtime_seconds':elapsed()}
    L.save(sys.argv[2], d)
    report(d)


if __name__ == '__main__':
    if '--read' in sys.argv:
        import json
        report(json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')))
    else:
        main()
