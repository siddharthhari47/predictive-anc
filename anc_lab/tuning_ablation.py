"""Search-versus-comparison ablation of the tune-by-ear tuner (development data). Never opens audio devices.

Four arms on the 37 eligible rooms of results-tuning-accuracy-01:

O   original tuner, unchanged (must reproduce the saved v2 tuning on the recorded seed);
S   search change only: four alternating phase sweeps instead of two, a 60-degree
    first fine phase step, and a best-of-three majority vote at every fine A/B step;
C   check change only: on/off pairs count only when the reference microphone's
    auditory-band level is stable across the two intervals (<= 1 dB); three valid
    pairs are needed, any valid "louder with anti-hum" mutes, at most six pairs;
SC  both.

The validity rule reads only the laptop microphone over intervals the listener has
already heard, which the live app has. It never reads the simulated ear. The
prefix oracle (known simulated ear) is used for diagnosis only. The live tuner,
the engine and every earlier result are imported without editing them.
"""
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import json

import numpy as np
from scipy import signal
from threadpoolctl import threadpool_limits

from . import selector_headroom as h
from . import selector_compatibility as compatibility
from . import selector_room_scoring as scoring
from . import tuning_accuracy_diagnostic as diag
from . import antihum_study as room
from .antihum import FS
from .tuning import (TuningSession, SimulatedListener, Presentation, Step, QUESTIONS, PHASE_STEPS,
                     GAIN_STEPS, SWEEP_HZ, SWEEP_TURNS, SWEEP_RETRIES, STEADY_SECONDS, circular_mean_deg)

ROOT = h.ROOT
STUDY = ROOT/'results-tuning-ablation-01'
LEAD = .03
ARMS = {'O': (False, False), 'S': (True, False), 'C': (False, True), 'SC': (True, True)}
SIGMAS = (1., .5, 2.)
EXTRA_SEEDS = 4
SEARCH_SWEEPS = 4
SEARCH_PHASE_STEPS = (60., 30., 15., 8., 4.)
VOTES = 3
MAX_CHECK_PAIRS = 6
VALID_PAIRS = 3
MIC_STABLE_DB = 1.
ROOM_HARM_BAND_DB = -.1
ROOM_HARM_THIRD_OCTAVE_DB = .5
USEFUL_DB = 1.
BOOTSTRAP = 10000
BOOTSTRAP_SEED = 20261028


def now():
    return datetime.now(timezone.utc).isoformat()


def seeds_for(case_id, original):
    """Recorded seed first, then predeclared extra seeds from the case id only."""
    extra = [int.from_bytes(hashlib.sha256(f'{case_id}-{k}'.encode()).digest()[:4], 'big')
             for k in range(1, EXTRA_SEEDS+1)]
    return [int(original)]+extra


