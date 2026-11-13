"""Study 02: remove the line-finder forecaster's third-octave boosts (results-tone-forecaster-02).

Why: in results-tone-forecaster-01 the observer bank with the line finder
(bank_wide_lines + gate) beat v2 + gate at the tones on 8 of 8 test recordings
but had more third-octave boosts (a band 1 dB or more louder; 6 cases against
4), so v2 stayed in the engine. This study asks whether an output rule
(tone_floors.py) removes those boosts while keeping the tone gain.

Order, enforced in code:
1. Diagnosis and design used development material only: the study-01
   development recordings (results-tone-forecaster-01/split.json) and the
   development synthetic scenes. The trials are kept in
   results-tone-forecaster-02/diagnosis.
2. `run_development` scores the candidates and every comparator on that
   material and applies DEVELOPMENT_RULE, written before this formal run.
3. `freeze_protocol` writes protocol.json: the chosen candidate, the
   comparators, the code hashes, the fresh recordings (Commons title, SHA-1,
   size, licence, author) and the synthetic test frequencies, drawn at freeze
   time so a failed draw shows up before any test.
4. `run_test` runs once, after the fresh recordings are downloaded (with the
   user's approval) into FRESH_AUDIO. It refuses if the test folder exists, the
   code changed or a file's SHA-1 differs from the protocol. It scores every
   method on the fresh recordings (primary), on the study-01 test recordings
   (secondary: seen, they motivated this study) and on fresh synthetic scenes.

Reference-signal prediction only: no acoustic path, no playback, no ear measurement.
"""
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from threadpoolctl import threadpool_limits

from . import forecaster_study as s1
from .generalization import DEVELOPMENT, HELD_OUT, normalized_prefix
from .predictors import DirectPredictor
from .real_hum_study import ELECTRICAL, PREFIX_FRACTION, load_any, prominent_tones, tonal_fraction
from .release_study import draw_groups, gate_output, objective
from .selection_study import BLOCK, FS, SECONDS, TEST_GROUPS, TRAIN_END, VAL_END, frequency_extent, horizon_setup, scene_set, synthesize_scene
from .tone_floors import FloorToneBank, JointCheckBank
from .tone_forecasters import OnlineRidgeAR, ProminentLines, ToneObserverBank, stream_forecasts
from .tone_selection import SelectedToneForecaster, ToneSelector

ROOT = s1.ROOT
STUDY = ROOT/'results-tone-forecaster-02'
FRESH_AUDIO = ROOT/'external-audio'/'wikimedia-commons-fresh-02'
WORKERS = min(6, s1.WORKERS)            # 19 workers ran out of paging file on this laptop
FROZEN_CODE = s1.FROZEN_CODE+('tone_floors.py', 'forecaster_study_02.py', 'forecaster_report_02.py')

# ---------- fresh recordings: chosen by Commons metadata only, never downloaded before the freeze ----------

