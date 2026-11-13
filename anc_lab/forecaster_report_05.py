"""Plain-language Markdown summaries for tone-forecaster study 05 (tones fading in and out of the joint check)."""
import json
from pathlib import Path

from .forecaster_report import fmt, label, paired, sign_test_p
from .forecaster_report_02 import NOTE, boost_lines, method_table, per_file_table, timing_rows
from .forecaster_report_03 import late_boosts_by_scene
from .forecaster_study_05 import CHANGE_SCENES, change_scene_boosts


def _rule_rows(result):
    lines = ['| Candidate | Boosts (rec + syn late) | On change scenes | Near-boosts | Whole-band boosts | Tone bins, median (dB) | '
             'Needed (dB) | Whole band, median (dB) | Synthetic objective (dB) | Windows < -0.5 dB | p99 ms per block, median over runs | '
             'Checks failed | Eligible |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|']
    for t in result['rule_table']:
        failed = ', '.join(k for k, ok in t['checks'].items() if not ok) or '—'
        lines.append(f"| {t['candidate']} | {t['recording_boosts']} + {t['synthetic_late_boosts']} = {t['boosts']} | "
                     f"{t['change_scene_boosts']} | {t['near_boosts']} | {t['whole_band_boosts']} | "
                     f"{fmt(t['tone_bin_median_db'], 2)} | {fmt(t['tone_bin_needed_db'], 2)} | {fmt(t['whole_band_median_db'], 2)} | "
                     f"{fmt(t['synthetic_objective_db'], 2)} | {t['synthetic_windows_below_minus_half_db']} | "
                     f"{fmt(t['p99_block_ms'], 2)} | {failed} | {'yes' if t['eligible'] else 'no'} |")
    for name, r in result['rule_reference'].items():
        lines.append(f"| *{name} + gate (reference)* | {r['recording_boosts']} + {r['synthetic_late_boosts']} = {r['boosts']} | "
                     f"{r['change_scene_boosts']} | {r['near_boosts']} | {r['whole_band_boosts']} | "
                     f"{fmt(r['tone_bin_median_db'], 2)} | | {fmt(r['whole_band_median_db'], 2)} | "
                     f"{fmt(r['synthetic_objective_db'], 2)} | {r['synthetic_windows_below_minus_half_db']} | "
                     f"{fmt(r['p99_block_ms'], 2)} | | |")
    return lines


def _common_tail(result, records, methods, other):
    """Per-recording tables, synthetic families and timing, shared by both reports."""
    key = [m for m in methods if m in ('v2_gated', 'prefix_ar', 'online_ar') or (m.endswith('_gated') and m != 'v2_gated')]
    lines = ['', '### Per recording: tone bins (dB, 20 / 120 ms)', '', per_file_table(records, key, 'tone_band_gain_db', other),
             '', '### Per recording: whole band (dB, 20 / 120 ms)', '', per_file_table(records, key, 'band_gain_db', other),
             '', '## Synthetic families (mean objective dB / late whole band dB)', '']
    fams = result['summary']['synthetic_by_family']
    lines += ['| Method | '+' | '.join(fams)+' |', '|---|'+'---:|'*len(fams)]
    for m in methods:
        lines.append(f'| {label(m)} | '+' | '.join(f"{fmt(fams[f][m]['mean_objective_db'], 2)} / {fmt(fams[f][m]['late_mean_whole_band_db'], 2)}"
                                                    for f in fams)+' |')
    gated = [m for m in methods if m.endswith('_gated') or m.endswith('_ungated')]
    lines += ['', '## Synthetic late windows with a boost (>= 1 dB), by scene', '',
              'Both horizons count. The change scenes are ' + ', '.join(CHANGE_SCENES)+'.', '']
    for m, counts in late_boosts_by_scene(result['scenes'], gated).items():
        lines.append(f"- {label(m)}: "+(', '.join(f'{k} {v}' for k, v in counts.items()) or 'none'))
    return lines


