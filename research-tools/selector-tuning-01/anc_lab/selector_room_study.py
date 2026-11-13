"""Frozen, coverage-first test of fixed tuning through L2 predictor switches."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import numpy as np
from threadpoolctl import threadpool_limits
from . import selector_headroom as h
from . import antihum_study as room
from . import selector_room_baseline as baseline
from .selector_stream_profile import cached_dpss
from .selector_room_stream import stream, switch_events, save_trace_fields, load_trace_fields
from .selector_room_scoring import score, summarize

ROOT = h.ROOT
STUDY = ROOT/'results-selector-tuning-01'
SUPPLEMENT = [5, 10, 18, 21, 23, 25, 26, 35]


def freeze():
    original = baseline.verified()
    assert h.read(baseline.STUDY/'results.json')['passed']
    alignment = ROOT/'results-selector-room-alignment-01'
    assert h.read(alignment/'results.json')['passed']
    for name, digest in h.read(alignment/'protocol.json')['code_sha256'].items():
        assert h.sha(ROOT/name) == digest, name
    old_names = h.read(baseline.OLD/'protocol.json')['recordings']
    old = [{**c, 'source_id': f'old-{old_names.index(c["file"]):03d}',
            'case_id': f'old-{old_names.index(c["file"]):03d}-r{c["room_index"]}',
            'cohort': 'original48', 'old_index': i,
            'source_path': str((baseline.AUDIO/c['file']).relative_to(ROOT)),
            'source_sha256': original['source_sha256'][c['file']]}
           for i, c in enumerate(original['cases'])]
    fresh = {c['id']: c for c in h.read(ROOT/'results-selector-fresh-01/test/results.json')['cases']}
    draws = np.random.SeedSequence(20261022).spawn(3*len(SUPPLEMENT))
    extra = []
    for i, number in enumerate(SUPPLEMENT):
        c = fresh[f'fresh-{number:03d}']
        for k in range(3):
            extra.append({'source_id': c['id'], 'case_id': f'{c["id"]}-r{k}', 'file': c['title'],
                'cohort': 'switch_enriched_seen', 'room_index': k,
                'seed': int(draws[3*i+k].generate_state(1)[0]),
                'source_path': c['arrays_path'], 'source_sha256': c['arrays_sha256'],
                'reference_tones_hz': c['reference_tones_hz']})
    code = dict(h.read(ROOT/'results-selector-components-01/protocol.json')['code_sha256'])
    for name in ('selector_room_study.py', 'selector_room_stream.py', 'selector_room_scoring.py',
                 'selector_room_baseline.py', 'selector_room_alignment.py', 'antihum_study.py',
                 'antihum.py', 'tuning.py', 'real_hum_study.py'):
        code['anc_lab/'+name] = h.sha(ROOT/'anc_lab'/name)
    for name in ('tests/test_selector_room_stream.py', 'tests/test_selector_room_scoring.py', 'docs/SELECTOR_ROOM_TEST.md'):
        code[name] = h.sha(ROOT/name)
    p = {'created_utc': datetime.now(timezone.utc).isoformat(), 'client_date': '2026-10-22',
         'kind': 'seen_data_simulated_ear_fixed_tuning_integration', 'code_sha256': code,
         'original_cases': old, 'conditional_supplement_cases': extra,
         'baseline_results_sha256': h.sha(baseline.STUDY/'results.json'),
         'alignment_results_sha256': h.sha(alignment/'results.json'),
         'fresh_protocol_sha256': h.sha(ROOT/'results-selector-fresh-01/protocol.json'),
         'lead_ms': {'primary': 30, 'exploratory': 200},
         'decision_stream': 'Original hard-gated 20/120 ms groups; 2 s completed-error L2, 1 dB margin, 100 ms fade, 3 s start floor. Native live origins seen-1 and common x[0] input. Primary output 30 ms uses group 20; exploratory output 200 ms uses group 120.',
         'rendering': 'Exact native per-tone renderer: no DC, each arm gate ramps over the block before L2 sample weights mix. Same prefix tone menu and native tuning seed in every arm. Untuned frequencies remain silent.',
         'coverage': 'Before any new ear score, count suffix transitions and command exposure at each lead. Primary requires >=6 distinct sources with at least one nonzero matched-tone command transition and complete +/-100 ms scoring window. If original48 has fewer, append ALL 24 fixed supplemental rooms once; no further source selection. Preserve original48 and enriched results separately.',
         'arms': ['zero', 'v2_tuned', 'chooser_reuse_v2', 'chooser_tuned', 'noncausal_unclipped_linear_retune_bound'],
         'primary_arm': 'chooser_reuse_v2', 'listener_sigma_db': 1.,
         'tuning': 'Original first-40% prefix and warmup, loop only within prefix; identical initial seeds, per-method fixed settings over entire suffix. Retune bound explicitly noncausal and excluded from pass criteria.',
         'score_start': 'prefix + 0.5 seconds; all available suffix, no crop selection',
         'noninferiority': {'aggregate': 'Mean rooms within each source, then equal source weights; tonal metrics use existing reference tone definitions; no-tone rooms remain in all harm counts.',
            'mean_margin_db': -.5, 'source_margin_db': -1., 'bootstrap': '20,000 source resamples, seed 20261022, two-sided 95% percentile interval; lower bound >= -0.5 required for a pass',
            'bands': 'No new room/source/third-octave amplification >1 dB where v2 <=1 dB; no new 35-350 Hz amplification >0.5 dB',
            'switches': 'Every complete +/-100 ms window around first arriving command of a suffix switch: 35-350 Hz residual power no more than +3 dB over simultaneous v2. Report all windows and missing/boundary cases. This is not an audibility threshold.',
            'clipping': 'No increase in clipped fraction above v2 by more than 1e-6',
            'insufficient_coverage': 'Inconclusive, with observed harms still fully reported; never safe'},
         'secondary_reference': 'Hard-gated DC-inclusive unweighted forecasts at exact output leads, measured at simulated microphone only, separate from ear scores.',
         'oracle': 'Unconstrained per-tone complex coefficients at each suffix switch, jointly fit to future band-filtered ear residual. Retains acoustic/filter transients; ignores cap. Upper bound only for the specified unclipped linear family, not implementable listener tuning.',
         'workers': 2, 'unit_checks': 5,
         'development_notes': ['Synthetic oracle control first exposed an incorrect post-filter coefficient model; corrected before freeze to place segment settings before the filters and fit segments jointly. All five targeted checks pass.'],
         'limits': 'Seen sources and synthetic modal rooms, no physical SPL, leakage or Bluetooth jitter measurement; 200 ms exploratory. No quiet timing claim and no engine promotion.'}
    STUDY.mkdir(exist_ok=False)
    h.write_new(STUDY/'protocol.json', p)
    h.write_new(STUDY/'frozen.json', {'sha256': h.sha(STUDY/'protocol.json')})
    print(json.dumps({'protocol_sha256': h.sha(STUDY/'protocol.json'), 'original_cases': 48, 'conditional_cases': 24}))


def verified():
    p = h.read(STUDY/'protocol.json')
    assert h.sha(STUDY/'protocol.json') == h.read(STUDY/'frozen.json')['sha256']
    for name, digest in p['code_sha256'].items():
        assert h.sha(ROOT/name) == digest, name
    assert h.sha(baseline.STUDY/'results.json') == p['baseline_results_sha256']
    assert h.sha(ROOT/'results-selector-room-alignment-01/results.json') == p['alignment_results_sha256']
    return p


def preparation_task(entry):
    path = ROOT/entry['source_path']
    assert h.sha(path) == entry['source_sha256']
    with threadpool_limits(limits=1), cached_dpss(True):
        if entry['cohort'] == 'original48':
            geometry, scene, rng = room.build_scene(path, entry['seed'])
        else:
            with np.load(path) as a:
                dry = a['reference'].copy()
            rng = np.random.default_rng(entry['seed'])
            geometry = room.draw_room(rng)
            scene = room.prepare_scene(dry, geometry, int(rng.integers(1 << 30)))
        trace = stream(scene['mic'], h.read(ROOT/'results-selector-fresh-01/protocol.json'))
    for key in scene['arrays']:
        np.testing.assert_allclose(trace['v2'][key], scene['arrays'][key], rtol=1e-8, atol=1e-9, equal_nan=True)
    seeds = {str(int(lead)): {str(float(sigma)): int(rng.integers(1 << 30))
             for sigma in room.PROTOCOL['tuning']['listener_sigma_db']} for lead in room.PROTOCOL['leads_ms']}
    switches, prefix_switches = {}, {}
    for g, lead_ms in enumerate((30, 200)):
        switches[str(lead_ms)] = switch_events(trace, lead_ms/1000, scene['prefix'], scene['n'], scene['unreported'],
                                               [t['frequency'] for t in scene['tones']])
        changed = np.flatnonzero(np.diff(trace['selected'][:, g], prepend=0) != 0)
        arrival = trace['v2']['seen'][changed]-1+round(lead_ms*2)+scene['unreported']
        prefix_switches[str(lead_ms)] = int(np.sum((arrival >= scene['warm']) & (arrival < scene['prefix'])))
    stem = STUDY/'cache'/entry['case_id']
    np.savez_compressed(stem.with_suffix('.npz'), mic=scene['mic'], ear=scene['ears'][0],
                        earphone_b=scene['earphone'][0], earphone_a=scene['earphone'][1], **save_trace_fields(trace))
    metadata = {**entry, 'geometry': geometry, 'tones': scene['tones'],
                **{key: scene[key] for key in ('prefix', 'n', 'warm', 'earphone_gain', 'unreported')},
                'tuning_seeds': seeds, 'switches': switches, 'prefix_switches': prefix_switches,
                'cache_path': str(stem.with_suffix('.npz').relative_to(ROOT)),
                'cache_sha256': h.sha(stem.with_suffix('.npz')), 'v2_trace_matches_original': True}
    metadata = json.loads(json.dumps(metadata, default=room._jsonable))
    h.write_new(stem.with_suffix('.json'), metadata)
    return {'case_id': entry['case_id'], 'source_id': entry['source_id'], 'cohort': entry['cohort'],
            'metadata_path': str(stem.with_suffix('.json').relative_to(ROOT)),
            'metadata_sha256': h.sha(stem.with_suffix('.json')),
            'switches': switches, 'prefix_switches': prefix_switches, 'prefix_tones': len(scene['tones'])}


def coverage_summary(rows):
    out = {}
    for lead in ('30', '200'):
        switched, exposed = set(), set()
        total, qualifying, incomplete = 0, 0, 0
        for row in rows:
            events = row['switches'][lead]
            if events:
                switched.add(row['source_id'])
            for e in events:
                total += 1
                incomplete += not e['complete_200ms_window']
                if e['command_exposed'] and e['complete_200ms_window']:
                    qualifying += 1
                    exposed.add(row['source_id'])
        out[lead] = {'sources_with_decisions': len(switched), 'exposed_complete_sources': len(exposed),
                     'source_ids': sorted(exposed), 'total_switches': total, 'qualifying_switches': qualifying,
                     'incomplete_windows': incomplete}
    return out


def coverage():
    p = verified()
    (STUDY/'cache').mkdir(exist_ok=False)
    h.write_new(STUDY/'coverage-start.json', {'started_utc': datetime.now(timezone.utc).isoformat(),
                                           'protocol_sha256': h.sha(STUDY/'protocol.json')})
    rows = []
    def prepare(entries):
        with ProcessPoolExecutor(p['workers']) as pool:
            futures = [pool.submit(preparation_task, e) for e in entries]
            for future in as_completed(futures):
                row = future.result()
                rows.append(row)
                print(json.dumps({'prepared': len(rows), 'case': row['case_id'],
                                  'suffix_decisions_30': len(row['switches']['30'])}), flush=True)
    prepare(p['original_cases'])
    original = coverage_summary(rows)
    h.write_new(STUDY/'original-coverage.json', {'summary': original, 'cases': sorted(rows, key=lambda r:r['case_id'])})
    supplement = original['30']['exposed_complete_sources'] < 6
    if supplement:
        print('Fixed supplement triggered before any candidate ear score', flush=True)
        prepare(p['conditional_supplement_cases'])
    outcome = {'created_utc': datetime.now(timezone.utc).isoformat(), 'original_summary': original,
               'summary': coverage_summary(rows), 'supplement_triggered': supplement,
               'cases': sorted(rows, key=lambda r:r['case_id']), 'ear_scoring_started': False}
    h.write_new(STUDY/'coverage.json', outcome)
    h.write_new(STUDY/'score-freeze.json', {'created_utc': datetime.now(timezone.utc).isoformat(),
        'protocol_sha256': h.sha(STUDY/'protocol.json'), 'coverage_sha256': h.sha(STUDY/'coverage.json'),
        'code_sha256': p['code_sha256'], 'included_cases': [r['case_id'] for r in outcome['cases']]})
    print(json.dumps({k:v for k,v in outcome.items() if k != 'cases'}, indent=2))


def load_case(receipt):
    meta_path = ROOT/receipt['metadata_path']
    assert h.sha(meta_path) == receipt['metadata_sha256']
    m = h.read(meta_path)
    path = ROOT/m['cache_path']
    assert h.sha(path) == m['cache_sha256']
    with np.load(path) as a:
        trace = load_trace_fields(a)
        scene = {'mic': a['mic'].copy(), 'ears': [a['ear'].copy()], 'trace': trace,
                 'arrays': trace['v2'], 'earphone': (a['earphone_b'].copy(), a['earphone_a'].copy())}
    scene.update({k: m[k] for k in ('prefix', 'n', 'warm', 'earphone_gain', 'unreported')})
    tones = []
    for t in m['tones']:
        tone = dict(t)
        for k in ('ear_over_mic', 'w_unit_earphone', 'w'):
            tone[k] = complex(*tone[k])
        tones.append(tone)
    scene['tones'] = tones
    return scene, m


def score_task(receipt):
    scene, metadata = load_case(receipt)
    with threadpool_limits(limits=1):
        outcome = score(scene, metadata)
    checked = 0
    if metadata['cohort'] == 'original48':
        old = h.read(baseline.STUDY/'cases'/f'{metadata["old_index"]:03d}.json')
        for lead in (30, 200):
            expected = next(r for r in old['rows'] if r['arm'] == 'tuned_sigma_1' and r['lead_ms'] == lead and r['move_cm'] == 0 and r['drift_ms'] == 0)
            actual = next(r for r in outcome['rows'] if r['arm'] == 'v2_tuned' and r['lead_ms'] == lead)
            for key, value in actual.items():
                if key in expected and key not in ('arm',):
                    if value is None:
                        assert expected[key] is None, key
                    else:
                        assert np.isclose(value, expected[key], rtol=1e-8, atol=1e-9), (metadata['case_id'], lead, key, value, expected[key])
                    checked += 1
            expected_tuning = [{k:v for k,v in r.items() if k not in ('file', 'room', 'lead_ms', 'sigma_db')}
                               for r in old['tuning'] if r['lead_ms'] == lead and r['sigma_db'] == 1.]
            actual_tuning = next(r['v2_tuning'] for r in outcome['details'] if r['lead_ms'] == lead)
            checked += len(baseline.compare(actual_tuning, expected_tuning))
    result = {k: metadata[k] for k in ('case_id', 'source_id', 'cohort', 'file', 'room_index')}
    result.update(outcome)
    result['v2_original_comparisons'] = checked
    result['prefix_switches'] = metadata['prefix_switches']
    h.write_new(STUDY/'scores'/(metadata['case_id']+'.json'), result)
    return result


def run_scores():
    p = verified()
    seal = h.read(STUDY/'score-freeze.json')
    assert h.sha(STUDY/'coverage.json') == seal['coverage_sha256']
    assert h.sha(STUDY/'protocol.json') == seal['protocol_sha256']
    coverage = h.read(STUDY/'coverage.json')
    assert [r['case_id'] for r in coverage['cases']] == seal['included_cases']
    (STUDY/'scores').mkdir(exist_ok=False)
    h.write_new(STUDY/'scoring-start.json', {'started_utc': datetime.now(timezone.utc).isoformat(), 'score_freeze_sha256': h.sha(STUDY/'score-freeze.json')})
    cases = []
    with ProcessPoolExecutor(p['workers']) as pool:
        futures = [pool.submit(score_task, c) for c in coverage['cases']]
        for future in as_completed(futures):
            cases.append(future.result())
            print(json.dumps({'scored': len(cases), 'of': len(coverage['cases']), 'case': cases[-1]['case_id']}), flush=True)
    cases.sort(key=lambda c:c['case_id'])
    result = {'kind': p['kind'], 'label': 'SIMULATED EAR ATTENUATION; seen sources, not physical ANC',
              'completed_utc': datetime.now(timezone.utc).isoformat(), 'protocol_sha256': h.sha(STUDY/'protocol.json'),
              'coverage': coverage['summary'], 'summary': summarize(cases, coverage['summary']),
              'original_only': summarize([c for c in cases if c['cohort'] == 'original48'], coverage['original_summary']),
              'v2_original_comparisons': sum(c['v2_original_comparisons'] for c in cases), 'cases': cases}
    h.write_new(STUDY/'results.json', result)
    print(json.dumps({lead: {arm: {k:v for k,v in out.items() if k in ('mean_paired_db', 'bootstrap95', 'decision', 'worst_source_mean_db', 'maximum_switch_excess_db')}
                           for arm, out in arms.items()} for lead, arms in result['summary'].items()}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['freeze', 'coverage', 'score'])
    args = parser.parse_args()
    {'freeze': freeze, 'coverage': coverage, 'score': run_scores}[args.stage]()
