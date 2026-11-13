"""Faster tone release, tuned on development scenes only, with multi-seed repeats.

Why this study exists: the first selection study (results-tone-selection-01)
showed about one second of slightly negative gain after tones stop. That
observation came from its test scenes, so those scenes are no longer untouched.
This study therefore uses new, randomly drawn frequency groups for both
development and test, and new seeds:

- development: the fixed development groups plus two random draws whose
  frequencies sit inside even-numbered 10 Hz bands;
- test: five random draws inside odd-numbered 10 Hz bands, checked to be more
  than 2 Hz from every development, earlier held-out and earlier test frequency.

Order, enforced in code: tune forecaster settings (stage A), then gate settings
(stage B), on development only; write release_protocol.json; only then draw and
synthesize test scenes. The first study's settings are evaluated unchanged as
"v1"; the tuned settings are "v2". Synthetic reference prediction only.
"""
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import csv
import hashlib
import itertools
import json
import os
from pathlib import Path
import time
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits

from .assessment import choose_method, forecast_scores
from .generalization import DEVELOPMENT, HELD_OUT, normalized_prefix, pooled_training, synthesize
from .predictors import DirectPredictor, ToneTracker, estimate_tones
from .selection_study import (BLOCK, DEV_GROUPS, FS, HORIZONS_MS, SECONDS, TEST_GROUPS, TRAIN_END, VAL_END,
                              apply_gate, detection_errors, frequency_extent, horizon_setup, scene_set,
                              static_detection_errors, synthesize_scene, transition_latency)
from .tone_selection import SelectedToneForecaster, ToneSelector, active_at, realized_gate

V1 = {'selector':{'alpha':1e-2, 'acquire':2, 'history':3, 'release':4},
      'forecaster':{'window_seconds':.6, 'release_ratio':None, 'release_window_seconds':.1},
      'gate':{'min_gain_db':-1., 'lookback':25, 'min_matured':10, 'shared_group':None},
      'source':'results-tone-selection-01/selection_protocol.json'}
STAGE_A = {'release':[1, 2, 4], 'release_ratio':[None, .3, .5], 'release_window_seconds':[.1, .2],
           'tracker_window_seconds':[.6, .3]}
STAGE_B = {'min_gain_db':[None, -1., 0., 1., 3.], 'lookback':[5, 10, 25], 'shared_group':[None, 0]}
GAIN_CAP_DB = 20.
EVENT_SECONDS = 1.5
DEV_REPEATS, TEST_REPEATS = 3, 5
LOW, HIGH, SPACING = 40., 330., 15.
WORKERS = max(1, min(24, (os.cpu_count() or 2)-2))


# ---------- fresh frequency draws ----------

