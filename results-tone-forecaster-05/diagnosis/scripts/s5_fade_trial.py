"""Study 05 diagnosis, step 4 (development material only): the real joint check with tones fading in and out.

Runs tone_react.FadeCheckBank variants next to the joint check through study 02's own scene/recording tasks
(same scoring, same v2 gate on top). Args: project path, output json, material ('change', 'scenes', 'all'),
then variant names (default: all). Material: 'change' = the 9 development change scenes; 'scenes' = all 44
development scenes + 8 study-03 buzz scenes; 'all' = that plus the 8 study-01 development recordings."""
import json
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])

import numpy as np

from anc_lab import forecaster_study as s1
from anc_lab import forecaster_study_02 as fs2
from anc_lab import forecaster_study_03 as fs3
from anc_lab.real_hum_study import ELECTRICAL
from anc_lab.tone_react import FadeCheckBank

fs2.BANK_KINDS.setdefault('fade_react', FadeCheckBank)
CHANGE = ('tone_appears_9s', 'tones_stop_9s', 'source_change_9s')


def fade(name, **options):
    return {'name':name, 'kind':'fade_react', 'nb_tau':0., 'lines':True, 'options':options}


VARIANTS = {
    'stepcheck':fade('stepcheck', fade_in_seconds=.01, fade_out_seconds=.01, shape='step'),
    'f05':fade('f05', fade_in_seconds=.05, fade_out_seconds=.05),
    'f10':fade('f10', fade_in_seconds=.1, fade_out_seconds=.1),
    'f20':fade('f20', fade_in_seconds=.2, fade_out_seconds=.2),
    'f10s10':fade('f10s10', fade_in_seconds=.1, fade_out_seconds=.1, switch_fade_seconds=.1),
    'f10s30':fade('f10s30', fade_in_seconds=.1, fade_out_seconds=.1, switch_fade_seconds=.3),
    'in10':fade('in10', fade_in_seconds=.1, fade_out_seconds=.01),
    'out10':fade('out10', fade_in_seconds=.01, fade_out_seconds=.1),
    'f10start2':fade('f10start2', fade_in_seconds=.1, fade_out_seconds=.1, start=[.2, False]),
    'f20s30':fade('f20s30', fade_in_seconds=.2, fade_out_seconds=.2, switch_fade_seconds=.3),
    'f10lin':fade('f10lin', fade_in_seconds=.1, fade_out_seconds=.1, shape='linear'),
}


def main():
    root, dest, material = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    names = sys.argv[4:] or list(VARIANTS)
    v2 = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
    joint = {'name':'joint', 'kind':'joint', 'nb_tau':0., 'lines':True, 'options':{}}
    v2m = [m for m in fs2.COMPARATORS if m['kind'] == 'v2']
    methods = v2m+[joint]+[VARIANTS[n] for n in names]
    _, _, scene_tasks = s1.development_scenes()
    if material == 'change':
        scene_tasks = [t for t in scene_tasks if t[0].split('#')[0] in CHANGE]
    else:
        scene_tasks = scene_tasks+fs3.buzz_scenes()[1]
    jobs = [(fs2._scene_task, (*t, methods, v2)) for t in scene_tasks]
    paths = []
    if material == 'all':
        paths = [s1.checked_path(e) for e in s1.load_split()['development_files']]
        jobs = [(fs2._recording_task, (str(p), methods, v2, p.name not in ELECTRICAL)) for p in paths]+jobs
    out = fs2._pool(jobs, 6)
    records, scenes = out[:len(paths)], out[len(paths):]
    mnames = fs2.method_names(methods)
    rec, syn, fams = fs2.summarize(records, scenes, mnames)
    slim = {'records':[{k:r[k] for k in ('file', 'scores')} for r in records],
            'scenes':[{k:s[k] for k in ('scene', 'family', 'late_window_scores', 'objective')} for s in scenes],
            'timing':{m['name']:max(x['methods'][m['name']].get('own_block_ms_p99', 0.) for x in records+scenes)
                      for m in methods if m['kind'] != 'v2'},
            'counters':{m['name']:[x['methods'][m['name']].get('counters', {}).get('ghosts') for x in scenes]
                        for m in methods if m['kind'] == 'fade_react'}}
    dest.write_text(json.dumps(slim, indent=1), encoding='utf-8')
    print(f'{"method":20s} late>=1  near  objective  ' + ('rec>=1 near tone wholeband' if records else ''))
    for m in mnames:
        if m == 'zero' or m.startswith('prefix') or m.startswith('online'):
            continue
        s = syn[m]
        line = f"{m:20s} {s['late_third_octave_boosts']:6d} {s['late_near_boosts']:5d} {s['mean_objective_db']:9.2f}"
        if records:
            r = rec[m]
            line += (f"   {len(r['third_octave_boosts']):5d} {len(r['near_boosts']):4d} "
                     f"{r['median_tone_bin_both_horizons_db']:5.2f} {r['median_whole_band_both_horizons_db']:6.2f}")
        print(line)
    if material != 'change':
        print('late boosts by family (gated):')
        for m in mnames:
            if m.endswith('_gated'):
                print(f'  {m:20s}', {f:v['late_third_octave_boosts'] for f, v in fams[m].items() if v['late_third_octave_boosts']}
                      if m in fams else '')
    print('p99 own block ms:', slim['timing'])


if __name__ == '__main__':
    main()
