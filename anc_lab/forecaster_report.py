"""Plain-language Markdown summaries for the tone-forecaster study."""
import json
from math import comb
from pathlib import Path

import numpy as np

LABELS = {'zero':'Predict nothing', 'v2_ungated':'v2, no gate', 'v2_gated':'v2 + gate',
          'prefix_ar':'AR adapted on prefix', 'online_ar':'AR refitted online'}


def label(method):
    if method in LABELS:
        return LABELS[method]
    base, _, tail = method.rpartition('_')
    return f"{base} + gate" if tail == 'gated' else f"{base}, no gate" if tail == 'ungated' else method


def fmt(v, digits=1):
    return '—' if v is None else f'{v:.{digits}f}'


def _score(record, method, ms, key):
    return next(s[key] for s in record['scores'] if s['method'] == method and s['horizon_start_ms'] == ms)


def per_file_table(records, methods, key):
    lines = ['| Recording | Tones (Hz) | '+' | '.join(label(m) for m in methods)+' |',
             '|---|---|'+'---:|'*len(methods)]
    for r in records:
        if key == 'tone_band_gain_db' and not r['reference_tones_hz']:
            continue
        tones = ', '.join(f'{f:.0f}' for f in r['reference_tones_hz']) or 'none'
        cells = [f"{fmt(_score(r, m, 20., key))} / {fmt(_score(r, m, 120., key))}" for m in methods]
        kind = ' (electrical)' if r['electrical_not_acoustic'] else ''
        lines.append(f"| {r['file'][:34]}{kind} | {tones} | "+' | '.join(cells)+' |')
    return '\n'.join(lines)


