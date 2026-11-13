"""In-band engine output study: phase-locked smoothing of each tone's phasor (development data). Never opens audio devices.

results-tuning-decision-01 (post hoc, posthoc-boost-source.json) found that the
remaining room harms are not bad tuning settings: the v2 renderer re-estimates
each tone's phasor every 10 ms block, so it also reproduces the room's own sound
a few hertz either side of the tone. With a 30 ms lead, content more than about
1/(6*lead) = 5.6 Hz from the tone arrives more than 60 degrees late and adds
instead of cancelling, lifting near-silent neighbouring third-octave bands.

This study smooths each tracked component's phasor causally in a frame that
rotates with the tone (a one-pole resonator, alpha per 10 ms block):

    P~[k] = alpha*P[k] + (1-alpha)*P~[prev]*exp(2j*pi*f_prev*dt*gap)

A steady tone passes unchanged; content away from the tone is attenuated.
States are matched to components within 2 Hz, last at most MAX_GAP blocks and
are cleared when the engine gate was off. Two bandwidths, both set from the
lead before any room was scored with retuning: alpha 0.3 (about 5.7 Hz, the
lead-limited band edge) and alpha 0.1 (about 1.7 Hz).

Arms: O and SD on v2 (reused from decision-01, parity rechecked), and the same
two tuners re-run on each smoothed engine.
"""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import argparse
import csv
import json

import numpy as np
from threadpoolctl import threadpool_limits

from . import selector_headroom as h
from . import selector_room_scoring as scoring
from . import tuning_accuracy_diagnostic as diag
from . import tuning_ablation as ab
from . import tuning_decision as td
from .antihum import FS, BLOCK

ROOT = h.ROOT
STUDY = ROOT/'results-engine-smoothing-01'
LEAD = ab.LEAD
ASSOCIATE_HZ = 2.
MAX_GAP = 10
ALPHAS = {'s30': .3, 's10': .1}
TUNERS = {'O': (False, False), 'SD': (True, True)}
ARMS = ['O', 'SD']+[f'{t}-{e}' for e in ALPHAS for t in TUNERS]
SIGMAS = td.SIGMAS
SEEDS = td.SEEDS
PARITY_SEEDS = (0, 1)
WORKERS = 30


def bandwidth_hz(alpha):
    """-3 dB half-width of the one-pole resonator, block rate FS/BLOCK."""
    return float(-np.log(1-alpha)*FS/BLOCK/(2*np.pi))


def smooth_arrays(arrays, alpha):
    """Causal phase-locked smoothing of every tracked component's phasor; other fields unchanged."""
    f, P, gate = arrays['frequency'], arrays['phasor'], arrays['gate']
    out = np.array(P, complex)
    dt = BLOCK/FS
    states = []  # [frequency, smoothed phasor, row]
    for k in range(len(f)):
        if k and not gate[k-1]:
            states = []
        states = [s for s in states if k-s[2] <= MAX_GAP]
        new = []
        for j in range(f.shape[1]):
            if np.isnan(f[k, j]) or P[k, j] == 0:
                continue
            match = None
            if states:
                d = [abs(s[0]-f[k, j]) for s in states]
                i = int(np.argmin(d))
                if d[i] <= ASSOCIATE_HZ:
                    match = states.pop(i)
            if match is not None:
                out[k, j] = alpha*P[k, j]+(1-alpha)*match[1]*np.exp(2j*np.pi*match[0]*dt*(k-match[2]))
            new.append([float(f[k, j]), out[k, j], k])
        states += new
    return {**arrays, 'phasor': out}


def engine_scene(scene, alpha):
    """The same room with the smoothed engine used by tuning, tone effects and scoring alike."""
    arrays = smooth_arrays(scene['arrays'], alpha)
    return {**scene, 'arrays': arrays, 'trace': {**scene['trace'], 'v2': arrays}}


# ---------------- protocol ----------------
FILES = ['anc_lab/engine_smoothing.py', 'tests/test_engine_smoothing.py', 'anc_lab/tuning_decision.py',
         'anc_lab/tuning_ablation.py', 'anc_lab/tuning.py', 'anc_lab/antihum_study.py', 'anc_lab/antihum.py',
         'anc_lab/selector_room_scoring.py', 'anc_lab/selector_room_study.py', 'anc_lab/selector_room_stream.py',
         'anc_lab/selector_compatibility.py', 'anc_lab/tuning_accuracy_diagnostic.py', 'docs/ENGINE_SMOOTHING.md']