class AblationSession(TuningSession):
    """TuningSession with the search change (`search`) and/or the validated check (`check`).

    With both off it is the original session, draw for draw.
    """
    def __init__(self, *args, search=False, check=False, seed=0, **kwargs):
        super().__init__(*args, seed=seed, **kwargs)
        self.search, self.valid_check = search, check
        self.votes, self.check_valid = [], []
        if check:
            self.check_on_first = list(np.random.default_rng([seed, 1]).integers(0, 2, MAX_CHECK_PAIRS).astype(bool))

    def next_step(self):
        if self._current is not None or not self.search or self.stage not in ('sweep', 'phase'):
            return super().next_step()
        if self.stage == 'sweep':
            direction = 1 if len(self.sweeps) % 2 == 0 else -1
            shown = [Presentation('sweep', self.setting(offset=direction*SWEEP_HZ), self.sweep_turns/SWEEP_HZ)]
            choices = ('presses',)
        else:
            d = SEARCH_PHASE_STEPS[self.fine_index]
            shown = [Presentation('A', self.setting(phase=self.phase-d), STEADY_SECONDS),
                     Presentation('B', self.setting(phase=self.phase+d), STEADY_SECONDS)]
            choices = ('A', 'B', 'same')
        self._current = Step(self.stage, QUESTIONS[self.stage], shown, choices)
        self.listening_seconds += sum(p.seconds for p in shown)
        return self._current

    def answer(self, choice, valid=True):
        kind = None if self._current is None else self._current.kind
        if self.search and kind in ('phase', 'gain'):
            if choice not in ('A', 'B', 'same'):
                raise ValueError('The answer is not A, B or same.')
            self._record(choice)
            self.votes.append(choice)
            counts = Counter(self.votes)
            winner = next((c for c in ('A', 'B', 'same') if counts[c] >= 2), None)
            if winner is None and len(self.votes) < VOTES:
                return
            move = {'A': -.5, 'B': .5, 'same': 0., None: 0.}[winner]
            self.votes = []
            if kind == 'phase':
                self.phase = (self.phase+move*SEARCH_PHASE_STEPS[self.fine_index]) % 360
                self._next_fine(SEARCH_PHASE_STEPS, 'gain')
            else:
                self._set_gain(self.gain*GAIN_STEPS[self.fine_index]**move)
                self._next_fine(GAIN_STEPS, 'check')
            return
        if self.valid_check and kind == 'check':
            if choice not in ('A', 'B', 'same'):
                raise ValueError('The answer is not A, B or same.')
            self._record(choice)
            on_first = self.check_on_first[len(self.check_answers)]
            self.check_answers.append('same' if choice == 'same' else 'on' if (choice == 'A') == on_first else 'off')
            self.check_valid.append(bool(valid))
            heard = [a for a, v in zip(self.check_answers, self.check_valid) if v]
            if 'off' in heard:
                self._finish_check('louder with anti-hum: switched off')
            elif len(heard) == VALID_PAIRS:
                self._finish_check(None if heard.count('on') >= 2 else 'no benefit heard: switched off')
            elif len(self.check_answers) == MAX_CHECK_PAIRS:
                self._finish_check('inconclusive (background kept changing): switched off')
            return
        super().answer(choice)

    def _finish_check(self, flag):
        self.gain_before_check = self.gain
        if flag:
            self.flags.append(flag)
            self.gain = 0.
        self.stage = 'done'

    def presses(self, times):
        if not self.search:
            return super().presses(times)
        if self._current is None or self._current.kind != 'sweep':
            raise ValueError('No sweep is waiting.')
        p = self._record([float(t) for t in times]).presentations[0]
        offset = p.setting.offset_hz
        phases = [(p.setting.phase_deg+360*offset*t) % 360 for t in times if 0 <= t <= p.seconds]
        if not phases and self.sweep_attempts < SWEEP_RETRIES:
            self.sweep_attempts += 1
            return
        self.sweeps.append((1 if offset > 0 else -1, phases))
        self.sweep_attempts = 0
        if len(self.sweeps) < SEARCH_SWEEPS:
            return
        # Average each direction first, so a lost sweep cannot unbalance the reaction-delay cancellation.
        directions = [circular_mean_deg([circular_mean_deg(ph) for d, ph in self.sweeps if d == sign and ph])
                      for sign in (1, -1) if any(ph for d, ph in self.sweeps if d == sign)]
        if not directions:
            self.flags.append('no quiet moment found: switched off')
            self.gain, self.stage = 0., 'done'
            return
        if len(directions) == 1:
            self.flags.append('one sweep direction only (reaction delay not cancelled)')
        self.phase = circular_mean_deg(directions)
        self.stage, self.fine_index = 'phase', 0

    def summary(self):
        out = super().summary()
        if self.valid_check:
            out.update(check_pairs=len(self.check_answers), valid_check_pairs=int(sum(self.check_valid)))
        return out


