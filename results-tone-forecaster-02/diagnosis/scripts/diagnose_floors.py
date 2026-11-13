"""Development-only trial of memory floors, the lean and the joint band check against the plain bank.
Development recordings and development synthetic scenes only (never a test file).
Args: project path, output json path, [scenes: 'all' | 'none']."""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, sys.argv[1])

import numpy as np

CENTRES = 1000*2**(np.arange(-14, -4)/3)

VARIANTS = {
    'base':None,
    'lines0.2':('floor', {'min_tau_lines_seconds':.2}),
    'lean1_lines0.2':('floor', {'lean_db':1., 'min_tau_lines_seconds':.2}),
    'joint':('joint', {}),
    'joint_start.05':('joint', {'start':(.05, False)}),
}

def make(v2, opts):
    from anc_lab.tone_floors import FloorToneBank, JointCheckBank
    from anc_lab.tone_forecasters import ProminentLines, ToneObserverBank
    from anc_lab.tone_selection import ToneSelector
    common = dict(nb_tau=0., release={'ratio':v2['forecaster']['release_ratio'],
                                      'seconds':v2['forecaster']['release_window_seconds']},
                  release_long_seconds=v2['forecaster']['window_seconds'], candidates=ProminentLines())
    if opts is None:
        return ToneObserverBank(2000, 20, ToneSelector(2000, **v2['selector']), **common)
    kind, kw = opts
    cls = FloorToneBank if kind == 'floor' else JointCheckBank
    return cls(2000, 20, ToneSelector(2000, **v2['selector']), **common, **kw)


def run_all(x, grid, v2):
    from anc_lab.release_study import gate_output
    from anc_lab.selection_study import horizon_setup
    from anc_lab.tone_forecasters import stream_forecasts
    _, horizons, groups = horizon_setup()
    out = {}
    for name, opts in VARIANTS.items():
        bank = make(v2, opts)
        shadow = stream_forecasts(bank, x, grid, horizons)
        gated, _ = gate_output(x, grid, shadow, groups, v2['gate'])
        own = 1e3*bank.block_seconds_own
        out[name] = (gated, {'own_p99_ms':float(np.percentile(own, 99)), 'own_max_ms':float(own.max()),
                             'own_mean_ms':float(own.mean()),
                             'counters':{k:v for k, v in bank.counters.items() if k != 'choice_histogram'}})
    return out


def rec_task(args):
    path, v2 = args
    from threadpoolctl import threadpool_limits
    from anc_lab.forecaster_study import score_forecasts
    from anc_lab.real_hum_study import PREFIX_FRACTION, load_any, prominent_tones
    from anc_lab.selection_study import BLOCK, horizon_setup
    with threadpool_limits(limits=1):
        audio, _ = load_any(Path(path))
        prefix = int(PREFIX_FRACTION*len(audio))
        x = (audio-audio[:prefix].mean())/max(audio[:prefix].std(), 1e-12)
        _, horizons, _ = horizon_setup()
        grid = np.arange(BLOCK*50, len(x)-int(max(horizons)), BLOCK)
        keep = grid >= prefix
        tones = prominent_tones(x[prefix:])
        res = run_all(x, grid, v2)
        out = {'file':Path(path).name, 'tones':tones, 'variants':{}}
        for name, (gated, info) in res.items():
            rows = score_forecasts(x, grid[keep], {name:gated[keep]}, tones)
            out['variants'][name] = {'info':info, 'scores':[{k:r[k] for k in ('horizon_start_ms', 'band_gain_db',
                                     'tone_band_gain_db', 'third_octave_change_db')} for r in rows]}
        return out


def scene_task(args):
    name, family, spec, seed, x, v2 = args
    from threadpoolctl import threadpool_limits
    from anc_lab.forecaster_study import score_forecasts, synthesize_wander
    from anc_lab.generalization import normalized_prefix
    from anc_lab.release_study import objective
    from anc_lab.selection_study import BLOCK, FS, SECONDS, TRAIN_END, VAL_END, horizon_setup, synthesize_scene
    with threadpool_limits(limits=1):
        if x is None:
            raw = synthesize_scene(spec, seed) if family == 'standard' else synthesize_wander(spec, seed)
            x, _ = normalized_prefix(raw, TRAIN_END)
        _, horizons, groups = horizon_setup()
        grid = np.arange(BLOCK*50, SECONDS*FS-int(max(horizons)), BLOCK)
        late = grid >= VAL_END
        steady = [tn['freq'] for tn in spec['tones'] if not tn['drift_hz_per_s'] and tn['start'] == 0 and tn['stop'] >= SECONDS]
        res = run_all(x, grid, v2)
        out = {'scene':name, 'variants':{}}
        for m, (gated, info) in res.items():
            rows = score_forecasts(x, grid[late], {m:gated[late]}, steady)
            value, gains = objective(x, spec, grid, gated, groups)
            out['variants'][m] = {'objective_db':value, 'windows_below_minus_half_db':int(sum(g < -.5 for g in gains)),
                                  'own_p99_ms':info['own_p99_ms'],
                                  'late':[{'ms':r['horizon_start_ms'], 'band':r['band_gain_db'], 'max_third':max(r['third_octave_change_db'])}
                                          for r in rows]}
        return out


if __name__ == '__main__':
    from anc_lab import forecaster_study as fsd
    v2 = json.loads(fsd.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
    split = fsd.load_split()
    test_names = {e['file'] for e in split['test_files']}
    paths = [str(fsd.checked_path(e)) for e in split['development_files']]
    assert not any(Path(p).name in test_names for p in paths)
    scenes = []
    if (sys.argv[3] if len(sys.argv) > 3 else 'all') == 'all':
        _, _, scenes = fsd.development_scenes()
    with ProcessPoolExecutor(min(6, fsd.WORKERS)) as pool:     # 19 workers ran out of paging file
        rj = [pool.submit(rec_task, (p, v2)) for p in paths]
        sj = [pool.submit(scene_task, (*t, v2)) for t in scenes]
        records = [j.result() for j in rj]
        scene_out = [j.result() for j in sj]
    Path(sys.argv[2]).write_text(json.dumps({'recordings':records, 'scenes':scene_out}, indent=1), encoding='utf-8')
    for r in records:
        print(f"\n{r['file']}  tones={[round(t, 1) for t in r['tones']]}")
        for name, v in r['variants'].items():
            for s in v['scores']:
                louder = ' '.join(f"{c:.0f}:{d:+.1f}" for c, d in zip(CENTRES, s['third_octave_change_db']) if d >= .5)
                tb = s['tone_band_gain_db']
                print(f"  {name:15s} {s['horizon_start_ms']:>5.0f}ms band {s['band_gain_db']:+5.2f} tone "
                      f"{'  -  ' if tb is None else f'{tb:5.1f}'} p99 {v['info']['own_p99_ms']:4.1f}  >=0.5dB: {louder}")
    if scene_out:
        print('\nSynthetic development scenes')
        for name in VARIANTS:
            vs = [s['variants'][name] for s in scene_out]
            boosts = sum(l['max_third'] >= 1. for v in vs for l in v['late'])
            half = sum(l['max_third'] >= .5 for v in vs for l in v['late'])
            print(f"  {name:15s} objective {np.mean([v['objective_db'] for v in vs]):6.2f}  windows<-0.5 "
                  f"{sum(v['windows_below_minus_half_db'] for v in vs):3d}  late boosts>=1 {boosts:3d}  >=0.5 {half:3d}  "
                  f"p99 max {max(v['own_p99_ms'] for v in vs):4.1f}")