FRESH_RECORDINGS = [
    {'file':'Pump.ogg', 'title':'File:Pump.ogg', 'sha1':'67a50ed90d40716d360517fa5412728c4eb822ee',
     'bytes':577517, 'seconds':31.6, 'author':'ezwa', 'licence':'Public domain', 'acoustic':True},
    {'file':'The_Sound_of_MOXIE_at_Work_on_Mars_(PIA26041).wav', 'title':'File:The Sound of MOXIE at Work on Mars (PIA26041).wav',
     'sha1':'cbbe0a741f6e853715ff4985a6a2f3264a007571', 'bytes':7483896, 'seconds':74.8,
     'author':'NASA/JPL-Caltech/CNES/IRAP', 'licence':'Public domain', 'acoustic':True},
    {'file':'Montreal_Clock_Tower_clock_mechanism.flac', 'title':'File:Montreal Clock Tower clock mechanism.flac',
     'sha1':'6adfeface692fed477977c05b8d4f8fe50b3c05e', 'bytes':7541121, 'seconds':40.8, 'author':'Andy Mabbett',
     'licence':'CC BY-SA 4.0', 'acoustic':True},
    {'file':'Siemens_Combino_Engine_Sound.wav', 'title':'File:Siemens Combino Engine Sound.wav',
     'sha1':'a754053ed389eef7e6da6cddecad707e1518a5f5', 'bytes':21168500, 'seconds':120.0, 'author':'Dawidpl4553',
     'licence':'CC BY-SA 4.0', 'acoustic':True},
    {'file':'Lille_subway_noise.wav', 'title':'File:Lille subway noise.wav', 'sha1':'5376ed0fbe22dd059ce33e1d96b7b4c53df208a8',
     'bytes':285582, 'seconds':17.8, 'author':'Dazhoid', 'licence':'CC BY-SA 4.0', 'acoustic':True},
    {'file':'Stirling_marble_engine_000.ogg', 'title':'File:Stirling marble engine 000.ogg',
     'sha1':'d31d23b652caf123943cb85131d6407d03de1f14', 'bytes':790697, 'seconds':28.2, 'author':'Nkim5706',
     'licence':'CC BY-SA 3.0', 'acoustic':True},
    {'file':'Buzzing_Speakers.ogg', 'title':'File:Buzzing Speakers.ogg', 'sha1':'a308007758f44df3ae1f44f50f062192db19a400',
     'bytes':225881, 'seconds':17.3, 'author':'buzzingspeakers.com', 'licence':'CC BY-SA 3.0', 'acoustic':True},
    {'file':'60-hz.wav', 'title':'File:60-hz.wav', 'sha1':'43bb3a76e976d070677aaf8befb6c2100262dd0b',
     'bytes':1927246, 'seconds':20.1, 'author':'Rayo v.2.0', 'licence':'CC BY-SA 4.0', 'acoustic':False,
     'note':'How it was captured is not stated; it may be a generated tone. Kept out of the acoustic medians; its boosts still count.'},
]
FRESH_INDEPENDENCE = (
    'Independent of all earlier work in this project: the eight recordings were chosen by their Commons title, '
    'description, length, licence and author only. None was downloaded, played or analysed before this protocol was '
    'frozen, and no author also made a development recording or a study-01 recording.')


def fresh_path(entry, folder=FRESH_AUDIO):
    """The downloaded file, or None if it is absent. A present file must match the frozen SHA-1 and size."""
    path = Path(folder)/entry['file']
    if not path.exists():
        return None
    data = path.read_bytes()
    if len(data) != entry['bytes'] or hashlib.sha1(data).hexdigest() != entry['sha1']:
        raise ValueError(f"{entry['file']} differs from the frozen protocol (size or SHA-1).")
    return path

# ---------- methods ----------

BANK_KINDS = {'bank':ToneObserverBank, 'floor':FloorToneBank, 'joint':JointCheckBank}
CANDIDATES = [
    {'name':'floor_lines0.2', 'kind':'floor', 'nb_tau':0., 'lines':True, 'options':{'min_tau_lines_seconds':.2}},
    {'name':'joint', 'kind':'joint', 'nb_tau':0., 'lines':True, 'options':{}},
]
COMPARATORS = s1.COMPARATORS+[{'name':'bank_wide_lines', 'kind':'bank', 'nb_tau':0., 'lines':True}]
DEVELOPMENT_RULE = (
    'Written after the diagnostic trials on development material (results-tone-forecaster-02/diagnosis) and before '
    'the formal development run. Candidates, all gated: the line-finder bank with a 0.2 s memory floor for '
    'line-finder tones (floor_lines0.2), and the line-finder bank with the joint band check (joint). Eligible only '
    'if, on development material: (a) whole-band boosts (whole 35-350 Hz band below -0.5 dB at either horizon, any '
    'development recording) are no more than v2 + gate has; (b) third-octave boosts (a third-octave band 1 dB or more '
    'louder, any development recording and horizon) are no more than v2 + gate has and fewer than bank_wide_lines + '
    'gate has; (c) near-boosts (a band 0.5 dB or more louder, same cases) are fewer than v2 + gate has and fewer than '
    'bank_wide_lines + gate has, a margin because study 01\'s candidate passed (b) on development and failed it on test; '
    '(d) third-octave boosts in the late windows of the synthetic development scenes are fewer than v2 + gate has and '
    'fewer than bank_wide_lines + gate has; (e) the tone gain is kept: the median, over development acoustic recordings '
    'with reference tones, of the tone-bin gain averaged over both horizons is at least v2 + gate\'s plus half of the '
    'amount by which bank_wide_lines + gate exceeds v2 + gate; (f) the median whole-band gain over development acoustic '
    'recordings, averaged over both horizons, is at least v2 + gate\'s minus 0.1 dB; (g) the mean synthetic development '
    'objective is at least v2 + gate\'s minus 0.5 dB and its synthetic windows below -0.5 dB are no more than v2 + gate '
    'has; (h) its own compute time per 10 ms block, excluding the tone-selector update that v2 also runs, is below 5 ms '
    'at the 99th percentile on every development recording and scene (offline Python, one thread, measured under the '
    'parallel pool). Among eligible candidates, pick the one with the fewest near-boosts (development recordings plus '
    'late synthetic windows, 0.5 dB or more); ties go to the higher tone-bin median. If none is eligible, no candidate '
    'is frozen and v2 stays.')
