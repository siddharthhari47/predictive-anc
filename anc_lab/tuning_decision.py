"""Keep-or-mute decision study: a microphone-corrected sequential check (development data). Never opens audio devices.

results-tuning-ablation-01 found that the better search (arm S) finds better
settings, but neither the original two-pair check nor the microphone-gated check
decides well. This study replaces the final check with a sequential test that
uses every on/off pair instead of discarding unstable ones:

- each pair's answer (on quieter / off quieter / same) is modelled as the listener
  hearing (effect + background change + noise); the background change is
  estimated from the laptop microphone over the two intervals already heard;
- the log-likelihood ratio of "the anti-hum helps by EFFECT_DB" against "it does
  nothing" is added up pair by pair (Wald sequential test, alpha = beta = 0.1);
- keep at the upper bound, mute at the lower one; after MAX_PAIRS pairs keep only
  if the evidence leans towards helping.

The decision assumes a 1 dB listener and 1 dB microphone error whatever the real
simulated listener is, so the 0.5 and 2 dB runs test a mismatched model. The
simulated ear is read only by the scoring, never by the decision.

Arms: O and S as in ablation-01 (must reproduce it exactly), D = original
search + new decision, SD = search change + new decision.
"""
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import json

import numpy as np
from threadpoolctl import threadpool_limits

from . import selector_headroom as h
from . import selector_room_scoring as scoring
from . import tuning_accuracy_diagnostic as diag
from . import tuning_ablation as ab
from . import antihum_study as room
from .antihum import FS
from .tuning import SimulatedListener, SWEEP_HZ, SWEEP_TURNS

ROOT = h.ROOT
STUDY = ROOT/'results-tuning-decision-01'
LEAD = ab.LEAD
ARMS = {'O': (False, False), 'S': (True, False), 'D': (False, True), 'SD': (True, True)}
SIGMAS = (1., .5, 2.)
SEEDS = 10
EFFECT_DB = 2.
ASSUMED_SIGMA_DB = 1.
MIC_ERROR_DB = 1.
SAME_DB = 1.
ALPHA = BETA = .1
UPPER, LOWER = float(np.log((1-BETA)/ALPHA)), float(np.log(BETA/(1-ALPHA)))
MAX_PAIRS = 6
USEFUL_DB = 1.
BOOTSTRAP = 10000
BOOTSTRAP_SEED = 20261029


def now():
    return datetime.now(timezone.utc).isoformat()


def seeds_for(case_id, original):
    """Seeds 0-4 are exactly ablation-01's; 5-9 are new, from the same rule."""
    extra = [int.from_bytes(hashlib.sha256(f'{case_id}-{k}'.encode()).digest()[:4], 'big') for k in range(1, SEEDS)]
    return [int(original)]+extra


def pair_llr(heard, background_db):
    """Log-likelihood ratio, helps-by-EFFECT_DB against no effect, for one on/off answer.

    heard: 'on' (on quieter), 'off' or 'same'. background_db: microphone level of
    the on interval minus the off interval. Per-presentation noise sigma and the
    microphone error give an on-minus-off SD of sqrt(2*sigma^2 + error^2).
    """
    sigma = np.sqrt(ASSUMED_SIGMA_DB**2+MIC_ERROR_DB**2/2)
    helps = diag.check_probabilities(-EFFECT_DB+background_db, sigma, SAME_DB)
    nothing = diag.check_probabilities(background_db, sigma, SAME_DB)
    return float(np.log(max(helps[heard], 1e-12)/max(nothing[heard], 1e-12)))


