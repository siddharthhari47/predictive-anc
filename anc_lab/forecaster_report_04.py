"""Plain-language Markdown summaries for tone-forecaster study 04 (a softer realized-error gate)."""
import json
from pathlib import Path

import numpy as np

from .forecaster_report import fmt, label, paired, sign_test_p
from .forecaster_report_02 import NOTE, boost_lines, method_table, per_file_table, timing_rows
from .forecaster_report_03 import late_boosts_by_scene

GATE_NOTE = ('"+ gate" always means the output after the v2 gate as that method uses it: switched (v2, joint, '
             'bank_wide_lines, gcheck) or faded (the names with fade8 or fade8in3out). The gate decides the same way in '
             'every case. gcheck is the band check that judges each setting after its own copy of the gate.')


def family_boosts(scenes, methods, threshold=1.):
    """Per method: late windows with a band `threshold` dB or more louder, by scene family."""
    families = sorted({sc['family'] for sc in scenes})
    return families, {m:{f:int(sum(s['max_third_octave_change_db'] >= threshold for sc in scenes if sc['family'] == f
                                   for s in sc['late_window_scores'] if s['method'] == m)) for f in families}
                      for m in methods}


def family_table(scenes, methods):
    families, counts = family_boosts(scenes, methods)
    near = family_boosts(scenes, methods, .5)[1]
    lines = ['| Method | '+' | '.join(families)+' |', '|---|'+'---:|'*len(families)]
    for m in methods:
        lines.append(f'| {label(m)} | '+' | '.join(f'{counts[m][f]} / {near[m][f]}' for f in families)+' |')
    return lines


def fade_timing_rows(infos_by_method):
    rows = []
    for m, infos in infos_by_method.items():
        if infos and infos[0].get('fade'):
            rows.append(f"| {m} | {np.median([i['fade_block_ms_p99'] for i in infos]):.3f} | "
                        f"{max(i['fade_block_ms_max'] for i in infos):.3f} |")
    return ['| Method | Fade p99 ms per block, median over runs | Fade worst block (ms) |', '|---|---:|---:|']+rows


