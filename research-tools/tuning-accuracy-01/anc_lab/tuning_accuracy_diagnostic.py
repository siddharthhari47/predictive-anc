"""Seen-data tuning diagnosis requested in review 55. Never opens audio devices.

The prefix oracle uses known simulated-ear pressure, so it is a diagnostic,
not a deployable listener or a new out-of-sample result. Original studies and
the live tuner are imported without editing them.
"""
from collections import Counter
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import argparse
import json

import numpy as np
from scipy import signal, special
from threadpoolctl import threadpool_limits

from . import selector_headroom as h
from . import selector_room_study as rooms
from . import selector_room_completion as completion
from . import selector_compatibility as compatibility
from . import antihum_study as room
from .antihum import FS, ToneSetting
from .tuning import TuningSession, SimulatedListener, Presentation, erb_hz

ROOT = h.ROOT
STUDY = ROOT / 'results-tuning-accuracy-01'
ORIGINAL_PLAYER = room.RoomPlayer
THRESHOLDS = (.1, .5, 1., 3., 6.)


def now():
    return datetime.now(timezone.utc).isoformat()


def coefficients(gain, phase):
    return float(gain)*np.array([np.cos(np.deg2rad(phase)), np.sin(np.deg2rad(phase))])


def attenuation(off, on):
    return compatibility.db(np.mean(np.asarray(off)**2), np.mean(np.asarray(on)**2))


def numbers_equal(actual, expected, atol=1e-10):
    """Strict structure and booleans, numerical tolerance only for floats."""
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys(), (actual.keys(), expected.keys())
        return sum(numbers_equal(actual[k], expected[k], atol) for k in expected)
    if isinstance(expected, list):
        assert len(actual) == len(expected)
        return sum(numbers_equal(a, b, atol) for a, b in zip(actual, expected))
    if isinstance(expected, (float, np.floating)):
        assert np.isclose(actual, expected, rtol=0, atol=atol), (actual, expected)
    else:
        assert actual == expected, (actual, expected)
    return 1


def projected_effect(basis, optimum, tested, start, end):
    """Error on the prefix's linearly cancellable component, not the full band."""
    x = basis[start:end]
    return attenuation(x@optimum, x@(tested-optimum))


def check_probabilities(on_minus_off_db, sigma_db=1., same_db=1.):
    """Independent Gaussian noise per presentation: difference SD is sqrt(2)*sigma."""
    sd = np.sqrt(2)*sigma_db
    if sd == 0:
        return {'on': float(on_minus_off_db <= -same_db),
                'same': float(abs(on_minus_off_db) < same_db),
                'off': float(on_minus_off_db >= same_db)}
    p_on = float(special.ndtr((-same_db-on_minus_off_db)/sd))
    p_off = float(special.ndtr((on_minus_off_db-same_db)/sd))
    return {'on': p_on, 'same': 1-p_on-p_off, 'off': p_off}


def keep_probability(a, b):
    return a['on']*b['on'] + a['on']*b['same'] + a['same']*b['on']