class DecisionSession(ab.AblationSession):
    """AblationSession whose final check (when `sequential`) is the microphone-corrected sequential test."""
    def __init__(self, *args, sequential=False, seed=0, **kwargs):
        super().__init__(*args, seed=seed, **kwargs)
        self.sequential = sequential
        self.evidence, self.backgrounds = 0., []
        if sequential:
            self.check_on_first = list(np.random.default_rng([seed, 2]).integers(0, 2, MAX_PAIRS).astype(bool))

    def answer(self, choice, valid=True, background_db=None):
        if not (self.sequential and self._current is not None and self._current.kind == 'check'):
            return super().answer(choice, valid)
        if choice not in ('A', 'B', 'same') or background_db is None:
            raise ValueError('A check answer needs A, B or same and the microphone background change.')
        self._record(choice)
        on_first = self.check_on_first[len(self.check_answers)]
        heard = 'same' if choice == 'same' else 'on' if (choice == 'A') == on_first else 'off'
        self.check_answers.append(heard)
        self.backgrounds.append(float(background_db))
        self.evidence += pair_llr(heard, background_db)
        if self.evidence >= UPPER:
            self._finish_check(None)
        elif self.evidence <= LOWER:
            self._finish_check('no benefit heard: switched off')
        elif len(self.check_answers) == MAX_PAIRS:
            self._finish_check(None if self.evidence > 0 else 'evidence leaned against benefit: switched off')

    def summary(self):
        out = super().summary()
        if self.sequential:
            out.update(check_pairs=len(self.check_answers), check_evidence=self.evidence,
                       check_backgrounds_db=self.backgrounds)
        return out


def background_change(listener, mic, intervals, on_first, frequency):
    """Microphone band level of the on interval minus the off interval (past samples only)."""
    a, b = (listener.level('check', mic[i:j], frequency) for i, j in intervals)
    return float(a-b if on_first else b-a)


def run(session, player, listener):
    while not session.done:
        step = session.next_step()
        signals = [player(p) for p in step.presentations]
        if step.kind == 'sweep':
            session.presses(listener.press(session.frequency, signals[0], step.presentations[0].setting.offset_hz))
            continue
        choice = listener.compare(step.kind, session.frequency, *signals)
        if step.kind == 'check' and session.sequential:
            on_first = step.presentations[0].setting.gain > 0
            session.answer(choice, background_db=background_change(listener, player.scene['mic'], player.intervals[-2:],
                                                                   on_first, session.frequency))
        else:
            session.answer(choice)


def tune(scene, seed, sigma=1., search=False, sequential=False):
    """Mirror of antihum_study.tune_by_ear (and tuning_ablation.tune) with identical random draws."""
    rng = np.random.default_rng(seed)
    T = room.PROTOCOL['tuning']
    turns = min(SWEEP_TURNS, int((scene['prefix']-scene['warm'])/FS*SWEEP_HZ))
    fixed, rows = [], []
    if turns < 1:
        return fixed, [{'skipped': 'tuning part shorter than one sweep turn'}]
    player = ab.IntervalPlayer(scene, LEAD, fixed)
    for tone in scene['tones']:
        w = tone['w']
        start = abs(w)*10**rng.uniform(-np.log10(T['start_gain_factor_max']), np.log10(T['start_gain_factor_max']))
        max_gain = min(start*T['gain_range_factor'], T['max_gain_drive_fraction_of_cap']*room.PROTOCOL['levels']['peak_cap']/tone['mic_amplitude'])
        session = DecisionSession(tone['frequency'], start, min_gain=start/T['gain_range_factor'], max_gain=max_gain,
                                  sweep_turns=turns, seed=int(rng.integers(1 << 30)), search=search, sequential=sequential)
        run(session, player, SimulatedListener(FS, sigma, seed=int(rng.integers(1 << 30))))
        fixed.append(session.result())
        summary = session.summary()
        summary.update(start_gain=start, check_mic_changes_db=[])
        rows.append(summary)
    return fixed, rows


# ---------------- protocol ----------------
FILES = ['anc_lab/tuning_decision.py', 'tests/test_tuning_decision.py', 'anc_lab/tuning_ablation.py',
         'anc_lab/tuning.py', 'anc_lab/antihum_study.py', 'anc_lab/antihum.py', 'anc_lab/selector_room_scoring.py',
         'anc_lab/selector_room_study.py', 'anc_lab/selector_room_stream.py', 'anc_lab/selector_compatibility.py',
         'anc_lab/tuning_accuracy_diagnostic.py', 'docs/TUNING_DECISION.md']


