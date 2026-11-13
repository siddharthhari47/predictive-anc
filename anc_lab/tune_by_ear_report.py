"""Plain-language report for the simulated tune-by-ear study."""
from pathlib import Path

import numpy as np

from .real_hum_report import short

LABELS = {'untuned_room_phase_ignored':'Untuned (room phase ignored)', 'path_oracle':'Path oracle (ear-mic measurement)',
          'tuned_sigma_0.5':'Tuned by ear, careful listener', 'tuned_sigma_1':'Tuned by ear, typical listener',
          'tuned_sigma_2':'Tuned by ear, unreliable listener'}
COLORS = {'untuned_room_phase_ignored':'#b34c66', 'path_oracle':'#222222', 'tuned_sigma_0.5':'#0b5d4b',
          'tuned_sigma_1':'#2f8f6f', 'tuned_sigma_2':'#8cc9b3'}
MAIN = 'tuned_sigma_1'


def _stats(values):
    v = np.array([x for x in values if x is not None], float)
    if not len(v):
        return '–'
    q1, q2, q3 = np.percentile(v, [25, 50, 75])
    return f'{q2:.1f} [{q1:.1f}, {q3:.1f}]'


def _f(value, digits=1):
    return '–' if value is None or not np.isfinite(value) else f'{value:.{digits}f}'


def _median(values):
    v = [x for x in values if x is not None]
    return float(np.median(v)) if v else float('nan')