def freeze():
    completion.verified()
    compatibility.verified()
    assert not STUDY.exists(), 'Never overwrite a diagnostic run'
    coverage = h.read(rooms.STUDY/'coverage.json')
    cases = []
    for receipt in coverage['cases']:
        meta = h.read(ROOT/receipt['metadata_path'])
        score = rooms.STUDY/'scores'/(meta['case_id']+'.json')
        detail = next(d for d in h.read(score)['details'] if d['lead_ms'] == 30)
        cases.append({**receipt, 'menu_tones': len(meta['tones']),
                      'score_path': str(score.relative_to(ROOT)), 'score_sha256': h.sha(score),
                      'saved_tones': len(detail['v2_tuning']),
                      'cache_path': meta['cache_path'], 'cache_sha256': meta['cache_sha256']})
    files = ['anc_lab/tuning_accuracy_diagnostic.py', 'tests/test_tuning_accuracy_diagnostic.py',
             'anc_lab/selector_compatibility.py', 'anc_lab/selector_room_study.py',
             'anc_lab/selector_room_completion.py', 'anc_lab/selector_room_scoring.py',
             'anc_lab/selector_room_stream.py', 'anc_lab/antihum_study.py',
             'anc_lab/antihum.py', 'anc_lab/tuning.py', 'results-release-study-01/release_protocol.json',
             'docs/TUNING_ACCURACY_DIAGNOSTIC.md']
    protocol = {
        'created_utc': now(), 'review': 55, 'kind': 'posthoc_development_diagnosis',
        'scope': 'Every saved v2 menu tone at 30 ms, sigma=1 dB; all 72 rooms remain in the inventory. No chooser retuning, new audio or physical output.',
        'stages': ['prefix_oracles', 'original_tuning_reproduction_and_check_instrumentation'],
        'oracle': 'Same two native 0/90-degree bases and causal second-order ERB band as compatibility-01; least squares on [warm,prefix) only, known simulated ear, each tone alone. No scored-suffix fitting. This is an unconstrained linear oracle, not necessarily attainable under tuner gain bounds or the digital cap.',
        'effects': 'Both pre-check and final gains; actual capped single-tone prefix and suffix ERB attenuation, projected cancellable-component attenuation, phase/gain errors. Projection geometry replaces an unjustified universal 60-degree harm rule.',
        'feasibility': 'Report original min/max gain and cap clipping separately. Radially clamp oracle gain into the original range and render under the original peak cap as a feasible candidate; this candidate is NOT claimed to be the globally optimal nonlinear capped solution.',
        'classification': 'Phase >60 degrees is a descriptive flag only. Harm = actual capped single-tone ERB attenuation below zero (numerical tolerance 1e-9); retain magnitudes and counts beyond 0.1/0.5/1 dB. Useful-oracle and useful-precheck counts are separately shown at the fixed descriptive grid, not a new pass rule. Require both prefix and scored suffix in an additional persistence table.',
        'benefit_thresholds_db': list(THRESHOLDS),
        'check_logging': 'Run the original tune_by_ear with observational subclasses; preserve RNG draws, intervals, order and settings. Require every summary and setting to reproduce saved scores before interpreting logs. Log original noiseless/noisy A/B levels and sequential on-minus-off, same-interval on/off counterfactuals with prior kept tones, and exact Gaussian-model keep probability conditional on settings and presentations.',
        'assumptions': 'sigma=1 dB per A/B presentation, same=1 dB, independent difference SD=sqrt(2) dB. Sweep clicks use the original reaction/miss/window model; their accuracy is not characterized by this Gaussian comparison calculation. All are simulated assumptions, not measured human acuity.',
        'aggregation': 'Full tone rows plus room and source counts; repeated tones and rooms are dependent. Descriptive only, no inferential confidence intervals or fresh-test claim.',
        'no_live_changes': True, 'cases': cases,
        'code_sha256': {name: h.sha(ROOT/name) for name in files},
        'original_results_sha256': h.sha(rooms.STUDY/'results.json'),
        'prior_compatibility_sha256': h.sha(compatibility.STUDY/'protocol.json'),
    }
    STUDY.mkdir()
    h.write_new(STUDY/'protocol.json', protocol)
    h.write_new(STUDY/'frozen.json', {'sha256': h.sha(STUDY/'protocol.json')})
    print(json.dumps({'protocol_sha256': h.sha(STUDY/'protocol.json'),
                      'rooms': len(cases), 'eligible_rooms': sum(c['menu_tones'] > 0 for c in cases),
                      'tones': sum(c['menu_tones'] for c in cases)}), flush=True)


def verified():
    p = h.read(STUDY/'protocol.json')
    assert h.sha(STUDY/'protocol.json') == h.read(STUDY/'frozen.json')['sha256']
    for name, digest in p['code_sha256'].items():
        assert h.sha(ROOT/name) == digest, name
    assert h.sha(rooms.STUDY/'results.json') == p['original_results_sha256']
    completion.verified()
    compatibility.verified()
    return p


