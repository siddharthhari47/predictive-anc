"""Study 03 diagnosis, step 1 (development material only): how often does the joint check's tie fallback
let a boosting setting through? Logs every decision of JointCheckBank on the study-01 development recordings
and the development synthetic scenes. Args: project path, output json."""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, sys.argv[1])

import numpy as np
from threadpoolctl import threadpool_limits

from anc_lab import forecaster_study as s1
from anc_lab.generalization import normalized_prefix
from anc_lab.real_hum_study import ELECTRICAL, PREFIX_FRACTION, load_any
from anc_lab.selection_study import BLOCK, FS, SECONDS, TRAIN_END, VAL_END, horizon_setup, synthesize_scene
from anc_lab.tone_floors import JointCheckBank
from anc_lab.tone_forecasters import ProminentLines, stream_forecasts
from anc_lab.tone_selection import ToneSelector


class Traced(JointCheckBank):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.trace = []

    def _band_check(self, g):
        super()._band_check(g)
        hist = self.history_db[g]
        if len(hist) < self.min_decide:
            return
        bands = np.median([b for b, _ in hist], axis=0)
        louder = bands.max(axis=1)
        total = np.median([t for _, t in hist], axis=0)
        self.trace.append({'t':self.seen/FS, 'g':g, 'active':self.active[g], 'louder':np.round(louder, 2).tolist(),
                           'worst_band':[int(i) for i in bands.argmax(axis=1)], 'total':np.round(total, 2).tolist()})


def make(v2):
    return Traced(FS, BLOCK, ToneSelector(FS, **v2['selector']), nb_tau=0.,
                  release={'ratio':v2['forecaster']['release_ratio'], 'seconds':v2['forecaster']['release_window_seconds']},
                  release_long_seconds=v2['forecaster']['window_seconds'], candidates=ProminentLines())


def rec_task(args):
    path, v2 = args
    with threadpool_limits(limits=1):
        audio, _ = load_any(Path(path))
        prefix = int(PREFIX_FRACTION*len(audio))
        x = (audio-float(np.mean(audio[:prefix])))/max(float(np.std(audio[:prefix])), 1e-12)
        _, horizons, _ = horizon_setup()
        grid = np.arange(BLOCK*50, len(x)-int(max(horizons)), BLOCK)
        bank = make(v2)
        stream_forecasts(bank, x, grid, horizons)
        return {'name':Path(path).name, 'kind':'recording', 'scored_from':prefix/FS, 'trace':bank.trace,
                'histogram':bank.counters['setting_histogram']}


def scene_task(args):
    name, family, spec, seed, x, v2 = args
    with threadpool_limits(limits=1):
        if x is None:
            raw = synthesize_scene(spec, seed) if family == 'standard' else s1.synthesize_wander(spec, seed)
            x, _ = normalized_prefix(raw, TRAIN_END)
        _, horizons, _ = horizon_setup()
        grid = np.arange(BLOCK*50, SECONDS*FS-int(max(horizons)), BLOCK)
        bank = make(v2)
        stream_forecasts(bank, x, grid, horizons)
        return {'name':name, 'kind':'scene', 'family':family, 'scored_from':VAL_END/FS, 'trace':bank.trace,
                'histogram':bank.counters['setting_histogram']}


if __name__ == '__main__':
    v2 = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
    split = s1.load_split()
    paths = [s1.checked_path(e) for e in split['development_files']]
    _, _, tasks = s1.development_scenes()
    with ProcessPoolExecutor(6) as pool:
        futs = [pool.submit(rec_task, (str(p), v2)) for p in paths]+[pool.submit(scene_task, (*t, v2)) for t in tasks]
        out = [f.result() for f in futs]
    Path(sys.argv[2]).write_text(json.dumps(out), encoding='utf-8')
    margin, tie = .5, .25
    print('name                         g  decisions  fallback%  active>margin%  max active louder  max min-louder')
    for r in out:
        for g in (0, 1):
            tr = [d for d in r['trace'] if d['g'] == g and d['t'] >= r['scored_from']]
            if not tr:
                continue
            fb = [min(d['louder'][1:])+tie > margin for d in tr]
            act = [d['louder'][d['active']] if d['active'] else 0. for d in tr]
            over = [a > margin for a in act]
            print(f"{r['name'][:28]:28s} {g}  {len(tr):9d}  {100*np.mean(fb):8.0f}  {100*np.mean(over):14.0f}  "
                  f"{max(act):17.2f}  {max(min(d['louder'][1:]) for d in tr):14.2f}")