def freeze():
    ab.verified()
    assert not STUDY.exists(), 'Never overwrite a decision run'
    previous = h.read(ab.STUDY/'protocol.json')
    cases = []
    for c in previous['cases']:
        seeds = seeds_for(c['case_id'], c['seeds'][0])
        assert seeds[:len(c['seeds'])] == c['seeds']
        cases.append({**c, 'seeds': seeds})
    protocol = {
        'created_utc': now(), 'kind': 'posthoc_development_decision_study',
        'scope': 'The 37 eligible rooms (78 tones, 14 sources) of results-tuning-ablation-01, seen development data, 30 ms lead, v2 forecasts. No new audio, no physical output, no live change.',
        'motivation': 'Ablation-01: the search change improved settings (phase error 37.6 -> 26.3 deg) but the room measure was swamped by keep/mute decisions; the microphone gate removed harmful keeps but muted 22% of tones as inconclusive.',
        'arms': {'O': 'Original tuner.', 'S': 'Ablation-01 search change, original check.',
                 'D': 'Original search, sequential check.', 'SD': 'Search change and sequential check.'},
        'sequential_check': f'Up to {MAX_PAIRS} on/off pairs of 2 s intervals (order default_rng([session seed, 2])). Per pair, the log-likelihood ratio of effect -{EFFECT_DB} dB against 0 dB, given the answer and the microphone ERB-band level of the on interval minus the off interval, under a Gaussian listener with assumed sigma {ASSUMED_SIGMA_DB} dB, same threshold {SAME_DB} dB and microphone error {MIC_ERROR_DB} dB. Keep at sum >= ln((1-b)/a) = {UPPER:.4f}, mute at <= ln(b/(1-a)) = {LOWER:.4f}, a = b = {ALPHA}; after {MAX_PAIRS} pairs keep only if the sum is > 0. All constants set from the listener model before any room was scored with this rule.',
        'deployability': 'Reads only the listener answers and the laptop microphone over already-heard intervals. The simulated microphone has no earphone leakage and its background follows the same source as the ear. The assumed sigma stays 1 dB in the 0.5 and 2 dB listener runs (model mismatch).',
        'seeds': f'{SEEDS} per room: seeds 0-4 are ablation-01\'s, 5-9 new from sha256(case_id-k). Same seeds for every arm and noise level.',
        'parity': 'Arms O and S must reproduce ablation-01 settings exactly for seeds 0-4 at every noise level, and O must reproduce the saved v2 tuning on the recorded seed.',
        'metrics': {
            'primary': 'Tone-level decision quality: per room and seed, the mean over the room\'s tones of the capped single-tone scored-suffix ERB attenuation (muted tones count 0). Chosen because ablation-01 showed the whole-room band measure is dominated by one room\'s single strong tone.',
            'guards': 'Whole-room scored-suffix 35-350 Hz band attenuation (band_db), harmful keeps (kept, single-tone prefix ERB attenuation < -1e-9 dB), room harms (band_db < -0.1 dB or third-octave boost > 0.5 dB).',
            'secondary': 'Useful keeps, missed opportunities, phase/gain error, pairs and listening seconds, as in ablation-01.',
        },
        'aggregation': f'Paired differences per room and seed, averaged over seeds per room, rooms per source, then the 14 sources; 95% percentile interval from {BOOTSTRAP} source-bootstrap resamples (seed {BOOTSTRAP_SEED}). Comparisons: each arm minus O; SD minus S (effect of the decision on top of the search).',
        'decision': 'At listener sigma 1, SD "helps" only if (1) the lower 95% bound of its mean paired tone-level gain over O is above 0, (2) its harmful keeps are no more than O\'s, (3) its room harms are no more than O\'s, and (4) its mean paired whole-room band_db difference over O is at least -0.05 dB. The same rule is reported for D and S. Sigma 0.5 and 2 are descriptive. Every arm is reported whatever the outcome.',
        'caveats': 'Seen development data: this chooses a candidate, it is not a fresh validation. The simulated listener is an assumption. No physical ANC is claimed.',
        'cases': cases,
        'code_sha256': {name: h.sha(ROOT/name) for name in FILES},
        'ablation_protocol_sha256': h.sha(ab.STUDY/'protocol.json'),
        'ablation_summary_sha256': h.sha(ab.STUDY/'summary.json'),
        'oracle_results_sha256': h.sha(diag.STUDY/'oracle-results.json'),
    }
    STUDY.mkdir()
    h.write_new(STUDY/'protocol.json', protocol)
    h.write_new(STUDY/'frozen.json', {'sha256': h.sha(STUDY/'protocol.json')})
    print(json.dumps({'protocol_sha256': h.sha(STUDY/'protocol.json'), 'rooms': len(cases)}), flush=True)