def load(c):
    assert h.sha(ROOT/c['score_path']) == c['score_sha256']
    scene, meta = rooms.load_case(c)
    saved = next(d for d in h.read(ROOT/c['score_path'])['details'] if d['lead_ms'] == 30)
    return scene, meta, saved


def band_filter(f):
    half = erb_hz(f)/2
    return signal.butter(2, [max(20., f-half), min(f+half, .45*FS)],
                         btype='bandpass', fs=FS, output='sos')


def rendered_effect(scene, drives, coef, sos):
    drive = drives@coef
    cap = room.PROTOCOL['levels']['peak_cap']
    sound = scene['earphone_gain']*signal.lfilter(*scene['earphone'], np.clip(drive, -cap, cap))
    start = int(scene['arrays']['seen'][0])-1+60+scene['unreported']
    on = room.add_at(scene['ears'][0], start, sound)
    off = signal.sosfilt(sos, scene['ears'][0])
    on = signal.sosfilt(sos, on)
    lo, hi = scene['warm'], scene['prefix']
    return {'prefix_erb_db': attenuation(off[lo:hi], on[lo:hi]),
            'suffix_erb_db': attenuation(off[hi+1000:], on[hi+1000:]),
            'unclipped_drive_peak': float(np.max(np.abs(drive), initial=0.)),
            'clipped_fraction': float(np.mean(np.abs(drive) > cap))}


def oracle_case(c):
    scene, meta, saved = load(c)
    result = []
    for k, tone in enumerate(scene['tones']):
        f = tone['frequency']
        tuned = saved['v2_tuning'][k]
        assert f == tuned['frequency']
        sos = band_filter(f)
        pairs = [compatibility.unit_sound(scene, scene['arrays'], f, phase) for phase in (0., 90.)]
        basis = np.column_stack([signal.sosfilt(sos, y) for _, y in pairs])
        drives = np.column_stack([d for d, _ in pairs])
        target = signal.sosfilt(sos, scene['ears'][0])
        fit = compatibility.fit_fixed(target, basis, scene['warm'], scene['prefix'])
        row = {'case_id': meta['case_id'], 'source_id': meta['source_id'], 'tone_index': k,
               'frequency': f, 'kept': tuned['kept'], 'tuning': tuned, 'oracle': fit,
               'prefix_start_s': scene['warm']/FS, 'prefix_end_s': scene['prefix']/FS}
        if fit['identifiable']:
            pre_gain = tuned['gain_before_check'] if tuned['gain_before_check'] is not None else tuned['gain']
            pre = coefficients(pre_gain, tuned['phase_deg'])
            opt = np.array(fit['coefficients'])
            minimum = tuned['start_gain']/room.PROTOCOL['tuning']['gain_range_factor']
            maximum = min(tuned['start_gain']*room.PROTOCOL['tuning']['gain_range_factor'],
                          room.PROTOCOL['tuning']['max_gain_drive_fraction_of_cap']*
                          room.PROTOCOL['levels']['peak_cap']/tone['mic_amplitude'])
            candidate_gain = float(np.clip(fit['gain'], minimum, maximum))
            row.update({
                'precheck_gain': pre_gain,
                'phase_error_deg': compatibility.phase_difference(tuned['phase_deg'], fit['phase_deg']),
                'gain_error_db': float(20*np.log10(pre_gain/fit['gain'])) if pre_gain > 0 and fit['gain'] > 0 else None,
                'projected_component_db': projected_effect(basis, opt, pre, scene['warm'], scene['prefix']),
                'idealized_equal_quadrature_db': float(-20*np.log10(max(np.linalg.norm(pre-opt)/max(fit['gain'], 1e-30), 1e-15))),
                'min_gain': minimum, 'max_gain': maximum,
                'oracle_in_gain_range': bool(minimum <= fit['gain'] <= maximum),
                'oracle_effect': rendered_effect(scene, drives, opt, sos),
                'bounded_candidate_gain': candidate_gain,
                'bounded_candidate_effect': rendered_effect(scene, drives, coefficients(candidate_gain, fit['phase_deg']), sos),
                'precheck_effect': rendered_effect(scene, drives, pre, sos),
                'final_effect': rendered_effect(scene, drives, coefficients(tuned['gain'], tuned['phase_deg']), sos),
            })
        result.append(row)
    return {'case_id': meta['case_id'], 'source_id': meta['source_id'], 'tones': result}


