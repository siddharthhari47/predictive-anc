"""Automatic tone-count/confidence selection on fresh synthetic source groups.

Order of operations, enforced in code:
1. Selector and gate settings are chosen on development scenes only (the
   development frequency groups of generalization.py, new seeds).
2. Those settings and the test scene definitions are written to
   selection_protocol.json before any test scene is synthesized.
3. Test scenes use fresh frequency groups, distinct from both development and
   the earlier held-out groups, and fresh seeds.

Old comparators keep their definitions: fixed top-three tracker, AR and MLP
adapted on the 6 s prefix, and the frozen pooled MLP trained on development
sources only. The selector-based methods adapt online from the first second,
with no prefix fit. Synthetic reference prediction only.
"""
from datetime import datetime, timezone
import csv
import hashlib
import itertools
import json
from pathlib import Path
import time
import warnings

import numpy as np
from scipy import signal
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits

from .assessment import choose_method, forecast_scores, load_reference
from .generalization import DEVELOPMENT, HELD_OUT, normalized_prefix, pooled_training, synthesize
from .predictors import DirectPredictor, ToneTracker, estimate_tones
from .tone_selection import SelectedToneForecaster, ToneSelector, active_at, realized_gate

FS, BLOCK, SECONDS = 2000, 20, 12
HORIZONS_MS = (20., 120.)
TRAIN_END, VAL_END = 6*FS, 8*FS
MATCH_HZ = 3.
GRID = {'alpha':[1e-2, 1e-3, 1e-4, 1e-5], 'acquire_history':[(1, 1), (2, 3), (3, 4)], 'release':[1, 2, 4]}
GATE_GRID = [-1., 0., 1., 3.]


def tone(freq, amp, start=0., stop=SECONDS, drift=0.):
    return {'freq':freq, 'amp':amp, 'start':start, 'stop':stop, 'drift_hz_per_s':drift}


def scene_set(groups):
    """Same scene types for development and test; only frequencies/seeds differ."""
    g = groups
    return {
        'silence_floor': {'noise':('white', 1e-4), 'tones':[]},
        'broadband_white': {'noise':('white', .3), 'tones':[]},
        'broadband_rumble': {'noise':('brown', .3), 'tones':[]},
        'single_tone': {'noise':('white', .012), 'tones':[tone(g['single'][0], .45)]},
        'unrelated_tones': {'noise':('white', .012), 'tones':[tone(f, a) for f, a in zip(g['unrelated'], [.45, .25, .13])]},
        'harmonic_tones': {'noise':('white', .012), 'tones':[tone(f, a) for f, a in zip(g['harmonic'], [.45, .25, .13])]},
        'drifting_tones': {'noise':('white', .012), 'tones':[tone(f, a, drift=.5) for f, a in zip(g['drift'], [.4, .2])]},
        'tone_appears_9s': {'noise':('white', .05), 'tones':[tone(g['appear'][0], .4, start=9.)]},
        'tones_stop_9s': {'noise':('white', .05), 'tones':[tone(f, a, stop=9.) for f, a in zip(g['stop'], [.4, .2])]},
        'source_change_9s': {'noise':('white', .05), 'tones':[tone(g['change_a'][0], .4, stop=9.)]
                             + [tone(f, a, start=9.) for f, a in zip(g['change_b'], [.35, .2])]},
        'weak_tones_in_noise': {'noise':('white', .3), 'tones':[tone(f, a) for f, a in zip(g['weak'], [.06, .04])]},
        'tones_in_rumble': {'noise':('brown', .3), 'tones':[tone(f, a) for f, a in zip(g['rumble'], [.2, .1])]},
    }


DEV_GROUPS = {'single':[47.3], 'unrelated':DEVELOPMENT[0], 'harmonic':[60.2, 120.4, 180.6],
              'drift':[68.4, 154.8], 'appear':[231.2], 'stop':[90.1, 267.9],
              'change_a':[113.7], 'change_b':[182.5, 302.6], 'weak':[68.4, 231.2], 'rumble':[47.3, 154.8]}
TEST_GROUPS = {'single':[133.9], 'unrelated':[62.8, 171.3, 288.4], 'harmonic':[85.3, 170.6, 255.9],
               'drift':[141.2, 276.5], 'appear':[197.7], 'stop':[77.0, 223.6],
               'change_a':[126.4], 'change_b':[208.9, 311.8], 'weak':[66.2, 247.3], 'rumble':[44.6, 137.2]}


