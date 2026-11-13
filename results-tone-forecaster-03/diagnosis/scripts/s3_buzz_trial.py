"""Study 03 diagnosis, step 3 (synthetic development scenes only): does the tie fallback let boosts through when a
wandering buzz sits above 100 Hz and the lowest third-octave bands are nearly empty? The study-02 test failure
had that shape (described in results-tone-forecaster-02/POST_TEST_NOTES.md); no data from that file is used here.
New development draws (parity 0, seed 20261019), scored in the late windows like every synthetic scene.
Args: project path, output json [--read]."""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, sys.argv[1])

import numpy as np

from anc_lab import forecaster_study as s1
from anc_lab import forecaster_study_02 as fs2
from anc_lab.generalization import HELD_OUT
from anc_lab.release_study import in_parity
from anc_lab.selection_study import TEST_GROUPS, frequency_extent
from anc_lab.tone_cap import CappedCheckBank

fs2.BANK_KINDS['capped'] = CappedCheckBank

CAPS = (1., 2., 3.)
METHODS = ([{'name':'v2', 'kind':'v2', 'window_seconds':.3}, {'name':'joint', 'kind':'joint', 'nb_tau':0., 'lines':True, 'options':{}}]
           + [{'name':f'cap{c:g}', 'kind':'capped', 'nb_tau':0., 'lines':True, 'options':{'cap_db':c}} for c in CAPS])
FLOOR = .01


def draw(rng, forbidden):
    def pick(lo, hi, n, spacing=15.):
        for _ in range(100000):
            fs = sorted(round(float(f), 1) for f in rng.uniform(lo, hi, n))
            if all(in_parity(f, 0) and all(abs(f-b) > 2 for b in forbidden) for f in fs) and all(b-a >= spacing for a, b in zip(fs, fs[1:])):
                return fs
        raise RuntimeError('no room')
    for _ in range(100000):
        f0 = pick(102., 157., 1)[0]
        if all(abs(2*f0-b) > 2 for b in forbidden):
            break
    return {'steady':pick(102., 315., 2), 'wander':pick(102., 315., 2), 'harmonic':[f0, round(2*f0, 1)], 'am':pick(102., 315., 2)}


def scenes(g):
    w = s1.wander_tone
    return {'buzz_steady':{'noise':('white', FLOOR), 'tones':[w(f, a, .1) for f, a in zip(g['steady'], [.4, .2])]},
            'buzz_wander':{'noise':('white', FLOOR), 'tones':[w(f, a, 1.) for f, a in zip(g['wander'], [.4, .2])]},
            'buzz_harmonic':{'noise':('white', FLOOR), 'tones':[w(f, a, .3) for f, a in zip(g['harmonic'], [.4, .25])]},
            'buzz_am':{'noise':('white', FLOOR), 'tones':[w(f, a, .3, .5) for f, a in zip(g['am'], [.4, .2])]}}


def report(d):
    print(f"runtime {d['runtime_seconds']:.0f} s; draws {d['draws']}")
    rows = {}
    for sc in d['scenes']:
        for s in sc['late_window_scores']:
            rows.setdefault(s['method'], []).append((sc['scene'], s['horizon_start_ms'], s['third_octave_change_db'], s['tone_band_gain_db']))
    for m, r in rows.items():
        if m in ('zero', 'prefix_ar', 'online_ar'):
            continue
        boosts = [(n, ms, round(max(c), 1)) for n, ms, c, _ in r if max(c) >= 1]
        print(f"{m:15s} late boosts {len(boosts):2d} near {sum(max(c) >= .5 for _, _, c, _ in r):2d}  "
              f"tone mean {np.mean([t for *_, t in r if t is not None]):5.2f}  objective "
              f"{np.mean([sc['objective'][m]['objective_db'] for sc in d['scenes']]):5.2f}  {boosts}")
    for sc in d['scenes']:
        c = sc['methods']['cap1'].get('counters', {})
        j = sc['methods']['joint'].get('counters', {})
        print(f"  {sc['scene']:22s} joint hist g0 {j['setting_histogram'][0]}  cap1 silent/decisions {c['silent_decisions']}/{c['decisions']}")


def main():
    release = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))
    p2 = json.loads((s1.ROOT/'results-tone-forecaster-02'/'protocol.json').read_text(encoding='utf-8'))['synthetic_test']
    forbidden = (frequency_extent(TEST_GROUPS)+[f for g in HELD_OUT.values() for f in g]
                 + [f for g in p2['standard_draws'] for f in frequency_extent(g)]
                 + [f for g in p2['wander_draws'] for fs in g.values() for f in fs])
    rng = np.random.default_rng(20261019)
    draws = [draw(rng, forbidden) for _ in range(2)]
    tasks = [(f'{n}#dev{rep}', 'wander', spec, 12100+100*rep+i, None) for rep, g in enumerate(draws) for i, (n, spec) in enumerate(scenes(g).items())]
    v2 = release['v2']
    started = time.perf_counter()
    with ProcessPoolExecutor(6) as pool:
        out = list(pool.map(fs2._scene_task, [(*t, METHODS, v2) for t in tasks]))
    d = {'draws':draws, 'methods':METHODS, 'scenes':out, 'runtime_seconds':time.perf_counter()-started}
    Path(sys.argv[2]).write_text(json.dumps(d, allow_nan=False), encoding='utf-8')
    report(d)


if __name__ == '__main__':
    if '--read' in sys.argv:
        report(json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')))
    else:
        main()