def run_oracles():
    p = verified()
    dest = STUDY/'oracles'
    dest.mkdir(exist_ok=False)
    h.write_new(STUDY/'oracle-start.json', {'started_utc': now(), 'protocol_sha256': h.sha(STUDY/'protocol.json')})
    results = []
    for c in p['cases']:
        if not c['menu_tones']:
            continue
        row = oracle_case(c)
        h.write_new(dest/(c['case_id']+'.json'), row)
        results.append(row)
        print(json.dumps({'stage': 'oracle', 'case': c['case_id'], 'complete': len(results)}), flush=True)
    h.write_new(STUDY/'oracle-results.json', {'completed_utc': now(), 'cases': results})


class TracePlayer(ORIGINAL_PLAYER):
    def __init__(self, *args, collector, **kwargs):
        super().__init__(*args, **kwargs)
        self.collector = collector
        collector['player'] = self
        self.latest = []

    def __call__(self, presentation):
        length = round(presentation.seconds*FS)
        n0 = self.cursor if self.cursor+length <= self.scene['prefix'] else self.scene['warm']
        actual = super().__call__(presentation)
        self.latest.append({'start': n0, 'end': n0+length, 'presentation': presentation,
                            'fixed': list(self.fixed), 'sound': actual})
        self.latest = self.latest[-2:]
        return actual


class TraceSession(TuningSession):
    def __init__(self, *args, collector, **kwargs):
        super().__init__(*args, **kwargs)
        self.collector = collector
        collector['session'] = self
        collector['sessions'].append(self)
        self.observations = []
        self.initial = {'start_gain': args[1] if len(args) > 1 else kwargs['start_gain'],
                        'min_gain': self.min_gain, 'max_gain': self.max_gain,
                        'check_on_first': [bool(v) for v in self.check_on_first],
                        'sweep_turns': self.sweep_turns}


class TraceListener(SimulatedListener):
    def __init__(self, *args, collector, **kwargs):
        super().__init__(*args, **kwargs)
        self.collector = collector

    def compare(self, kind, frequency, a, b):
        # Clone the RNG state for observation. Never draw from the live RNG here.
        clone = np.random.default_rng(0)
        clone.bit_generator.state = deepcopy(self.rng.bit_generator.state)
        noise = [float(clone.normal(0, self.sigma)), float(clone.normal(0, self.sigma))]
        levels = [self.level(kind, x, frequency) for x in (a, b)]
        answer = super().compare(kind, frequency, a, b)
        assert self.rng.bit_generator.state == clone.bit_generator.state
        noisy = np.array(levels)+noise
        recomputed = 'same' if abs(noisy[0]-noisy[1]) < self.same_db else ('A' if noisy[0] < noisy[1] else 'B')
        assert answer == recomputed
        records = self.collector['player'].latest
        assert len(records) == 2
        row = {'kind': kind, 'frequency': frequency, 'answer': answer,
               'intervals': [{'start_s': r['start']/FS, 'end_s': r['end']/FS,
                              'setting': asdict(r['presentation'].setting)} for r in records],
               'noiseless_levels_db': levels, 'noise_db': noise, 'noisy_levels_db': noisy.tolist()}
        if kind == 'check':
            session = self.collector['session']
            on_index = 0 if records[0]['presentation'].setting.gain > 0 else 1
            assert records[1-on_index]['presentation'].setting.gain == 0
            row.update(on_index=on_index, on_minus_off_db=levels[on_index]-levels[1-on_index],
                       noisy_on_minus_off_db=float(noisy[on_index]-noisy[1-on_index]))
            row['choice_as_on_off'] = 'same' if answer == 'same' else ('on' if (answer == 'A') == (on_index == 0) else 'off')
            row['choice_probabilities'] = check_probabilities(row['on_minus_off_db'], self.sigma, self.same_db)
            counterfactuals = []
            for i, r in enumerate(records):
                values = {}
                for enabled in (False, True):
                    setting = replace(r['presentation'].setting, gain=session.gain if enabled else 0.)
                    presenter = ORIGINAL_PLAYER(self.collector['player'].scene, .03, list(r['fixed']))
                    presenter.cursor = r['start']
                    sound = presenter(Presentation('counterfactual', setting, r['presentation'].seconds))
                    if enabled == (i == on_index):
                        np.testing.assert_array_equal(sound, r['sound'])
                    values['on_db' if enabled else 'off_db'] = self.level('check', sound, frequency)
                values['on_minus_off_db'] = values['on_db']-values['off_db']
                counterfactuals.append(values)
            row['same_interval'] = counterfactuals
            row['off_background_on_interval_minus_off_interval_db'] = counterfactuals[on_index]['off_db']-counterfactuals[1-on_index]['off_db']
            assert abs(row['on_minus_off_db']-(counterfactuals[on_index]['on_minus_off_db']+row['off_background_on_interval_minus_off_interval_db'])) < 1e-10
        self.collector['session'].observations.append(row)
        return answer


