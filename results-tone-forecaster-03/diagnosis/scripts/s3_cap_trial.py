"""Study 03 diagnosis, step 2 (development material only): the joint check with a ceiling on its tie fallback,
for several ceilings, against v2 and the uncapped joint check. Study-01 development recordings and the 44
development synthetic scenes; scored with study 02's helpers.
Args: project path, output json [--read: only print an earlier output]."""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, sys.argv[1])

from anc_lab import forecaster_study as s1
from anc_lab import forecaster_study_02 as fs2
from anc_lab.real_hum_study import ELECTRICAL
from anc_lab.tone_cap import CappedCheckBank

fs2.BANK_KINDS['capped'] = CappedCheckBank          # this process and every worker (the script is re-imported there)

CAPS = (.5, .75, 1., 1.5, 2.)
METHODS = ([{'name':'v2', 'kind':'v2', 'window_seconds':.3}, {'name':'joint', 'kind':'joint', 'nb_tau':0., 'lines':True, 'options':{}}]
           + [{'name':f'cap{c:g}', 'kind':'capped', 'nb_tau':0., 'lines':True, 'options':{'cap_db':c}} for c in CAPS])


def report(d):
    records, scenes, methods = d['recordings'], d['scenes'], d['methods']
    rec, syn, fams = d['summary']['recordings'], d['summary']['synthetic'], d['summary']['synthetic_by_family']
    print(f"runtime {d['runtime_seconds']:.0f} s")
    print('method            rec>=1 rec>=.5 whole  tone   whole  | syn>=1 syn>=.5 objective <-.5 | p99 ms | silent/decisions (rec; scenes)')
    for m in fs2.method_names(methods):
        if not (m.endswith('_gated') or m.endswith('_ungated')):
            continue
        r, s = rec[m], syn[m]
        base = m.rsplit('_', 1)[0]
        p99 = max(x['methods'][base].get('own_block_ms_p99', 0.) for x in records+scenes)

        def dec(xs):
            c = [x['methods'][base].get('counters', {}) for x in xs]
            return sum(sum(k.get('silent_decisions', [0])) for k in c), sum(sum(k.get('decisions', [0])) for k in c)
        print(f"{m:17s} {len(r['third_octave_boosts']):6d} {len(r['near_boosts']):7d} {len(r['whole_band_boosts']):5d} "
              f"{r['median_tone_bin_both_horizons_db']:6.2f} {r['median_whole_band_both_horizons_db']:6.2f} | "
              f"{s['late_third_octave_boosts']:6d} {s['late_near_boosts']:7d} {s['mean_objective_db']:9.2f} {s['windows_below_minus_half_db']:4d} | "
              f"{p99:6.2f} | {dec(records)} ; {dec(scenes)}")
    shown = ['v2_gated', 'joint_gated']+[m['name']+'_gated' for m in methods if m['kind'] == 'capped']
    print('\nper recording (gated): tone-bin gain 20/120 ms (worst band change over both horizons)')
    print('  ' + ' '*24 + '  '.join(f'{m[:-6]:>17s}' for m in shown))
    for x in records:
        row = []
        for m in shown:
            sc = {s['horizon_start_ms']:s for s in x['scores'] if s['method'] == m}
            t = [sc[ms]['tone_band_gain_db'] for ms in (20, 120)]
            tt = '/'.join('-' if v is None else f'{v:.1f}' for v in t)
            row.append(f"{tt:>9s} ({max(sc[20]['max_third_octave_change_db'], sc[120]['max_third_octave_change_db']):+.2f})")
        print(f"  {x['file'][:24]:24s} " + '  '.join(row))
    print('\nsynthetic late windows with a boost, by scene name (gated):')
    for m in shown:
        late = {}
        for sc in scenes:
            for s in sc['late_window_scores']:
                if s['method'] == m and s['max_third_octave_change_db'] >= 1:
                    k = sc['scene'].split('#')[0]
                    late[k] = late.get(k, 0)+1
        print(f"  {m[:-6]:8s} {dict(sorted(late.items()))}")
    print('\nsynthetic objective by family (gated):')
    for fam, dd in fams.items():
        print(f"  {fam:9s} " + '  '.join(f"{m[:-6]}={dd[m]['mean_objective_db']:.2f}" for m in shown))


def main():
    split = s1.load_split()
    v2 = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
    paths = [s1.checked_path(e) for e in split['development_files']]
    _, _, tasks = s1.development_scenes()
    started = time.perf_counter()
    with ProcessPoolExecutor(6) as pool:
        futs = ([pool.submit(fs2._recording_task, (str(p), METHODS, v2, p.name not in ELECTRICAL)) for p in paths]
                + [pool.submit(fs2._scene_task, (*t, METHODS, v2)) for t in tasks])
        out = [f.result() for f in futs]
    records, scenes = out[:len(paths)], out[len(paths):]
    rec, syn, fams = fs2.summarize(records, scenes, fs2.method_names(METHODS))
    d = {'methods':METHODS, 'recordings':records, 'scenes':scenes,
         'summary':{'recordings':rec, 'synthetic':syn, 'synthetic_by_family':fams}, 'runtime_seconds':time.perf_counter()-started}
    Path(sys.argv[2]).write_text(json.dumps(d, allow_nan=False), encoding='utf-8')
    report(d)


if __name__ == '__main__':
    if '--read' in sys.argv:
        report(json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')))
    else:
        main()