def frequency_extent(groups, drift=.5):
    out = []
    for key, freqs in groups.items():
        for f in freqs:
            out += [f, f+drift*SECONDS] if key == 'drift' else [f]
    return out


def synthesize_scene(spec, seed):
    rng = np.random.default_rng(seed)
    t = np.arange(SECONDS*FS)/FS
    kind, level = spec['noise']
    noise = rng.standard_normal(len(t))
    if kind == 'brown':
        noise = signal.lfilter([1.], [1., -.98], noise)
    audio = level*noise/np.std(noise)
    for tn in spec['tones']:
        on = (t >= tn['start']) & (t < tn['stop'])
        phase = 2*np.pi*(tn['freq']*t+.5*tn['drift_hz_per_s']*t**2)+rng.uniform(-np.pi, np.pi)
        audio += on*tn['amp']*np.sin(phase)
    return audio


def truth_at(spec, sample):
    s = sample/FS
    return [tn['freq']+tn['drift_hz_per_s']*s for tn in spec['tones'] if tn['start'] <= s < tn['stop']]


def detection_errors(spec, decisions, start, end):
    """False/missed tone counts over update times in [start, end)."""
    false = missed = matched = 0
    freq_error, updates = [], 0
    for t, active in decisions:
        if not start <= t < end:
            continue
        updates += 1
        truth, found = truth_at(spec, t), [f for f, _ in active]
        used = set()
        for f in truth:
            near = [j for j, d in enumerate(found) if j not in used and abs(d-f) <= MATCH_HZ]
            if near:
                j = min(near, key=lambda j: abs(found[j]-f)); used.add(j)
                matched += 1; freq_error.append(abs(found[j]-f))
            else:
                missed += 1
        false += len(found)-len(used)
    truth_count = sum(len(truth_at(spec, t)) for t, _ in decisions if start <= t < end)
    return {'updates':updates, 'false_activations':false, 'missed_tones':missed, 'matched':matched,
            'true_tone_updates':truth_count,
            'updates_with_false_activation':sum(1 for t, a in decisions if start <= t < end and
                                                 len(a) > len([f for f in truth_at(spec, t)])),
            'mean_abs_frequency_error_hz':float(np.mean(freq_error)) if freq_error else None,
            'max_abs_frequency_error_hz':float(np.max(freq_error)) if freq_error else None}


def static_detection_errors(spec, frequencies, start, end, step):
    """Score a fixed (prefix-detected) tone list at the same update times."""
    return detection_errors(spec, [(t, [(f, 1.) for f in frequencies]) for t in range(step-1, end, step)], start, end)


def transition_latency(spec, decisions):
    """Seconds from a scheduled tone onset/offset until the selector reflects it."""
    out = {}
    for tn in spec['tones']:
        for edge, when in (('onset', tn['start']), ('offset', tn['stop'])):
            if 0 < when < SECONDS:
                latency = None
                for t, active in decisions:
                    if t/FS < when:
                        continue
                    f_now = tn['freq']+tn['drift_hz_per_s']*t/FS
                    present = any(abs(f-f_now) <= MATCH_HZ for f, _ in active)
                    if present == (edge == 'onset'):
                        latency = t/FS-when; break
                out[f"{edge}_{tn['freq']:g}Hz"] = latency
    return out


def horizon_setup():
    delays = [round(ms*FS/1000) for ms in HORIZONS_MS]
    horizons = np.unique(np.concatenate([d+np.arange(1, BLOCK+1) for d in delays]))
    groups = [(np.searchsorted(horizons, d+np.arange(1, BLOCK+1)), d+np.arange(1, BLOCK+1)) for d in delays]
    return delays, horizons, groups


def apply_gate(shadow, enabled, groups):
    out = shadow.copy()
    for g, (columns, _) in enumerate(groups):
        rows = ~enabled[:, g]
        out[np.ix_(rows, columns)] = 0.
    return out


