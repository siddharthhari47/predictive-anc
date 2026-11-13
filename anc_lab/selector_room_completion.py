"""Preserved-protocol completion with an explicit pre-scoring null-value fix.

The original frozen runner and scorer stay byte-for-byte unchanged. Only the
name of the worst band for a completely muted command is restored to the
original baseline convention (None). No signal, power, decision or limit changes.
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import json

from . import selector_headroom as h
from . import selector_room_study as study
from . import selector_room_scoring as scoring

ROOT, STUDY = study.ROOT, study.STUDY
ORIGINAL_EVALUATE = scoring.evaluate
AMENDMENT = STUDY/'pre-scoring-amendment-01.json'


def muted_parity_evaluate(scene, settings, lead, method, reference_tones):
    metrics, on = ORIGINAL_EVALUATE(scene, settings, lead, method, reference_tones)
    if not any(s.gain > 0 for s in settings):
        # The old scorer names an arbitrary tied band for identical signals;
        # the historical zero-output shortcut correctly names no worst band.
        assert metrics['drive_peak'] == metrics['clipped_fraction'] == 0.
        assert metrics['max_third_octave_amplification_db'] == 0.
        metrics['worst_third_octave_hz'] = None
    return metrics, on


def freeze_amendment():
    study.verified()
    assert not (STUDY/'scores').exists()
    assert not (STUDY/'scoring-start.json').exists()
    coverage = h.read(STUDY/'coverage.json')
    seal = h.read(STUDY/'score-freeze.json')
    assert h.sha(STUDY/'coverage.json') == seal['coverage_sha256']
    names = ['anc_lab/selector_room_completion.py',
             'tests/test_selector_room_completion.py']
    receipt = {'created_utc': datetime.now(timezone.utc).isoformat(),
        'stage': 'after coverage; before any candidate ear scoring',
        'reason': 'Code inspection found that a muted command produced an arbitrary tied worst-band frequency, whereas the original baseline records null. Comparing the two would raise a type error.',
        'change': 'Call the frozen evaluator unchanged, then set only worst_third_octave_hz to null when all tone gains are nonpositive and output is exactly zero. Active-output metrics, signals, tuning, thresholds and source inclusion are unchanged.',
        'original_files_modified': [],
        'protocol_sha256': h.sha(STUDY/'protocol.json'),
        'coverage_sha256': h.sha(STUDY/'coverage.json'),
        'score_freeze_sha256': h.sha(STUDY/'score-freeze.json'),
        'original_code_sha256': seal['code_sha256'],
        'additional_code_sha256': {n: h.sha(ROOT/n) for n in names},
        'unit_check_log_sha256': h.sha(STUDY/'pre-scoring-checks.txt'),
        'included_cases': seal['included_cases'],
        'known_coverage_before_scoring': coverage['summary'],
        'outcome_access': 'No scores directory or scoring-start receipt exists; candidate ear outcomes have not been computed.'}
    h.write_new(AMENDMENT, receipt)
    h.write_new(STUDY/'pre-scoring-amendment-01-frozen.json', {'sha256': h.sha(AMENDMENT)})
    print(json.dumps({'amendment_sha256': h.sha(AMENDMENT), 'cases': len(seal['included_cases'])}))


def verified():
    p = study.verified()
    a = h.read(AMENDMENT)
    assert h.sha(AMENDMENT) == h.read(STUDY/'pre-scoring-amendment-01-frozen.json')['sha256']
    for name, digest in a['additional_code_sha256'].items():
        assert h.sha(ROOT/name) == digest, name
    for name, key in [('protocol.json', 'protocol_sha256'), ('coverage.json', 'coverage_sha256'),
                      ('score-freeze.json', 'score_freeze_sha256'),
                      ('pre-scoring-checks.txt', 'unit_check_log_sha256')]:
        assert h.sha(STUDY/name) == a[key], name
    assert a['original_code_sha256'] == p['code_sha256']
    coverage = h.read(STUDY/'coverage.json')
    assert [c['case_id'] for c in coverage['cases']] == a['included_cases']
    return p, coverage


def score_task(receipt):
    # Each spawned worker has its own module state. Restore it after each case.
    assert scoring.evaluate is ORIGINAL_EVALUATE
    scoring.evaluate = muted_parity_evaluate
    try:
        return study.score_task(receipt)
    finally:
        scoring.evaluate = ORIGINAL_EVALUATE


def run_scores():
    p, coverage = verified()
    (STUDY/'scores').mkdir(exist_ok=False)
    h.write_new(STUDY/'scoring-start.json', {
        'started_utc': datetime.now(timezone.utc).isoformat(),
        'score_freeze_sha256': h.sha(STUDY/'score-freeze.json'),
        'pre_scoring_amendment_sha256': h.sha(AMENDMENT)})
    cases = []
    with ProcessPoolExecutor(p['workers']) as pool:
        futures = [pool.submit(score_task, c) for c in coverage['cases']]
        for future in as_completed(futures):
            cases.append(future.result())
            print(json.dumps({'scored': len(cases), 'of': len(coverage['cases']),
                              'case': cases[-1]['case_id']}), flush=True)
    cases.sort(key=lambda c:c['case_id'])
    result = {'kind': p['kind'], 'label': 'SIMULATED EAR ATTENUATION; seen sources, not physical ANC',
        'completed_utc': datetime.now(timezone.utc).isoformat(),
        'protocol_sha256': h.sha(STUDY/'protocol.json'),
        'pre_scoring_amendment_sha256': h.sha(AMENDMENT),
        'coverage': coverage['summary'], 'summary': scoring.summarize(cases, coverage['summary']),
        'original_only': scoring.summarize([c for c in cases if c['cohort'] == 'original48'], coverage['original_summary']),
        'v2_original_comparisons': sum(c['v2_original_comparisons'] for c in cases), 'cases': cases}
    h.write_new(STUDY/'results.json', result)
    print(json.dumps({lead: {arm: {k:v for k,v in out.items() if k in
        ('mean_paired_db', 'bootstrap95', 'decision', 'worst_source_mean_db', 'maximum_switch_excess_db')}
        for arm, out in arms.items()} for lead, arms in result['summary'].items()}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['freeze', 'score'])
    args = parser.parse_args()
    {'freeze': freeze_amendment, 'score': run_scores}[args.stage]()
