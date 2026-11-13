"""Plain-language report for the tone-selection study."""
from pathlib import Path

import numpy as np

METHODS = ['zero', 'fixed_top3_tracker', 'auto_selected_tracker', 'auto_selected_gated',
           'adapted_ridge_ar', 'adapted_mlp', 'frozen_pooled_mlp']
LABELS = ['Predict nothing', 'Old: fixed top-3 tracker', 'New: auto-count tracker', 'New: auto-count + mute gate',
          'AR adapted on prefix', 'MLP adapted on prefix', 'Frozen pooled MLP']
COLORS = ['#9a9a9a', '#b34c66', '#087f8c', '#0b5d4b', '#6567a5', '#e3a126', '#7a3b8f']


def gain(result, case, method, ms):
    return next(r['test']['band_prediction_gain_db'] for r in result['rows']
                if r['case'] == case and r['method'] == method and r['horizon_start_ms'] == ms)


def write_selection_report(output, result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    output = Path(output)
    cases = list(result['detections'])
    fig, axes = plt.subplots(2, 1, figsize=(14, 8.5), sharex=True)
    for axis, ms in zip(axes, (20., 120.)):
        for j, (m, label, color) in enumerate(zip(METHODS, LABELS, COLORS)):
            values = np.clip([gain(result, c, m, ms) for c in cases], -15, 40)
            axis.bar(np.arange(len(cases))+(j-3)*.12, values, width=.12, label=label, color=color)
        axis.axhline(0, color='#555', linewidth=.7); axis.axhline(6, color='#999', linestyle='--', linewidth=1)
        axis.set_ylabel('Test prediction gain (dB)\nclipped to [-15, 40]'); axis.set_title(f'Forecast starting {ms:g} ms ahead')
        axis.grid(axis='y', alpha=.2)
    axes[-1].set_xticks(range(len(cases)), [c.replace('_', '\n') for c in cases], fontsize=8)
    fig.legend(*axes[0].get_legend_handles_labels(), loc='lower center', ncol=4, frameon=False, fontsize=9)
    fig.suptitle('Fresh synthetic sources: automatic tone count versus fixed top-3 (reference prediction only)')
    fig.tight_layout(rect=(0, .08, 1, .97)); fig.savefig(output/'selection.png', dpi=140); plt.close(fig)

    p = result['protocol']
    s = p['selector_settings']
    lines = ['# Automatic tone count and confidence: first study', '',
             'Synthetic **reference-signal prediction** only. No acoustic path, playback or ear measurement. Not evidence of real-world noise cancellation.', '',
             '![Prediction comparison](selection.png)', '',
             '## Settings frozen on development scenes before any test scene was made', '',
             f"- Detector: multitaper line test, {s['window_seconds']:g} s window, NW={s['nw']:g}, family false-alarm level {s['alpha_family']:g} per window, "
             f"active after {s['acquire']} of {s['history']} passing updates, released after {s['release']} missed updates, update every {s['update_seconds']:g} s.",
             f"- Warm-up before the first possible detection: {s['warm_up_seconds']:g} s. No prefix fit and no frequency labels.",
             f"- Mute gate: output enabled only when recent fully-matured forecasts beat zero by at least {p['gate']['min_realized_gain_db']:g} dB.",
             '', '## Detection on fresh test scenes (test window 8–12 s, 17 updates)', '',
             '| Scene | True tones (test) | New: false / missed | New: freq error | Old top-3: false / missed | Transition latency | Final active (Hz) |',
             '|---|---|---:|---:|---:|---|---|']
    for case, d in result['detections'].items():
        a, o = d['auto_selector_test'], d['fixed_top3_test']
        err = '—' if a['mean_abs_frequency_error_hz'] is None else f"{a['mean_abs_frequency_error_hz']:.2f} Hz"
        lat = ', '.join(f"{k}: {'never' if v is None else f'{v:.2f} s'}" for k, v in d['transition_latency_seconds'].items()) or '—'
        truth = ', '.join(f"{t['freq']:g}" for t in d['truth_tones']) or 'none'
        lines.append(f"| {case} | {truth} | {a['false_activations']} / {a['missed_tones']} | {err} | "
                     f"{o['false_activations']} / {o['missed_tones']} | {lat} | {', '.join(map(str, d['final_active_hz'])) or 'none'} |")
    lines += ['', 'False and missed counts are summed over updates (a tone missed for 4 updates counts 4).', '',
              '## Test prediction gain, 35–350 Hz band (dB; negative = worse than predicting nothing)', '',
              '| Scene | Horizon | ' + ' | '.join(LABELS[1:]) + ' | Validation pick |', '|---|---:|' + '---:|'*6 + '---|']
    for case in result['detections']:
        for ms in (20., 120.):
            pick = next(r['method'] for r in result['rows'] if r['case'] == case and r['horizon_start_ms'] == ms and r['selected_on_validation'])
            lines.append(f"| {case} | {ms:g} ms | " + ' | '.join(f"{gain(result, case, m, ms):.2f}" for m in METHODS[1:]) + f" | {pick} |")
    if result['real_reanalysis']:
        lines += ['', '## Re-analysis of earlier real recordings (not independent evidence)', '',
                  'These recordings and their 18–30 s test segments were already reported. Settings come from synthetic development scenes only.', '',
                  '| File | Tone-count share of updates | Most frequent active lines | 20 ms: ungated / gated / gate on | 120 ms: ungated / gated / gate on |',
                  '|---|---|---|---|---|']
        for r in result['real_reanalysis']:
            counts = ', '.join(f"{k}: {v:.0%}" for k, v in r['tone_count_fraction'].items())
            common = ', '.join(f"{c['hz_rounded']} Hz ({c['fraction_of_updates']:.0%})" for c in r['most_frequent_active_hz'][:5]) or 'none'
            cells = [f"{g['auto_selected_tracker']:.2f} / {g['auto_selected_gated']:.2f} dB / {g['gate_enabled_fraction']:.0%}"
                     for g in r['test_band_gain_db'].values()]
            lines.append(f"| {r['file']} | {counts} | {common} | {cells[0]} | {cells[1]} |")
    lines += ['', '## Limits', '',
              '- One seed per scene and twelve scene types; development and test share scene *types* but not frequencies or seeds.',
              '- The mute gate needs a matured forecast history; it reacts to a change only after the forecast horizon plus the lookback.',
              '- Tones closer than the taper half-bandwidth are reported as one line.',
              '- Synthetic white/brown noise is not a microphone with unknown processing. A fresh real recording with user readiness is the next real-data test.',
              f"- Frozen pooled MLP fit: {result['frozen_pooled_mlp']['iterations']} iterations; warnings in selection_study.json.",
              f"- Runtime {result['runtime_seconds']:.1f} s."]
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