PRIMARY_QUESTION = (
    'On the fresh recordings, (1) are the boosts gone: does the frozen candidate + gate have no more third-octave '
    'boosts (a band 1 dB or more louder, any fresh recording, either horizon) and no more whole-band boosts than '
    'v2 + gate? (2) Is the tone gain kept: is its median tone-bin gain at 20 ms, over the fresh acoustic recordings '
    'with reference tones, above v2 + gate\'s? The two parts are answered separately. bank_wide_lines + gate, the '
    'study-01 candidate, is reported alongside so the report can say how much of its gain survives.')


def make_bank(method, v2):
    return BANK_KINDS[method['kind']](FS, BLOCK, ToneSelector(FS, **v2['selector']), nb_tau=method['nb_tau'],
                                      release={'ratio':v2['forecaster']['release_ratio'],
                                               'seconds':v2['forecaster']['release_window_seconds']},
                                      release_long_seconds=v2['forecaster']['window_seconds'],
                                      candidates=ProminentLines() if method.get('lines') else None,
                                      **method.get('options', {}))


def run_methods(x, grid, keep, methods, v2, train_end):
    """As forecaster_study.run_methods, with the tone_floors banks as further bank kinds."""
    _, horizons, groups = horizon_setup()
    preds, info = {'zero':np.zeros((int(keep.sum()), len(horizons)))}, {}
    for m in methods:
        started, extra = time.perf_counter(), {}
        if m['kind'] == 'v2' or m['kind'] in BANK_KINDS:
            if m['kind'] == 'v2':
                fc = SelectedToneForecaster(FS, ToneSelector(FS, **v2['selector']), window_seconds=m['window_seconds'],
                                            release_ratio=v2['forecaster']['release_ratio'],
                                            release_window_seconds=v2['forecaster']['release_window_seconds'])
                shadow = fc.predict(x, grid, horizons)
                extra = {'fast_drops':fc.fast_drops, 'forecast_ms_per_origin':1e3*fc.predict_seconds_per_origin}
            else:
                bank = make_bank(m, v2)
                shadow = stream_forecasts(bank, x, grid, horizons)
                b, own = 1e3*bank.block_seconds, 1e3*bank.block_seconds_own
                extra = {'block_ms_mean':float(b.mean()), 'block_ms_p99':float(np.percentile(b, 99)),
                         'block_ms_max':float(b.max()), 'own_block_ms_mean':float(own.mean()),
                         'own_block_ms_p99':float(np.percentile(own, 99)), 'own_block_ms_max':float(own.max()),
                         'counters':bank.counters, 'seconds_by_part':{k:round(v, 4) for k, v in bank.timing.items()},
                         'settings':bank.settings()}
            gated, enabled = gate_output(x, grid, shadow, groups, v2['gate'])
            preds[m['name']+'_ungated'], preds[m['name']+'_gated'] = shadow[keep], gated[keep]
            extra['gate_open_fraction'] = enabled[keep].mean(axis=0).tolist()
        elif m['kind'] == 'prefix_ar':
            preds[m['name']] = DirectPredictor('ridge_ar', horizons, seed=7).fit(x, train_end).predict(x, grid[keep], horizons)
        elif m['kind'] == 'online_ar':
            ar = OnlineRidgeAR(FS, horizons)
            preds[m['name']] = ar.predict(x, grid[keep], horizons)
            extra = {'refits':ar.fit_count, 'settings':ar.settings()}
        else:
            raise ValueError(m['kind'])
        extra['seconds'] = time.perf_counter()-started
        info[m['name']] = extra
    return preds, info


def method_names(methods):
    names = ['zero']
    for m in methods:
        names += [m['name']+'_ungated', m['name']+'_gated'] if m['kind'] == 'v2' or m['kind'] in BANK_KINDS else [m['name']]
    return names

