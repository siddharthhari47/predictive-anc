"""Frequency-blind adaptation versus frozen-ML transfer; synthetic reference only.

Each held-out source is a different frequency group, not a crop of a training
source. Adapted methods may observe/learn the new source's first six seconds.
The frozen pooled MLP never updates its weights on held-out sources.
"""
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import time
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits

from .assessment import choose_method, forecast_scores
from .predictors import DirectPredictor, ToneTracker, estimate_tones, lag_matrix


FS = 2000
BLOCK = 20
HORIZONS_MS = (20., 120.)
DEVELOPMENT = ([47.3, 113.7, 231.2], [68.4, 154.8, 302.6], [90.1, 182.5, 267.9])
HELD_OUT = {'single_tone':[57.6], 'unrelated_tones':[103.2, 187.4, 319.6],
            'harmonic_tones':[79.7, 159.4, 239.1], 'broadband_negative_control':[]}


def synthesize(frequencies, seed, seconds=12):
    rng = np.random.default_rng(seed)
    time_axis = np.arange(seconds*FS)/FS
    if not frequencies:
        return .3*rng.standard_normal(len(time_axis))
    audio = .012*rng.standard_normal(len(time_axis))
    for frequency, amplitude in zip(frequencies, [.45, .25, .13]):
        audio += amplitude*np.sin(2*np.pi*frequency*time_axis+rng.uniform(-np.pi, np.pi))
    return audio


def normalized_prefix(audio, train_end):
    mean = float(np.mean(audio[:train_end]))
    scale = max(float(np.std(audio[:train_end])), 1e-8)
    return (audio-mean)/scale, {'mean':mean, 'scale':scale, 'samples':train_end}


def pooled_training(sources, horizons, lags=128):
    """Build per-source windows so no supervised example crosses a source join."""
    inputs, targets, counts = [], [], []
    for source in sources:
        x, _ = normalized_prefix(source, len(source))
        origins = np.arange(lags-1, len(x)-int(max(horizons)), 5)
        inputs.append(lag_matrix(x, origins, lags))
        targets.append(x[origins[:, None]+horizons])
        counts.append({'examples':len(origins), 'last_target':int(origins[-1]+max(horizons)),
                       'source_samples':len(x)})
    return np.concatenate(inputs), np.concatenate(targets), counts