def write_development_summary(output, result):
    rec, syn = result['summary']['recordings'], result['summary']['synthetic']
    methods = list(rec)
    lines = ['# Tone forecaster study 05: development run', '',
             '**Development material only.** No study-01 test recording, study-02 fresh recording, synthetic test scene or '
             'new fresh recording was read. '+NOTE, '',
             f"Development recordings: {', '.join(result['development_files'])}. Synthetic: the 44 development scenes of "
             f"studies 01 and 02 plus study 03's 8 buzz scenes (seed {result['buzz_development']['seed']}).", '']
    if result.get('note'):
        lines += [f"**Note:** {result['note']}", '']
    lines += ['## Rule', '', result['rule'], ''] + _rule_rows(result)
    lines += ['', f"Development pick: **{result['development_pick'] or 'none (the joint check and v2 stay as they are)'}**", '',
              '## How often the fades acted', '',
              'Summed over horizon groups, output settings and runs. A "ghost" is a tone the selector dropped while some '
              'setting was still fading it out; it runs on from its last phasor until it is silent. "Fading tone-blocks" '
              'counts (setting, tone, block) cells with a level strictly between 0 and 1.', '',
              '| Candidate | Part | Ghosts | Fading tone-blocks |', '|---|---|---:|---:|']
    for name, row in result['fade_activity'].items():
        for part, c in row.items():
            lines.append(f"| {name} | {part} | {c['ghosts']} | {c['fading_tone_blocks']} |")
    lines += ['', '## All methods on development material', ''] + method_table(rec, syn, methods)
    lines += ['', '### Boosts on the development recordings', ''] + boost_lines(rec, [m for m in methods if m.endswith('_gated')])
    lines += _common_tail(result, result['recordings'], methods, 'electrical')
    names = [m['name'] for m in result['comparators']+result['candidates']]
    runs = result['recordings']+result['scenes']
    lines += ['', '## Compute time', '', 'Offline Python, one thread per process, measured under the parallel pool. "Own" '
              'excludes the tone-selector update that v2 also runs. One block is 10 ms of audio.', '']
    lines += timing_rows({m:[r['methods'][m] for r in runs] for m in names})
    lines += ['', f"Runtime: {result['runtime_seconds']/60:.1f} minutes."]
    (Path(output)/'DEVELOPMENT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


def answer(result, c, joint='joint_gated', base='v2_gated'):
    """The three-part primary answer as (parts, numbers); each part is True or False."""
    fresh, scenes = result['summary']['fresh'], result['scenes']
    change = {m:change_scene_boosts(scenes, m) for m in (c, joint, base)}
    r, j, b = fresh[c], fresh[joint], fresh[base]
    cm, bm = r['median_tone_bin_db']['20'], b['median_tone_bin_db']['20']
    parts = {'fewer_change_boosts':change[c] < change[joint],
             'no_more_recording_boosts':(len(r['third_octave_boosts']) <= len(j['third_octave_boosts'])
                                         and len(r['whole_band_boosts']) <= len(j['whole_band_boosts'])),
             'tone_gain_above_v2':cm is not None and bm is not None and cm > bm}
    return parts, {'change_scene_boosts':change, 'tone_bin_20ms':{c:cm, base:bm, joint:j['median_tone_bin_db']['20']}}


def write_test_report(study, result):
    """REPORT.md for the study-05 test stage, at the study root."""
    protocol = result['protocol']
    fresh, syn = result['summary']['fresh'], result['summary']['synthetic']
    methods = list(fresh)
    cand = protocol['frozen_candidate']
    c, joint, base = cand['name']+'_gated', 'joint_gated', 'v2_gated'
    parts, nums = answer(result, c)
    r, j, b = fresh[c], fresh[joint], fresh[base]
    ch = nums['change_scene_boosts']
    tb = nums['tone_bin_20ms']
    n_change = sum(sc['scene'].split('#')[0] in CHANGE_SCENES for sc in result['scenes'])
    yes = all(parts.values())
    lines = ['# Tone forecaster study 05: test on fresh material', '', NOTE, '',
             f"**Independence.** {protocol['fresh_independence']}", '',
             '## Answer', '', f"Primary question: {protocol['primary_question']}", '',
             f"**{'Yes' if yes else 'No'}.**", '',
             f"1. **Fewer boosts where the sound changes suddenly? {'Yes' if parts['fewer_change_boosts'] else 'No'}.** On the "
             f"{n_change} fresh change scenes {label(c)} has {ch[c]} late windows with a band 1 dB or more louder, against "
             f"{ch[joint]} for the joint check + gate and {ch[base]} for v2 + gate (both horizons).",
             f"2. **No more boosts on the fresh recordings? {'Yes' if parts['no_more_recording_boosts'] else 'No'}.** "
             f"Third-octave boosts {len(r['third_octave_boosts'])} against {len(j['third_octave_boosts'])} for the joint check "
             f"+ gate and {len(b['third_octave_boosts'])} for v2 + gate; whole-band boosts {len(r['whole_band_boosts'])}, "
             f"{len(j['whole_band_boosts'])} and {len(b['whole_band_boosts'])}. Near-boosts (0.5 dB or more): "
             f"{len(r['near_boosts'])}, {len(j['near_boosts'])} and {len(b['near_boosts'])}.",
             f"3. **Tone gain still above v2's? {'Yes' if parts['tone_gain_above_v2'] else 'No'}.** Median tone-bin gain at 20 ms "
             f"over the {r['tone_files']} fresh acoustic recordings with reference tones: {fmt(tb[c])} dB for {label(c)}, "
             f"{fmt(tb[joint])} dB for the joint check + gate and {fmt(tb[base])} dB for v2 + gate.", '']
    for other, name in ((joint, 'the joint check + gate'), (base, 'v2 + gate')):
        d = paired(result['fresh_recordings'], c, other, 20., 'tone_band_gain_db')
        wb = paired(result['fresh_recordings'], c, other, 20., 'band_gain_db')
        if d:
            wins, losses = sum(v > 0 for _, v in d), sum(v < 0 for _, v in d)
            lines.append(f"Against {name}, per file at 20 ms: ahead at the tones on {wins} of {len(d)} files, behind on {losses} "
                         f"(exact sign test p = {fmt(sign_test_p(wins, losses), 3)}), differences {fmt(min(v for _, v in d))} to "
                         f"{fmt(max(v for _, v in d))} dB; ahead on the whole band on {sum(v > 0 for _, v in wb)} of {len(wb)} files.")
    lines += ['', 'With this few files the medians are coarse; the per-file tables are the evidence. The reference tones are '
              'chosen with hindsight (lines 10 dB above their +-10 Hz median), which flatters the line finder; the whole-band '
              'score has no such bias.', '']
    missing = result['fresh_missing']
    lines += ['## What was frozen before this run', '',
              f"- Development run: `{protocol['development_run']}` (its DEVELOPMENT.md). Rule:", '', f"  > {protocol['rule']}", '',
              f"- Frozen candidate: **{cand['name']}** ({json.dumps({k:v for k, v in cand.items() if k != 'name'})})",
              '- Comparators: predict nothing; v2 with and without its realized-error gate (today\'s engine); ridge AR adapted '
              'on each file\'s first 40% (prefix AR) and refitted every second on past samples (online AR); the study-01 '
              'line-finder bank (bank_wide_lines); and the study-02 joint check (joint), with and without the gate.',
              f"- Fresh recordings scored ({len(result['fresh_files'])}): {', '.join(result['fresh_files'])}."
              + (f" Missing, not replaced: {', '.join(missing)}." if missing else ''), '']
    lines += ['## All methods on the fresh recordings', ''] + method_table(fresh, {}, methods)
    lines += ['', '### Boosts', ''] + boost_lines(fresh, [m for m in methods if m.endswith('_gated') or m in ('prefix_ar', 'online_ar')])
    lines += _common_tail(result, result['fresh_recordings'], methods, 'capture unknown')
    st = protocol['synthetic_test']
    lines += ['', '## Fresh synthetic scenes', '',
              f"{len(result['scenes'])} scenes from seeds {st['standard_seed']} and {st['wander_seed']}, odd 10 Hz bands, more "
              f"than 2 Hz from every development frequency and study 03's buzz draws. {st['not_excluded']}", '',
              '| Method | Objective (dB) | Windows < -0.5 dB | Late whole band, mean / min (dB) | Late tone bins, median (dB) | '
              'Late boosts (>= 1 / >= 0.5 dB) | On change scenes (>= 1 dB) |', '|---|---:|---:|---:|---:|---:|---:|']
    for m in methods:
        s = syn[m]
        lines.append(f"| {label(m)} | {fmt(s['mean_objective_db'], 2)} | "
                     f"{s['windows_below_minus_half_db'] if s['windows_below_minus_half_db'] is not None else '—'} | "
                     f"{fmt(s['late_mean_whole_band_db'], 2)} / {fmt(s['late_min_whole_band_db'], 2)} | "
                     f"{fmt(s['late_median_tone_bin_db'])} | {s['late_third_octave_boosts']} / {s['late_near_boosts']} | "
                     f"{change_scene_boosts(result['scenes'], m)} |")
    names = [m['name'] for m in protocol['comparators']+[cand]]
    runs = result['fresh_recordings']+result['scenes']
    lines += ['', '## Compute time', '', 'Offline Python, one thread per process, measured under the parallel pool. "Own" '
              'excludes the tone-selector update that v2 also runs. One block is 10 ms of audio.', '']
    lines += timing_rows({m:[r['methods'][m] for r in runs] for m in names})
    lines += ['', '## Fresh recordings and credits', '', '| File | Author | Licence | Seconds | Counted as acoustic |', '|---|---|---|---:|---|']
    for e in protocol['fresh_recordings']:
        lines.append(f"| {e['file']} | {e['author']} | {e['licence']} | {e['seconds']:.0f} | {'yes' if e['acoustic'] else 'no'} |")
    lines += ['', f"Files are local only, in `{protocol['fresh_folder']}`, from Wikimedia Commons (each file's page is "
              'https://commons.wikimedia.org/wiki/ followed by its title).', '',
              f"Runtime: {result['runtime_seconds']/60:.1f} minutes. Created {result['created_utc']}. Numbers: `test/test.json`. "
              'Frozen protocol: `protocol.json`.']
    (Path(study)/'REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