def verified():
    p = h.read(STUDY/'protocol.json')
    assert h.sha(STUDY/'protocol.json') == h.read(STUDY/'frozen.json')['sha256']
    for name, digest in p['code_sha256'].items():
        assert h.sha(ROOT/name) == digest, name
    assert h.sha(ab.STUDY/'summary.json') == p['ablation_summary_sha256']
    return p


# ---------------- scoring ----------------
def score_case(c, oracle):
    scene, meta, saved = diag.load(c)
    bases = ab.tone_bases(scene)
    previous = h.read(ab.STUDY/'cases'/(c['case_id']+'.json'))
    old = {(r['sigma'], r['seed_index'], r['arm']): r for r in previous['runs']}
    runs, parity = [], 0
    for sigma in SIGMAS:
        for k, seed in enumerate(c['seeds']):
            for arm, (search, sequential) in ARMS.items():
                settings, summaries = tune(scene, seed, sigma, search, sequential)
                if arm in ('O', 'S') and (sigma, k, arm) in old:
                    assert [asdict(s) for s in settings] == old[(sigma, k, arm)]['settings']
                    parity += len(settings)+1
                if arm == 'O' and sigma == 1. and k == 0:
                    parity += diag.numbers_equal([asdict(s) for s in settings], saved['v2_settings'])
                metrics, _ = scoring.evaluate(scene, settings, LEAD, 'v2', meta['reference_tones_hz'])
                tones = ab.tone_rows(scene, summaries, bases, oracle)
                for t, s in zip(tones, summaries):
                    t.update(check_evidence=s.get('check_evidence'), check_backgrounds_db=s.get('check_backgrounds_db'))
                runs.append({'sigma': sigma, 'seed_index': k, 'seed': seed, 'arm': arm,
                             'settings': [asdict(s) for s in settings], 'room': metrics, 'tones': tones})
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
def tone_level(run):
    return float(np.mean([t['final_effect']['suffix_erb_db'] for t in run['tones']]))


def paired(runs, arm, base, value):
    out = {}
    for (case, k, a), (source, r) in runs.items():
        if a == arm:
            out.setdefault(source, {}).setdefault(case, []).append(value(r)-value(runs[(case, k, base)][1]))
    return ab.source_means(out)