def run_generalization(output):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Generalization output must be new or empty; earlier results are preserved.')
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    delays = [round(ms*FS/1000) for ms in HORIZONS_MS]
    horizons = np.unique(np.concatenate([d+np.arange(1, BLOCK+1) for d in delays]))
    train_end, val_end, count = 6*FS, 8*FS, 12*FS
    validation_origins = np.arange(train_end, val_end-max(horizons), BLOCK)
    test_origins = np.arange(val_end, count-max(horizons), BLOCK)
    plan = {'kind':'synthetic_reference_frequency_generalization', 'fs':FS, 'block':BLOCK,
            'partition_seconds':[6,2,4], 'horizon_start_ms':list(HORIZONS_MS),
            'development_frequencies_hz':DEVELOPMENT, 'held_out_frequencies_hz':HELD_OUT,
            'development_seeds':[401,402,403], 'held_out_seeds':[701,702,703,704],
            'criterion':'Choose maximum validation 35-350 Hz prediction gain, including zero; require >=6 dB test band gain and full NRMSE <=1.',
            'adaptation':'Automatic tracker detection and ridge/MLP fitting see only each new source training prefix. No ground-truth frequency labels enter predictors.',
            'frozen_transfer':'Pooled MLP weights trained only on three development sources. New-source normalization uses its six-second prefix; this is unsupervised calibration, not an uncalibrated zero-shot claim.',
            'limitations':'Small synthetic diagnostic, one seed per source. No measured acoustic path, playback, or ear residual. No claim of arbitrary-tone universality.',
            'code_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')},
            'created_utc':datetime.now(timezone.utc).isoformat()}
    (output/'protocol.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
    rows, model_info, choices = [], {}, {}
    with threadpool_limits(limits=1):
        # Training is complete before any held-out source is synthesized.
        development = [synthesize(f, 401+i, seconds=6) for i,f in enumerate(DEVELOPMENT)]
        inputs, targets, counts = pooled_training(development, horizons)
        frozen = DirectPredictor('mlp', horizons, seed=7)
        frozen.mean, frozen.scale = 0., 1.
        print('Training frozen pooled MLP on development frequencies only', flush=True)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always', ConvergenceWarning)
            frozen.model.fit(inputs, targets)
        model_info['frozen_pooled_mlp'] = {'source_windows':counts,
                                         'iterations':int(frozen.model.n_iter_),
                                         'warnings':[str(w.message) for w in caught]}
        for index, (case, truth_frequencies) in enumerate(HELD_OUT.items()):
            print(f'Evaluating unseen source: {case}', flush=True)
            x, normalization = normalized_prefix(synthesize(truth_frequencies, 701+index), train_end)
            detected = estimate_tones(x[:train_end], FS)
            models = {'auto_tone_tracker':ToneTracker(FS, detected),
                      'adapted_ridge_ar':DirectPredictor('ridge_ar', horizons, seed=7).fit(x, train_end),
                      'adapted_mlp':DirectPredictor('mlp', horizons, seed=7).fit(x, train_end),
                      'frozen_pooled_mlp':frozen}
            model_info[case] = {'detected_frequencies_hz':detected, 'normalization':normalization,
                                'ridge':models['adapted_ridge_ar'].metadata,
                                'mlp':models['adapted_mlp'].metadata}
            val_predictions = {'zero':np.zeros((len(validation_origins), len(horizons)))}
            val_predictions.update({name:model.predict(x, validation_origins, horizons)
                                    for name, model in models.items()})
            val_scores, selected = {}, {}
            for delay, ms in zip(delays, HORIZONS_MS):
                cols = np.searchsorted(horizons, delay+np.arange(1, BLOCK+1))
                target = x[validation_origins[:, None]+horizons[cols]]
                scores = {name:forecast_scores(target, prediction[:, cols], FS)
                          for name, prediction in val_predictions.items()}
                val_scores[str(ms)] = scores
                selected[str(ms)] = choose_method(scores)
            choices[case] = selected.copy()
            # Choices are frozen before evaluating any held-out test samples.
            test_predictions = {'zero':np.zeros((len(test_origins), len(horizons)))}
            test_predictions.update({name:model.predict(x, test_origins, horizons)
                                     for name, model in models.items()})
            for delay, ms in zip(delays, HORIZONS_MS):
                cols = np.searchsorted(horizons, delay+np.arange(1, BLOCK+1))
                target = x[test_origins[:, None]+horizons[cols]]
                for name, prediction in test_predictions.items():
                    score = forecast_scores(target, prediction[:, cols], FS)
                    rows.append({'case':case, 'method':name, 'horizon_start_ms':ms,
                                 'selected_on_validation':name==selected[str(ms)],
                                 'validation':val_scores[str(ms)][name], 'test':score,
                                 'numerical_target_met':bool(score['band_prediction_gain_db']>=6 and score['nrmse']<=1)})
    result = {'protocol':plan, 'model_info':model_info, 'choices':choices, 'rows':rows,
              'runtime_seconds':time.perf_counter()-started,
              'status':'Synthetic reference prediction only; no physical ANC validation.'}
    (output/'generalization.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    with (output/'metrics.csv').open('w', newline='', encoding='utf-8') as handle:
        columns = ['case','method','horizon_start_ms','selected_on_validation','test_band_gain_db','test_nrmse','validation_band_gain_db']
        writer = csv.DictWriter(handle, fieldnames=columns); writer.writeheader()
        for row in rows:
            writer.writerow({**{k:row[k] for k in columns[:4]},
                             'test_band_gain_db':row['test']['band_prediction_gain_db'],
                             'test_nrmse':row['test']['nrmse'],
                             'validation_band_gain_db':row['validation']['band_prediction_gain_db']})
    write_report(output, result)
    return result


def write_report(output, result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    output = Path(output)
    names = ['auto_tone_tracker','adapted_ridge_ar','adapted_mlp','frozen_pooled_mlp']
    labels = ['Automatic tone tracker','AR adapted to new source','MLP adapted to new source','Frozen pooled MLP']
    colors = ['#087f8c','#6567a5','#e3a126','#b34c66']
    cases = list(HELD_OUT)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
    for axis, ms in zip(axes, HORIZONS_MS):
        for j, (method, label, color) in enumerate(zip(names, labels, colors)):
            values = [next(r['test']['band_prediction_gain_db'] for r in result['rows']
                           if r['case']==case and r['method']==method and r['horizon_start_ms']==ms)
                      for case in cases]
            axis.bar(np.arange(len(cases))+(j-1.5)*.19, values, width=.19, label=label, color=color)
        axis.axhline(0, color='#666', linewidth=.7)
        axis.axhline(6, color='#999', linestyle='--', linewidth=1)
        axis.set_xticks(range(len(cases)), ['New single\ntone','New unrelated\ntones','New harmonic\ntones','Broadband\ncontrol'], fontsize=8)
        axis.set_title(f'{ms:g} ms forecast start'); axis.grid(axis='y', alpha=.2)
        axis.set_ylabel('Test prediction gain in 35–350 Hz (dB)')
    fig.legend(*axes[0].get_legend_handles_labels(), loc='lower center', ncol=2, frameon=False, fontsize=9)
    fig.suptitle('New frequencies: automatic adaptation versus frozen ML transfer', fontsize=13)
    fig.tight_layout(rect=(0,.13,1,.96)); fig.savefig(output/'generalization.png', dpi=150); plt.close(fig)
    lines = ['# Automatic adaptation is different from frozen-ML transfer','',
             'This small synthetic diagnostic tests new frequencies without giving their labels to the predictors. It does not establish real-world ANC or arbitrary-tone performance.','',
             '![Prediction comparison](generalization.png)','',
             '| Source | Horizon | Validation-selected method | Test band prediction gain | Full-reference NRMSE |',
             '|---|---:|---|---:|---:|']
    for row in result['rows']:
        if row['selected_on_validation']:
            lines.append(f"| {row['case']} | {row['horizon_start_ms']:g} ms | {row['method']} | {row['test']['band_prediction_gain_db']:.2f} dB | {row['test']['nrmse']:.4f} |")
    lines += ['', 'The automatic tracker detects up to three peaks from the new source prefix. Adapted AR and MLP models train on that prefix. The frozen pooled MLP has weights trained on three other source groups; only input scaling uses the new prefix. These are different adaptation budgets and are reported separately.', '',
              'Training / validation / test are chronological 6 / 2 / 4 seconds. The two forecasts cover the next 10 ms starting just after 20 or 120 ms. Validation selection includes zero. Training targets are embargoed from validation and test; pooled windows never cross source boundaries. Settings and frequency groups were saved before training/evaluation.', '',
              'The MLP is a first 64-unit comparator, not a claim about the limits of ML. Review convergence warnings in generalization.json. There is one seed per source case and no frequency-drift, microphone processing, acoustic path or playback jitter in this diagnostic; the original simulator separately covers assumed delay, jitter and path errors.', '',
              'A broadly trained model must later be assessed on whole withheld recordings, devices and environments. The same source may not be split into near-duplicate train/test recordings to claim transfer.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