def write_development_summary(output, result):
    rec, syn = result['summary']['recordings'], result['summary']['synthetic']
    methods = list(rec)
    lines = ['# Tone forecaster: development run', '',
             '**Development material only.** No test recording or test scene was read. Reference-signal prediction at the '
             'recording microphone; not cancellation at an ear.', '',
             f"Development recordings: {', '.join(result['development_files'])}.", '']
    if result.get('note'):
        lines += [f"**Change since the earlier development run:** {result['note']}", '']
    lines += ['## Rule (stated before the first development run)', '', result['rule'], '',
              '| Candidate | Tone bins, median (dB) | Whole band, median (dB) | Synthetic objective (dB) | p99 ms per block | Checks failed | Eligible |',
              '|---|---:|---:|---:|---:|---|---|']
    for t in result['rule_table']:
        failed = ', '.join(k for k, ok in t['checks'].items() if not ok) or '—'
        lines.append(f"| {t['candidate']} | {fmt(t['tone_bin_median_db'])} | {fmt(t['whole_band_median_db'], 2)} | "
                     f"{fmt(t['synthetic_objective_db'], 2)} | {fmt(t['p99_block_ms'], 2)} | {failed} | {'yes' if t['eligible'] else 'no'} |")
    lines += ['', f"Development pick: **{result['development_pick'] or 'none (v2 stays)'}**", '',
              '## All methods on development material', '',
              '| Method | Tone bins median, 20 / 120 ms | Whole band median, 20 / 120 ms | Whole-band boosts | Third-octave boosts | Synthetic objective | Synthetic windows < -0.5 dB | Synthetic late whole band (mean / min) |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for m in methods:
        r, s = rec[m], syn[m]
        lines.append(f"| {label(m)} | {fmt(r['median_tone_bin_db']['20'])} / {fmt(r['median_tone_bin_db']['120'])} | "
                     f"{fmt(r['median_whole_band_db']['20'], 2)} / {fmt(r['median_whole_band_db']['120'], 2)} | "
                     f"{len(r['whole_band_boosts'])} | {len(r['third_octave_boosts'])} | {fmt(s['mean_objective_db'], 2)} | "
                     f"{s['windows_below_minus_half_db'] if s['windows_below_minus_half_db'] is not None else '—'} | "
                     f"{fmt(s['late_mean_whole_band_db'], 2)} / {fmt(s['late_min_whole_band_db'], 2)} |")
    key_methods = [m for m in methods if m in ('v2_gated', 'prefix_ar', 'online_ar') or
                   (m.endswith('_gated') and m != 'v2_gated')]
    lines += ['', '## Per recording: tone bins (dB, 20 / 120 ms)', '', per_file_table(result['recordings'], key_methods, 'tone_band_gain_db'),
              '', '## Per recording: whole band (dB, 20 / 120 ms)', '', per_file_table(result['recordings'], key_methods, 'band_gain_db'),
              '', '## Synthetic families (mean objective dB / late whole band dB)', '']
    fams = result['summary']['synthetic_by_family']
    lines += ['| Method | '+' | '.join(fams)+' |', '|---|'+'---:|'*len(fams)]
    for m in methods:
        lines.append(f'| {label(m)} | '+' | '.join(f"{fmt(fams[f][m]['mean_objective_db'], 2)} / {fmt(fams[f][m]['late_mean_whole_band_db'], 2)}"
                                                    for f in fams)+' |')
    lines += ['', f"Runtime: {result['runtime_seconds']/60:.1f} minutes."]
    (Path(output)/'DEVELOPMENT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


def sign_test_p(wins, losses):
    """Two-sided exact sign test (ties dropped)."""
    n = wins+losses
    if not n:
        return None
    tail = sum(comb(n, k) for k in range(0, min(wins, losses)+1))/2**n
    return min(1., 2*tail)


def paired(records, a, b, ms, key):
    """Per-file differences a - b on the files where both have a score."""
    out = []
    for r in records:
        if key == 'tone_band_gain_db' and (not r['reference_tones_hz'] or r['electrical_not_acoustic']):
            continue
        if key == 'band_gain_db' and r['electrical_not_acoustic']:
            continue
        out.append((r['file'], _score(r, a, ms, key)-_score(r, b, ms, key)))
    return out


def timing_rows(result, methods):
    rows = []
    for m in methods:
        infos = [r['methods'][m] for r in result['recordings']+result['scenes']]
        if 'own_block_ms_p99' in infos[0]:
            rows.append(f"| {m} | {np.mean([i['own_block_ms_mean'] for i in infos]):.2f} | "
                        f"{np.median([i['own_block_ms_p99'] for i in infos]):.2f} | {max(i['own_block_ms_p99'] for i in infos):.2f} | "
                        f"{max(i['own_block_ms_max'] for i in infos):.1f} | {np.mean([i['block_ms_mean'] for i in infos]):.2f} |")
        elif 'forecast_ms_per_origin' in infos[0]:
            rows.append(f"| {m} | {np.mean([i['forecast_ms_per_origin'] for i in infos]):.2f} (per origin, refit) | — | — | — | — |")
    return rows


def write_test_report(study, result):
    """REPORT.md for the frozen test stage, at the study root."""
    protocol = result['protocol']
    rec, syn, fams = result['summary']['recordings'], result['summary']['synthetic'], result['summary']['synthetic_by_family']
    methods = list(rec)
    cand = protocol['frozen_candidate']
    c = cand['name']+'_gated' if cand else None
    base = 'v2_gated'
    lines = ['# Tone forecaster: frozen test', '',
             '**Reference-signal prediction only.** Every number is how well a forecaster predicts the recording '
             'microphone\'s own signal 20 ms or 120 ms ahead. Nothing was played, no acoustic path was modelled, and no '
             'attenuation at an ear was measured. No real-world cancellation is claimed.', '',
             f"**Independence.** {protocol['independence']}", '',
             '## What was frozen before this run', '',
             f"- Development run: `{protocol['development_run']}` (see its DEVELOPMENT.md). Rule, stated before the first "
             'development run:', '', f"  > {protocol['rule']}", '',
             f"- Frozen candidate: **{cand['name'] if cand else 'none'}**"
             + (f" ({json.dumps({k:v for k, v in cand.items() if k != 'name'})})" if cand else f" — {protocol['frozen_candidate_note']}"),
             '- Comparators: predict nothing; v2 with and without its realized-error gate (today\'s engine); ridge AR '
             'adapted on each file\'s first 40% (prefix AR); ridge AR refitted every second on past samples (online AR). '
             'The AR comparators are adapted models and forecast the whole waveform, not separate tones.']
    if protocol.get('ablations'):
        lines.append(f"- Secondary (ablation, not part of the primary question): {', '.join(a['name'] for a in protocol['ablations'])}, "
                     'the frozen candidate without its line finder.')
    amendment = protocol.get('amendment')
    if amendment:
        lines.append(f"- **Amendment before any test score** (`{amendment['name']}.json`): {amendment['reason']} "
                     f"{amendment['change']} The stopped attempt is recorded in `test/FAILED_ATTEMPT.md`.")
    lines += [f"- Test recordings ({len(result['test_files'])}): {', '.join(result['test_files'])}.",
              f"- Synthetic test scenes: {len(result['scenes'])}, drawn fresh from seeds {protocol['synthetic_test']['standard_seed']} "
              f"and {protocol['synthetic_test']['wander_seed']} in odd 10 Hz bands (development used even bands), at least 2 Hz "
              'from every frequency used before.', '',
              '## Primary question', '', protocol['primary_question'], '']
    if c:
        r, b = rec[c], rec[base]
        ar = rec['prefix_ar']
        d = paired(result['recordings'], c, base, 20., 'tone_band_gain_db')
        wins, losses = sum(v > 0 for _, v in d), sum(v < 0 for _, v in d)
        cm, bm, am = r['median_tone_bin_db']['20'], b['median_tone_bin_db']['20'], ar['median_tone_bin_db']['20']
        failed = []
        if cm <= bm:
            failed.append('it does not raise the median tone-bin gain at 20 ms above v2 + gate')
        if len(r['whole_band_boosts']) > len(b['whole_band_boosts']):
            failed.append(f"it has more whole-band boosts than v2 + gate ({len(r['whole_band_boosts'])} against {len(b['whole_band_boosts'])})")
        if len(r['third_octave_boosts']) > len(b['third_octave_boosts']):
            failed.append(f"it has more third-octave boosts than v2 + gate ({len(r['third_octave_boosts'])} against "
                          f"{len(b['third_octave_boosts'])}), which the frozen question does not allow")
        gap = (cm-bm)/(am-bm) if am > bm else None
        answer = 'No: '+'; '.join(failed) if failed else 'Yes'
        lines += [f"**Answer: {answer}.**", '', f"On the {r['tone_files']} test acoustic recordings with reference tones, the median "
                  f"tone-bin gain at 20 ms is {fmt(cm)} dB for {label(c)}, {fmt(bm)} dB for v2 + gate and {fmt(am)} dB for "
                  f"prefix AR" + (f" ({100*gap:.0f}% of the v2-to-prefix-AR gap closed)." if gap is not None else
                                  ' (prefix AR is not ahead of v2 + gate on these files, so there is no gap to close).'),
                  '', f"Whole-band boosts (whole band below -0.5 dB): {len(r['whole_band_boosts'])} for the candidate, "
                  f"{len(b['whole_band_boosts'])} for v2 + gate. Third-octave boosts (a third-octave band 1 dB or more louder): "
                  f"{len(r['third_octave_boosts'])} for the candidate (on {len({x['file'] for x in r['third_octave_boosts']})} files, "
                  f"largest +{max([x['max_change_db'] for x in r['third_octave_boosts']], default=0):.1f} dB), "
                  f"{len(b['third_octave_boosts'])} for v2 + gate (on {len({x['file'] for x in b['third_octave_boosts']})} files, "
                  f"largest +{max([x['max_change_db'] for x in b['third_octave_boosts']], default=0):.1f} dB). "
                  'A boost here is a count of (file, horizon) cases; the full list is below.', '',
                  f"Per file at 20 ms, the candidate beats v2 + gate at the tones on {wins} of {len(d)} files and loses on "
                  f"{losses} (exact sign test p = {fmt(sign_test_p(wins, losses), 3)}); differences range from "
                  f"{fmt(min(v for _, v in d))} to {fmt(max(v for _, v in d))} dB. With this few files the median is a coarse "
                  'summary; the per-file tables below are the evidence.', '']
        wb = paired(result['recordings'], c, base, 20., 'band_gain_db')
        lines += [f"Whole band (35-350 Hz, all acoustic test files) is the cross-check that does not depend on how the "
                  f"reference tones were picked: median {fmt(r['median_whole_band_db']['20'], 2)} dB for the candidate against "
                  f"{fmt(b['median_whole_band_db']['20'], 2)} dB for v2 + gate at 20 ms; the candidate is ahead on "
                  f"{sum(v > 0 for _, v in wb)} of {len(wb)} files.", '',
                  '**Caveat on the tone-bin score.** The reference tones are the scored segment\'s lines standing 10 dB above '
                  'their +-10 Hz median (chosen with hindsight). A line finder that uses a similar prominence rule causally '
                  'will tend to follow exactly those lines, so tone-bin gains flatter it. The whole-band score has no such bias.', '']
    lines += ['## All methods on the test recordings', '',
              '| Method | Tone bins median, 20 / 120 ms | Whole band median, 20 / 120 ms | Whole-band boosts | Third-octave boosts |',
              '|---|---:|---:|---:|---:|']
    for m in methods:
        r = rec[m]
        lines.append(f"| {label(m)} | {fmt(r['median_tone_bin_db']['20'])} / {fmt(r['median_tone_bin_db']['120'])} | "
                     f"{fmt(r['median_whole_band_db']['20'], 2)} / {fmt(r['median_whole_band_db']['120'], 2)} | "
                     f"{len(r['whole_band_boosts'])} | {len(r['third_octave_boosts'])} |")
    key = [m for m in methods if m in ('v2_gated', 'prefix_ar', 'online_ar') or (m.endswith('_gated') and m != 'v2_gated')]
    lines += ['', '## Per recording: tone bins (dB, 20 / 120 ms)', '', per_file_table(result['recordings'], key, 'tone_band_gain_db'),
              '', '## Per recording: whole band (dB, 20 / 120 ms)', '', per_file_table(result['recordings'], key, 'band_gain_db'),
              '', '## Boosts on the test recordings', '']
    for m in methods:
        r = rec[m]
        items = ([f"whole band {x['band_gain_db']:.2f} dB on {x['file']} at {x['horizon_start_ms']:g} ms" for x in r['whole_band_boosts']]
                 + [f"{x['bands_over_1db']} third-octave band(s) up to +{x['max_change_db']:.1f} dB on {x['file']} at "
                    f"{x['horizon_start_ms']:g} ms" for x in r['third_octave_boosts']])
        lines.append(f"- {label(m)}: " + ('; '.join(items) if items else 'none'))
    lines += ['', '## Synthetic test scenes', '',
              '| Method | Objective (dB) | Windows < -0.5 dB | Late whole band, mean / min (dB) | Late windows < -0.5 dB | Late tone bins, median (dB) |',
              '|---|---:|---:|---:|---:|---:|']
    for m in methods:
        s = syn[m]
        lines.append(f"| {label(m)} | {fmt(s['mean_objective_db'], 2)} | "
                     f"{s['windows_below_minus_half_db'] if s['windows_below_minus_half_db'] is not None else '—'} | "
                     f"{fmt(s['late_mean_whole_band_db'], 2)} / {fmt(s['late_min_whole_band_db'], 2)} | "
                     f"{s['late_whole_band_below_minus_half_db']} | {fmt(s['late_median_tone_bin_db'])} |")
    lines += ['', 'By family (mean objective dB / late whole band dB):', '',
              '| Method | '+' | '.join(fams)+' |', '|---|'+'---:|'*len(fams)]
    for m in methods:
        lines.append(f'| {label(m)} | '+' | '.join(f"{fmt(fams[f][m]['mean_objective_db'], 2)} / {fmt(fams[f][m]['late_mean_whole_band_db'], 2)}"
                                                    for f in fams)+' |')
    names = [m['name'] for m in protocol['comparators']+protocol.get('ablations', [])+([cand] if cand else [])]
    lines += ['', '## Compute time', '',
              'Offline Python, one thread per process, measured while the test ran in a parallel pool (so slower than a quiet '
              'machine). "Own" excludes the tone-selector update that v2 also runs. One block is 10 ms of audio.', '',
              '| Method | Own ms per block, mean | Own p99, median over files | Own p99, worst file | Own worst block | ms per block incl. selector, mean |',
              '|---|---:|---:|---:|---:|---:|'] + timing_rows(result, names)
    quiet = Path(study)/'timing-quiet-01.json'
    if quiet.exists():
        q = json.loads(quiet.read_text(encoding='utf-8'))
        lines += ['', f"Quiet machine, one process, one thread, after the test (`{quiet.name}`): {q['seconds_of_audio']:.0f} s of "
                  f"the development recording {q['file']} ({q['blocks']} blocks).", '',
                  '| Method | Own ms per block: mean / p99 / p99.9 / worst | Including the selector: mean / p99 / worst | Blocks over 10 ms incl. selector | Faster than real time |',
                  '|---|---:|---:|---:|---:|']
        for m, t in q['methods'].items():
            if 'own_ms_mean' in t:
                lines.append(f"| {m} | {t['own_ms_mean']:.2f} / {t['own_ms_p99']:.2f} / {t['own_ms_p999']:.2f} / {t['own_ms_max']:.1f} | "
                             f"{t['with_selector_ms_mean']:.2f} / {t['with_selector_ms_p99']:.2f} / {t['with_selector_ms_max']:.1f} | "
                             f"{t['blocks_over_10ms_with_selector']} | {t['real_time_factor']:.0f}x |")
        worst = max(t['own_ms_max'] for t in q['methods'].values() if 'own_ms_max' in t)
        lines += ['', 'The selector update (every 0.25 s) is the same work v2 does today and causes the slow blocks in both rows; '
                  f"the forecaster's own share peaks at {worst:.1f} ms in a 10 ms block. For comparison, v2's own refit costs "
                  f"{q['methods']['v2']['forecast_ms_per_origin']:.2f} ms per block on the same file."]
    lines += ['', f"Runtime: {result['runtime_seconds']/60:.1f} minutes. Created {result['created_utc']}.", '',
              f"Numbers: `{amendment['test_output'] if amendment else 'test'}/test.json`. Frozen protocol: `protocol.json`"
              + (f" with `{amendment['name']}.json`" if amendment else '') + '. Split: `split.json`.']
    (Path(study)/'REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