# ---------- tasks (as forecaster_study's, with this module's methods) ----------

def _recording_task(args):
    path, methods, v2, acoustic = args
    path = Path(path)
    with threadpool_limits(limits=1):
        audio, info = load_any(path)
        prefix = int(PREFIX_FRACTION*len(audio))
        x = (audio-float(np.mean(audio[:prefix])))/max(float(np.std(audio[:prefix])), 1e-12)
        _, horizons, _ = horizon_setup()
        grid = np.arange(BLOCK*50, len(x)-int(max(horizons)), BLOCK)
        keep = grid >= prefix
        preds, method_info = run_methods(x, grid, keep, methods, v2, prefix)
        tones = prominent_tones(x[prefix:])
        fraction = tonal_fraction(x[prefix:], tones)
        # 'electrical_not_acoustic' keeps forecaster_study's summaries working; here it means "not a known acoustic capture".
        return {'file':path.name, 'electrical_not_acoustic':not acoustic, 'audio':info,
                'analysed_seconds':len(x)/FS, 'prefix_seconds':prefix/FS, 'test_seconds':(len(x)-prefix)/FS,
                'reference_tones_hz':tones, 'reference_tone_band_power_fraction':fraction,
                'tone_only_ceiling_db':float(-10*np.log10(max(1-fraction, 1e-6))),
                'methods':method_info, 'scores':s1.score_forecasts(x, grid[keep], preds, tones)}


def _scene_task(args):
    name, family, spec, seed, x, methods, v2 = args
    with threadpool_limits(limits=1):
        if x is None:
            raw = synthesize_scene(spec, seed) if family == 'standard' else s1.synthesize_wander(spec, seed)
            x, _ = normalized_prefix(raw, TRAIN_END)
        _, horizons, groups = horizon_setup()
        grid = np.arange(BLOCK*50, SECONDS*FS-int(max(horizons)), BLOCK)
        preds, method_info = run_methods(x, grid, np.ones(len(grid), bool), methods, v2, TRAIN_END)
        late = grid >= VAL_END
        steady = [tn['freq'] for tn in spec['tones'] if not tn['drift_hz_per_s'] and tn['start'] == 0 and tn['stop'] >= SECONDS]
        rows = s1.score_forecasts(x, grid[late], {m:p[late] for m, p in preds.items()}, steady)
        objectives = {}
        for m, p in preds.items():
            if m in ('prefix_ar', 'zero'):
                continue
            value, gains = objective(x, spec, grid, p, groups)
            objectives[m] = {'objective_db':value, 'window_gains_db':gains,
                             'windows_below_minus_half_db':int(sum(g < -.5 for g in gains))}
        return {'scene':name, 'family':family, 'seed':seed, 'spec':spec, 'methods':method_info,
                'late_window_scores':rows, 'objective':objectives}

# ---------- summaries and the development rule ----------

NEAR_DB = .5


def near_boosts(records, method):
    """(file, horizon, largest band change) for every case with a third-octave band NEAR_DB or more louder."""
    return [{'file':r['file'], 'horizon_start_ms':s['horizon_start_ms'], 'max_change_db':s['max_third_octave_change_db']}
            for r in records for s in r['scores'] if s['method'] == method and s['max_third_octave_change_db'] >= NEAR_DB]


def summarize(records, scenes, names):
    rec = s1.recording_summary(records, names) if records else {}
    for m in rec:
        rec[m]['near_boosts'] = near_boosts(records, m)
    syn, fams = s1.scene_summary(scenes, names) if scenes else ({}, {})
    for m in syn:
        late = [s for sc in scenes for s in sc['late_window_scores'] if s['method'] == m]
        syn[m]['late_near_boosts'] = int(sum(s['max_third_octave_change_db'] >= NEAR_DB for s in late))
    return rec, syn, fams


