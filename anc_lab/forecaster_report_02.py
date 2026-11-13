"""Plain-language Markdown summaries for tone-forecaster study 02 (third-octave boosts)."""
import json
from pathlib import Path

import numpy as np

from .forecaster_report import _score, fmt, label, paired, sign_test_p

NOTE = ('**Reference-signal prediction only.** Every number is how well a forecaster predicts the recording microphone\'s '
        'own signal 20 ms or 120 ms ahead. Nothing was played, no acoustic path was modelled, and no attenuation at an '
        'ear was measured. No real-world cancellation is claimed.')


def per_file_table(records, methods, key, other='not acoustic'):
    lines = ['| Recording | Tones (Hz) | '+' | '.join(label(m) for m in methods)+' |', '|---|---|'+'---:|'*len(methods)]
    for r in records:
        if key == 'tone_band_gain_db' and not r['reference_tones_hz']:
            continue
        tones = ', '.join(f'{f:.0f}' for f in r['reference_tones_hz']) or 'none'
        cells = [f"{fmt(_score(r, m, 20., key))} / {fmt(_score(r, m, 120., key))}" for m in methods]
        kind = f' ({other})' if r['electrical_not_acoustic'] else ''
        lines.append(f"| {r['file'][:40]}{kind} | {tones} | "+' | '.join(cells)+' |')
    return '\n'.join(lines)


def boost_lines(rec, methods):
    out = []
    for m in methods:
        r = rec[m]
        items = ([f"whole band {x['band_gain_db']:.2f} dB on {x['file']} at {x['horizon_start_ms']:g} ms" for x in r['whole_band_boosts']]
                 + [f"third-octave +{x['max_change_db']:.1f} dB on {x['file']} at {x['horizon_start_ms']:g} ms" for x in r['third_octave_boosts']])
        near = [x for x in r['near_boosts'] if x['max_change_db'] < 1.]
        if near:
            items.append('near (0.5-1 dB): '+', '.join(f"{x['file'][:24]} {x['horizon_start_ms']:g} ms +{x['max_change_db']:.2f}" for x in near))
        out.append(f"- {label(m)}: "+('; '.join(items) if items else 'none'))
    return out