def choose_settings(dev_scenes, horizons, groups):
    """Detector grid by development detection errors; gate by development gain."""
    trials = []
    for alpha, (acquire, history), release in itertools.product(GRID['alpha'], GRID['acquire_history'], GRID['release']):
        selector = ToneSelector(FS, alpha=alpha, acquire=acquire, history=history, release=release)
        false = missed = truth = 0
        for name, (spec, x) in dev_scenes.items():
            d = detection_errors(spec, selector.timeline(x), FS, len(x))
            false += d['false_activations']; missed += d['missed_tones']; truth += d['true_tone_updates']
        trials.append({'alpha':alpha, 'acquire':acquire, 'history':history, 'release':release,
                       'false_activations':false, 'missed_tones':missed, 'true_tone_updates':truth,
                       'error_count':false+missed,
                       'warm_up_seconds':selector.settings()['warm_up_seconds']})
    best = min(trials, key=lambda r: (r['error_count'], r['warm_up_seconds'], -r['alpha']))
    selector = ToneSelector(FS, alpha=best['alpha'], acquire=best['acquire'],
                            history=best['history'], release=best['release'])
    grid = np.arange(BLOCK*50, SECONDS*FS-int(max(horizons)), BLOCK)
    eval_rows = grid >= 2*FS
    shadows = {name:SelectedToneForecaster(FS, selector).predict(x, grid, horizons)
               for name, (_, x) in dev_scenes.items()}
    gate_trials = []
    for gate_db in GATE_GRID:
        gains = []
        for name, (_, x) in dev_scenes.items():
            out = apply_gate(shadows[name], realized_gate(x, grid, shadows[name], groups, gate_db), groups)
            for columns, hz in groups:
                target = x[grid[eval_rows][:, None]+hz]
                gains.append(forecast_scores(target, out[eval_rows][:, columns], FS)['band_prediction_gain_db'])
        gate_trials.append({'min_realized_gain_db':gate_db, 'worst_dev_gain_db':float(min(gains)),
                            'mean_dev_gain_db':float(np.mean(gains))})
    gate_best = max(gate_trials, key=lambda r: (round(r['worst_dev_gain_db'], 2), r['mean_dev_gain_db']))
    return selector, best, trials, gate_best, gate_trials


