"""Plain-language Markdown summary for tone-forecaster study 03 (a ceiling on the joint check's tie fallback)."""
from pathlib import Path

from .forecaster_report import fmt, label
from .forecaster_report_02 import NOTE, boost_lines, method_table, per_file_table, timing_rows


def late_boosts_by_scene(scenes, methods, threshold=1.):
    """Per method: {scene name without its draw tag: count of late windows with a band `threshold` dB or more louder}."""
    out = {}
    for m in methods:
        late = {}
        for sc in scenes:
            for s in sc['late_window_scores']:
                if s['method'] == m and s['max_third_octave_change_db'] >= threshold:
                    k = sc['scene'].split('#')[0]
                    late[k] = late.get(k, 0)+1
        out[m] = dict(sorted(late.items()))
    return out


def write_development_summary(output, result):
    rec, syn = result['summary']['recordings'], result['summary']['synthetic']
    methods = list(rec)
    lines = ['# Tone forecaster study 03: development run', '',
             '**Development material only.** No study-01 test recording, study-02 fresh recording, synthetic test scene or '
             'new fresh recording was read. '+NOTE, '',
             f"Development recordings: {', '.join(result['development_files'])}. Synthetic: the 44 development scenes of "
             f"studies 01 and 02 plus 8 new buzz scenes (seed {result['buzz_development']['seed']}; draws "
             f"{result['buzz_development_draws']}).", '']
    if result.get('note'):
        lines += [f"**Note:** {result['note']}", '']
    lines += ['## Rule', '', result['rule'], '',
              '| Candidate | Boosts (rec + syn late) | Near-boosts | Whole-band boosts | Tone bins, median (dB) | Needed (dB) | '
              'Whole band, median (dB) | Synthetic objective (dB) | Windows < -0.5 dB | p99 ms per block | Checks failed | Eligible |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|']
    for t in result['rule_table']:
        failed = ', '.join(k for k, ok in t['checks'].items() if not ok) or '—'
        lines.append(f"| {t['candidate']} | {t['recording_boosts']} + {t['synthetic_late_boosts']} = {t['boosts']} | "
                     f"{t['near_boosts']} | {t['whole_band_boosts']} | {fmt(t['tone_bin_median_db'], 2)} | "
                     f"{fmt(t['tone_bin_needed_db'], 2)} | {fmt(t['whole_band_median_db'], 2)} | "
                     f"{fmt(t['synthetic_objective_db'], 2)} | {t['synthetic_windows_below_minus_half_db']} | "
                     f"{fmt(t['p99_block_ms'], 2)} | {failed} | {'yes' if t['eligible'] else 'no'} |")
    for name, r in result['rule_reference'].items():
        lines.append(f"| *{name} + gate (reference)* | {r['recording_boosts']} + {r['synthetic_late_boosts']} = {r['boosts']} | "
                     f"{r['near_boosts']} | {r['whole_band_boosts']} | {fmt(r['tone_bin_median_db'], 2)} | | "
                     f"{fmt(r['whole_band_median_db'], 2)} | {fmt(r['synthetic_objective_db'], 2)} | "
                     f"{r['synthetic_windows_below_minus_half_db']} | {fmt(r['p99_block_ms'], 2)} | | |")
    lines += ['', f"Development pick: **{result['development_pick'] or 'none (the joint check and v2 stay as they are)'}**", '',
              '## How often each cap acted', '',
              'Summed over horizon groups and runs. A decision is a band check after the first 4 s buffer and 5 checks. '
              '"Fallback" means the tie rule loosened the limit past 0.5 dB; "cap binding" means the cap, not the tie rule, '
              'set the limit; "silent" means only no output was allowed.', '',
              '| Candidate | Part | Decisions | Fallback | Cap binding | Silent | Setting switches |', '|---|---|---:|---:|---:|---:|---:|']
    for name, row in result['cap_activity'].items():
        for part, c in row.items():
            lines.append(f"| {name} | {part} | {c['decisions']} | {c['fallback_decisions']} | {c['capped_decisions']} | "
                         f"{c['silent_decisions']} | {c['setting_switches']} |")
    lines += ['', '## All methods on development material', ''] + method_table(rec, syn, methods)
    key = [m for m in methods if m in ('v2_gated', 'prefix_ar', 'online_ar') or (m.endswith('_gated') and m != 'v2_gated')]
    lines += ['', '## Boosts on the development recordings', ''] + boost_lines(rec, [m for m in methods if m.endswith('_gated')])
    gated = [m for m in methods if m.endswith('_gated') or m.endswith('_ungated')]
    lines += ['', '## Synthetic late windows with a boost (>= 1 dB), by scene', '']
    for m, counts in late_boosts_by_scene(result['scenes'], gated).items():
        lines.append(f"- {label(m)}: "+(', '.join(f'{k} {v}' for k, v in counts.items()) or 'none'))
    lines += ['', '## Per recording: tone bins (dB, 20 / 120 ms)', '', per_file_table(result['recordings'], key, 'tone_band_gain_db', 'electrical'),
              '', '## Per recording: whole band (dB, 20 / 120 ms)', '', per_file_table(result['recordings'], key, 'band_gain_db', 'electrical'),
              '', '## Synthetic families (mean objective dB / late whole band dB)', '']
    fams = result['summary']['synthetic_by_family']
    lines += ['| Method | '+' | '.join(fams)+' |', '|---|'+'---:|'*len(fams)]
    for m in methods:
        lines.append(f'| {label(m)} | '+' | '.join(f"{fmt(fams[f][m]['mean_objective_db'], 2)} / {fmt(fams[f][m]['late_mean_whole_band_db'], 2)}"
                                                    for f in fams)+' |')
    names = [m['name'] for m in result['comparators']+result['candidates']]
    runs = result['recordings']+result['scenes']
    lines += ['', '## Compute time', '', 'Offline Python, one thread per process, measured under the parallel pool. "Own" '
              'excludes the tone-selector update that v2 also runs. One block is 10 ms of audio.', '']
    lines += timing_rows({m:[r['methods'][m] for r in runs] for m in names})
    lines += ['', f"Runtime: {result['runtime_seconds']/60:.1f} minutes."]
    (Path(output)/'DEVELOPMENT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