def freeze():
    td.verified()
    assert not STUDY.exists(), 'Never overwrite a smoothing run'
    previous = h.read(td.STUDY/'protocol.json')
    protocol = {
        'created_utc': td.now(), 'kind': 'posthoc_development_engine_study',
        'scope': 'The 37 eligible rooms (78 tones, 14 sources) of results-tuning-decision-01, seen development data, 30 ms lead. No new audio, no physical output, no live change.',
        'motivation': 'Decision-01 post hoc: harmed rooms are near-silent neighbouring third-octave bands lifted by the v2 renderer reproducing off-tone room sound late; same kept tones give 16 vs 15 harms for the two tuners, so tuning cannot remove them.',
        'smoother': f'Per 10 ms block, each tracked component phasor P is replaced by alpha*P + (1-alpha)*S*exp(2j*pi*f_S*dt*gap), S the smoothed state of the nearest component within {ASSOCIATE_HZ} Hz seen at most {MAX_GAP} blocks ago; states cleared after a gate-off block. Causal, current and past blocks only.',
        'alphas': {e: {'alpha': a, 'half_bandwidth_hz': bandwidth_hz(a)} for e, a in ALPHAS.items()},
        'alpha_choice': 'Set from the lead: 1/(6*0.030 s) = 5.6 Hz is where a late copy starts to add; alpha 0.3 puts the -3 dB edge there, alpha 0.1 at about a third of it. A fixed-setting probe on six rooms with v2-tuned settings was looked at before freezing (worst third-octave boost in old-007-r0 1.11 -> 0.41 / 0.15 dB); no retuned room was scored.',
        'arms': {'O': 'Original tuner, v2 engine (decision-01 runs reused).', 'SD': 'Search change + sequential check, v2 engine (decision-01 runs reused).',
                 **{f'{t}-{e}': f'{"Original tuner" if t == "O" else "Search change + sequential check"}, re-tuned on the alpha {a} engine.' for e, a in ALPHAS.items() for t in TUNERS}},
        'parity': f'O and SD are recomputed for seeds {list(PARITY_SEEDS)} at sigma 1 and must equal decision-01 settings and room metrics exactly; all other v2 runs are copied from decision-01 case files (sha256 recorded).',
        'seeds': 'The 10 decision-01 seeds per room, same for every arm and noise level.',
        'metrics': 'As decision-01: primary tone level (mean over the room\'s tones of capped single-tone scored-suffix ERB attenuation, muted = 0), guards band_db, harmful keeps (prefix), room harms (band_db < -0.1 dB or third-octave boost > 0.5 dB). Per-tone oracle phase/gain errors and missed opportunities stay relative to the v2 oracle (labelled secondary).',
        'aggregation': 'Paired differences per room and seed, averaged over seeds per room, rooms per source, then 14 sources; 95% percentile interval from 10000 source-bootstrap resamples. Comparisons: every arm minus O; engine effect X-e minus X.',
        'decision': 'At sigma 1, SD-e "helps" only if (1) the lower 95% bound of its tone-level gain over O is above 0, (2) harmful keeps <= O, (3) room harms <= O, (4) mean band_db difference over O >= -0.05 dB. If both SD-s30 and SD-s10 help, the candidate is the one with the larger tone-level mean. The same rule is reported for O-e. Sigma 0.5 and 2 are descriptive. Every arm is reported whatever the outcome.',
        'caveats': 'Seen development data: this chooses a candidate, it is not a fresh validation. The engine change also alters the live renderer, whose compute timing is unmeasured. Simulated listener and microphone. No physical ANC is claimed.',
        'cases': previous['cases'],
        'code_sha256': {name: h.sha(ROOT/name) for name in FILES},
        'decision_protocol_sha256': h.sha(td.STUDY/'protocol.json'),
        'decision_summary_sha256': h.sha(td.STUDY/'summary.json'),
        'decision_case_sha256': {c['case_id']: h.sha(td.STUDY/'cases'/(c['case_id']+'.json')) for c in previous['cases']},
    }
    STUDY.mkdir()
    h.write_new(STUDY/'protocol.json', protocol)
    h.write_new(STUDY/'frozen.json', {'sha256': h.sha(STUDY/'protocol.json')})
    print(json.dumps({'protocol_sha256': h.sha(STUDY/'protocol.json'), 'rooms': len(protocol['cases'])}), flush=True)