def method_table(rec, syn, methods):
    lines = ['| Method | Tone bins median, 20 / 120 ms | Whole band median, 20 / 120 ms | Whole-band boosts | '
             'Third-octave boosts (>= 1 dB) | Near-boosts (>= 0.5 dB) | Synthetic objective | Synthetic windows < -0.5 dB | '
             'Synthetic late boosts (>= 1 / >= 0.5 dB) |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for m in methods:
        r, s = rec[m], syn.get(m)
        lines.append(f"| {label(m)} | {fmt(r['median_tone_bin_db']['20'])} / {fmt(r['median_tone_bin_db']['120'])} | "
                     f"{fmt(r['median_whole_band_db']['20'], 2)} / {fmt(r['median_whole_band_db']['120'], 2)} | "
                     f"{len(r['whole_band_boosts'])} | {len(r['third_octave_boosts'])} | {len(r['near_boosts'])} | "
                     + (f"{fmt(s['mean_objective_db'], 2)} | "
                        f"{s['windows_below_minus_half_db'] if s['windows_below_minus_half_db'] is not None else '—'} | "
                        f"{s['late_third_octave_boosts']} / {s['late_near_boosts']} |" if s else '— | — | — |'))
    return lines


def timing_rows(infos_by_method):
    rows = []
    for m, infos in infos_by_method.items():
        if infos and 'own_block_ms_p99' in infos[0]:
            rows.append(f"| {m} | {np.mean([i['own_block_ms_mean'] for i in infos]):.2f} | "
                        f"{np.median([i['own_block_ms_p99'] for i in infos]):.2f} | {max(i['own_block_ms_p99'] for i in infos):.2f} | "
                        f"{max(i['own_block_ms_max'] for i in infos):.1f} | {np.mean([i['block_ms_mean'] for i in infos]):.2f} |")
    return ['| Method | Own ms per block, mean | Own p99, median over runs | Own p99, worst run | Own worst block | ms per block incl. selector, mean |',
            '|---|---:|---:|---:|---:|---:|']+rows


def write_development_summary(output, result):
    rec, syn = result['summary']['recordings'], result['summary']['synthetic']
    methods = list(rec)
    lines = ['# Tone forecaster study 02: development run', '',
             '**Development material only.** No study-01 test recording, fresh recording or test scene was read. '+NOTE, '',
             f"Development recordings: {', '.join(result['development_files'])}.", '']
    if result.get('note'):
        lines += [f"**Note:** {result['note']}", '']
    lines += ['## Rule', '', result['rule'], '',
              '| Candidate | Tone bins, median (dB) | Needed (dB) | Whole band, median (dB) | Third-octave boosts | Near-boosts | '
              'Synthetic late boosts (>= 1 / >= 0.5) | Synthetic objective (dB) | p99 ms per block | Checks failed | Eligible |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|']
    for t in result['rule_table']:
        failed = ', '.join(k for k, ok in t['checks'].items() if not ok) or '—'
        lines.append(f"| {t['candidate']} | {fmt(t['tone_bin_median_db'], 2)} | {fmt(t['tone_bin_needed_db'], 2)} | "
                     f"{fmt(t['whole_band_median_db'], 2)} | {t['third_octave_boosts']} | {t['near_boosts']} | "
                     f"{t['synthetic_late_boosts']} / {t['synthetic_late_near_boosts']} | {fmt(t['synthetic_objective_db'], 2)} | "
                     f"{fmt(t['p99_block_ms'], 2)} | {failed} | {'yes' if t['eligible'] else 'no'} |")
    for name, r in result['rule_reference'].items():
        lines.append(f"| *{name} + gate (reference)* | {fmt(r['tone_bin_median_db'], 2)} | | {fmt(r['whole_band_median_db'], 2)} | "
                     f"{r['third_octave_boosts']} | {r['near_boosts']} | {r['synthetic_late_boosts']} / {r['synthetic_late_near_boosts']} | "
                     f"{fmt(r['synthetic_objective_db'], 2)} | | | |")
    lines += ['', f"Development pick: **{result['development_pick'] or 'none (v2 stays)'}**", '',
              '## All methods on development material', ''] + method_table(rec, syn, methods)
    key = [m for m in methods if m in ('v2_gated', 'prefix_ar', 'online_ar') or (m.endswith('_gated') and m != 'v2_gated')]
    lines += ['', '## Boosts on the development recordings', ''] + boost_lines(rec, [m for m in methods if m.endswith('_gated')])
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


def _answer(rec, c, base='v2_gated', ref='bank_wide_lines_gated'):
    """The two-part primary answer on the fresh recordings, as (boosts_gone, tone_kept, sentences)."""
    r, b, w = rec[c], rec[base], rec[ref]
    gone = len(r['third_octave_boosts']) <= len(b['third_octave_boosts']) and len(r['whole_band_boosts']) <= len(b['whole_band_boosts'])
    cm, bm, wm = r['median_tone_bin_db']['20'], b['median_tone_bin_db']['20'], w['median_tone_bin_db']['20']
    kept = cm is not None and bm is not None and cm > bm
    share = (cm-bm)/(wm-bm) if None not in (cm, bm, wm) and wm > bm else None
    return gone, kept, cm, bm, wm, share


def write_test_report(study, result):
    """REPORT.md for the study-02 test stage, at the study root."""
    protocol = result['protocol']
    fresh, seen, syn = result['summary']['fresh'], result['summary']['seen'], result['summary']['synthetic']
    fams = result['summary']['synthetic_by_family']
    methods = list(fresh)
    cand = protocol['frozen_candidate']
    c = cand['name']+'_gated' if cand else None
    base, ref = 'v2_gated', 'bank_wide_lines_gated'
    lines = ['# Tone forecaster study 02: test on fresh recordings', '', NOTE, '',
             f"**Independence.** {protocol['fresh_independence']}", '']
    if c:
        gone, kept, cm, bm, wm, share = _answer(fresh, c)
        r, b, w = fresh[c], fresh[base], fresh[ref]
        lines += ['## Answer', '',
                  f"1. **Are the boosts gone? {'Yes' if gone else 'No'}.** On the fresh recordings {label(c)} has "
                  f"{len(r['third_octave_boosts'])} third-octave boost case(s) (a band 1 dB or more louder) against "
                  f"{len(b['third_octave_boosts'])} for v2 + gate and {len(w['third_octave_boosts'])} for the study-01 line-finder "
                  f"bank + gate; whole-band boosts {len(r['whole_band_boosts'])} against {len(b['whole_band_boosts'])} and "
                  f"{len(w['whole_band_boosts'])}. Near-boosts (0.5 dB or more): {len(r['near_boosts'])}, {len(b['near_boosts'])} "
                  f"and {len(w['near_boosts'])}.",
                  f"2. **Is the tone gain kept? {'Yes' if kept else 'No'}.** Median tone-bin gain at 20 ms over the "
                  f"{r['tone_files']} fresh acoustic recordings with reference tones: {fmt(cm)} dB for {label(c)}, {fmt(bm)} dB "
                  f"for v2 + gate and {fmt(wm)} dB for the study-01 line-finder bank + gate"
                  + (f"; the candidate keeps {100*share:.0f}% of that bank's lead over v2." if share is not None else
                     '; the study-01 bank is not ahead of v2 here, so there is no lead to keep.'), '']
        d = paired(result['fresh_recordings'], c, base, 20., 'tone_band_gain_db')
        wins, losses = sum(v > 0 for _, v in d), sum(v < 0 for _, v in d)
        wb = paired(result['fresh_recordings'], c, base, 20., 'band_gain_db')
        if d:
            lines += [f"Per file at 20 ms the candidate beats v2 + gate at the tones on {wins} of {len(d)} files and loses on "
                      f"{losses} (exact sign test p = {fmt(sign_test_p(wins, losses), 3)}); differences run from "
                      f"{fmt(min(v for _, v in d))} to {fmt(max(v for _, v in d))} dB. With this few files the median is coarse; "
                      'the per-file tables are the evidence.', '']
        lines += [f"Whole band (35-350 Hz), the score that does not depend on how the reference tones were picked: median "
                  f"{fmt(r['median_whole_band_db']['20'], 2)} dB for the candidate against {fmt(b['median_whole_band_db']['20'], 2)} "
                  f"dB for v2 + gate at 20 ms; the candidate is ahead on {sum(v > 0 for _, v in wb)} of {len(wb)} files.", '',
                  '**Caveat on the tone-bin score.** The reference tones are the scored segment\'s lines standing 10 dB above '
                  'their +-10 Hz median, chosen with hindsight. The line finder uses a similar prominence rule causally, so '
                  'tone-bin gains flatter it. The whole-band score has no such bias.', '']
    else:
        lines += ['## Answer', '', f"No candidate was frozen ({protocol['frozen_candidate_note']}), so the question has no "
                  'candidate to answer for. The comparators are reported below.', '']
    missing = result['fresh_missing']
    lines += ['## What was frozen before this run', '',
              f"- Development run: `{protocol['development_run']}` (its DEVELOPMENT.md). Rule:", '', f"  > {protocol['rule']}", '',
              f"- Frozen candidate: **{cand['name'] if cand else 'none'}**"
              + (f" ({json.dumps({k:v for k, v in cand.items() if k != 'name'})})" if cand else ''),
              '- Comparators: predict nothing; v2 with and without its realized-error gate (today\'s engine); ridge AR adapted '
              'on each file\'s first 40% (prefix AR) and refitted every second on past samples (online AR), which are adapted '
              'models that forecast the whole waveform; and the study-01 line-finder bank (bank_wide_lines).',
              f"- Primary question: {protocol['primary_question']}",
              f"- Fresh recordings scored ({len(result['fresh_files'])}): {', '.join(result['fresh_files'])}."
              + (f" Missing, not replaced: {', '.join(missing)}." if missing else ''), '']
    lines += ['## All methods on the fresh recordings', ''] + method_table(fresh, {}, methods)
    key = [m for m in methods if m in ('v2_gated', 'prefix_ar', 'online_ar') or (m.endswith('_gated') and m != 'v2_gated')]
    lines += ['', '### Boosts', ''] + boost_lines(fresh, [m for m in methods if m.endswith('_gated') or m in ('prefix_ar', 'online_ar')])
    lines += ['', '### Per recording: tone bins (dB, 20 / 120 ms)', '',
              per_file_table(result['fresh_recordings'], key, 'tone_band_gain_db', 'capture unknown'),
              '', '### Per recording: whole band (dB, 20 / 120 ms)', '',
              per_file_table(result['fresh_recordings'], key, 'band_gain_db', 'capture unknown'), '',
              'A file marked "capture unknown" is kept out of the medians; its boosts still count.', '']
    lines += ['## Secondary: the study-01 test recordings (seen, not independent)', '', protocol['seen_note'], ''] + method_table(seen, {}, methods)
    lines += ['', '### Boosts', ''] + boost_lines(seen, [m for m in methods if m.endswith('_gated')])
    lines += ['', '### Per recording: tone bins (dB, 20 / 120 ms)', '',
              per_file_table(result['seen_recordings'], key, 'tone_band_gain_db', 'electrical'), '']
    lines += ['## Secondary: fresh synthetic scenes', '',
              f"{len(result['scenes'])} scenes from seeds {protocol['synthetic_test']['standard_seed']} and "
              f"{protocol['synthetic_test']['wander_seed']}, odd 10 Hz bands, more than 2 Hz from every development frequency. "
              f"{protocol['synthetic_test']['not_excluded']}", '',
              '| Method | Objective (dB) | Windows < -0.5 dB | Late whole band, mean / min (dB) | Late tone bins, median (dB) | Late boosts (>= 1 / >= 0.5 dB) |',
              '|---|---:|---:|---:|---:|---:|']
    for m in methods:
        s = syn[m]
        lines.append(f"| {label(m)} | {fmt(s['mean_objective_db'], 2)} | "
                     f"{s['windows_below_minus_half_db'] if s['windows_below_minus_half_db'] is not None else '—'} | "
                     f"{fmt(s['late_mean_whole_band_db'], 2)} / {fmt(s['late_min_whole_band_db'], 2)} | "
                     f"{fmt(s['late_median_tone_bin_db'])} | {s['late_third_octave_boosts']} / {s['late_near_boosts']} |")
    lines += ['', 'By family (mean objective dB / late whole band dB):', '', '| Method | '+' | '.join(fams)+' |', '|---|'+'---:|'*len(fams)]
    for m in methods:
        lines.append(f'| {label(m)} | '+' | '.join(f"{fmt(fams[f][m]['mean_objective_db'], 2)} / {fmt(fams[f][m]['late_mean_whole_band_db'], 2)}"
                                                    for f in fams)+' |')
    names = [m['name'] for m in protocol['comparators']+([cand] if cand else [])]
    runs = result['fresh_recordings']+result['seen_recordings']+result['scenes']
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
