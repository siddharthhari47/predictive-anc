"""Audit and summarize saved held-out scores without rerunning models or changing choices."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(r"C:\Users\talk2.000\Desktop\Claude\predictive-anc")
OUT = Path(r"C:\Users\talk2.000\Documents\Codex\2026-10-15\referenced-chatgpt-conversation-this-is-an\outputs\anc-studies-20261020")
sys.path.insert(0, str(ROOT))
from anc_lab.forecaster_report import paired, sign_test_p
from anc_lab.forecaster_study_05 import CHANGE_SCENES


def dump(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write('\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fmt(value, places=2):
    return 'not available' if value is None else f'{value:.{places}f}'


def main(study):
    folder = ROOT/f'results-tone-forecaster-{study}'
    source = folder/'test/test.json'
    r = json.loads(source.read_text(encoding='utf-8'))
    protocol = json.loads((folder/'protocol.json').read_text(encoding='utf-8'))
    assert r['protocol'] == protocol
    for name, expected in protocol['code_sha256'].items():
        assert digest(ROOT/'anc_lab'/name) == expected, name
    c = protocol['frozen_candidate']['name']+'_gated'
    labels = {'zero':'Predict nothing', 'v2_gated':'v2 (current engine)', 'joint_gated':'Joint check',
              c:'Frozen fade candidate', 'prefix_ar':'Prefix-adapted AR', 'online_ar':'Online AR'}
    stats = {}
    checks = []
    for name, label in labels.items():
        summary = r['summary']['fresh'][name]
        scores = [s for file in r['fresh_recordings'] for s in file['scores'] if s['method'] == name]
        tonal = [s['tone_band_gain_db'] for file in r['fresh_recordings']
                 if file['reference_tones_hz'] and not file['electrical_not_acoustic']
                 for s in file['scores'] if s['method']==name and s['horizon_start_ms']==20]
        tb = sum(s['third_octave_boosts_over_1db']>0 for s in scores)
        wb = sum(s['band_gain_db']<-.5 for s in scores)
        assert tb == len(summary['third_octave_boosts'])
        assert wb == len(summary['whole_band_boosts'])
        median = statistics.median(tonal) if tonal else None
        saved = summary['median_tone_bin_db']['20']
        assert median == saved or (median is not None and math.isclose(median,saved,abs_tol=1e-12))
        late = [s for sc in r['scenes'] for s in sc['late_window_scores'] if s['method']==name]
        late_boosts = sum(s['third_octave_boosts_over_1db']>0 for s in late)
        assert late_boosts==r['summary']['synthetic'][name]['late_third_octave_boosts']
        change = sum(s['third_octave_boosts_over_1db']>0 for sc in r['scenes']
                     if sc['scene'].split('#')[0] in CHANGE_SCENES for s in sc['late_window_scores'] if s['method']==name)
        stats[name] = {'label':label, 'tone_median_20ms_db':median,
                       'tone_median_120ms_db':summary['median_tone_bin_db']['120'],
                       'whole_band_median_20ms_db':summary['median_whole_band_db']['20'],
                       'whole_band_median_120ms_db':summary['median_whole_band_db']['120'],
                       'recording_band_boost_cases':tb, 'recording_whole_band_boost_cases':wb,
                       'synthetic_late_band_boost_cases':late_boosts, 'change_late_band_boost_cases':change,
                       'tone_files':summary['tone_files'], 'recording_case_count':len(scores),
                       'worst_recording_band_amplification_db':max(s['max_third_octave_change_db'] for s in scores),
                       'worst_recording_whole_band_gain_db':min(s['band_gain_db'] for s in scores)}
        checks.append(name)
    a, j, b = (stats[x] for x in (c,'joint_gated','v2_gated'))
    if study == '04':
        primary = {'fewer_synthetic_late_boosts_and_no_more_recording_boosts':
                   a['synthetic_late_band_boost_cases'] < j['synthetic_late_band_boost_cases'] and
                   a['recording_band_boost_cases'] <= j['recording_band_boost_cases'],
                   'tone_gain_above_v2':a['tone_median_20ms_db'] is not None and b['tone_median_20ms_db'] is not None and
                   a['tone_median_20ms_db'] > b['tone_median_20ms_db']}
        from anc_lab.forecaster_report_04 import _answer
        official = _answer(r['summary']['fresh'],r['summary']['synthetic'],c)
        assert list(primary.values())==list(official[:2])
    else:
        primary = {'fewer_change_boosts':a['change_late_band_boost_cases'] < j['change_late_band_boost_cases'],
                   'no_more_recording_boosts':a['recording_band_boost_cases'] <= j['recording_band_boost_cases'] and
                   a['recording_whole_band_boost_cases'] <= j['recording_whole_band_boost_cases'],
                   'tone_gain_above_v2':a['tone_median_20ms_db'] is not None and b['tone_median_20ms_db'] is not None and
                   a['tone_median_20ms_db'] > b['tone_median_20ms_db']}
        from anc_lab.forecaster_report_05 import answer
        assert primary == answer(r,c)[0]
    comparisons = {}
    for other in ('joint_gated','v2_gated'):
        differences = paired(r['fresh_recordings'],c,other,20.,'tone_band_gain_db')
        wins=sum(v>0 for _,v in differences);losses=sum(v<0 for _,v in differences)
        comparisons[other]={'wins':wins,'losses':losses,'ties':len(differences)-wins-losses,
                             'two_sided_sign_test_p':sign_test_p(wins,losses), 'file_differences_db':differences}
    audit = {'study':study,'reviewed_utc':datetime.now(timezone.utc).isoformat(), 'candidate':c,
             'all_frozen_questions_pass':all(primary.values()), 'primary_questions':primary,
             'metrics':stats,'paired_tone_comparisons_20ms':comparisons,
             'fresh_files':r['fresh_files'],'fresh_missing':r['fresh_missing'],'synthetic_scenes':len(r['scenes']),
             'runtime_seconds':r['runtime_seconds'],'test_json_sha256':digest(source),
             'protocol_sha256':digest(folder/'protocol.json'), 'summary_recomputed_from_saved_scores_for':checks,
             'models_rerun':False,'engine_changed':False,'claim':'Reference-microphone waveform prediction only; not measured ANC.'}
    dump(folder/'CODEX_REVIEW.json',audit)
    OUT.mkdir(parents=True,exist_ok=True)
    dump(OUT/f'study-{study}-review.json',audit)
    lines = [f'# Study {study}: frozen offline result', '',
             f"**Frozen criteria: {'passed' if all(primary.values()) else 'not all passed'}.** "
             f"Candidate: `{c}`. Reference-microphone prediction only; no playback or ear-level measurement.", '',
             f"{len(r['fresh_files'])} fresh recordings; {len(r['scenes'])} fresh synthetic scenes; "
             f"{a['tone_files']} acoustic recordings with reference tones. Missing files: {r['fresh_missing'] or 'none'}. "
             f"The unchanged frozen test ran once in {r['runtime_seconds']/60:.2f} minutes.", '',
             '## Frozen questions', '']
    lines.extend(f"- {key.replace('_',' ')}: **{'yes' if ok else 'no'}**." for key,ok in primary.items())
    lines += ['', '## Fresh-recording evidence', '',
              '| Method | Tone bins, 20 / 120 ms (dB) | Whole band, 20 / 120 ms (dB) | Band boosts | Whole-band boosts |',
              '|---|---:|---:|---:|---:|']
    for v in stats.values():
        lines.append(f"| {v['label']} | {fmt(v['tone_median_20ms_db'])} / {fmt(v['tone_median_120ms_db'])} | "
                     f"{fmt(v['whole_band_median_20ms_db'])} / {fmt(v['whole_band_median_120ms_db'])} | "
                     f"{v['recording_band_boost_cases']} | {v['recording_whole_band_boost_cases']} |")
    lines += ['', 'Band boosts count recording-by-horizon cases with at least one third-octave band amplified by 1 dB or more; '
              'whole-band boosts use a greater-than-0.5 dB amplification threshold. Each file contributes two cases '
              '(20 and 120 ms). Positive prediction gain means reduced reference-waveform error; it is not measured sound reduction at an ear.', '',
              '## Fresh synthetic evidence', '',
              '| Method | All late band boosts | Sudden-change late band boosts |', '|---|---:|---:|']
    for v in stats.values():
        lines.append(f"| {v['label']} | {v['synthetic_late_band_boost_cases']} | {v['change_late_band_boost_cases']} |")
    lines += ['', '## Uncertainty and integrity', '']
    for name, comp in comparisons.items():
        lines.append(f"- Against {labels[name]}, at 20 ms on paired tonal files: {comp['wins']} wins, {comp['losses']} losses, "
                     f"{comp['ties']} ties; exact two-sided sign-test p={fmt(comp['two_sided_sign_test_p'],3)}.")
    lines += ['- These are small, purposively selected samples. Reference tones are located with hindsight for scoring; '
              'that does not feed future data to the causal predictors, but it can flatter tone-focused metrics.',
              '- This review recounts boosts and recomputes medians from saved scores; it does not rerun the predictors, '
              'retune a candidate or replace any held-out recording.',
              '- Timing during a multiprocessing offline run is not a quiet-machine real-time qualification. The live engine remains v2.', '',
              f"[Full frozen report]({(folder/'REPORT.md').as_posix()}) · [Audit]({(OUT/f'study-{study}-review.json').as_posix()})"]
    content='\n'.join(lines)+'\n'
    for target in (folder/'CODEX_REVIEW.md',OUT/f'study-{study}-review.md'):
        with target.open('x',encoding='utf-8',newline='\n') as f:f.write(content)
    print(json.dumps({k:audit[k] for k in ('study','all_frozen_questions_pass','primary_questions','metrics')},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('study',choices=['04','05']);main(parser.parse_args().study)