def summarize():
    p = verified()
    assert (STUDY/'run-complete.json').exists()
    cases = [h.read(STUDY/'cases'/(c['case_id']+'.json')) for c in p['cases']]
    assert all(c['parity_fields'] > 0 for c in cases)
    out, table = {'parity_fields': sum(c['parity_fields'] for c in cases), 'by_sigma': {}}, []
    band = lambda r: r['room']['band_db']
    for sigma in SIGMAS:
        runs = {(c['case_id'], r['seed_index'], r['arm']): (c['source_id'], r) for c in cases for r in c['runs'] if r['sigma'] == sigma}
        stats = {}
        for i, arm in enumerate(ARMS):
            rng = lambda j: np.random.default_rng([BOOTSTRAP_SEED, int(sigma*10), i, j])
            counts, phase_err, seconds, pairs = Counter(), [], [], []
            for (case, k, a), (source, r) in runs.items():
                if a != arm:
                    continue
                counts['room_runs'] += 1
                counts['room_harms'] += ab.room_harm(r['room'])
                for t in r['tones']:
                    oracle = t.get('bounded_oracle_prefix_db', -np.inf)
                    counts['tones'] += 1
                    counts['kept'] += t['kept']
                    counts['harmful_keeps_prefix'] += t['kept'] and t['final_effect']['prefix_erb_db'] < -1e-9
                    counts['harmful_keeps_suffix'] += t['kept'] and t['final_effect']['suffix_erb_db'] < -1e-9
                    counts['useful_keeps'] += t['kept'] and t['final_effect']['prefix_erb_db'] >= USEFUL_DB
                    counts['useful_precheck'] += t['precheck_effect']['prefix_erb_db'] >= USEFUL_DB
                    counts['useful_precheck_muted'] += (not t['kept']) and t['precheck_effect']['prefix_erb_db'] >= USEFUL_DB
                    counts['missed_opportunities'] += (not t['kept']) and oracle >= USEFUL_DB
                    if t['identifiable']:
                        phase_err.append(abs(t['phase_error_deg']))
                    seconds.append(t['listening_seconds'])
                    if t['check_pairs'] is not None:
                        pairs.append(t['check_pairs'])
                    table.append({'sigma': sigma, 'arm': arm, 'case_id': case, 'source_id': source, 'seed_index': k,
                                  'tone_index': t['tone_index'], 'frequency_hz': t['frequency'], 'kept': t['kept'],
                                  'phase_error_deg': t.get('phase_error_deg'),
                                  'precheck_prefix_erb_db': t['precheck_effect']['prefix_erb_db'],
                                  'precheck_suffix_erb_db': t['precheck_effect']['suffix_erb_db'],
                                  'final_suffix_erb_db': t['final_effect']['suffix_erb_db'],
                                  'bounded_oracle_prefix_db': t.get('bounded_oracle_prefix_db'),
                                  'check_pairs': t['check_pairs'], 'check_evidence': t['check_evidence'],
                                  'listening_seconds': t['listening_seconds'], 'flags': '; '.join(t['flags']),
                                  'room_band_db': r['room']['band_db']})
            level = {}
            for (case, k, a), (source, r) in runs.items():
                if a == arm:
                    level.setdefault(source, {}).setdefault(case, []).append(tone_level(r))
            stats[arm] = {'tone_level_db': ab.bootstrap(ab.source_means(level), rng(0)),
                          'tone_level_minus_O': ab.bootstrap(paired(runs, arm, 'O', tone_level), rng(1)),
                          'band_db_minus_O': ab.bootstrap(paired(runs, arm, 'O', band), rng(2)),
                          'counts': dict(counts),
                          'median_abs_phase_error_deg': float(np.median(phase_err)),
                          'mean_listening_seconds_per_tone': float(np.mean(seconds)),
                          'mean_check_pairs': float(np.mean(pairs)) if pairs else None}
        stats['SD_minus_S'] = {'tone_level': ab.bootstrap(paired(runs, 'SD', 'S', tone_level), np.random.default_rng([BOOTSTRAP_SEED, int(sigma*10), 7])),
                               'band_db': ab.bootstrap(paired(runs, 'SD', 'S', band), np.random.default_rng([BOOTSTRAP_SEED, int(sigma*10), 8]))}
        for arm in ('S', 'D', 'SD'):
            s, o = stats[arm], stats['O']
            s['helps'] = bool(s['tone_level_minus_O']['ci95'][0] > 0
                              and s['counts']['harmful_keeps_prefix'] <= o['counts']['harmful_keeps_prefix']
                              and s['counts']['room_harms'] <= o['counts']['room_harms']
                              and s['band_db_minus_O']['mean'] >= -.05)
        out['by_sigma'][f'{sigma:g}'] = stats
    out['decision_sigma'] = '1'
    h.write_new(STUDY/'summary.json', out)
    with (STUDY/'tone-runs.csv').open('x', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['freeze', 'run', 'summarize'])
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        {'freeze': freeze, 'run': run_all, 'summarize': summarize}[args.stage]()