def write_tune_by_ear_report(output, result, protocol):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    output = Path(output)
    cases = result['cases']
    rows = [r for c in cases for r in c['rows']]
    tuning = [r for c in cases for r in c['tuning'] if 'skipped' not in r]
    skipped = [(c['file'], c['room_index']) for c in cases if any('skipped' in r for r in c['tuning'])]
    leads, arms = protocol['leads_ms'], protocol['arms']
    moves, drifts = protocol['robustness']['head_moves_cm'], protocol['robustness']['latency_drift_ms']
    sigmas = protocol['tuning']['listener_sigma_db']
    with_tones = {(c['file'], c['room_index']) for c in cases if c['tones']}
    pick = lambda arm, lead, move=0., drift=0., scenes=None: [
        r for r in rows if r['arm'] == arm and r['lead_ms'] == lead and r['move_cm'] == move and r['drift_ms'] == drift
        and (scenes is None or (r['file'], r['room']) in scenes)]
    boosted = lambda rs: float(np.mean([r['max_third_octave_amplification_db'] > 1. for r in rs])) if rs else float('nan')
    louder = lambda rs: float(np.mean([r['band_db'] < -.5 for r in rs])) if rs else float('nan')
    tone = lambda rs: [r['tone_db'] for r in rs]
    band = lambda rs: [r['band_db'] for r in rs]
    lead0 = leads[0]

    # ---- figure ----
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2), gridspec_kw={'width_ratios':[2.2, 1, 1]})
    axis = axes[0]
    for j, lead in enumerate(leads):
        for k, arm in enumerate(arms):
            values = [v for v in tone(pick(arm, lead, scenes=with_tones)) if v is not None]
            if not values:
                continue
            position = j*(len(arms)+1)+k
            parts = axis.boxplot([np.clip(values, -15, 45)], positions=[position], widths=.7, patch_artist=True,
                                 medianprops={'color':'white' if arm == 'path_oracle' else '#111'})
            parts['boxes'][0].set_facecolor(COLORS[arm])
    axis.set_xticks([j*(len(arms)+1)+(len(arms)-1)/2 for j in range(len(leads))],
                    [f'{lead:g} ms playback lead' for lead in leads])
    axis.axhline(0, color='#555', linewidth=.7)
    axis.set_ylabel('Tone-bin quieting at the simulated ear (dB)')
    axis.set_title('Held-out 60% of each recording, head and timing unchanged')
    axis.legend([plt.Rectangle((0, 0), 1, 1, color=COLORS[a]) for a in arms], [LABELS[a] for a in arms],
                fontsize=8, loc='lower left', frameon=False)
    axis.grid(axis='y', alpha=.2)
    for axis, key, values, xlabel in ((axes[1], 'move_cm', moves, 'Head moved after tuning (cm)'),
                                      (axes[2], 'drift_ms', drifts, 'Extra playback delay after tuning (ms)')):
        for arm in ('path_oracle', MAIN):
            for lead, style in zip(leads, ('-', '--')):
                med = [_median(tone(pick(arm, lead, *((v, 0.) if key == 'move_cm' else (0., v)), scenes=with_tones))) for v in values]
                axis.plot(values, med, style, marker='o', color=COLORS[arm], label=f'{LABELS[arm]}, {lead:g} ms')
        axis.axhline(0, color='#555', linewidth=.7)
        axis.set_xlabel(xlabel); axis.set_ylabel('Median tone-bin quieting (dB)'); axis.grid(alpha=.2)
    axes[1].legend(fontsize=7, frameon=False)
    fig.suptitle('SIMULATED EAR ATTENUATION: modal rooms, real recorded hums as sources. Nothing was played or measured.', y=.995)
    fig.tight_layout(rect=(0, 0, 1, .95)); fig.savefig(output/'tune_by_ear.png', dpi=140); plt.close(fig)

    # ---- numbers for the summary ----
    n_scenes = len(cases)
    main = pick(MAIN, lead0, scenes=with_tones)
    oracle = pick('path_oracle', lead0, scenes=with_tones)
    untuned = pick('untuned_room_phase_ignored', lead0, scenes=with_tones)
    main_tuning = [r for r in tuning if r['sigma_db'] == 1. and r['lead_ms'] == lead0]
    kept = float(np.mean([r['kept'] for r in main_tuning])) if main_tuning else float('nan')
    all_main = [r for r in rows if r['arm'].startswith('tuned_') and r['move_cm'] == 0 and r['drift_ms'] == 0]
    tone_counts = [len(c['tones']) for c in cases]
    gate_open = [c['scene']['test_fraction_gate_open_with_tones'] for c in cases if c['scene']['test_fraction_gate_open_with_tones'] is not None]

    lines = ['# Tune-by-ear in simulated rooms with real recorded hums', '',
             '**Simulated ear attenuation.** Every number below is computed sound at a simulated ear in a simulated room. '
             'Nothing was played through earphones and nothing was measured. This is not evidence of real-world noise cancellation; '
             'it checks whether the procedure can find the right setting when the room, the earphones and the listener behave as modelled.', '',
             f"Protocol frozen before the run in `protocol.json` (seed {protocol['seed']}). Recordings: {len(protocol['recordings'])} acoustic files "
             f"from Wikimedia Commons (the two electrical mains-hum clips are excluded), {protocol['rooms_per_recording']} random rooms each. "
             'Tones were chosen and tuned on the first 40% of each recording only; the remaining 60% was evaluated with every setting frozen. '
             'No setting of the engine, the tuning procedure or the simulation was changed after seeing these results.', '',
             '![Tune-by-ear simulation](tune_by_ear.png)', '',
             '## Summary (computed from the tables below)', '',
             f"- Scenes: {n_scenes} (recording × room). In {len(with_tones)} the engine held at least one steady tone for most of the tuning part "
             f"(tones per scene: median {np.median(tone_counts):.0f}, max {max(tone_counts)}); the other {n_scenes-len(with_tones)} had nothing to tune, "
             'so every arm stays silent there and scores 0 dB.'
             + (f" {len(skipped)} scene(s) had a tuning part shorter than one phase sweep and were not tuned." if skipped else ''),
             f"- At the tones, {lead0:g} ms lead, head still: tuned by a typical simulated listener {_median(tone(main)):.1f} dB median quieting; "
             f"path oracle {_median(tone(oracle)):.1f} dB; untuned {_median(tone(untuned)):.1f} dB. No anti-hum is 0 dB by definition.",
             f"- Whole 35–350 Hz band (what is actually heard, including the broadband part nobody can predict): tuned {_median(band(main)):.1f} dB, "
             f"oracle {_median(band(oracle)):.1f} dB. This is limited by how much of each hum is steady tone (see the per-recording table).",
             f"- Making things worse: any one-third-octave band louder by more than 1 dB in {100*boosted(main):.0f}% of tuned scenes "
             f"({100*boosted(untuned):.0f}% untuned, {100*boosted(oracle):.0f}% oracle); whole band louder by more than 0.5 dB in {100*louder(main):.0f}% "
             f"(untuned {100*louder(untuned):.0f}%). Across all listeners and both leads: {100*boosted(all_main):.0f}% and {100*louder(all_main):.0f}%.",
             f"- Tuning cost per tone (typical listener): median {_median([r['listening_seconds'] for r in main_tuning]):.0f} s of listening "
             f"and {_median([r['questions'] for r in main_tuning]):.0f} answers; {100*kept:.0f}% of tuned tones passed the final on/off check.",
             f"- Moving the head after tuning (typical listener, {lead0:g} ms): "
             + ', '.join(f"{m:g} cm {_median(tone(pick(MAIN, lead0, m, scenes=with_tones))):.1f} dB" for m in moves[1:]) + '.',
             f"- Playback delay changing after tuning: "
             + ', '.join(f"+{d:g} ms {_median(tone(pick(MAIN, lead0, 0., d, scenes=with_tones))):.1f} dB" for d in drifts[1:])
             + '. A delay change must trigger a retune (or be measured); it cannot be tolerated silently.',
             f"- Bluetooth-like {leads[-1]:g} ms lead: tuned {_median(tone(pick(MAIN, leads[-1], scenes=with_tones))):.1f} dB at the tones, "
             f"oracle {_median(tone(pick('path_oracle', leads[-1], scenes=with_tones))):.1f} dB (forecasting further ahead costs accuracy when tones wander).",
             f"- Engine gate open for {100*_median(gate_open):.0f}% (median) of held-out blocks that had tones.", '']

    lines += ['## Every arm, head still, timing unchanged', '',
              'Median [quartiles] over scenes with at least one tuned tone. Tone bins: ±1.5 Hz around the reference tones '
              'found non-causally in the earlier real-hum study (an independent yardstick, not the tuned frequencies).', '',
              '| Arm | Lead (ms) | Tone bins (dB) | 35–350 Hz (dB) | Broadband (dB) | Worst 1 s window (dB) | Any 1/3-oct boost > 1 dB | Band louder > 0.5 dB | Peak drive |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for lead in leads:
        for arm in arms:
            rs = pick(arm, lead, scenes=with_tones)
            lines.append(f"| {LABELS[arm]} | {lead:g} | {_stats(tone(rs))} | {_stats(band(rs))} | {_stats([r['broadband_db'] for r in rs])} | "
                         f"{_stats([r['worst_1s_band_db'] for r in rs])} | {100*boosted(rs):.0f}% | {100*louder(rs):.0f}% | "
                         f"{max([r['drive_peak'] for r in rs], default=0):.3f} |")
    lines += ['', '## After tuning: head moves and delay changes (nothing retuned)', '',
              '| Arm | Lead (ms) | Change | Tone bins (dB) | 35–350 Hz (dB) | Any 1/3-oct boost > 1 dB | Band louder > 0.5 dB |',
              '|---|---:|---|---:|---:|---:|---:|']
    for arm in ('path_oracle', MAIN):
        for lead in leads:
            for move, drift in [(m, 0.) for m in moves]+[(0., d) for d in drifts[1:]]:
                rs = pick(arm, lead, move, drift, scenes=with_tones)
                change = 'none' if move == drift == 0 else (f'head {move:g} cm' if move else f'delay +{drift:g} ms')
                lines.append(f"| {LABELS[arm]} | {lead:g} | {change} | {_stats(tone(rs))} | {_stats(band(rs))} | {100*boosted(rs):.0f}% | {100*louder(rs):.0f}% |")
    lines += ['', 'The 20 ms delay row can look better than 5 ms: a delay that is close to a whole number of cycles of a tone '
              'happens to keep its phase. That is a coincidence of the tone frequencies, not tolerance.', '']

    lines += ['## How accurately the listener found the setting', '',
              'Error against the exact path ratio at each tuned frequency (gain before the final on/off check). '
              '"Predicted" is the quieting that setting would give a perfectly steady tone.', '',
              '| Listener | Lead (ms) | Tones | Gain error, median abs (dB) | Phase error, median abs (deg) | Predicted quieting (dB) | Kept after check | Listening (s) | Answers | Flags raised |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for sigma in sigmas:
        for lead in leads:
            ts = [r for r in tuning if r['sigma_db'] == sigma and r['lead_ms'] == lead]
            if not ts:
                continue
            lines.append(f"| ±{sigma:g} dB judgement noise | {lead:g} | {len(ts)} | {_median([abs(r['gain_error_db']) for r in ts if r['gain_error_db'] is not None]):.2f} | "
                         f"{_median([abs(r['phase_error_deg']) for r in ts]):.1f} | {_stats([r['predicted_tone_attenuation_db'] for r in ts])} | "
                         f"{100*np.mean([r['kept'] for r in ts]):.0f}% | {_median([r['listening_seconds'] for r in ts]):.0f} | "
                         f"{_median([r['questions'] for r in ts]):.0f} | {sum(bool(r['flags']) for r in ts)} |")
    flags = {}
    for r in tuning:
        for f in r['flags']:
            flags[f] = flags.get(f, 0)+1
    if flags:
        lines += ['', 'Flags: '+'; '.join(f'"{k}" ×{v}' for k, v in sorted(flags.items(), key=lambda kv: -kv[1]))+'.']

    lines += ['', f'## Per recording (typical listener, {lead0:g} ms lead, head still)', '',
              'Median over the three rooms. "Tone ceiling" is from the earlier real-hum study: the whole-band quieting if every steady tone '
              'were removed perfectly at the microphone; no method can beat it in the 35–350 Hz band.', '',
              '| Recording | Tones tuned (per room) | Tuned: tone bins (dB) | Oracle: tone bins (dB) | Tuned: 35–350 Hz (dB) | Tone ceiling (dB) | Any boost > 1 dB |',
              '|---|---|---:|---:|---:|---:|---:|']
    for name in protocol['recordings']:
        here = [c for c in cases if c['file'] == name]
        tuned_rows = [r for r in pick(MAIN, lead0) if r['file'] == name]
        oracle_rows = [r for r in pick('path_oracle', lead0) if r['file'] == name]
        ceiling = result['recordings'][name]['tone_only_ceiling_db']
        lines.append(f"| {short(name)} | {', '.join(str(len(c['tones'])) for c in sorted(here, key=lambda c: c['room_index']))} | "
                     f"{_f(_median(tone(tuned_rows)))} | {_f(_median(tone(oracle_rows)))} | {_f(_median(band(tuned_rows)))} | "
                     f"{_f(ceiling)} | {_f(100*boosted(tuned_rows), 0)}% |")

    lines += ['', '## What this simulation does and does not show', '',
              '- Rooms are rigid rectangular boxes described by their acoustic modes below 1.1 kHz, with uniform damping. Real rooms have '
              'furniture, openings and uneven absorption. Each recording is treated as a point source, although real fans and compressors are not.',
              '- One ear (left) only, one fixed earphone fit. Real fit changes with every insertion; the earphone model is a simple bass roll-off plus delay.',
              '- The earphone sound never reaches the microphone here. A real laptop microphone hears some leakage from the earphones, '
              'which the engine would then try to predict too.',
              '- The simulated listener judges loudness inside one narrow band around the tone being tuned, with random judgement noise, '
              'and has no hearing threshold. Real listeners hear everything at once, get tired, and may not hear 40 Hz at all at low levels.',
              '- When the tuning part is short, presentations loop over it, so the listener hears the same audio more than once.',
              '- No sound-pressure calibration: the output cap is a digital bound only. The first physical step remains a low-output '
              'calibrated fixture with a near-ear measurement microphone.', '',
              f"Runtime {result['runtime_seconds']/60:.1f} min on {result['workers']} worker processes. "
              'Files: `protocol.json` (frozen settings), `tune_by_ear.json` (everything), `metrics.csv`, `tuning.csv`.']
    if skipped:
        lines += ['', 'Not tuned (tuning part shorter than one sweep): '+', '.join(f'{short(f)} room {k}' for f, k in skipped)+'.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
