"""Plain-language report for the tone-release study (multi-seed)."""
from pathlib import Path

import numpy as np

METHODS = ['zero', 'fixed_top3_tracker', 'auto_v1_gated', 'auto_v2_ungated', 'auto_v2_gated',
           'adapted_ridge_ar', 'adapted_mlp', 'frozen_pooled_mlp']
LABELS = ['Predict nothing', 'Old: fixed top-3', 'Study-01 settings (v1, gated)', 'Tuned v2, no gate',
          'Tuned v2 + gate', 'AR adapted on prefix', 'MLP adapted on prefix', 'Frozen pooled MLP']
COLORS = ['#9a9a9a', '#b34c66', '#6aa6b0', '#2f8f6f', '#0b5d4b', '#6567a5', '#e3a126', '#7a3b8f']


def fmt(v, digits=1):
    return '—' if v is None else f'{v:.{digits}f}'


def write_release_report(output, result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    output = Path(output)
    summary = {(r['case'], r['method'], r['horizon_start_ms']):r for r in result['summary']}
    cases = list(dict.fromkeys(r['case'] for r in result['summary']))
    fig, axes = plt.subplots(2, 1, figsize=(15, 8.5), sharex=True)
    for axis, ms in zip(axes, (20., 120.)):
        for j, (m, label, color) in enumerate(zip(METHODS, LABELS, COLORS)):
            rows = [summary[(c, m, ms)] for c in cases]
            mean = np.array([r['test_mean_db'] for r in rows])
            lo, hi = np.array([r['test_min_db'] for r in rows]), np.array([r['test_max_db'] for r in rows])
            pos = np.arange(len(cases))+(j-3.5)*.1
            clipped = np.clip(mean, -15, 40)
            axis.bar(pos, clipped, width=.1, color=color, label=label)
            axis.vlines(pos, np.clip(lo, -15, 40), np.clip(hi, -15, 40), color='#333', linewidth=.6)
        axis.axhline(0, color='#555', linewidth=.7)
        axis.set_ylabel('Test gain (dB), mean and\nmin–max over repeats'); axis.set_title(f'Forecast starting {ms:g} ms ahead')
        axis.grid(axis='y', alpha=.2)
    axes[-1].set_xticks(range(len(cases)), [c.replace('_', '\n') for c in cases], fontsize=8)
    fig.legend(*axes[0].get_legend_handles_labels(), loc='lower center', ncol=4, frameon=False, fontsize=9)
    fig.suptitle('Fresh random frequency draws: tone release study (reference prediction only, clipped to [-15, 40] dB)')
    fig.tight_layout(rect=(0, .08, 1, .97)); fig.savefig(output/'release.png', dpi=140); plt.close(fig)

    p = result['protocol']
    v1, v2 = p['v1'], p['v2']
    reps = max(r['repeats'] for r in result['summary'])
    gate2 = v2['gate']
    gate_text = 'no gate' if gate2['min_gain_db'] is None else (
        f"mute unless the last {gate2['lookback']} matured blocks beat zero by {gate2['min_gain_db']:g} dB"
        + (' (shared, driven by the 20 ms horizon)' if gate2['shared_group'] == 0 else ''))
    fast = 'off' if v2['forecaster']['release_ratio'] is None else (
        f"drop a tone when its last {v2['forecaster']['release_window_seconds']:g} s amplitude falls below "
        f"{v2['forecaster']['release_ratio']:g}× its {v2['forecaster']['window_seconds']:g} s amplitude")
    lines = ['# Faster tone release, tuned on development only, with repeats', '',
             'Synthetic **reference-signal prediction** only. No acoustic path, playback or ear measurement. Not evidence of real-world noise cancellation.', '',
             f"Every test number is over {reps} independent random frequency draws (each a full set of 12 scenes, new seeds). Bars are the mean; whiskers are the lowest and highest repeat.", '',
             '![Release comparison](release.png)', '',
             '## What was tuned, and on what', '',
             f"- Development only: {len(p['development_draws'])} frequency draws × 12 scenes. Test draws were generated after the settings below were written to `release_protocol.json`.",
             f"- Objective: {p['objective']}",
             f"- v1 (study-01 settings, unchanged): release after {v1['selector']['release']} misses, tracker window {v1['forecaster']['window_seconds']:g} s, no fast release, gate −1 dB over 25 blocks. Development objective {p['v1_dev_objective']:.2f}.",
             f"- **v2 (tuned):** release after {v2['selector']['release']} misses, tracker window {v2['forecaster']['window_seconds']:g} s, fast release {fast}; gate: {gate_text}. "
             f"Development objective {max(r['dev_objective'] for r in p['stage_b']):.2f}.",
             '', '### Stage A on development (no gate), best 8', '',
             '| Release misses | Fast-release ratio | Short window (s) | Tracker window (s) | Dev objective | Worst dev scene |', '|---:|---:|---:|---:|---:|---:|']
    for r in sorted(p['stage_a'], key=lambda r: -r['dev_objective'])[:8]:
        f = r['forecaster']
        lines.append(f"| {r['selector']['release']} | {fmt(f['release_ratio'])} | {f['release_window_seconds'] if f['release_ratio'] is not None else '—'} | "
                     f"{f['window_seconds']:g} | {r['dev_objective']:.2f} | {r['dev_worst_scene_objective']:.2f} |")
    lines += ['', '### Stage B on development (gate on the stage-A winner)', '',
              '| Gate threshold (dB) | Lookback blocks | Shared | Dev objective | Worst dev scene |', '|---:|---:|---|---:|---:|']
    for r in sorted(p['stage_b'], key=lambda r: -r['dev_objective']):
        threshold = 'none' if r['min_gain_db'] is None else format(r['min_gain_db'], 'g')
        lines.append(f"| {threshold} | {r['lookback'] if r['min_gain_db'] is not None else '—'} | "
                     f"{'yes' if r['shared_group'] == 0 else 'no'} | {r['dev_objective']:.2f} | {r['dev_worst_scene_objective']:.2f} |")
    lines += ['', '## Test prediction gain over repeats, 35–350 Hz (dB; mean [min, max])', '',
              '| Scene | Horizon | ' + ' | '.join(LABELS[1:]) + ' |', '|---|---:|' + '---:|'*7]
    for c in cases:
        for ms in (20., 120.):
            cells = [f"{summary[(c, m, ms)]['test_mean_db']:.1f} [{summary[(c, m, ms)]['test_min_db']:.1f}, {summary[(c, m, ms)]['test_max_db']:.1f}]"
                     for m in METHODS[1:]]
            lines.append(f'| {c} | {ms:g} ms | ' + ' | '.join(cells) + ' |')
    event_cases = [c for c in cases if summary[(c, 'zero', 20.)]['post_event_mean_db'] is not None]
    lines += ['', '## Right after a tone starts or stops (forecasts issued in the 1.5 s after each event; mean / worst over repeats and events)', '',
              '| Scene | Horizon | ' + ' | '.join(LABELS[1:]) + ' |', '|---|---:|' + '---:|'*7]
    for c in event_cases:
        for ms in (20., 120.):
            cells = [f"{fmt(summary[(c, m, ms)]['post_event_mean_db'])} / {fmt(summary[(c, m, ms)]['post_event_min_db'])}" for m in METHODS[1:]]
            lines.append(f'| {c} | {ms:g} ms | ' + ' | '.join(cells) + ' |')
    lines += ['', '## Detection and release timing (test window 8–12 s, summed over repeats)', '',
              '| Scene | v1 false / missed | v2 false / missed | Old top-3 false / missed | v1 output quiet after stop (s) | v2 output quiet after stop (s) |',
              '|---|---:|---:|---:|---:|---:|']
    for c in cases:
        scenes = [s for s in result['scenes'] if s['case'] == c]
        def tot(label, key):
            return sum(s['detection'][label]['test'][key] for s in scenes)
        def quiet(label):
            vals = [v for s in scenes for v in s['detection'][label]['output_release_latency_s'].values()]
            if not vals:
                return '—'
            known = [v for v in vals if v is not None]
            text = f"{np.mean(known):.2f} (max {max(known):.2f})" if known else 'never'
            return text + (f", {len(vals)-len(known)} never" if known and len(known) < len(vals) else '')
        has_stop = c == 'tones_stop_9s'
        lines.append(f"| {c} | {tot('v1', 'false_activations')} / {tot('v1', 'missed_tones')} | {tot('v2', 'false_activations')} / {tot('v2', 'missed_tones')} | "
                     f"{tot('fixed_top3', 'false_activations')} / {tot('fixed_top3', 'missed_tones')} | {quiet('v1') if has_stop else '—'} | {quiet('v2') if has_stop else '—'} |")
    t = [s['timing']['v2'] for s in result['scenes']]
    lines += ['', '"Output quiet" = seconds after every tone stops until the (gated) forecast RMS stays under 10% of its level in the second before. Only defined for the tones-stop scene.', '',
              '## Compute (offline Python, one thread per process; not a real-time callback measurement)', '',
              f"- v2 selector update: mean {np.mean([x['selector_update_ms_mean'] for x in t]):.1f} ms, max {max(x['selector_update_ms_max'] for x in t):.1f} ms.",
              f"- v2 forecast: mean {np.mean([x['forecast_ms_per_origin'] for x in t]):.2f} ms per 10 ms block (includes the fast-release amplitude checks).",
              f"- Whole study: {result['runtime_seconds']/60:.1f} minutes.",
              '', '## Honest limits', '',
              f"- {p['why_new_test_scenes']} This study's test draws are new, but the *idea* of improving release came from looking at study-01 test results.",
              '- Scene types are the same twelve as in study 01; only frequencies and noise seeds vary. Repeats measure seed/frequency spread, not coverage of real-world sources.',
              f"- {p['limitations']}",
              f"- Frozen pooled MLP: {result['frozen_pooled_mlp']['iterations']} iterations; it is a frozen-weight transfer result, reported separately from per-source adaptation."]
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