def write_development_summary(output, result):
    rec, syn = result['summary']['recordings'], result['summary']['synthetic']
    methods = list(rec)
    lines = ['# Tone forecaster study 04: development run', '',
             '**Development material only.** No study-01 test recording, study-02 fresh recording, synthetic test scene or '
             'new fresh recording was read. '+NOTE, '',
             f"Development recordings: {', '.join(result['development_files'])}. Synthetic: the 44 development scenes of "
             f"studies 01 and 02 plus study 03's 8 buzz scenes (seed {result['buzz_development']['seed']}).", '', GATE_NOTE, '']
    if result.get('note'):
        lines += [f"**Note:** {result['note']}", '']
    lines += ['## Rule', '', result['rule'], '',
              '| Candidate | Boosts (rec + syn late) | Buzz late boosts | Near-boosts | Whole-band boosts | Tone bins, median (dB) | '
              'Needed (dB) | Whole band, median (dB) | Synthetic objective (dB) | Windows < -0.5 dB | p99 ms per block, median | '
              'Added over joint (ms) | Checks failed | Eligible |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|']
    for t in result['rule_table']:
        failed = ', '.join(k for k, ok in t['checks'].items() if not ok) or '—'
        lines.append(f"| {t['candidate']} | {t['recording_boosts']} + {t['synthetic_late_boosts']} = {t['boosts']} | "
                     f"{t['buzz_late_boosts']} | {t['near_boosts']} | {t['whole_band_boosts']} | "
                     f"{fmt(t['tone_bin_median_db'], 2)} | {fmt(t['tone_bin_needed_db'], 2)} | "
                     f"{fmt(t['whole_band_median_db'], 2)} | {fmt(t['synthetic_objective_db'], 2)} | "
                     f"{t['synthetic_windows_below_minus_half_db']} | {fmt(t['p99_block_ms_median'], 2)} | "
                     f"{t['p99_added_ms']:+.2f} | {failed} | {'yes' if t['eligible'] else 'no'} |")
    for name, r in result['rule_reference'].items():
        lines.append(f"| *{name} (reference)* | {r['recording_boosts']} + {r['synthetic_late_boosts']} = {r['boosts']} | "
                     f"{r['buzz_late_boosts']} | {r['near_boosts']} | {r['whole_band_boosts']} | "
                     f"{fmt(r['tone_bin_median_db'], 2)} | | {fmt(r['whole_band_median_db'], 2)} | "
                     f"{fmt(r['synthetic_objective_db'], 2)} | {r['synthetic_windows_below_minus_half_db']} | "
                     f"{fmt(r['p99_block_ms_median'], 2)} | | | |")
    lines += ['', f"Development pick: **{result['development_pick'] or 'none (the joint check and v2 stay as they are)'}**", '',
              '## How often the gate switched', '',
              'Summed over runs, 20 ms group (the gate shares its decision across groups). "Open" is the share of scored '
              'blocks the gate let through; "mean gain" is the faded gain (equal to "open" for a switched gate).', '',
              '| Method | Part | Switches | Open | Mean gain |', '|---|---|---:|---:|---:|']
    for name, row in result['gate_activity'].items():
        for part, c in row.items():
            lines.append(f"| {name} | {part} | {c['gate_switches']} | {c['gate_open_fraction']:.3f} | {c['mean_gain']:.3f} |")
    lines += ['', '## All methods on development material', ''] + method_table(rec, syn, methods)
    key = [m for m in methods if m in ('v2_gated', 'prefix_ar', 'online_ar') or (m.endswith('_gated') and m != 'v2_gated')]
    gated = [m for m in methods if m.endswith('_gated') or m.endswith('_ungated')]
    lines += ['', '## Synthetic late boosts by family (>= 1 dB / >= 0.5 dB)', ''] + family_table(result['scenes'], gated)
    lines += ['', '## Boosts on the development recordings', ''] + boost_lines(rec, [m for m in methods if m.endswith('_gated')])
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
              'excludes the tone-selector update that v2 also runs and, for a faded method, includes the fade. One block '
              'is 10 ms of audio. The rule compares each candidate with joint + gate run by run, so a busy machine slows '
              'both.', '']
    lines += timing_rows({m:[r['methods'][m] for r in runs] for m in names})
    lines += ['', 'The fade alone, as an engine would run it (one BlockFade per horizon group, one step per block):', '']
    lines += fade_timing_rows({m:[r['methods'][m] for r in runs] for m in names})
    lines += ['', f"Runtime: {result['runtime_seconds']/60:.1f} minutes."]
    (Path(output)/'DEVELOPMENT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


def _answer(fresh, syn, c, joint='joint_gated', base='v2_gated'):
    """The two-part primary answer: (boosts gone, tone kept, candidate tone median, v2 tone median)."""
    gone = (syn[c]['late_third_octave_boosts'] < syn[joint]['late_third_octave_boosts']
            and len(fresh[c]['third_octave_boosts']) <= len(fresh[joint]['third_octave_boosts']))
    cm, bm = fresh[c]['median_tone_bin_db']['20'], fresh[base]['median_tone_bin_db']['20']
    kept = cm is not None and bm is not None and cm > bm
    return gone, kept, cm, bm


def write_test_report(study, result):
    """REPORT.md for the study-04 test stage, at the study root."""
    protocol = result['protocol']
    fresh, seen, syn = result['summary']['fresh'], result['summary']['seen'], result['summary']['synthetic']
    fams = result['summary']['synthetic_by_family']
    methods = list(fresh)
    cand = protocol['frozen_candidate']
    c, joint, base = cand['name']+'_gated', 'joint_gated', 'v2_gated'
    gone, kept, cm, bm = _answer(fresh, syn, c)
    r, j, b = fresh[c], fresh[joint], fresh[base]
    jm = j['median_tone_bin_db']['20']
    _, buzz = family_boosts(result['scenes'], [c, joint, 'joint_ungated'])
    lines = ['# Tone forecaster study 04: test on fresh material', '', NOTE, '', GATE_NOTE, '',
             f"**Independence.** {protocol['fresh_independence']}", '',
             '## Answer', '',
             f"1. **Are the gate's boosts gone, with none added? {'Yes' if gone else 'No'}.** Over the late windows of the "
             f"{len(result['scenes'])} fresh synthetic scenes {label(c)} has {syn[c]['late_third_octave_boosts']} "
             f"third-octave boosts (a band 1 dB or more louder) against {syn[joint]['late_third_octave_boosts']} for joint + "
             f"gate and {syn['joint_ungated']['late_third_octave_boosts']} for the joint check with no gate; on the buzz "
             f"scenes alone {buzz[c].get('buzz', 0)}, {buzz[joint].get('buzz', 0)} and {buzz['joint_ungated'].get('buzz', 0)}. "
             f"On the fresh recordings it has {len(r['third_octave_boosts'])} against {len(j['third_octave_boosts'])} for "
             f"joint + gate and {len(b['third_octave_boosts'])} for v2 + gate; near-boosts (0.5 dB or more) "
             f"{len(r['near_boosts'])}, {len(j['near_boosts'])} and {len(b['near_boosts'])}; whole-band boosts "
             f"{len(r['whole_band_boosts'])}, {len(j['whole_band_boosts'])} and {len(b['whole_band_boosts'])}.",
             f"2. **Is the tone gain kept? {'Yes' if kept else 'No'}.** Median tone-bin gain at 20 ms over the "
             f"{r['tone_files']} fresh acoustic recordings with reference tones: {fmt(cm)} dB for {label(c)}, {fmt(bm)} dB "
             f"for v2 + gate and {fmt(jm)} dB for joint + gate.", '']
    d = paired(result['fresh_recordings'], c, base, 20., 'tone_band_gain_db')
    dj = paired(result['fresh_recordings'], c, joint, 20., 'tone_band_gain_db')
    if d:
        wins, losses = sum(v > 0 for _, v in d), sum(v < 0 for _, v in d)
        lines += [f"Per file at 20 ms the candidate beats v2 + gate at the tones on {wins} of {len(d)} files and loses on "
                  f"{losses} (exact sign test p = {fmt(sign_test_p(wins, losses), 3)}); against joint + gate the "
                  f"differences run from {fmt(min(v for _, v in dj), 2)} to {fmt(max(v for _, v in dj), 2)} dB. With this "
                  'few files the median is coarse; the per-file tables are the evidence.', '']
    wb = paired(result['fresh_recordings'], c, base, 20., 'band_gain_db')
    lines += [f"Whole band (35-350 Hz), the score that does not depend on how the reference tones were picked: median "
              f"{fmt(r['median_whole_band_db']['20'], 2)} dB for the candidate, {fmt(j['median_whole_band_db']['20'], 2)} dB "
              f"for joint + gate and {fmt(b['median_whole_band_db']['20'], 2)} dB for v2 + gate at 20 ms; the candidate is "
              f"ahead of v2 + gate on {sum(v > 0 for _, v in wb)} of {len(wb)} files.", '',
              '**Caveat on the tone-bin score.** The reference tones are the scored segment\'s lines standing 10 dB above '
              'their +-10 Hz median, chosen with hindsight. The line finder uses a similar prominence rule causally, so '
              'tone-bin gains flatter it. The whole-band score has no such bias.', '']
    missing = result['fresh_missing']
    lines += ['## What was frozen before this run', '',
              f"- Development run: `{protocol['development_run']}` (its DEVELOPMENT.md). Rule:", '', f"  > {protocol['rule']}", '',
              f"- Frozen candidate: **{cand['name']}** ({json.dumps({k:v for k, v in cand.items() if k != 'name'})})",
              '- Comparators: predict nothing; v2 with and without its gate (today\'s engine); ridge AR adapted on each '
              'file\'s first 40% (prefix AR) and refitted every second on past samples (online AR); the study-01 '
              'line-finder bank (bank_wide_lines); the study-02 joint check (joint); and v2 with the 8-block fade (v2_fade8).',
              f"- Primary question: {protocol['primary_question']}",
              f"- Fresh recordings scored ({len(result['fresh_files'])}): {', '.join(result['fresh_files'])}."
              + (f" Missing, not replaced: {', '.join(missing)}." if missing else ''), '']
    key = [m for m in methods if m in ('v2_gated', 'prefix_ar', 'online_ar') or (m.endswith('_gated') and m != 'v2_gated')]
    gated = [m for m in methods if m.endswith('_gated') or m.endswith('_ungated')]
    lines += ['## Fresh synthetic scenes', '',
              f"{len(result['scenes'])} scenes in three families (standard, drifting, buzz) from seeds "
              f"{protocol['synthetic_test']['standard_seed']}, {protocol['synthetic_test']['wander_seed']} and "
              f"{protocol['synthetic_test']['buzz_seed']}, odd 10 Hz bands, more than 2 Hz from every development "
              f"frequency. {protocol['synthetic_test']['not_excluded']}", '',
              '| Method | Objective (dB) | Windows < -0.5 dB | Late whole band, mean / min (dB) | Late tone bins, median (dB) | Late boosts (>= 1 / >= 0.5 dB) |',
              '|---|---:|---:|---:|---:|---:|']
    for m in methods:
        s = syn[m]
        lines.append(f"| {label(m)} | {fmt(s['mean_objective_db'], 2)} | "
                     f"{s['windows_below_minus_half_db'] if s['windows_below_minus_half_db'] is not None else '—'} | "
                     f"{fmt(s['late_mean_whole_band_db'], 2)} / {fmt(s['late_min_whole_band_db'], 2)} | "
                     f"{fmt(s['late_median_tone_bin_db'])} | {s['late_third_octave_boosts']} / {s['late_near_boosts']} |")
    lines += ['', 'Late boosts by family (>= 1 dB / >= 0.5 dB):', ''] + family_table(result['scenes'], gated)
    lines += ['', 'By family (mean objective dB / late whole band dB):', '', '| Method | '+' | '.join(fams)+' |', '|---|'+'---:|'*len(fams)]
    for m in methods:
        lines.append(f'| {label(m)} | '+' | '.join(f"{fmt(fams[f][m]['mean_objective_db'], 2)} / {fmt(fams[f][m]['late_mean_whole_band_db'], 2)}"
                                                    for f in fams)+' |')
    lines += ['', '## Fresh recordings', ''] + method_table(fresh, {}, methods)
    lines += ['', '### Boosts', ''] + boost_lines(fresh, [m for m in methods if m.endswith('_gated') or m in ('prefix_ar', 'online_ar')])
    lines += ['', '### Per recording: tone bins (dB, 20 / 120 ms)', '',
              per_file_table(result['fresh_recordings'], key, 'tone_band_gain_db', 'capture unknown'),
              '', '### Per recording: whole band (dB, 20 / 120 ms)', '',
              per_file_table(result['fresh_recordings'], key, 'band_gain_db', 'capture unknown'), '',
              'A file marked "capture unknown" is kept out of the medians; its boosts still count.', '']
    lines += ['## Secondary: seen recordings (not independent)', '', protocol['seen_note'], ''] + method_table(seen, {}, methods)
    lines += ['', '### Boosts', ''] + boost_lines(seen, [m for m in methods if m.endswith('_gated')])
    lines += ['', '### Per recording: tone bins (dB, 20 / 120 ms)', '',
              per_file_table(result['seen_recordings'], key, 'tone_band_gain_db', 'not acoustic'), '']
    names = [m['name'] for m in protocol['comparators']+protocol['candidates']]
    runs = result['fresh_recordings']+result['seen_recordings']+result['scenes']
    lines += ['## Gate activity', '', '| Method | Part | Switches | Open | Mean gain |', '|---|---|---:|---:|---:|']
    for name, row in result['gate_activity'].items():
        for part, a in row.items():
            lines.append(f"| {name} | {part} | {a['gate_switches']} | {a['gate_open_fraction']:.3f} | {a['mean_gain']:.3f} |")
    lines += ['', '## Compute time', '', 'Offline Python, one thread per process, measured under the parallel pool. "Own" '
              'excludes the tone-selector update that v2 also runs and includes the fade. One block is 10 ms of audio.', '']
    lines += timing_rows({m:[x['methods'][m] for x in runs] for m in names})
    lines += ['', '## Fresh recordings and credits', '', '| File | Author | Licence | Seconds | Counted as acoustic |', '|---|---|---|---:|---|']
    for e in protocol['fresh_recordings']:
        lines.append(f"| {e['file']} | {e['author']} | {e['licence']} | {e['seconds']:.0f} | {'yes' if e['acoustic'] else 'no'} |")
    lines += ['', f"Files are local only, in `{protocol['fresh_folder']}`, from Wikimedia Commons (each file's page is "
              'https://commons.wikimedia.org/wiki/ followed by its title).', '',
              f"Runtime: {result['runtime_seconds']/60:.1f} minutes. Created {result['created_utc']}. Numbers: `test/test.json`. "
              'Frozen protocol: `protocol.json`.']
    (Path(study)/'REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


def write_timing_summary(output, result):
    names = result['methods']
    per = result['per_recording']
    lines = ['# Tone forecaster study 04: compute time, one run at a time', '',
             'Offline Python, one thread, no process pool, on the eight development recordings. "Own" excludes the '
             'tone-selector update that v2 also runs and includes the fade where a method has one. One block is 10 ms of '
             'audio. Reference-signal prediction only.', '']
    if result.get('note'):
        lines += [f"**Note:** {result['note']}", '']
    lb, la = result['load_before'], result['load_after']
    lines += [f"Machine load: {lb['cpu_percent']:.0f}% CPU before ({', '.join(lb['busiest'])} busiest), "
              f"{la['cpu_percent']:.0f}% after ({', '.join(la['busiest'])}); {result['cpu_count']} logical CPUs. The "
              'total is a share of the whole machine; a process\'s figure is a share of one CPU, over one second.', '',
              '| Method | Own mean (ms) | Own p99, median over files (ms) | Own p99, worst file (ms) | Own worst block (ms) | '
              'p99 minus joint\'s, median over files (ms) |', '|---|---:|---:|---:|---:|---:|']
    for n in names:
        p99 = [r['methods'][n]['own_block_ms_p99'] for r in per]
        diff = [r['methods'][n]['own_block_ms_p99']-r['methods']['joint']['own_block_ms_p99'] for r in per] if 'joint' in names else []
        lines.append(f"| {n} | {np.mean([r['methods'][n]['own_block_ms_mean'] for r in per]):.2f} | {np.median(p99):.2f} | "
                     f"{max(p99):.2f} | {max(r['methods'][n]['own_block_ms_max'] for r in per):.1f} | "
                     + (f"{np.median(diff):+.2f} |" if diff else '— |'))
    lines += ['', f"Runtime: {result['runtime_seconds']/60:.1f} minutes. Created {result['created_utc']}."]
    (Path(output)/'TIMING.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
