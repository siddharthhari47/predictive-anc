"""Frozen reconstruction gate before any new fixed-tuning room simulation."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import numpy as np
from threadpoolctl import threadpool_limits

from . import selector_headroom as h
from . import selector_timing_study as timing
from .selector_components import ComponentForecastChain
from .selector_stream_profile import cached_dpss
from .antihum import ToneSetting
from .selection_study import BLOCK

ROOT = h.ROOT
STUDY = ROOT/'results-selector-components-01'


def freeze():
    original = timing.verified()
    STUDY.mkdir(exist_ok=False)
    hashes = dict(original['code_sha256'])
    for name in ('anc_lab/selector_components.py', 'anc_lab/selector_component_study.py',
                 'tests/test_selector_components.py', 'anc_lab/antihum.py', 'anc_lab/antihum_study.py'):
        hashes[name] = h.sha(ROOT/name)
    p = {'created_utc': datetime.now(timezone.utc).isoformat(), 'client_date': '2026-10-22',
         'kind': 'offline_component_reconstruction_not_ear_attenuation',
         'timing_protocol_sha256': h.sha(timing.STUDY/'protocol.json'),
         'code_sha256': hashes, 'cases': original['cases'], 'input_seconds': 30,
         'parity': {'atol': 1e-9, 'rtol': 1e-8, 'decisions': 'exact'},
         'coverage': {'rule': 'Report numerical parity separately. Exercised-switch coverage requires at least one chooser transition per horizon and at least one ghost frame in the fixed corpus. No replacement or longer crop after seeing results.',
                      'unit_controls': ['known different-frequency fade', 'zero arm', 'DC omitted from tone drive',
                                        'explicit block ramp', 'fast release', 'phase-reversed switching harm']},
         'horizons_samples': [[41, 60], [241, 260]],
         'mapping': 'At newest input sample origin, h=41..60 / 241..260. First synthesized samples are 20.5 / 120.5 ms after that origin. No interpolation or extrapolation to old room 30/200 ms leads.',
         'renderer': 'Reconstruction includes original hard gates and DC. Optional tone drive excludes DC and explicitly selects hard gates or block ramps. No tuned-room result or physical claim.',
         'unit_checks_before_freeze': {'passed': 4, 'seconds': .004,
             'development_note': 'A first check used zero absolute tolerance at a sine zero crossing; corrected to 1e-12 for a 1.78e-15 floating-point difference before freeze.'},
         'scope': 'Diagnostic refit exposes original v2 phasors; original bank components include ghosts/releases. Extra work is not the timed implementation and is not live integration.'}
    h.write_new(STUDY/'protocol.json', p)
    h.write_new(STUDY/'frozen.json', {'sha256': h.sha(STUDY/'protocol.json')})
    print(json.dumps({'protocol_sha256': h.sha(STUDY/'protocol.json'), 'sources': len(p['cases'])}))


def verified():
    p = h.read(STUDY/'protocol.json')
    assert h.sha(STUDY/'protocol.json') == h.read(STUDY/'frozen.json')['sha256']
    assert h.sha(timing.STUDY/'protocol.json') == p['timing_protocol_sha256']
    for name, digest in p['code_sha256'].items():
        assert h.sha(ROOT/name) == digest, name
    return p


def run():
    p = verified()
    stage = STUDY/'parity'
    stage.mkdir(exist_ok=False)
    h.write_new(stage/'start.json', {'started_utc': datetime.now(timezone.utc).isoformat(),
                                  'protocol_sha256': h.sha(STUDY/'protocol.json')})
    source_protocol = h.read(timing.FRESH/'protocol.json')
    rows = []
    for entry in p['cases']:
        x, origins, expected, expected_choices = timing.load(entry)
        output = {name: [] for name in expected}
        decisions = []
        errors = {name: 0.0 for name in expected}
        local_errors = dict(errors)
        drive_error = 0.0
        transitions = np.zeros(2, int)
        mixed_blocks = np.zeros(2, int)
        previous = np.zeros(2, int)
        ghost_frames = 0
        dc_max = 0.0
        gates_changed = 0
        with threadpool_limits(limits=1), cached_dpss(True):
            chain = ComponentForecastChain(source_protocol, x[0])
            for end in range(1+BLOCK, int(origins[-1])+2, BLOCK):
                base = chain.push(x[end-BLOCK:end])
                if base is None:
                    continue
                frame = chain.frame
                reconstructed = frame.reconstruct()
                for name, original in zip(output, base):
                    values = reconstructed[name]
                    np.testing.assert_allclose(values, original, rtol=p['parity']['rtol'], atol=p['parity']['atol'])
                    local_errors[name] = max(local_errors[name], float(np.max(np.abs(values-original))))
                    output[name].append(values)
                # Unity tuned tone drive equals minus the mixed prediction with
                # only its explicit v2 DC contribution removed, at each sample.
                settings = [ToneSetting(f, 1.) for f in sorted({f for f, _ in frame.v2}
                                | {f for components in frame.fade for f, _ in components})]
                for g, (columns, _) in enumerate(chain.groups):
                    wanted = -reconstructed['causal_L2'][columns]+frame.mix_weights[g][:, 0]*frame.gates[0]*frame.dc
                    actual = frame.anti_noise(settings, g)
                    np.testing.assert_allclose(actual, wanted, rtol=p['parity']['rtol'], atol=p['parity']['atol'])
                    drive_error = max(drive_error, float(np.max(np.abs(actual-wanted))))
                    mixed_blocks[g] += bool(np.any(np.sum(frame.mix_weights[g] > 1e-12, axis=1) > 1))
                selected = np.array(frame.selected)
                transitions += selected != previous
                previous = selected
                decisions.append(selected)
                ghost_frames += frame.ghosts > 0
                dc_max = max(dc_max, abs(frame.dc))
                gates_changed += bool(np.any(frame.gates != frame.previous_gates))
        for name in output:
            values = np.asarray(output[name])
            np.testing.assert_allclose(values, expected[name], rtol=p['parity']['rtol'], atol=p['parity']['atol'])
            errors[name] = float(np.max(np.abs(values-expected[name])))
        np.testing.assert_array_equal(decisions, expected_choices)
        row = {'id': entry['id'], 'passed': True, 'origins': len(origins), 'exact_choices': True,
               'max_error_to_saved': errors, 'max_error_to_local_core': local_errors,
               'unity_tuned_drive_max_error': drive_error,
               'chooser_transitions_by_horizon': transitions.tolist(),
               'mixed_blocks_by_horizon': mixed_blocks.tolist(),
               'ghost_frames': ghost_frames, 'gate_change_frames': gates_changed,
               'maximum_absolute_fitted_dc': dc_max}
        h.write_new(stage/(entry['id']+'.json'), row)
        rows.append(row)
        print(json.dumps({'completed': len(rows), 'of': len(p['cases']), 'id': entry['id'],
                          'max_error': max(errors.values()), 'switches': transitions.tolist(),
                          'ghost_frames': ghost_frames}), flush=True)
    switches = np.sum([r['chooser_transitions_by_horizon'] for r in rows], axis=0)
    ghosts = sum(r['ghost_frames'] for r in rows)
    result = {'completed_utc': datetime.now(timezone.utc).isoformat(), 'passed_numerical_parity': True,
              'sources': len(rows), 'forecast_method_comparisons': 3*len(rows),
              'exact_decision_arrays': len(rows), 'maximum_forecast_error': max(max(r['max_error_to_saved'].values()) for r in rows),
              'maximum_unity_drive_error': max(r['unity_tuned_drive_max_error'] for r in rows),
              'switches_by_horizon': switches.tolist(), 'ghost_frames': ghosts,
              'mixed_blocks_by_horizon': np.sum([r['mixed_blocks_by_horizon'] for r in rows], axis=0).tolist(),
              'coverage_sufficient_for_exercised_switches': bool(np.all(switches > 0) and ghosts > 0),
              'not_yet_done': 'Old v2 room reproduction; freeze renderer/horizon mapping and harm criteria; fixed-tuning 48-room study. No live integration or acoustic validation.',
              'cases': rows}
    h.write_new(STUDY/'results.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'cases'}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['freeze', 'run'])
    args = parser.parse_args()
    {'freeze': freeze, 'run': run}[args.stage]()