def in_parity(f, parity, lo=2.5, hi=7.5):
    return int(f//10) % 2 == parity and lo <= f % 10 <= hi


def draw_groups(rng, parity, forbidden, drift=.5):
    """Random groups with the same keys/sizes as TEST_GROUPS, inside parity bands.

    Tones within one scene are >= SPACING apart; every frequency is > 2 Hz from
    `forbidden`. Drift tones start in [10k+2, 10k+2.5] so their 6 Hz path stays
    inside their own 10 Hz band.
    """
    def fresh(fs):
        return all(LOW <= f <= HIGH and all(abs(f-b) > 2 for b in forbidden) for f in fs)

    def pick(n, test=lambda f: in_parity(f, parity)):
        for _ in range(100000):
            fs = sorted(round(float(f), 1) for f in rng.uniform(LOW, HIGH, n))
            if all(test(f) for f in fs) and fresh(fs) and all(b-a >= SPACING for a, b in zip(fs, fs[1:])):
                return fs
        raise RuntimeError('Could not draw fresh frequencies.')

    groups = {'single':pick(1), 'unrelated':pick(3), 'appear':pick(1), 'stop':pick(2),
              'weak':pick(2), 'rumble':pick(2)}
    for _ in range(100000):
        f0 = round(float(rng.uniform(LOW, HIGH/3)), 1)
        h = [round(f0*k, 1) for k in (1, 2, 3)]
        # Exact harmonics cannot all sit in the 2.5-7.5 Hz interiors; use 1-9 Hz.
        # Freshness (> 2 Hz from forbidden) is still checked explicitly.
        if all(in_parity(f, parity, 1., 9.) for f in h) and fresh(h):
            groups['harmonic'] = h; break
    else:
        raise RuntimeError('Could not draw harmonic group.')
    for _ in range(100000):
        starts = sorted(round(float(f), 2) for f in 10*rng.choice(np.arange(4, 33)[np.arange(4, 33) % 2 == parity],
                                                                  2, replace=False) + rng.uniform(2., 2.5, 2))
        ends = [f+drift*SECONDS for f in starts]
        on_path = any(a-2 <= b <= e+2 for a, e in zip(starts, ends) for b in forbidden)
        if starts[1]-starts[0] >= SPACING and fresh(starts) and fresh(ends) and not on_path:
            groups['drift'] = starts; break
    change = pick(3)
    groups['change_a'] = [change.pop(int(rng.integers(3)))]
    groups['change_b'] = change
    return groups


# ---------- scoring ----------

def event_times(spec):
    return sorted({e for tn in spec['tones'] for e in (tn['start'], tn['stop']) if 0 < e < SECONDS})


def windowed_gain(x, grid, prediction, columns, horizons, start_s, end_s):
    """Band gain for forecasts issued in [start_s, end_s); 0.5 s of filter warm-up precedes it."""
    rows = (grid >= (start_s-.5)*FS) & (grid < end_s*FS)
    target = x[grid[rows][:, None]+horizons]
    return forecast_scores(target, prediction[rows][:, columns], FS)['band_prediction_gain_db']


def objective_windows(spec):
    windows = [(2.5, SECONDS-.2)]
    windows += [(e, min(e+EVENT_SECONDS, SECONDS-.2)) for e in event_times(spec)]
    return windows


def objective(x, spec, grid, prediction, groups):
    gains = []
    for columns, hz in groups:
        for a, b in objective_windows(spec):
            gains.append(windowed_gain(x, grid, prediction, columns, hz, a, b))
    return float(np.mean(np.minimum(gains, GAIN_CAP_DB))), gains


def output_release_latency(spec, grid, prediction, columns):
    """For scenes where every tone stops: seconds after the stop until predicted
    output RMS stays below 10% of its level in the preceding second."""
    stops = {tn['stop'] for tn in spec['tones']}
    starts_after = [tn['start'] for tn in spec['tones'] if tn['start'] > 0]
    if len(stops) != 1 or starts_after or not 0 < min(stops) < SECONDS:
        return None
    stop = min(stops)
    rms = np.sqrt(np.mean(prediction[:, columns]**2, axis=1))
    before = rms[(grid >= (stop-1)*FS) & (grid < stop*FS)].mean()
    after = np.nonzero(grid >= stop*FS)[0]
    quiet = rms[after] < .1*before
    for k in range(len(after)):
        if quiet[k:].all():
            return float(grid[after[k]]/FS-stop)
    return None


# ---------- workers (top level for Windows process pools) ----------

def _forecast_task(args):
    selector_kw, forecaster_kw, x, spec_name = args
    with threadpool_limits(limits=1):
        _, horizons, _ = horizon_setup()
        grid = np.arange(BLOCK*50, SECONDS*FS-int(max(horizons)), BLOCK)
        forecaster = SelectedToneForecaster(FS, ToneSelector(FS, **selector_kw), **forecaster_kw)
        return spec_name, forecaster.predict(x, grid, horizons)


def make_dev_scenes():
    rng = np.random.default_rng(31)
    forbidden = frequency_extent(TEST_GROUPS)+[f for g in HELD_OUT.values() for f in g]
    draws = [DEV_GROUPS]+[draw_groups(rng, 0, forbidden) for _ in range(DEV_REPEATS-1)]
    scenes = {}
    for rep, groups in enumerate(draws):
        for i, (name, spec) in enumerate(scene_set(groups).items()):
            x, _ = normalized_prefix(synthesize_scene(spec, 3100+100*rep+i), TRAIN_END)
            scenes[f'{name}#dev{rep}'] = (spec, x)
    return draws, scenes


def tune(dev_scenes, pool):
    _, horizons, groups = horizon_setup()
    grid = np.arange(BLOCK*50, SECONDS*FS-int(max(horizons)), BLOCK)
    configs = []
    for release, ratio, short, window in itertools.product(*STAGE_A.values()):
        if ratio is None and short != STAGE_A['release_window_seconds'][0]:
            continue
        configs.append(({'alpha':V1['selector']['alpha'], 'acquire':V1['selector']['acquire'],
                         'history':V1['selector']['history'], 'release':release},
                        {'window_seconds':window, 'release_ratio':ratio, 'release_window_seconds':short}))
    tasks = [(sel, fc, x, name) for sel, fc in configs for name, (_, x) in dev_scenes.items()]
    results = list(pool.map(_forecast_task, tasks, chunksize=4))
    by_config, stage_a = {}, []
    for k, (sel, fc) in enumerate(configs):
        preds = dict(results[k*len(dev_scenes):(k+1)*len(dev_scenes)])
        scores = [objective(x, spec, grid, preds[name], groups)[0] for name, (spec, x) in dev_scenes.items()]
        by_config[k] = preds
        stage_a.append({'selector':sel, 'forecaster':fc, 'dev_objective':float(np.mean(scores)),
                        'dev_worst_scene_objective':float(np.min(scores))})
    best_a = max(range(len(configs)), key=lambda k: (round(stage_a[k]['dev_objective'], 3),
                                                     configs[k][1]['window_seconds'], configs[k][0]['release']))
    shadows = by_config[best_a]
    stage_b = []
    for gate_db, lookback, shared in itertools.product(*STAGE_B.values()):
        if gate_db is None and (lookback != 25 or shared is not None):
            continue
        scores = []
        for name, (spec, x) in dev_scenes.items():
            out = shadows[name] if gate_db is None else apply_gate(
                shadows[name], realized_gate(x, grid, shadows[name], groups, gate_db, lookback,
                                             max(3, lookback//2), shared), groups)
            scores.append(objective(x, spec, grid, out, groups)[0])
        stage_b.append({'min_gain_db':gate_db, 'lookback':lookback, 'min_matured':max(3, lookback//2),
                        'shared_group':shared, 'dev_objective':float(np.mean(scores)),
                        'dev_worst_scene_objective':float(np.min(scores))})
    best_b = max(stage_b, key=lambda r: (round(r['dev_objective'], 3), r['min_gain_db'] is None))
    # v1 on development, for reference only (its settings are fixed, not tuned here).
    v1_index = next(k for k, (sel, fc) in enumerate(configs) if sel['release'] == 4 and fc['release_ratio'] is None
                    and fc['window_seconds'] == .6)
    v1_scores = []
    for name, (spec, x) in dev_scenes.items():
        sh = by_config[v1_index][name]
        out = apply_gate(sh, realized_gate(x, grid, sh, groups, -1., 25, 10), groups)
        v1_scores.append(objective(x, spec, grid, out, groups)[0])
    return configs[best_a], best_b, stage_a, stage_b, float(np.mean(v1_scores))


def gate_output(x, grid, shadow, groups, gate):
    if gate['min_gain_db'] is None:
        return shadow, np.ones((len(grid), len(groups)), bool)
    enabled = realized_gate(x, grid, shadow, groups, gate['min_gain_db'], gate['lookback'],
                            gate['min_matured'], gate['shared_group'])
    return apply_gate(shadow, enabled, groups), enabled


def _test_task(args):
    name, rep, spec, seed, v2, frozen = args
    with threadpool_limits(limits=1):
        delays, horizons, groups = horizon_setup()
        grid = np.arange(BLOCK*50, SECONDS*FS-int(max(horizons)), BLOCK)
        validation_origins = np.arange(TRAIN_END, VAL_END-max(horizons), BLOCK)
        test_origins = np.arange(VAL_END, SECONDS*FS-max(horizons), BLOCK)
        x, _ = normalized_prefix(synthesize_scene(spec, seed), TRAIN_END)
        outputs, detect, timing = {}, {}, {}
        for label, cfg in (('v1', V1), ('v2', v2)):
            selector = ToneSelector(FS, **cfg['selector'])
            fc = SelectedToneForecaster(FS, selector, **cfg['forecaster'])
            shadow = fc.predict(x, grid, horizons)
            gate = cfg['gate']
            out, enabled = gate_output(x, grid, shadow, groups, gate)
            outputs[f'auto_{label}_ungated'], outputs[f'auto_{label}_gated'] = shadow, out
            detect[label] = {'test':detection_errors(spec, fc.decisions, VAL_END, SECONDS*FS),
                             'latency':transition_latency(spec, fc.decisions), 'fast_drops':fc.fast_drops,
                             'output_release_latency_s':{str(ms):output_release_latency(spec, grid, out, cols)
                                                         for (cols, _), ms in zip(groups, HORIZONS_MS)},
                             'gate_enabled_fraction_test':[float(np.mean(enabled[grid >= VAL_END, g]))
                                                           for g in range(len(groups))]}
            timing[label] = {'selector_update_ms_mean':1e3*float(np.mean(selector.update_seconds_measured)),
                             'selector_update_ms_max':1e3*float(np.max(selector.update_seconds_measured)),
                             'forecast_ms_per_origin':1e3*fc.predict_seconds_per_origin}
        fixed = estimate_tones(x[:TRAIN_END], FS)
        models = {'fixed_top3_tracker':ToneTracker(FS, fixed),
                  'adapted_ridge_ar':DirectPredictor('ridge_ar', horizons, seed=7).fit(x, TRAIN_END),
                  'adapted_mlp':DirectPredictor('mlp', horizons, seed=7).fit(x, TRAIN_END),
                  'frozen_pooled_mlp':frozen}
        detect['fixed_top3'] = {'test':static_detection_errors(spec, fixed, VAL_END, SECONDS*FS, round(.25*FS)),
                                'frequencies_hz':fixed}

        def predictions(origins):
            rows = np.searchsorted(grid, origins)
            out = {'zero':np.zeros((len(origins), len(horizons)))}
            out.update({m:p[rows] for m, p in outputs.items()})
            out.update({m:model.predict(x, origins, horizons) for m, model in models.items()})
            return out
        val, test = predictions(validation_origins), predictions(test_origins)
        full = {m:model.predict(x, grid, horizons) for m, model in models.items()}
        full.update(outputs); full['zero'] = np.zeros((len(grid), len(horizons)))
        rows = []
        for (cols, hz), ms in zip(groups, HORIZONS_MS):
            target_v = x[validation_origins[:, None]+hz]
            val_scores = {m:forecast_scores(target_v, p[:, cols], FS) for m, p in val.items()}
            pick = choose_method(val_scores)
            target_t = x[test_origins[:, None]+hz]
            for m, p in test.items():
                score = forecast_scores(target_t, p[:, cols], FS)
                events = {f'{e:g}s':windowed_gain(x, grid, full[m], cols, hz, e, min(e+EVENT_SECONDS, SECONDS-.2))
                          for e in event_times(spec)}
                rows.append({'case':name, 'repeat':rep, 'seed':seed, 'method':m, 'horizon_start_ms':ms,
                             'selected_on_validation':m == pick, 'test':score,
                             'validation_band_gain_db':val_scores[m]['band_prediction_gain_db'],
                             'post_event_band_gain_db':events})
        return {'case':name, 'repeat':rep, 'rows':rows, 'detection':detect, 'timing':timing,
                'mlp_iterations':models['adapted_mlp'].metadata['iterations']}


def run_release_study(output):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Release-study output must be new or empty; earlier results are preserved.')
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    _, horizons, _ = horizon_setup()
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        print(f'Tuning on development scenes only ({WORKERS} worker processes)', flush=True)
        dev_draws, dev_scenes = make_dev_scenes()
        (sel, fc), gate, stage_a, stage_b, v1_dev = tune(dev_scenes, pool)
        v2 = {'selector':sel, 'forecaster':fc,
              'gate':{k:gate[k] for k in ('min_gain_db', 'lookback', 'min_matured', 'shared_group')}}
        # Test frequencies are drawn only after tuning is complete.
        rng = np.random.default_rng(41)
        forbidden = ([f for g in dev_draws for f in frequency_extent(g)] + frequency_extent(TEST_GROUPS)
                     + [f for g in DEVELOPMENT for f in g] + [f for g in HELD_OUT.values() for f in g])
        test_draws = [draw_groups(rng, 1, forbidden) for _ in range(TEST_REPEATS)]
        if any(abs(a-b) <= 2 for g in test_draws for a in frequency_extent(g) for b in forbidden):
            raise ValueError('Test draw is not fresh.')
        protocol = {'kind':'tone_release_tuning_and_multiseed_evaluation', 'fs':FS, 'block':BLOCK, 'seconds':SECONDS,
                    'horizon_start_ms':list(HORIZONS_MS), 'v1':V1, 'v2':v2,
                    'stage_a_grid':{k:[str(v) for v in vals] for k, vals in STAGE_A.items()}, 'stage_a':stage_a,
                    'stage_b_grid':{k:[str(v) for v in vals] for k, vals in STAGE_B.items()}, 'stage_b':stage_b,
                    'v1_dev_objective':v1_dev,
                    'objective':f'Mean over development scenes of the mean band gain (capped at {GAIN_CAP_DB:g} dB) over the 2.5-11.8 s window and each {EVENT_SECONDS:g} s post-onset/offset window, both horizons. Stage A (selector release, fast amplitude release, tracker window) without gate; then stage B (gate) on the stage-A winner. Ties (objective equal to 0.001 dB): longer tracker window, then larger selector release, i.e. the setting closer to v1. Stage B ties prefer no gate.',
                    'development_draws':dev_draws, 'development_seeds':'3100+100*repeat+scene index',
                    'test_draws':test_draws, 'test_seeds':'4100+100*repeat+scene index',
                    'freshness':'Development random draws in even 10 Hz bands, test in odd 10 Hz bands (interior 2.5-7.5 Hz; harmonic groups 1-9 Hz; drift tones start at 10k+2 to 10k+2.5 and drift paths avoid forbidden frequencies). Test frequencies checked > 2 Hz from all development, earlier held-out and study-01 test frequencies.',
                    'why_new_test_scenes':'The release weakness was found on study-01 test scenes, so those are no longer untouched.',
                    'limitations':'Synthetic reference prediction only. No acoustic path, playback timing, microphone processing or ear measurement.',
                    'code_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')},
                    'created_utc':datetime.now(timezone.utc).isoformat()}
        (output/'release_protocol.json').write_text(json.dumps(protocol, indent=2), encoding='utf-8')
        print(f"Frozen v2: {json.dumps(v2)}", flush=True)
        with threadpool_limits(limits=1):
            development = [synthesize(f, 401+i, seconds=6) for i, f in enumerate(DEVELOPMENT)]
            inputs, targets, _ = pooled_training(development, horizons)
            frozen = DirectPredictor('mlp', horizons, seed=7)
            frozen.mean, frozen.scale = 0., 1.
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always', ConvergenceWarning)
                frozen.model.fit(inputs, targets)
        frozen_info = {'iterations':int(frozen.model.n_iter_), 'warnings':[str(w.message) for w in caught]}
        tasks = [(name, rep, spec, 4100+100*rep+i, v2, frozen)
                 for rep, groups in enumerate(test_draws) for i, (name, spec) in enumerate(scene_set(groups).items())]
        print(f'Evaluating {len(tasks)} fresh test scenes', flush=True)
        scenes = list(pool.map(_test_task, tasks))
    result = {'protocol':protocol, 'frozen_pooled_mlp':frozen_info, 'scenes':scenes,
              'summary':summarize(scenes), 'runtime_seconds':time.perf_counter()-started,
              'status':'Synthetic reference prediction only; no physical ANC validation.'}
    (output/'release_study.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    with (output/'metrics.csv').open('w', newline='', encoding='utf-8') as handle:
        cols = ['case', 'repeat', 'seed', 'method', 'horizon_start_ms', 'selected_on_validation',
                'test_band_gain_db', 'test_nrmse', 'validation_band_gain_db', 'post_event_band_gain_db']
        writer = csv.DictWriter(handle, fieldnames=cols); writer.writeheader()
        for scene in scenes:
            for r in scene['rows']:
                writer.writerow({**{k:r[k] for k in cols[:6]}, 'test_band_gain_db':r['test']['band_prediction_gain_db'],
                                 'test_nrmse':r['test']['nrmse'], 'validation_band_gain_db':r['validation_band_gain_db'],
                                 'post_event_band_gain_db':json.dumps(r['post_event_band_gain_db'])})
    from .release_report import write_release_report
    write_release_report(output, result)
    return result


def summarize(scenes):
    """Mean / min / max over repeats per case, method and horizon."""
    out = {}
    for scene in scenes:
        for r in scene['rows']:
            key = (r['case'], r['method'], r['horizon_start_ms'])
            entry = out.setdefault(key, {'test':[], 'post_event':[], 'picked':0})
            entry['test'].append(r['test']['band_prediction_gain_db'])
            entry['post_event'] += list(r['post_event_band_gain_db'].values())
            entry['picked'] += r['selected_on_validation']
    summary = []
    for (case, method, ms), e in out.items():
        t, p = np.array(e['test']), np.array(e['post_event'])
        summary.append({'case':case, 'method':method, 'horizon_start_ms':ms, 'repeats':len(t),
                        'test_mean_db':float(t.mean()), 'test_min_db':float(t.min()), 'test_max_db':float(t.max()),
                        'post_event_mean_db':float(p.mean()) if len(p) else None,
                        'post_event_min_db':float(p.min()) if len(p) else None,
                        'validation_picked':e['picked']})
    return summary