def apply_development_rule(rec, syn, records, scenes, candidates):
    timing = {c['name']:max(r['methods'][c['name']]['own_block_ms_p99'] for r in records+scenes) for c in candidates}
    v2, bwl = rec['v2_gated'], rec['bank_wide_lines_gated']
    v2s, bwls = syn['v2_gated'], syn['bank_wide_lines_gated']
    tone_floor = v2['median_tone_bin_both_horizons_db']+.5*(bwl['median_tone_bin_both_horizons_db']-v2['median_tone_bin_both_horizons_db'])
    table = []
    for c in candidates:
        m = c['name']+'_gated'
        r, s = rec[m], syn[m]
        checks = {
            'a_whole_band_boosts':len(r['whole_band_boosts']) <= len(v2['whole_band_boosts']),
            'b_third_octave_boosts':(len(r['third_octave_boosts']) <= len(v2['third_octave_boosts'])
                                     and len(r['third_octave_boosts']) < len(bwl['third_octave_boosts'])),
            'c_near_boosts':len(r['near_boosts']) < len(v2['near_boosts']) and len(r['near_boosts']) < len(bwl['near_boosts']),
            'd_synthetic_late_boosts':(s['late_third_octave_boosts'] < v2s['late_third_octave_boosts']
                                       and s['late_third_octave_boosts'] < bwls['late_third_octave_boosts']),
            'e_tone_gain_kept':r['median_tone_bin_both_horizons_db'] >= tone_floor,
            'f_whole_band':r['median_whole_band_both_horizons_db'] >= v2['median_whole_band_both_horizons_db']-.1,
            'g_synthetic':(s['mean_objective_db'] >= v2s['mean_objective_db']-.5
                           and s['windows_below_minus_half_db'] <= v2s['windows_below_minus_half_db']),
            'h_time':timing[c['name']] < 5.}
        table.append({'candidate':c['name'], 'tone_bin_median_db':r['median_tone_bin_both_horizons_db'],
                      'tone_bin_needed_db':tone_floor, 'whole_band_median_db':r['median_whole_band_both_horizons_db'],
                      'third_octave_boosts':len(r['third_octave_boosts']), 'near_boosts':len(r['near_boosts']),
                      'synthetic_late_boosts':s['late_third_octave_boosts'], 'synthetic_late_near_boosts':s['late_near_boosts'],
                      'synthetic_objective_db':s['mean_objective_db'], 'p99_block_ms':timing[c['name']],
                      'checks':checks, 'eligible':all(checks.values())})
    eligible = [t for t in table if t['eligible']]
    pick = min(eligible, key=lambda t: (t['near_boosts']+t['synthetic_late_near_boosts'], -t['tone_bin_median_db']))['candidate'] if eligible else None
    reference = {name:{'third_octave_boosts':len(rec[name+'_gated']['third_octave_boosts']),
                       'near_boosts':len(rec[name+'_gated']['near_boosts']),
                       'synthetic_late_boosts':syn[name+'_gated']['late_third_octave_boosts'],
                       'synthetic_late_near_boosts':syn[name+'_gated']['late_near_boosts'],
                       'tone_bin_median_db':rec[name+'_gated']['median_tone_bin_both_horizons_db'],
                       'whole_band_median_db':rec[name+'_gated']['median_whole_band_both_horizons_db'],
                       'synthetic_objective_db':syn[name+'_gated']['mean_objective_db'],
                       'synthetic_windows_below_minus_half_db':syn[name+'_gated']['windows_below_minus_half_db']}
                 for name in ('v2', 'bank_wide_lines')}
    return pick, table, reference

# ---------- stages ----------

def _code_hashes():
    here = Path(__file__).parent
    return {name:hashlib.sha256((here/name).read_bytes()).hexdigest() for name in FROZEN_CODE}


def _pool(jobs, workers):
    with ProcessPoolExecutor(workers) as pool:
        futures = [pool.submit(fn, args) for fn, args in jobs]
        return [f.result() for f in futures]