def run_selection_study(output, real_inputs=()):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Selection-study output must be new or empty; earlier results are preserved.')
    extent_old = frequency_extent(DEV_GROUPS)+[f for grp in DEVELOPMENT for f in grp]+[f for grp in HELD_OUT.values() for f in grp]
    if any(abs(a-b) <= 2 for a in frequency_extent(TEST_GROUPS) for b in extent_old):
        raise ValueError('Test frequencies must be >2 Hz from development and earlier held-out groups.')
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    delays, horizons, groups = horizon_setup()
    with threadpool_limits(limits=1):
        print('Choosing selector and gate settings on development scenes only', flush=True)
        dev_specs = scene_set(DEV_GROUPS)
        dev_scenes = {name:(spec, synthesize_scene(spec, 1100+i)) for i, (name, spec) in enumerate(dev_specs.items())}
        selector, best, trials, gate_best, gate_trials = choose_settings(dev_scenes, horizons, groups)
        gate_db = gate_best['min_realized_gain_db']
        test_specs = scene_set(TEST_GROUPS)
        protocol = {
            'kind':'causal_tone_count_confidence_selection', 'fs':FS, 'block':BLOCK, 'seconds':SECONDS,
            'partition_seconds':[6, 2, 4], 'horizon_start_ms':list(HORIZONS_MS),
            'selector_settings':selector.settings(), 'selector_grid':GRID, 'selector_choice':best,
            'gate':{'min_realized_gain_db':gate_db, 'lookback_blocks':25, 'min_matured_blocks':10,
                    'rule':'Enable output at origin t only if forecasts whose whole target block ended by t beat zero by the threshold.'},
            'gate_grid':gate_trials, 'development_groups':DEV_GROUPS, 'development_seeds':'1100+scene index',
            'test_groups':TEST_GROUPS, 'test_seeds':'2100+scene index', 'test_scenes':test_specs,
            'detection_match_hz':MATCH_HZ,
            'selection_rule':'Detector: fewest development false+missed tone-updates, tie: shorter warm-up, larger alpha. Gate: best worst-case then mean development band gain.',
            'adaptation_budgets':{
                'fixed_top3_tracker':'estimate_tones on 6 s prefix (unchanged earlier method), frozen afterwards',
                'adapted_ridge_ar / adapted_mlp':'fit on 6 s prefix of each new scene',
                'frozen_pooled_mlp':'weights from three development sources only; prefix scaling only',
                'auto_selected_tracker':'online, uses only the latest 1 s window for detection and 0.6 s for fitting; no prefix fit',
                'auto_selected_gated':'auto_selected_tracker plus realized-error mute gate'},
            'limitations':'Synthetic reference only, one seed per scene, no acoustic path, playback timing or microphone processing. Not evidence of physical ANC.',
            'code_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')},
            'created_utc':datetime.now(timezone.utc).isoformat()}
        (output/'selection_protocol.json').write_text(json.dumps(protocol, indent=2), encoding='utf-8')
        print(f"Frozen settings: {best} gate {gate_db} dB", flush=True)

        development = [synthesize(f, 401+i, seconds=6) for i, f in enumerate(DEVELOPMENT)]
        inputs, targets, _ = pooled_training(development, horizons)
        frozen = DirectPredictor('mlp', horizons, seed=7)
        frozen.mean, frozen.scale = 0., 1.
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always', ConvergenceWarning)
            frozen.model.fit(inputs, targets)
        frozen_info = {'iterations':int(frozen.model.n_iter_), 'warnings':[str(w.message) for w in caught]}

        grid = np.arange(BLOCK*50, SECONDS*FS-int(max(horizons)), BLOCK)
        validation_origins = np.arange(TRAIN_END, VAL_END-max(horizons), BLOCK)
        test_origins = np.arange(VAL_END, SECONDS*FS-max(horizons), BLOCK)
        rows, detections, info = [], {}, {}
        for i, (name, spec) in enumerate(test_specs.items()):
            print(f'Evaluating fresh scene: {name}', flush=True)
            x, normalization = normalized_prefix(synthesize_scene(spec, 2100+i), TRAIN_END)
            fixed = estimate_tones(x[:TRAIN_END], FS)
            forecaster = SelectedToneForecaster(FS, selector)
            shadow = forecaster.predict(x, grid, horizons)
            enabled = realized_gate(x, grid, shadow, groups, gate_db)
            selected_out = apply_gate(shadow, enabled, groups)
            models = {'fixed_top3_tracker':ToneTracker(FS, fixed),
                      'adapted_ridge_ar':DirectPredictor('ridge_ar', horizons, seed=7).fit(x, TRAIN_END),
                      'adapted_mlp':DirectPredictor('mlp', horizons, seed=7).fit(x, TRAIN_END),
                      'frozen_pooled_mlp':frozen}
            def predictions(origins):
                rows_in_grid = np.searchsorted(grid, origins)
                out = {'zero':np.zeros((len(origins), len(horizons))),
                       'auto_selected_tracker':shadow[rows_in_grid],
                       'auto_selected_gated':selected_out[rows_in_grid]}
                out.update({m:model.predict(x, origins, horizons) for m, model in models.items()})
                return out
            val_pred = predictions(validation_origins)
            selected = {}
            val_scores = {}
            for (columns, hz), ms in zip(groups, HORIZONS_MS):
                target = x[validation_origins[:, None]+hz]
                val_scores[str(ms)] = {m:forecast_scores(target, p[:, columns], FS) for m, p in val_pred.items()}
                selected[str(ms)] = choose_method(val_scores[str(ms)])
            test_pred = predictions(test_origins)
            test_rows = np.searchsorted(grid, test_origins)
            for g, ((columns, hz), ms) in enumerate(zip(groups, HORIZONS_MS)):
                target = x[test_origins[:, None]+hz]
                for m, p in test_pred.items():
                    score = forecast_scores(target, p[:, columns], FS)
                    rows.append({'case':name, 'method':m, 'horizon_start_ms':ms,
                                 'selected_on_validation':m == selected[str(ms)],
                                 'validation':val_scores[str(ms)][m], 'test':score,
                                 'gate_enabled_fraction_test':float(np.mean(enabled[test_rows, g])) if m == 'auto_selected_gated' else None,
                                 'numerical_target_met':bool(score['band_prediction_gain_db'] >= 6 and score['nrmse'] <= 1)})
            decisions = forecaster.decisions
            detections[name] = {
                'truth_tones':spec['tones'],
                'auto_selector_test':detection_errors(spec, decisions, VAL_END, SECONDS*FS),
                'auto_selector_after_warmup':detection_errors(spec, decisions, FS, SECONDS*FS),
                'fixed_top3_test':static_detection_errors(spec, fixed, VAL_END, SECONDS*FS, selector.step),
                'fixed_top3_frequencies_hz':fixed,
                'transition_latency_seconds':transition_latency(spec, decisions),
                'final_active_hz':[round(f, 3) for f, _ in active_at(decisions, SECONDS*FS-1)]}
            info[name] = {'normalization':normalization,
                          'selector_update_seconds_mean':float(np.mean(selector.update_seconds_measured)),
                          'selector_update_seconds_max':float(np.max(selector.update_seconds_measured)),
                          'auto_predict_seconds_per_origin':forecaster.predict_seconds_per_origin,
                          'ridge':models['adapted_ridge_ar'].metadata, 'mlp':models['adapted_mlp'].metadata}
        real = [real_reanalysis(Path(p), selector, gate_db, horizons, groups) for p in real_inputs]
    result = {'protocol':protocol, 'frozen_pooled_mlp':frozen_info, 'rows':rows, 'detections':detections,
              'model_info':info, 'real_reanalysis':real, 'runtime_seconds':time.perf_counter()-started,
              'status':'Synthetic reference prediction and detector behavior only; no physical ANC validation.'}
    (output/'selection_study.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    with (output/'metrics.csv').open('w', newline='', encoding='utf-8') as handle:
        columns = ['case', 'method', 'horizon_start_ms', 'selected_on_validation', 'test_band_gain_db', 'test_nrmse', 'validation_band_gain_db']
        writer = csv.DictWriter(handle, fieldnames=columns); writer.writeheader()
        for row in rows:
            writer.writerow({**{k:row[k] for k in columns[:4]}, 'test_band_gain_db':row['test']['band_prediction_gain_db'],
                             'test_nrmse':row['test']['nrmse'], 'validation_band_gain_db':row['validation']['band_prediction_gain_db']})
    from .selection_report import write_selection_report
    write_selection_report(output, result)
    return result


def real_reanalysis(path, selector, gate_db, horizons, groups):
    """Previously analysed recordings: detector timeline and gated test gain.

    The 18-30 s test segment was already seen in earlier reports; settings here
    come from synthetic development only, but this is not independent evidence.
    """
    x, quality = load_reference(path, FS, 30., 12.)
    forecaster = SelectedToneForecaster(FS, selector)
    grid = np.arange(BLOCK*50, len(x)-int(max(horizons)), BLOCK)
    shadow = forecaster.predict(x, grid, horizons)
    enabled = realized_gate(x, grid, shadow, groups, gate_db)
    out = apply_gate(shadow, enabled, groups)
    test = grid >= 18*FS
    scores = {}
    for g, ((columns, hz), ms) in enumerate(zip(groups, HORIZONS_MS)):
        target = x[grid[test][:, None]+hz]
        scores[str(ms)] = {'zero':forecast_scores(target, np.zeros_like(target), FS)['band_prediction_gain_db'],
                           'auto_selected_tracker':forecast_scores(target, shadow[test][:, columns], FS)['band_prediction_gain_db'],
                           'auto_selected_gated':forecast_scores(target, out[test][:, columns], FS)['band_prediction_gain_db'],
                           'gate_enabled_fraction':float(np.mean(enabled[test, g]))}
    counts = [len(a) for _, a in forecaster.decisions]
    freqs = [f for _, a in forecaster.decisions for f, _ in a]
    hist = {}
    for f in freqs:
        key = f'{round(f):d}'
        hist[key] = hist.get(key, 0)+1
    common = sorted(hist.items(), key=lambda kv: -kv[1])[:8]
    return {'file':path.name, 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'note':'Re-analysis of a previously reported recording; not independent evidence.',
            'quality':{k:quality[k] for k in ('sample_rate', 'peak_digital', 'rms_digital')},
            'tone_count_fraction':{str(c):counts.count(c)/len(counts) for c in sorted(set(counts))},
            'most_frequent_active_hz':[{'hz_rounded':int(k), 'fraction_of_updates':v/len(counts)} for k, v in common],
            'test_band_gain_db':scores}