def verified():
    p = h.read(STUDY/'protocol.json')
    assert h.sha(STUDY/'protocol.json') == h.read(STUDY/'frozen.json')['sha256']
    for name, digest in p['code_sha256'].items():
        assert h.sha(ROOT/name) == digest, name
    for case, digest in p['decision_case_sha256'].items():
        assert h.sha(td.STUDY/'cases'/(case+'.json')) == digest, case
    return p


# ---------------- scoring ----------------
def tuned_run(scene, meta, bases, oracle, sigma, k, seed, arm, search, sequential):
    settings, summaries = td.tune(scene, seed, sigma, search, sequential)
    metrics, _ = scoring.evaluate(scene, settings, LEAD, 'v2', meta['reference_tones_hz'])
    tones = ab.tone_rows(scene, summaries, bases, oracle)
    for t, s in zip(tones, summaries):
        t.update(check_evidence=s.get('check_evidence'), check_backgrounds_db=s.get('check_backgrounds_db'))
    return {'sigma': sigma, 'seed_index': k, 'seed': seed, 'arm': arm,
            'settings': [asdict(s) for s in settings], 'room': metrics, 'tones': tones}


def score_case(c, oracle):
    with threadpool_limits(limits=1):
        scene, meta, _ = diag.load(c)
        previous = h.read(td.STUDY/'cases'/(c['case_id']+'.json'))
        old = {(r['sigma'], r['seed_index'], r['arm']): r for r in previous['runs']}
        runs, parity = [], 0
        bases = ab.tone_bases(scene)
        for k in PARITY_SEEDS:
            for arm, (search, sequential) in TUNERS.items():
                r = tuned_run(scene, meta, bases, oracle, 1., k, c['seeds'][k], arm, search, sequential)
                ref = old[(1., k, arm)]
                assert r['settings'] == ref['settings'] and r['room'] == ref['room'], (c['case_id'], k, arm)
                parity += len(r['settings'])+len(r['room'])
        runs += [r for r in previous['runs'] if r['arm'] in TUNERS]
        for e, alpha in ALPHAS.items():
            s = engine_scene(scene, alpha)
            bases = ab.tone_bases(s)
            for sigma in SIGMAS:
                for k, seed in enumerate(c['seeds']):
                    for t, (search, sequential) in TUNERS.items():
                        runs.append(tuned_run(s, meta, bases, oracle, sigma, k, seed, f'{t}-{e}', search, sequential))
        return {'case_id': c['case_id'], 'source_id': c['source_id'], 'parity_fields': parity, 'runs': runs}


def run_all():
    p = verified()
    oracles = {o['case_id']: o['tones'] for o in h.read(diag.STUDY/'oracle-results.json')['cases']}
    dest = STUDY/'cases'
    dest.mkdir(exist_ok=False)
    h.write_new(STUDY/'run-start.json', {'started_utc': td.now(), 'protocol_sha256': h.sha(STUDY/'protocol.json'), 'workers': WORKERS})
    done = 0
    with ProcessPoolExecutor(WORKERS) as pool:
        jobs = {pool.submit(score_case, c, oracles[c['case_id']]): c['case_id'] for c in p['cases']}
        for job in as_completed(jobs):
            result = job.result()
            h.write_new(dest/(result['case_id']+'.json'), result)
            done += 1
            print(json.dumps({'case': result['case_id'], 'complete': done, 'of': len(p['cases']),
                              'parity_fields': result['parity_fields']}), flush=True)
    h.write_new(STUDY/'run-complete.json', {'completed_utc': td.now(), 'cases': len(p['cases'])})


