"""Reproduce the original 48 simulated rooms without changing historical output."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import numbers
import numpy as np

from . import antihum_study as room
from . import selector_headroom as h

ROOT = h.ROOT
STUDY = ROOT/'results-selector-room-baseline-01'
OLD = ROOT/'results-tune-by-ear-sim-01'
AUDIO = ROOT/'external-audio/wikimedia-commons-2026-10-16'


def compare(actual, expected, path='', errors=None):
    errors = {} if errors is None else errors
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys(), path
        for key in expected:
            if key in ('seconds', 'engine_ms_per_block'):
                continue
            compare(actual[key], expected[key], path+'/'+key, errors)
    elif isinstance(expected, list):
        assert len(actual) == len(expected), path
        for i, (a, b) in enumerate(zip(actual, expected)):
            compare(a, b, path+'/'+str(i), errors)
    elif isinstance(expected, numbers.Real) and not isinstance(expected, bool):
        assert np.isclose(actual, expected, rtol=1e-8, atol=1e-9), (path, actual, expected)
        errors[path] = abs(float(actual)-float(expected))
    else:
        assert actual == expected, (path, actual, expected)
    return errors


def freeze():
    old = h.read(OLD/'tune_by_ear.json')
    records = [{'file': name} for name in h.read(OLD/'protocol.json')['recordings']]
    seeds = room.case_seeds(records)
    names = sorted(set(c['file'] for c in old['cases']))
    assert len(old['cases']) == 48 and len(names) == 16
    source_hashes = {name: h.sha(AUDIO/name) for name in names}
    STUDY.mkdir(exist_ok=False)
    code = ['selector_room_baseline.py', 'antihum_study.py', 'antihum.py', 'tuning.py',
            'predictors.py', 'tone_selection.py', 'real_hum_study.py']
    p = {'kind': 'original_room_baseline_reproduction', 'created_utc': datetime.now(timezone.utc).isoformat(),
         'original_protocol_sha256': h.sha(OLD/'protocol.json'), 'original_results_sha256': h.sha(OLD/'tune_by_ear.json'),
         'code_sha256': {f'anc_lab/{name}': h.sha(ROOT/'anc_lab'/name) for name in code},
         'source_sha256': source_hashes,
         'cases': [{'file': c['file'], 'room_index': c['room_index'], 'seed': seeds[c['file'], c['room_index']],
                    'reference_tones_hz': c['reference_tones_hz']} for c in old['cases']],
         'parity': {'atol': 1e-9, 'rtol': 1e-8, 'exclude': ['seconds', 'engine_ms_per_block'],
                    'scope': 'Every saved scalar, room, tuning summary and metric, except elapsed times'},
         'workers': 2, 'safety': 'Pure offline original simulator; no audio device, output overwrite or candidate ear score.'}
    h.write_new(STUDY/'protocol.json', p)
    h.write_new(STUDY/'frozen.json', {'sha256': h.sha(STUDY/'protocol.json')})
    print(json.dumps({'protocol_sha256': h.sha(STUDY/'protocol.json'), 'cases': 48}))


def verified():
    p = h.read(STUDY/'protocol.json')
    assert h.sha(STUDY/'protocol.json') == h.read(STUDY/'frozen.json')['sha256']
    for name, digest in p['code_sha256'].items():
        assert h.sha(ROOT/name) == digest, name
    assert h.sha(OLD/'protocol.json') == p['original_protocol_sha256']
    assert h.sha(OLD/'tune_by_ear.json') == p['original_results_sha256']
    return p


def task(item):
    i, entry, expected, digest = item
    path = AUDIO/entry['file']
    assert h.sha(path) == digest
    output = room._task((str(path), {'file': entry['file'], 'reference_tones_hz': entry['reference_tones_hz']},
                         entry['room_index'], entry['seed']))
    errors = compare(output, expected)
    h.write_new(STUDY/'cases'/f'{i:03d}.json', output)
    receipt = {'index': i, 'file': entry['file'], 'room_index': entry['room_index'], 'passed': True,
               'compared_numeric_scalars': len(errors), 'max_absolute_error': max(errors.values(), default=0.),
               'output_sha256': h.sha(STUDY/'cases'/f'{i:03d}.json')}
    h.write_new(STUDY/'cases'/f'{i:03d}-parity.json', receipt)
    return receipt


def run():
    p = verified()
    (STUDY/'cases').mkdir(exist_ok=False)
    h.write_new(STUDY/'start.json', {'started_utc': datetime.now(timezone.utc).isoformat()})
    old = h.read(OLD/'tune_by_ear.json')['cases']
    jobs = [(i, e, old[i], p['source_sha256'][e['file']]) for i, e in enumerate(p['cases'])]
    rows = []
    with ProcessPoolExecutor(p['workers']) as pool:
        futures = [pool.submit(task, item) for item in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            print(json.dumps({'completed': len(rows), 'of': len(jobs), **rows[-1]}), flush=True)
    result = {'passed': True, 'cases': len(rows), 'sources': len(p['source_sha256']),
              'compared_numeric_scalars': sum(r['compared_numeric_scalars'] for r in rows),
              'max_absolute_error': max(r['max_absolute_error'] for r in rows),
              'completed_utc': datetime.now(timezone.utc).isoformat(), 'receipts': sorted(rows, key=lambda r:r['index'])}
    h.write_new(STUDY/'results.json', result)
    print(json.dumps({k:v for k,v in result.items() if k != 'receipts'}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['freeze', 'run'])
    args = parser.parse_args()
    {'freeze': freeze, 'run': run}[args.stage]()