def run_development(output, candidates=CANDIDATES, workers=WORKERS, note=None):
    """Development only: the study-01 development recordings and development synthetic scenes."""
    output = s1._fresh(output)
    split = s1.load_split()
    v2 = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
    methods = COMPARATORS+list(candidates)
    started = time.perf_counter()
    paths = [s1.checked_path(e) for e in split['development_files']]
    test_names = {e['file'] for e in split['test_files']}|{e['file'] for e in FRESH_RECORDINGS}
    if any(p.name in test_names for p in paths):
        raise ValueError('A test recording reached development.')
    draws, wander, scene_tasks = s1.development_scenes()
    n = len(paths)
    out = _pool([(_recording_task, (str(p), methods, v2, p.name not in ELECTRICAL)) for p in paths]
                + [(_scene_task, (*t, methods, v2)) for t in scene_tasks], workers)
    records, scenes = out[:n], out[n:]
    names = method_names(methods)
    rec, syn, fams = summarize(records, scenes, names)
    pick, table, reference = apply_development_rule(rec, syn, records, scenes, candidates)
    result = {'kind':'tone_forecaster_02_development', 'created_utc':datetime.now(timezone.utc).isoformat(),
              'stage':'development only; no test recording, fresh recording or test scene was read', 'note':note, 'v2':v2,
              'candidates':list(candidates), 'comparators':COMPARATORS, 'rule':DEVELOPMENT_RULE,
              'development_files':[p.name for p in paths], 'release_development_draws':draws,
              'wander_development_draws':wander, 'recordings':records, 'scenes':scenes,
              'summary':{'recordings':rec, 'synthetic':syn, 'synthetic_by_family':fams},
              'rule_table':table, 'rule_reference':reference, 'development_pick':pick,
              'runtime_seconds':time.perf_counter()-started, 'code_sha256':_code_hashes(),
              'labels':'Reference-signal prediction only. Not acoustic attenuation.'}
    (output/'development.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    from .forecaster_report_02 import write_development_summary
    write_development_summary(output, result)
    return result


SYNTHETIC_TEST = {'standard_seed':20261020, 'standard_repeats':3, 'standard_scene_seeds':'10100+100*repeat+scene index',
                  'wander_seed':20261021, 'wander_repeats':3, 'wander_scene_seeds':'11100+100*repeat+scene index',
                  'parity':1, 'parity_note':'odd 10 Hz bands (development used even)', 'forbidden_within_hz':2.}


def development_frequencies(release, wander_dev):
    """Every frequency a development scene used (the same list as study 01's amended protocol)."""
    out = ([f for g in release['development_draws'] for f in frequency_extent(g)]
           + [f for g in wander_dev for fs in g.values() for f in fs]
           + frequency_extent(TEST_GROUPS)+[f for g in DEVELOPMENT for f in g]+[f for g in HELD_OUT.values() for f in g])
    return sorted(set(round(f, 2) for f in out))


def draw_synthetic_test(syn, forbidden):
    rng = np.random.default_rng(syn['standard_seed'])
    standard = [draw_groups(rng, syn['parity'], forbidden) for _ in range(syn['standard_repeats'])]
    rng = np.random.default_rng(syn['wander_seed'])
    wander = [s1.draw_wander(rng, syn['parity'], forbidden) for _ in range(syn['wander_repeats'])]
    used = [f for g in standard for f in frequency_extent(g)]+[f for g in wander for fs in g.values() for f in fs]
    if any(abs(a-b) <= syn['forbidden_within_hz'] for a in used for b in forbidden):
        raise ValueError('Test draw is not fresh.')
    return standard, wander


def freeze_protocol(development_folder, output=STUDY/'protocol.json'):
    """Write the frozen protocol from a development run. Refuses to overwrite."""
    output = Path(output)
    if output.exists():
        raise ValueError('protocol.json already exists; the protocol is frozen once.')
    dev = json.loads((Path(development_folder)/'development.json').read_text(encoding='utf-8'))
    if dev['code_sha256'] != _code_hashes():
        raise ValueError('Code changed after the development run; rerun development before freezing.')
    split = s1.load_split()
    chosen = next((c for c in dev['candidates'] if c['name'] == dev['development_pick']), None)
    release = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))
    forbidden = development_frequencies(release, dev['wander_development_draws'])
    syn = dict(SYNTHETIC_TEST, forbidden_frequencies=forbidden,
               not_excluded=('The study-01 and release-study test draws are not excluded: no study-02 choice used them, '
                             'and excluding the study-01 test draws as well within 2 Hz leaves no room in either band '
                             'parity (checked with a draw before this freeze).'))
    standard, wander = draw_synthetic_test(syn, forbidden)
    syn.update(standard_draws=standard, wander_draws=wander)
    protocol = {'kind':'tone_forecaster_02_frozen_protocol', 'created_utc':datetime.now(timezone.utc).isoformat(),
                'development_run':str(Path(development_folder).resolve().relative_to(ROOT)), 'rule':dev['rule'],
                'rule_table':dev['rule_table'], 'rule_reference':dev['rule_reference'], 'frozen_candidate':chosen,
                'frozen_candidate_note':None if chosen else 'No candidate met the rule; v2 stays and the test reports comparators only.',
                'comparators':dev['comparators'], 'v2':dev['v2'],
                'fresh_recordings':FRESH_RECORDINGS, 'fresh_folder':str(FRESH_AUDIO.relative_to(ROOT)),
                'fresh_independence':FRESH_INDEPENDENCE,
                'fresh_missing_rule':('A recording that cannot be downloaded is reported as missing and is not replaced; '
                                      'a present file whose size or SHA-1 differs stops the test.'),
                'seen_recordings':split['test_files'],
                'seen_note':('Secondary, not independent: the study-01 test recordings. Their study-01 boosts motivated this '
                             'study, but no study-02 choice was made on them.'),
                'synthetic_test':syn, 'primary_question':PRIMARY_QUESTION, 'code_sha256':_code_hashes()}
    output.write_text(json.dumps(protocol, indent=2), encoding='utf-8')
    return protocol


