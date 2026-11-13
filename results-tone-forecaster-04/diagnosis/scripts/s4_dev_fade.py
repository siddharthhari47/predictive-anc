"""Study 04 diagnosis, trial 2 (all development material: the eight study-01 development recordings, the 44
development scenes and the 8 buzz scenes): what do fades of several lengths, and a band check that judges the gated
output, cost and gain across everything? Args: project path, output json [--read]."""
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, sys.argv[1])

import s4_lib as L

GATES = {'none':None, 'hard':None,
         'cos3':{'in_blocks':3, 'out_blocks':3, 'shape':'cosine'},
         'cos5':{'in_blocks':5, 'out_blocks':5, 'shape':'cosine'},
         'cos8':{'in_blocks':8, 'out_blocks':8, 'shape':'cosine'},
         'cos12':{'in_blocks':12, 'out_blocks':12, 'shape':'cosine'},
         'cos8in3out':{'in_blocks':8, 'out_blocks':3, 'shape':'cosine'},
         'cos12in4out':{'in_blocks':12, 'out_blocks':4, 'shape':'cosine'}}
METHODS = [{'name':'v2', 'kind':'v2', 'window_seconds':.3},
           {'name':'joint', 'kind':'joint', 'nb_tau':0., 'lines':True, 'options':{}},
           {'name':'gcheck_hard', 'kind':'gated_check', 'nb_tau':0., 'lines':True, 'options':{'gate':L.V2['gate']}},
           {'name':'gcheck_cos8', 'kind':'gated_check', 'nb_tau':0., 'lines':True,
            'options':{'gate':L.V2['gate'], 'fade':GATES['cos8']}}]


def report(d):
    print(f"runtime {d['runtime_seconds']/60:.1f} min")
    print('--- recordings + all scenes')
    L.print_summary(L.summarize(d['records'], d['scenes']), verbose=False)
    for fam in ('standard', 'wander', 'buzz'):
        print(f'--- {fam} scenes')
        L.print_summary(L.summarize([], [s for s in d['scenes'] if s['family'] == fam]), verbose=False)
    print('--- boosts per key (recordings, all scenes)')
    L.print_summary({k:v for k, v in L.summarize(d['records'], d['scenes']).items()
                     if k.split('|')[-1] in ('none', 'hard', 'cos5', 'cos8', 'cos8in3out')}, verbose=True)


def main():
    elapsed = L.timer()
    tasks = L.development_tasks()
    paths = L.development_paths()
    with ProcessPoolExecutor(6) as pool:
        rec_jobs = [pool.submit(L.recording_task, (str(p), METHODS, GATES)) for p in paths]
        scene_jobs = [pool.submit(L.scene_task, (*t, METHODS, GATES)) for t in tasks]
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