class IntervalPlayer(room.RoomPlayer):
    """The original room player, also recording each presentation's sample interval."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.intervals = []

    def __call__(self, presentation):
        length = round(presentation.seconds*FS)
        n0 = self.cursor if self.cursor+length <= self.scene['prefix'] else self.scene['warm']
        sound = super().__call__(presentation)
        assert n0+length <= self.scene['prefix']
        self.intervals.append((n0, n0+length))
        return sound


def mic_stable(listener, mic, intervals, frequency):
    """Deployable validity: reference-microphone band level changes by at most MIC_STABLE_DB."""
    (a0, a1), (b0, b1) = intervals
    la, lb = (listener.level('check', mic[i:j], frequency) for i, j in ((a0, a1), (b0, b1)))
    return abs(la-lb) <= MIC_STABLE_DB, float(la-lb)


def run(session, player, listener):
    mic_changes = []
    while not session.done:
        step = session.next_step()
        signals = [player(p) for p in step.presentations]
        if step.kind == 'sweep':
            session.presses(listener.press(session.frequency, signals[0], step.presentations[0].setting.offset_hz))
            continue
        choice = listener.compare(step.kind, session.frequency, *signals)
        if step.kind == 'check' and session.valid_check:
            valid, change = mic_stable(listener, player.scene['mic'], player.intervals[-2:], session.frequency)
            mic_changes.append(change)
            session.answer(choice, valid=valid)
        else:
            session.answer(choice)
    return mic_changes


def tune(scene, seed, sigma=1., search=False, check=False):
    """Mirror of antihum_study.tune_by_ear with identical random draws."""
    rng = np.random.default_rng(seed)
    T = room.PROTOCOL['tuning']
    turns = min(SWEEP_TURNS, int((scene['prefix']-scene['warm'])/FS*SWEEP_HZ))
    fixed, rows = [], []
    if turns < 1:
        return fixed, [{'skipped': 'tuning part shorter than one sweep turn'}]
    player = IntervalPlayer(scene, LEAD, fixed)
    for tone in scene['tones']:
        w = tone['w']
        start = abs(w)*10**rng.uniform(-np.log10(T['start_gain_factor_max']), np.log10(T['start_gain_factor_max']))
        max_gain = min(start*T['gain_range_factor'], T['max_gain_drive_fraction_of_cap']*room.PROTOCOL['levels']['peak_cap']/tone['mic_amplitude'])
        session = AblationSession(tone['frequency'], start, min_gain=start/T['gain_range_factor'], max_gain=max_gain,
                                  sweep_turns=turns, seed=int(rng.integers(1 << 30)), search=search, check=check)
        changes = run(session, player, SimulatedListener(FS, sigma, seed=int(rng.integers(1 << 30))))
        fixed.append(session.result())
        summary = session.summary()
        summary.update(start_gain=start, check_mic_changes_db=changes)
        rows.append(summary)
    return fixed, rows


# ---------------- protocol ----------------
FILES = ['anc_lab/tuning_ablation.py', 'tests/test_tuning_ablation.py', 'anc_lab/tuning.py',
         'anc_lab/antihum_study.py', 'anc_lab/antihum.py', 'anc_lab/selector_room_scoring.py',
         'anc_lab/selector_room_study.py', 'anc_lab/selector_room_stream.py', 'anc_lab/selector_compatibility.py',
         'anc_lab/tuning_accuracy_diagnostic.py', 'docs/TUNING_ABLATION.md']


def freeze():
    diag.verified()
    assert not STUDY.exists(), 'Never overwrite an ablation run'
    accuracy = h.read(diag.STUDY/'protocol.json')
    cases = []
    for c in accuracy['cases']:
        if not c['menu_tones']:
            continue
        meta = h.read(ROOT/c['metadata_path'])
        cases.append({**c, 'seeds': seeds_for(c['case_id'], meta['tuning_seeds']['30']['1.0'])})
    protocol = {
        'created_utc': now(), 'kind': 'posthoc_development_ablation',
        'scope': 'The 37 eligible rooms (78 menu tones, 14 sources) of results-tuning-accuracy-01, seen development data, 30 ms lead, v2 forecasts. No new audio, no physical output, no live change.',
        'arms': {
            'O': 'Original TuningSession and SimulatedListener, unchanged.',
            'S': f'Search only: {SEARCH_SWEEPS} alternating phase sweeps (+,-,+,-), phase = circular mean of the two per-direction means; fine phase steps {list(SEARCH_PHASE_STEPS)} deg; every fine phase/gain step asks up to {VOTES} A/B questions and moves half a step once A or B has 2 votes, no move once "same" has 2 or after a 1/1/1 split. Level staircase and final check unchanged.',
            'C': f'Check only: up to {MAX_CHECK_PAIRS} on/off pairs (order from default_rng([session seed, 1])). A pair is valid only if the noiseless reference-microphone ERB-band level of its two intervals differs by <= {MIC_STABLE_DB} dB. Any valid "off" mutes at once; at {VALID_PAIRS} valid pairs keep only with >= 2 "on"; fewer than {VALID_PAIRS} valid after {MAX_CHECK_PAIRS} pairs mutes as inconclusive. Search unchanged.',
            'SC': 'Both changes.',
        },
        'deployability': 'The validity rule reads only the laptop microphone over already-heard intervals. In this simulation the microphone carries no earphone leakage and its background follows the same source as the ear; a real microphone may differ. The oracle uses the known simulated ear and is diagnostic only.',
        'seeds': f'Per room the recorded seed plus {EXTRA_SEEDS} extra seeds from sha256(case_id-k), k=1..{EXTRA_SEEDS}; the same seeds for every arm and listener noise.',
        'listener_sigma_db': {'primary': 1., 'secondary': [.5, 2.]},
        'parity': 'Arm O at sigma 1 with the recorded seed must reproduce the saved v2 settings, and the original tune_by_ear, in every room before any arm is summarised.',
        'metrics': {
            'primary': 'Scored-suffix 35-350 Hz band attenuation (band_db) of the whole room, from selector_room_scoring.evaluate with the v2 method.',
            'secondary': ['tone_db', 'max_third_octave_amplification_db', 'clipped_fraction',
                          'phase and gain error of the pre-check setting against the prefix oracle (identifiable tones)',
                          'harmful keep: kept tone whose capped single-tone prefix ERB attenuation is below -1e-9 dB (prefix and suffix both reported)',
                          f'useful keep: kept tone with single-tone prefix ERB attenuation >= {USEFUL_DB} dB',
                          f'missed opportunity: muted tone whose bounded oracle candidate gives >= {USEFUL_DB} dB prefix ERB attenuation',
                          'room harm: band_db < -0.1 dB or a third-octave boost > 0.5 dB',
                          'listening seconds, questions, sweeps, check pairs, valid pairs, inconclusive mutes'],
        },
        'aggregation': f'Paired difference arm minus O per room and seed, averaged over seeds per room, then over rooms per source, then over the 14 sources. 95% percentile interval from {BOOTSTRAP} source-bootstrap resamples (seed {BOOTSTRAP_SEED}). Counts are summed over all rooms and seeds. Attribution: S-O, C-O and interaction SC-S-C+O.',
        'decision': 'At sigma 1, an arm "helps" only if the lower 95% bound of its mean paired band_db difference over O is above 0, its harmful keeps are no more than O\'s, and its room harms are no more than O\'s. Its listening cost is reported beside it. Sigma 0.5 and 2 are descriptive sensitivity only. Every arm is reported whatever the outcome.',
        'caveats': 'Seen development data, so this chooses where to spend effort; it is not a fresh validation. The simulated listener is an assumption, not measured human acuity. No physical ANC is claimed.',
        'cases': cases,
        'code_sha256': {name: h.sha(ROOT/name) for name in FILES},
        'accuracy_protocol_sha256': h.sha(diag.STUDY/'protocol.json'),
        'oracle_results_sha256': h.sha(diag.STUDY/'oracle-results.json'),
    }
    STUDY.mkdir()
    h.write_new(STUDY/'protocol.json', protocol)
    h.write_new(STUDY/'frozen.json', {'sha256': h.sha(STUDY/'protocol.json')})
    print(json.dumps({'protocol_sha256': h.sha(STUDY/'protocol.json'), 'rooms': len(cases),
                      'tones': sum(c['menu_tones'] for c in cases)}), flush=True)


def verified():
    p = h.read(STUDY/'protocol.json')
    assert h.sha(STUDY/'protocol.json') == h.read(STUDY/'frozen.json')['sha256']
    for name, digest in p['code_sha256'].items():
        assert h.sha(ROOT/name) == digest, name
    assert h.sha(diag.STUDY/'oracle-results.json') == p['oracle_results_sha256']
    return p


# ---------------- scoring ----------------
def tone_bases(scene):
    out = []
    for tone in scene['tones']:
        pairs = [compatibility.unit_sound(scene, scene['arrays'], tone['frequency'], phase) for phase in (0., 90.)]
        out.append((np.column_stack([d for d, _ in pairs]), diag.band_filter(tone['frequency'])))
    return out


def tone_rows(scene, summaries, bases, oracle):
    rows = []
    for k, (s, (drives, sos), o) in enumerate(zip(summaries, bases, oracle)):
        pre = s['gain_before_check'] if s['gain_before_check'] is not None else s['gain']
        row = {'tone_index': k, 'frequency': s['frequency'], 'kept': s['kept'], 'gain': s['gain'],
               'precheck_gain': pre, 'phase_deg': s['phase_deg'], 'flags': s['flags'],
               'questions': s['questions'], 'sweeps': s['sweeps'], 'presses': s['presses'],
               'listening_seconds': s['listening_seconds'], 'check_pairs': s.get('check_pairs'),
               'valid_check_pairs': s.get('valid_check_pairs'), 'check_mic_changes_db': s['check_mic_changes_db'],
               'identifiable': o['oracle']['identifiable']}
        if o['oracle']['identifiable']:
            row.update(phase_error_deg=compatibility.phase_difference(s['phase_deg'], o['oracle']['phase_deg']),
                       gain_error_db=float(20*np.log10(pre/o['oracle']['gain'])) if pre > 0 else None,
                       bounded_oracle_prefix_db=o['bounded_candidate_effect']['prefix_erb_db'])
        row['precheck_effect'] = diag.rendered_effect(scene, drives, diag.coefficients(pre, s['phase_deg']), sos)
        row['final_effect'] = diag.rendered_effect(scene, drives, diag.coefficients(s['gain'], s['phase_deg']), sos)
        rows.append(row)
    return rows


def score_case(c, oracle):
    scene, meta, saved = diag.load(c)
    bases = tone_bases(scene)
    assert [o['tone_index'] for o in oracle] == list(range(len(scene['tones'])))
    runs, parity = [], 0
    for sigma in SIGMAS:
        for k, seed in enumerate(c['seeds']):
            for arm, (search, check) in ARMS.items():
                settings, summaries = tune(scene, seed, sigma, search, check)
                if arm == 'O' and sigma == 1. and k == 0:
                    parity += diag.numbers_equal([asdict(s) for s in settings], saved['v2_settings'])
                    reference, _ = room.tune_by_ear(scene, LEAD, 1., seed)
                    parity += diag.numbers_equal([asdict(s) for s in settings], [asdict(s) for s in reference], atol=0)
                metrics, _ = scoring.evaluate(scene, settings, LEAD, 'v2', meta['reference_tones_hz'])
                runs.append({'sigma': sigma, 'seed_index': k, 'seed': seed, 'arm': arm,
                             'settings': [asdict(s) for s in settings], 'room': metrics,
                             'tones': tone_rows(scene, summaries, bases, oracle)})
    return {'case_id': c['case_id'], 'source_id': c['source_id'], 'parity_fields': parity, 'runs': runs}


def run_all():
    p = verified()
    oracles = {o['case_id']: o['tones'] for o in h.read(diag.STUDY/'oracle-results.json')['cases']}
    dest = STUDY/'cases'
    dest.mkdir(exist_ok=False)
    h.write_new(STUDY/'run-start.json', {'started_utc': now(), 'protocol_sha256': h.sha(STUDY/'protocol.json')})
    for i, c in enumerate(p['cases']):
        result = score_case(c, oracles[c['case_id']])
        h.write_new(dest/(c['case_id']+'.json'), result)
        print(json.dumps({'case': c['case_id'], 'complete': i+1, 'of': len(p['cases']),
                          'parity_fields': result['parity_fields']}), flush=True)
    h.write_new(STUDY/'run-complete.json', {'completed_utc': now(), 'cases': len(p['cases'])})


# ---------------- summary ----------------
def room_harm(m):
    return m['band_db'] < ROOM_HARM_BAND_DB or m['max_third_octave_amplification_db'] > ROOM_HARM_THIRD_OCTAVE_DB


def source_means(values):
    """{source: {room: [per-seed values]}} -> per-source means (rooms equally weighted within a source)."""
    return {s: float(np.mean([np.mean(v) for v in rooms.values()])) for s, rooms in values.items()}


def bootstrap(per_source, rng):
    sources = sorted(per_source)
    x = np.array([per_source[s] for s in sources])
    idx = rng.integers(0, len(x), (BOOTSTRAP, len(x)))
    means = x[idx].mean(axis=1)
    return {'mean': float(x.mean()), 'ci95': [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))],
            'sources': len(x)}


def summarize():
    p = verified()
    assert (STUDY/'run-complete.json').exists()
    cases = [h.read(STUDY/'cases'/(c['case_id']+'.json')) for c in p['cases']]
    assert all(c['parity_fields'] > 0 for c in cases)
    table, out = [], {'parity_fields': sum(c['parity_fields'] for c in cases), 'by_sigma': {}}
    for sigma in SIGMAS:
        runs = {(c['case_id'], r['seed_index'], r['arm']): (c['source_id'], r) for c in cases for r in c['runs'] if r['sigma'] == sigma}
        stats = {}
        for arm in ARMS:
            band, tone = {}, {}
            counts = Counter()
            phase_err, gain_err, seconds = [], [], []
            for (case, k, a), (source, r) in runs.items():
                if a != arm:
                    continue
                o = runs[(case, k, 'O')][1]
                band.setdefault(source, {}).setdefault(case, []).append(r['room']['band_db']-o['room']['band_db'])
                if r['room']['tone_db'] is not None and o['room']['tone_db'] is not None:
                    tone.setdefault(source, {}).setdefault(case, []).append(r['room']['tone_db']-o['room']['tone_db'])
                counts['room_runs'] += 1
                counts['room_harms'] += room_harm(r['room'])
                for t in r['tones']:
                    counts['tones'] += 1
                    counts['kept'] += t['kept']
                    counts['harmful_keeps_prefix'] += t['kept'] and t['final_effect']['prefix_erb_db'] < -1e-9
                    counts['harmful_keeps_suffix'] += t['kept'] and t['final_effect']['suffix_erb_db'] < -1e-9
                    counts['useful_keeps'] += t['kept'] and t['final_effect']['prefix_erb_db'] >= USEFUL_DB
                    counts['useful_precheck'] += t['precheck_effect']['prefix_erb_db'] >= USEFUL_DB
                    counts['oracle_useful'] += t.get('bounded_oracle_prefix_db', -np.inf) >= USEFUL_DB
                    counts['missed_opportunities'] += (not t['kept']) and t.get('bounded_oracle_prefix_db', -np.inf) >= USEFUL_DB
                    counts['inconclusive_mutes'] += any(f.startswith('inconclusive') for f in t['flags'])
                    if t['identifiable']:
                        phase_err.append(abs(t['phase_error_deg']))
                        if t['gain_error_db'] is not None:
                            gain_err.append(abs(t['gain_error_db']))
                    seconds.append(t['listening_seconds'])
                    table.append({'sigma': sigma, 'arm': arm, 'case_id': case, 'source_id': source, 'seed_index': k,
                                  'tone_index': t['tone_index'], 'frequency_hz': t['frequency'], 'kept': t['kept'],
                                  'phase_error_deg': t.get('phase_error_deg'), 'gain_error_db': t.get('gain_error_db'),
                                  'precheck_prefix_erb_db': t['precheck_effect']['prefix_erb_db'],
                                  'final_prefix_erb_db': t['final_effect']['prefix_erb_db'],
                                  'final_suffix_erb_db': t['final_effect']['suffix_erb_db'],
                                  'bounded_oracle_prefix_db': t.get('bounded_oracle_prefix_db'),
                                  'questions': t['questions'], 'sweeps': t['sweeps'],
                                  'check_pairs': t['check_pairs'], 'valid_check_pairs': t['valid_check_pairs'],
                                  'listening_seconds': t['listening_seconds'], 'flags': '; '.join(t['flags']),
                                  'room_band_db': r['room']['band_db']})
            arm_rng = np.random.default_rng([BOOTSTRAP_SEED, int(sigma*10), list(ARMS).index(arm)])
            band_level = source_means({s: {c: [runs[(c, k, arm)][1]['room']['band_db'] for k in range(EXTRA_SEEDS+1)]
                                           for c in rooms} for s, rooms in band.items()})
            stats[arm] = {
                'band_db': bootstrap(band_level, arm_rng),
                'band_db_minus_O': bootstrap(source_means(band), arm_rng),
                'tone_db_minus_O': bootstrap(source_means(tone), arm_rng) if tone else None,
                'counts': dict(counts),
                'median_abs_phase_error_deg': float(np.median(phase_err)),
                'median_abs_gain_error_db': float(np.median(gain_err)),
                'mean_listening_seconds_per_tone': float(np.mean(seconds)),
            }
        inter = {}
        for (case, k, a), (source, r) in runs.items():
            if a == 'O':
                v = lambda arm: runs[(case, k, arm)][1]['room']['band_db']
                inter.setdefault(source, {}).setdefault(case, []).append(v('SC')-v('S')-v('C')+v('O'))
        stats['interaction_SC_minus_S_minus_C_plus_O'] = bootstrap(source_means(inter), np.random.default_rng([BOOTSTRAP_SEED, int(sigma*10), 9]))
        for arm in ('S', 'C', 'SC'):
            s = stats[arm]
            s['helps'] = bool(s['band_db_minus_O']['ci95'][0] > 0
                              and s['counts']['harmful_keeps_prefix'] <= stats['O']['counts']['harmful_keeps_prefix']
                              and s['counts']['room_harms'] <= stats['O']['counts']['room_harms'])
        out['by_sigma'][f'{sigma:g}'] = stats
    out['decision_sigma'] = '1'
    h.write_new(STUDY/'summary.json', out)
    with (STUDY/'tone-runs.csv').open('x', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)
    print(json.dumps({k: {a: (v[a]['band_db_minus_O'] if a in ARMS else v[a]) for a in v} for k, v in out['by_sigma'].items()}, indent=1))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['freeze', 'run', 'summarize'])
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        {'freeze': freeze, 'run': run_all, 'summarize': summarize}[args.stage]()