# ---------------- summary ----------------
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
    boost = lambda r: r['room']['max_third_octave_amplification_db']
    for sigma in SIGMAS:
        runs = {(c['case_id'], r['seed_index'], r['arm']): (c['source_id'], r) for c in cases for r in c['runs'] if r['sigma'] == sigma}
        stats = {}
        for i, arm in enumerate(ARMS):
            rng = lambda j: np.random.default_rng([td.BOOTSTRAP_SEED, int(sigma*10), i, j])
            counts, seconds, pairs = Counter(), [], []
            for (case, k, a), (source, r) in runs.items():
                if a != arm:
                    continue
                counts['room_runs'] += 1
                counts['room_harms'] += ab.room_harm(r['room'])
                counts['third_octave_harms'] += r['room']['max_third_octave_amplification_db'] > ab.ROOM_HARM_THIRD_OCTAVE_DB
                counts['band_harms'] += r['room']['band_db'] < ab.ROOM_HARM_BAND_DB
                for t in r['tones']:
                    counts['tones'] += 1
                    counts['kept'] += t['kept']
                    counts['harmful_keeps_prefix'] += t['kept'] and t['final_effect']['prefix_erb_db'] < -1e-9
                    counts['harmful_keeps_suffix'] += t['kept'] and t['final_effect']['suffix_erb_db'] < -1e-9
                    counts['useful_keeps'] += t['kept'] and t['final_effect']['prefix_erb_db'] >= td.USEFUL_DB
                    seconds.append(t['listening_seconds'])
                    if t['check_pairs'] is not None:
                        pairs.append(t['check_pairs'])
                    table.append({'sigma': sigma, 'arm': arm, 'case_id': case, 'source_id': source, 'seed_index': k,
                                  'tone_index': t['tone_index'], 'frequency_hz': t['frequency'], 'kept': t['kept'],
                                  'precheck_prefix_erb_db': t['precheck_effect']['prefix_erb_db'],
                                  'final_suffix_erb_db': t['final_effect']['suffix_erb_db'],
                                  'check_pairs': t['check_pairs'], 'listening_seconds': t['listening_seconds'],
                                  'flags': '; '.join(t['flags']), 'room_band_db': r['room']['band_db'],
                                  'room_max_third_octave_db': r['room']['max_third_octave_amplification_db']})
            level = {}
            for (case, k, a), (source, r) in runs.items():
                if a == arm:
                    level.setdefault(source, {}).setdefault(case, []).append(td.tone_level(r))
            stats[arm] = {'tone_level_db': ab.bootstrap(ab.source_means(level), rng(0)),
                          'tone_level_minus_O': ab.bootstrap(paired(runs, arm, 'O', td.tone_level), rng(1)),
                          'band_db_minus_O': ab.bootstrap(paired(runs, arm, 'O', band), rng(2)),
                          'max_third_octave_minus_O': ab.bootstrap(paired(runs, arm, 'O', boost), rng(3)),
                          'counts': dict(counts),
                          'mean_listening_seconds_per_tone': float(np.mean(seconds)),
                          'mean_check_pairs': float(np.mean(pairs)) if pairs else None}
        for j, arm in enumerate(a for a in ARMS if '-' in a):
            base = arm.split('-')[0]
            rng = lambda m: np.random.default_rng([td.BOOTSTRAP_SEED, int(sigma*10), 50+j, m])
            stats[arm]['engine_effect'] = {'versus': base,
                                           'tone_level': ab.bootstrap(paired(runs, arm, base, td.tone_level), rng(0)),
                                           'band_db': ab.bootstrap(paired(runs, arm, base, band), rng(1)),
                                           'max_third_octave': ab.bootstrap(paired(runs, arm, base, boost), rng(2))}
        o = stats['O']
        for arm in ARMS[1:]:
            s = stats[arm]
            s['helps'] = bool(s['tone_level_minus_O']['ci95'][0] > 0
                              and s['counts']['harmful_keeps_prefix'] <= o['counts']['harmful_keeps_prefix']
                              and s['counts']['room_harms'] <= o['counts']['room_harms']
                              and s['band_db_minus_O']['mean'] >= -.05)
        out['by_sigma'][f'{sigma:g}'] = stats
    passing = [f'SD-{e}' for e in ALPHAS if out['by_sigma']['1'][f'SD-{e}']['helps']]
    out['candidate'] = max(passing, key=lambda a: out['by_sigma']['1'][a]['tone_level_minus_O']['mean']) if passing else None
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
