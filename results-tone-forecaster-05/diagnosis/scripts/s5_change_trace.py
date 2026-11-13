"""Study 05 diagnosis, step 1 (development material only): where do the boosts on the sudden-change scenes come from?

On the 9 development change scenes (tone_appears_9s, tones_stop_9s, source_change_9s; 3 release-study development
draws each) this scores, in the late windows (8-12 s) the bar uses:
- v2 and the joint check as they are, gated and ungated;
- each of the joint check's 10 output settings held fixed for the whole scene (ungated), from one run that records
  every setting's forecast at every origin;
- oracle changes to the joint output, which no causal method can do, to bound what a faster check could reach:
  silent from the change on (an instant change detector), silent for D s after the change and then back on, and
  silent for every target after the change (no forecast tail at all);
- an ideal tone forecaster: the clean synthesized tones themselves, switched on D s after a tone starts and off D s
  after it stops (a perfect tracker with detection delay D; at 120 ms the forecasts made just before a stop still
  run past it).
Args: project path, output json."""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, sys.argv[1])

import numpy as np
from threadpoolctl import threadpool_limits

from anc_lab import forecaster_study as s1
from anc_lab import forecaster_study_02 as fs2
from anc_lab.release_study import gate_output
from anc_lab.selection_study import BLOCK, FS, SECONDS, TRAIN_END, VAL_END, horizon_setup, synthesize_scene
from anc_lab.tone_floors import JointCheckBank
from anc_lab.tone_forecasters import stream_forecasts
from anc_lab.tone_selection import SelectedToneForecaster, ToneSelector

CHANGE = ('tone_appears_9s', 'tones_stop_9s', 'source_change_9s')


class Recorded(JointCheckBank):
    """JointCheckBank that keeps every setting's forecast at every origin, and the active setting."""
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.rec, self.act = {}, {}

    def _choose(self):
        super()._choose()
        self.rec[self.seen-1] = [self.gqueue[g][-1][1].copy() for g in range(len(self.group_h))]
        self.act[self.seen-1] = list(self.active)


def scene_seed(name):
    base, rep = name.split('#dev')
    from anc_lab.selection_study import scene_set, DEV_GROUPS
    keys = list(scene_set(DEV_GROUPS))
    return 3100+100*int(rep)+keys.index(base)


def clean_tones(spec, seed):
    """The synthesized tones alone, each separately, in the scene's normalized units."""
    raw = synthesize_scene(spec, seed)
    mean, scale = float(np.mean(raw[:TRAIN_END])), max(float(np.std(raw[:TRAIN_END])), 1e-8)
    quiet = dict(spec, noise=('white', 0.))
    out = []
    rng = np.random.default_rng(seed)
    t = np.arange(SECONDS*FS)/FS
    rng.standard_normal(len(t))                      # same draw order as synthesize_scene
    for tn in spec['tones']:
        phase = 2*np.pi*(tn['freq']*t+.5*tn['drift_hz_per_s']*t**2)+rng.uniform(-np.pi, np.pi)
        out.append((tn, tn['amp']*np.sin(phase)/scale))
    return out


def score(x, grid, pred, late):
    _, _, groups = horizon_setup()
    rows = []
    for (cols, hz), ms in zip(groups, (20., 120.)):
        target = x[grid[late][:, None]+hz]
        ch = s1.third_octave_changes(target, pred[late][:, cols])
        rows.append({'ms':ms, 'max':max(ch), 'changes':[round(c, 2) for c in ch],
                     'band_gain':float(10*np.log10(np.sum(target**2)/max(np.sum((target-pred[late][:, cols])**2), 1e-30)))})
    return rows


def task(args):
    name, spec, x, v2 = args
    with threadpool_limits(limits=1):
        _, horizons, groups = horizon_setup()
        grid = np.arange(BLOCK*50, SECONDS*FS-int(max(horizons)), BLOCK)
        late = grid >= VAL_END
        out = {'scene':name, 'tones':[(t['freq'], t['start'], t['stop']) for t in spec['tones']], 'scores':{}}
        fc = SelectedToneForecaster(FS, ToneSelector(FS, **v2['selector']), window_seconds=.3,
                                    release_ratio=v2['forecaster']['release_ratio'],
                                    release_window_seconds=v2['forecaster']['release_window_seconds'])
        v2s = fc.predict(x, grid, horizons)
        method = {'name':'joint', 'kind':'joint', 'nb_tau':0., 'lines':True, 'options':{}}
        bank = fs2.make_bank(method, v2)
        bank.__class__ = Recorded
        bank.rec, bank.act = {}, {}
        js = stream_forecasts(bank, x, grid, horizons)
        preds = {'v2_ungated':v2s, 'v2_gated':gate_output(x, grid, v2s, groups, v2['gate'])[0],
                 'joint_ungated':js, 'joint_gated':gate_output(x, grid, js, groups, v2['gate'])[0]}
        off = int(grid[0]+1) % BLOCK
        settings = np.zeros((len(bank.options), len(grid), len(horizons)))
        for row, o in enumerate(grid):
            for g, (cols, _) in enumerate(groups):
                settings[:, row, cols] = bank.rec[int(o)-off][g]
        for s, (level, lines) in enumerate(bank.options):
            preds[f'fixed_{level:g}_{"lines" if lines else "sel"}'] = settings[s]
        out["active"] = [[round(o/FS, 2)]+bank.act[int(o)-off] for o in grid if (o/FS) % .5 < BLOCK/FS]
        change = 9.*FS
        for d in (0., .25, .5, 1.):
            p = js.copy()
            p[(grid >= change) & (grid < change+d*FS) if d else grid >= change] = 0.
            preds[f'oracle_silent_after_change' if not d else f'oracle_silent_{d:g}s_then_joint'] = p
        p = js.copy()
        p[grid[:, None]+horizons[None, :] >= change] = 0.
        preds['oracle_no_forecast_after_change'] = p
        tones = clean_tones(spec, scene_seed(name))
        for d in (0., .05, .1, .2, .3):
            p = np.zeros_like(js)
            for tn, wave in tones:
                on = (grid >= (tn['start']+d)*FS) & (grid < (tn['stop']+d)*FS)
                p[on] += wave[grid[on][:, None]+horizons[None, :]]
            preds[f'ideal_delay_{d:g}s'] = p
        for m, p in preds.items():
            out['scores'][m] = score(x, grid, p, late)
        return out


def main():
    root, dest = Path(sys.argv[1]), Path(sys.argv[2])
    v2 = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
    _, _, tasks = s1.development_scenes()
    jobs = [(n, spec, x, v2) for n, fam, spec, seed, x in tasks if n.split('#')[0] in CHANGE]
    with ProcessPoolExecutor(6) as pool:
        res = list(pool.map(task, jobs))
    dest.write_text(json.dumps(res, indent=1), encoding='utf-8')
    for r in res:
        print(r['scene'], r['tones'])
        for m, rows in r['scores'].items():
            print(f'  {m:34s}', '  '.join(f"{x['ms']:3.0f}ms max {x['max']:5.2f} gain {x['band_gain']:5.2f}" for x in rows))
    print('\nboost counts (>=1 dB, both horizons, 9 scenes):')
    for m in res[0]['scores']:
        n = sum(x['max'] >= 1. for r in res for x in r['scores'][m])
        nn = sum(x['max'] >= .5 for r in res for x in r['scores'][m])
        g = np.mean([x['band_gain'] for r in res for x in r['scores'][m]])
        print(f'  {m:34s} {n:2d} boosts  {nn:2d} near  mean late band gain {g:5.2f} dB')


if __name__ == '__main__':
    main()
