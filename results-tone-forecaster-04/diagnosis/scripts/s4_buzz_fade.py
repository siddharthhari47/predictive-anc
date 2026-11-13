"""Study 04 diagnosis, trial 1 (the 8 development buzz scenes of study 03 only): how much of the gate's added boosts
does a fade remove, and does a band check that judges the gated output help? Each forecaster runs once per scene; every
gate variant is applied to the same ungated forecast. Args: project path, output json [--read]."""
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, sys.argv[1])

import s4_lib as L

GATES = {'none':None, 'hard':None,
         'lin1':{'in_blocks':1, 'out_blocks':1, 'shape':'linear'},
         'cos2':{'in_blocks':2, 'out_blocks':2, 'shape':'cosine'},
         'cos3':{'in_blocks':3, 'out_blocks':3, 'shape':'cosine'},
         'cos5':{'in_blocks':5, 'out_blocks':5, 'shape':'cosine'},
         'cos8':{'in_blocks':8, 'out_blocks':8, 'shape':'cosine'},
         'cos5in2out':{'in_blocks':5, 'out_blocks':2, 'shape':'cosine'},
         'cos8in3out':{'in_blocks':8, 'out_blocks':3, 'shape':'cosine'}}
METHODS = [{'name':'v2', 'kind':'v2', 'window_seconds':.3},
           {'name':'joint', 'kind':'joint', 'nb_tau':0., 'lines':True, 'options':{}},
           {'name':'gcheck_hard', 'kind':'gated_check', 'nb_tau':0., 'lines':True, 'options':{'gate':L.V2['gate']}},
           {'name':'gcheck_cos3', 'kind':'gated_check', 'nb_tau':0., 'lines':True,
            'options':{'gate':L.V2['gate'], 'fade':GATES['cos3']}}]


def report(d):
    print(f"runtime {d['runtime_seconds']:.0f} s")
    L.print_summary(L.summarize([], d['scenes']))
    for sc in d['scenes']:
        print(f"  {sc['scene']:20s} transitions hard v2 {sc['methods']['v2']['transitions|hard']:3d} joint "
              f"{sc['methods']['joint']['transitions|hard']:3d}; open joint {sc['methods']['joint']['open|hard']:.2f}")


def main():
    elapsed = L.timer()
    tasks = L.development_tasks(include=('buzz',))
    with ProcessPoolExecutor(6) as pool:
        scenes = list(pool.map(L.scene_task, [(*t, METHODS, GATES) for t in tasks]))
    d = {'gates':GATES, 'methods':METHODS, 'scenes':scenes, 'runtime_seconds':elapsed()}
    L.save(sys.argv[2], d)
    report(d)


if __name__ == '__main__':
    if '--read' in sys.argv:
        import json
        report(json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')))
    else:
        main()