def trace_tuning(scene, seed):
    collector = {'sessions': []}
    with ExitStack() as stack:
        stack.enter_context(patch.object(room, 'RoomPlayer', lambda *a, **kw: TracePlayer(*a, collector=collector, **kw)))
        stack.enter_context(patch.object(room, 'TuningSession', lambda *a, **kw: TraceSession(*a, collector=collector, **kw)))
        stack.enter_context(patch.object(room, 'SimulatedListener', lambda *a, **kw: TraceListener(*a, collector=collector, **kw)))
        settings, summary = room.tune_by_ear(scene, .03, 1., seed)
    sessions = []
    for s in collector['sessions']:
        checks = [r for r in s.observations if r['kind'] == 'check']
        item = {'frequency': s.frequency, 'initial': s.initial, 'summary': s.summary(),
                'steps': s.log, 'comparisons': s.observations}
        if len(checks) == 2:
            item['conditional_keep_probability'] = keep_probability(*[r['choice_probabilities'] for r in checks])
            item['same_interval_keep_probabilities'] = [keep_probability(*[
                check_probabilities(r['same_interval'][i]['on_minus_off_db']) for r in checks]) for i in (0, 1)]
        sessions.append(item)
    return settings, summary, sessions


def run_acceptance():
    p = verified()
    assert (STUDY/'oracle-results.json').exists(), 'Oracles precede instrumentation'
    dest = STUDY/'acceptance'
    dest.mkdir(exist_ok=False)
    h.write_new(STUDY/'acceptance-start.json', {'started_utc': now(), 'protocol_sha256': h.sha(STUDY/'protocol.json')})
    results = []
    for c in p['cases']:
        if not c['menu_tones']:
            continue
        scene, meta, saved = load(c)
        settings, summary, sessions = trace_tuning(scene, meta['tuning_seeds']['30']['1.0'])
        checked = numbers_equal(summary, saved['v2_tuning'])
        checked += numbers_equal([asdict(s) for s in settings], saved['v2_settings'])
        result = {'case_id': c['case_id'], 'source_id': c['source_id'], 'parity_fields': checked,
                  'saved_settings_and_summaries_match': True, 'sessions': sessions}
        h.write_new(dest/(c['case_id']+'.json'), result)
        results.append(result)
        print(json.dumps({'stage': 'acceptance', 'case': c['case_id'], 'complete': len(results), 'parity': True}), flush=True)
    h.write_new(STUDY/'acceptance-results.json', {'completed_utc': now(), 'cases': results,
                 'parity_fields': sum(r['parity_fields'] for r in results)})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['freeze', 'oracles', 'acceptance'])
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        {'freeze': freeze, 'oracles': run_oracles, 'acceptance': run_acceptance}[args.stage]()