def test_scene_tasks(protocol):
    syn = protocol['synthetic_test']
    standard, wander = draw_synthetic_test(syn, syn['forbidden_frequencies'])
    if json.loads(json.dumps([standard, wander])) != [syn['standard_draws'], syn['wander_draws']]:
        raise ValueError('Synthetic test draws differ from the protocol.')
    tasks = []
    for rep, g in enumerate(standard):
        tasks += [(f'{n}#test{rep}', 'standard', s, 10100+100*rep+i, None) for i, (n, s) in enumerate(scene_set(g).items())]
    for rep, g in enumerate(wander):
        tasks += [(f'{n}#test{rep}', 'wander', s, 11100+100*rep+i, None) for i, (n, s) in enumerate(s1.wander_scene_set(g).items())]
    return tasks


def run_test(output=STUDY/'test', protocol_path=STUDY/'protocol.json', fresh_folder=FRESH_AUDIO, workers=WORKERS):
    """Runs once: fresh recordings (primary), study-01 test recordings (secondary, seen), fresh synthetic scenes."""
    output = Path(output)
    if output.exists():
        raise ValueError('The test stage has already run (its folder exists); it runs once.')
    protocol = json.loads(Path(protocol_path).read_text(encoding='utf-8'))
    if protocol['code_sha256'] != _code_hashes():
        raise ValueError('Code changed after the protocol was frozen.')
    fresh = [(e, fresh_path(e, fresh_folder)) for e in protocol['fresh_recordings']]
    present = [(e, p) for e, p in fresh if p is not None]
    if not present:
        raise ValueError('No fresh recording is present; the test cannot run.')
    seen = [s1.checked_path(e) for e in protocol['seen_recordings']]
    v2 = protocol['v2']
    methods = protocol['comparators']+([protocol['frozen_candidate']] if protocol['frozen_candidate'] else [])
    tasks = test_scene_tasks(protocol)
    output.mkdir(parents=True)
    started = time.perf_counter()
    jobs = ([(_recording_task, (str(p), methods, v2, e['acoustic'])) for e, p in present]
            + [(_recording_task, (str(p), methods, v2, p.name not in ELECTRICAL)) for p in seen]
            + [(_scene_task, (*t, methods, v2)) for t in tasks])
    out = _pool(jobs, workers)
    fresh_records, seen_records, scenes = out[:len(present)], out[len(present):len(present)+len(seen)], out[len(present)+len(seen):]
    names = method_names(methods)
    frec, syn, fams = summarize(fresh_records, scenes, names)
    srec, _, _ = summarize(seen_records, [], names)
    result = {'kind':'tone_forecaster_02_test', 'created_utc':datetime.now(timezone.utc).isoformat(), 'protocol':protocol,
              'fresh_files':[p.name for _, p in present], 'fresh_missing':[e['file'] for e, p in fresh if p is None],
              'fresh_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for _, p in present},
              'seen_files':[p.name for p in seen], 'fresh_recordings':fresh_records, 'seen_recordings':seen_records,
              'scenes':scenes, 'summary':{'fresh':frec, 'seen':srec, 'synthetic':syn, 'synthetic_by_family':fams},
              'runtime_seconds':time.perf_counter()-started,
              'labels':'Reference-signal prediction only. Not acoustic attenuation.'}
    (output/'test.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    from .forecaster_report_02 import write_test_report
    write_test_report(output.parent, result)
    return result
