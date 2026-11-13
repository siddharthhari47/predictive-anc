"""Study 04: a softer realized-error gate on the joint band check (results-tone-forecaster-04).

Why: study 03 (results-tone-forecaster-03) traced the joint band check's 25
development boosts. 5 of them come from the v2 gate's on/off switching: on the
development buzz scenes the joint check had 2 late boosts with no gate and 7
with it. The gate zeros whole 10 ms blocks, and each switch spreads tone energy
into nearly empty low bands. The band check judges each setting before the
gate, so it cannot see this. This study asks whether a softer gate removes
those boosts without losing the check's tone gain over v2. tone_gate_fade.py
has the two remedies: a fade of the gate's decision over a few blocks, and a
band check that judges each setting after its own copy of the gate
(GatedCheckBank).

Order, enforced in code:
1. Diagnosis and design used development material only: the study-01
   development recordings, the 44 development synthetic scenes and study 03's
   8 buzz scenes. No study-01 test recording, study-02 fresh recording
   (Buzzing_Speakers.ogg included) or synthetic test scene was used. The
   trials are kept in results-tone-forecaster-04/diagnosis.
2. `run_development` scores the candidates and every comparator on that
   material and applies DEVELOPMENT_RULE, written after the trials and before
   this formal run.
3. `freeze_protocol` writes protocol.json once. With no candidate it records
   that and nothing is tested. With a candidate it records the fresh
   recordings, chosen by Commons metadata only after the development run and
   listed with each file's SHA-1 and size in FRESH_LIST (a data file, so the
   code hashes from the development run still hold), and draws the fresh
   synthetic scenes, so a failed draw shows up before any test.
4. `run_test` runs once, after the fresh recordings are downloaded (with the
   user's approval) into FRESH_AUDIO. It refuses if the test folder exists,
   the code changed, or a file's size or SHA-1 differs from the protocol.
5. `run_timing` times the bank and the fade one run at a time, outside the
   pool, on the development recordings, for a reading on a quieter machine.

Reference-signal prediction only: no acoustic path, no playback, no ear measurement.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
from threadpoolctl import threadpool_limits

from . import forecaster_study as s1
from . import forecaster_study_02 as fs2
from . import forecaster_study_03 as fs3
from .generalization import normalized_prefix
from .predictors import DirectPredictor
from .real_hum_study import ELECTRICAL, PREFIX_FRACTION, load_any, prominent_tones, tonal_fraction
from .release_study import objective
from .selection_study import BLOCK, FS, SECONDS, TRAIN_END, VAL_END, frequency_extent, horizon_setup, scene_set, synthesize_scene
from .tone_forecasters import OnlineRidgeAR, stream_forecasts
from .tone_gate_fade import BlockFade, GatedCheckBank, fade_gate_output
from .tone_selection import SelectedToneForecaster, ToneSelector

ROOT = s1.ROOT
STUDY = ROOT/'results-tone-forecaster-04'
FRESH_AUDIO = ROOT/'external-audio'/'wikimedia-commons-fresh-04'
FRESH_LIST = STUDY/'fresh-metadata'/'fresh_recordings.json'
WORKERS = fs2.WORKERS
FROZEN_CODE = fs3.FROZEN_CODE+('tone_gate_fade.py', 'forecaster_study_04.py', 'forecaster_report_04.py')

# forecaster_study_02.make_bank and method_names look bank kinds up in study 02's table (that file is frozen, so it
# is not edited). Registering here also registers in every worker, since workers import this module to run its tasks.
fs2.BANK_KINDS.setdefault('gated_check', GatedCheckBank)

# ---------- methods ----------

FADE8 = {'in_blocks':8, 'out_blocks':8, 'shape':'cosine'}
FADE8_IN_3_OUT = {'in_blocks':8, 'out_blocks':3, 'shape':'cosine'}
_CHECK = {'nb_tau':0., 'lines':True, 'options':{}}
# 'fade' is how the v2 gate's decision reaches the output: absent or None is the hard gate. A gated_check bank judges
# each setting after the same gate and fade as its output gets (make_bank passes both in).
CANDIDATES = [
    dict(_CHECK, name='joint_fade8', kind='joint', fade=FADE8),
    dict(_CHECK, name='joint_fade8in3out', kind='joint', fade=FADE8_IN_3_OUT),
    dict(_CHECK, name='gcheck', kind='gated_check', fade=None),
    dict(_CHECK, name='gcheck_fade8', kind='gated_check', fade=FADE8),
    dict(_CHECK, name='gcheck_fade8in3out', kind='gated_check', fade=FADE8_IN_3_OUT),
]
COMPARATORS = fs3.COMPARATORS+[{'name':'v2_fade8', 'kind':'v2', 'window_seconds':.3, 'fade':FADE8}]
DEVELOPMENT_RULE = (
    'Written after the diagnostic trials on development material (results-tone-forecaster-04/diagnosis) and before '
    'the formal development run. Candidates, all driven by the v2 gate\'s decision: the joint band check of study 02 '
    'with the gate faded instead of switched (a cosine fade over 8 blocks in and 8 out, joint_fade8; 8 in and 3 out, '
    'joint_fade8in3out; one block is 10 ms), and the band check that judges each setting after its own copy of the '
    'gate (tone_gate_fade.GatedCheckBank) with the hard gate (gcheck), the 8/8 fade (gcheck_fade8) and the 8/3 fade '
    '(gcheck_fade8in3out). Development material: the eight study-01 development recordings, the 44 development '
    'synthetic scenes and study 03\'s 8 buzz scenes. A boost is a third-octave band 1 dB or more louder; a near-boost '
    '0.5 dB or more; both are counted over development recordings (either horizon) plus late synthetic windows. '
    'Eligible only if: (a) fewer boosts than joint + gate; (b) the gate\'s boosts are gone: on the buzz scenes, no '
    'more late boosts than the joint check with no gate at all; (c) no more near-boosts than joint + gate; (d) no '
    'more whole-band boosts (whole 35-350 Hz band below -0.5 dB on a development recording) than joint + gate; (e) '
    'the tone gain over v2 is kept: the median, over development acoustic recordings with reference tones, of the '
    'tone-bin gain averaged over both horizons is at least v2 + gate\'s plus half of the amount by which joint + gate '
    'exceeds v2 + gate; (f) the median whole-band gain over development acoustic recordings, averaged over both '
    'horizons, is at least joint + gate\'s minus 0.1 dB; (g) the mean synthetic objective is at least joint + gate\'s '
    'minus 0.5 dB and its synthetic windows below -0.5 dB are no more than joint + gate has; (h) the compute it adds '
    'is small: over all development runs, the median of its own 99th-percentile time per 10 ms block (fade included) '
    'minus joint + gate\'s in the same run is at most 1 ms. Among eligible candidates, pick the one with the fewest '
    'boosts, then the fewest near-boosts, then the higher tone-bin median. If none is eligible, nothing is frozen: the '
    'joint check and v2 are unchanged, and there is nothing to test on fresh recordings.')
PRIMARY_QUESTION = (
    'Only if a candidate is frozen. On material no study-04 choice used: (1) are the gate\'s boosts gone, with none '
    'added: does the frozen candidate have fewer third-octave boosts (a band 1 dB or more louder) than joint + gate '
    'over the late windows of the fresh synthetic scenes, and no more than joint + gate over the fresh recordings '
    '(either horizon)? (2) Is the tone gain kept: is its median tone-bin gain at 20 ms, over the fresh acoustic '
    'recordings with reference tones, above v2 + gate\'s? The two parts are answered separately. The other '
    'candidates, v2 with the fade, the study-02 fresh recordings and the study-01 test recordings are reported for '
    'information and answer nothing.')


def make_bank(method, v2):
    if method['kind'] == 'gated_check':
        method = dict(method, options=dict(method.get('options', {}), gate=v2['gate'], fade=method.get('fade')))
    return fs2.make_bank(method, v2)


def gated(method):
    return method['kind'] == 'v2' or method['kind'] in fs2.BANK_KINDS


def method_names(methods):
    names = ['zero']
    for m in methods:
        names += [m['name']+'_ungated', m['name']+'_gated'] if gated(m) else [m['name']]
    return names


def fade_block_seconds(enabled, fade, groups):
    """Time of the streaming fade (BlockFade, every group) for each origin's block, in seconds."""
    if not fade:
        return np.zeros(len(enabled))
    fades = [BlockFade(len(columns), fade['in_blocks'], fade['out_blocks'], fade.get('shape', 'cosine'))
             for columns, _ in groups]
    out = np.zeros(len(enabled))
    for r, row in enumerate(enabled):
        t0 = time.perf_counter()
        for g, f in enumerate(fades):
            f.step(bool(row[g]))
        out[r] = time.perf_counter()-t0
    return out


def run_methods(x, grid, keep, methods, v2, train_end):
    """As forecaster_study_02.run_methods, with the gated band check as a further bank kind and the gate's decision
    faded where a method says so ('fade'). '_gated' always means the output after the gate as that method uses it."""
    _, horizons, groups = horizon_setup()
    preds, info = {'zero':np.zeros((int(keep.sum()), len(horizons)))}, {}
    for m in methods:
        started, extra = time.perf_counter(), {}
        if gated(m):
            if m['kind'] == 'v2':
                fc = SelectedToneForecaster(FS, ToneSelector(FS, **v2['selector']), window_seconds=m['window_seconds'],
                                            release_ratio=v2['forecaster']['release_ratio'],
                                            release_window_seconds=v2['forecaster']['release_window_seconds'])
                shadow = fc.predict(x, grid, horizons)
                extra = {'fast_drops':fc.fast_drops, 'forecast_ms_per_origin':1e3*fc.predict_seconds_per_origin}
            else:
                bank = make_bank(m, v2)
                shadow = stream_forecasts(bank, x, grid, horizons)
            fade = m.get('fade')
            out, gains, enabled = fade_gate_output(x, grid, shadow, groups, v2['gate'], fade)
            fade_ms = 1e3*fade_block_seconds(enabled, fade, groups)
            if m['kind'] != 'v2':
                b, own = 1e3*bank.block_seconds, 1e3*bank.block_seconds_own
                # One pushed block per grid origin at the end of the stream; the fade runs once per origin.
                own = own.copy()
                own[len(own)-len(fade_ms):] += fade_ms
                extra = {'block_ms_mean':float(b.mean()), 'block_ms_p99':float(np.percentile(b, 99)),
                         'block_ms_max':float(b.max()), 'own_block_ms_mean':float(own.mean()),
                         'own_block_ms_p99':float(np.percentile(own, 99)), 'own_block_ms_max':float(own.max()),
                         'counters':bank.counters, 'seconds_by_part':{k:round(v, 4) for k, v in bank.timing.items()},
                         'settings':bank.settings()}
            e = np.asarray(enabled, bool)[keep]
            extra.update(fade=fade, gate_open_fraction=e.mean(axis=0).tolist(),
                         gate_switches=int(np.sum(e[1:, 0] != e[:-1, 0])),
                         mean_gain=np.asarray(gains)[keep].mean(axis=0).tolist(),
                         fade_block_ms_p99=float(np.percentile(fade_ms, 99)), fade_block_ms_max=float(fade_ms.max()))
            preds[m['name']+'_ungated'], preds[m['name']+'_gated'] = shadow[keep], out[keep]
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

# ---------- tasks (as forecaster_study_02's, with this module's methods) ----------

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

# ---------- the development rule ----------

def late_boosts(scenes, method, family=None, threshold=1.):
    return int(sum(s['max_third_octave_change_db'] >= threshold for sc in scenes if family in (None, sc['family'])
                   for s in sc['late_window_scores'] if s['method'] == method))


def paired_p99(runs, name, reference='joint'):
    """Median over runs of (name's own p99 ms per block minus reference's in the same run), and name's own p99s."""
    own = [r['methods'][name]['own_block_ms_p99'] for r in runs]
    diff = [r['methods'][name]['own_block_ms_p99']-r['methods'][reference]['own_block_ms_p99'] for r in runs]
    return float(np.median(diff)), float(np.median(own)), float(max(own))


def apply_development_rule(rec, syn, records, scenes, candidates):
    runs = records+scenes
    j, v2 = fs3._counts(rec, syn, 'joint_gated'), fs3._counts(rec, syn, 'v2_gated')
    tone_needed = v2['tone_bin_median_db']+.5*(j['tone_bin_median_db']-v2['tone_bin_median_db'])
    buzz_no_gate = late_boosts(scenes, 'joint_ungated', 'buzz')
    table = []
    for c in candidates:
        n = fs3._counts(rec, syn, c['name']+'_gated')
        buzz = late_boosts(scenes, c['name']+'_gated', 'buzz')
        added, p99_median, p99_worst = paired_p99(runs, c['name'])
        checks = {'a_fewer_boosts':n['boosts'] < j['boosts'],
                  'b_gate_boosts_gone':buzz <= buzz_no_gate,
                  'c_near_boosts':n['near_boosts'] <= j['near_boosts'],
                  'd_whole_band_boosts':n['whole_band_boosts'] <= j['whole_band_boosts'],
                  'e_tone_gain_kept':n['tone_bin_median_db'] >= tone_needed,
                  'f_whole_band':n['whole_band_median_db'] >= j['whole_band_median_db']-.1,
                  'g_synthetic':(n['synthetic_objective_db'] >= j['synthetic_objective_db']-.5
                                 and n['synthetic_windows_below_minus_half_db'] <= j['synthetic_windows_below_minus_half_db']),
                  'h_time':added <= 1.}
        table.append(dict(candidate=c['name'], kind=c['kind'], fade=c.get('fade'), tone_bin_needed_db=tone_needed,
                          buzz_late_boosts=buzz, buzz_late_boosts_no_gate=buzz_no_gate, p99_added_ms=added,
                          p99_block_ms_median=p99_median, p99_block_ms_worst=p99_worst, checks=checks,
                          eligible=all(checks.values()), **n))
    eligible = [t for t in table if t['eligible']]
    pick = min(eligible, key=lambda t: (t['boosts'], t['near_boosts'], -t['tone_bin_median_db']))['candidate'] if eligible else None
    reference = {}
    for name in ('joint', 'v2', 'bank_wide_lines', 'v2_fade8'):
        timing = paired_p99(runs, name)[1:] if name not in ('v2', 'v2_fade8') else (None, None)
        reference[name+' + gate' if name != 'v2_fade8' else 'v2 + fade8'] = dict(
            buzz_late_boosts=late_boosts(scenes, name+'_gated', 'buzz'), p99_block_ms_median=timing[0],
            p99_block_ms_worst=timing[1], **fs3._counts(rec, syn, name+'_gated'))
    reference['joint, no gate'] = dict(buzz_late_boosts=buzz_no_gate, p99_block_ms_median=None, p99_block_ms_worst=None,
                                       **fs3._counts(rec, syn, 'joint_ungated'))
    return pick, table, reference


def gate_activity(records, scenes, methods):
    """Per gated method: gate switches and the share of blocks the gate was open, over recordings and scenes."""
    out = {}
    for m in methods:
        if not gated(m):
            continue
        row = {}
        for part, runs in (('recordings', records), ('scenes', scenes)):
            i = [r['methods'][m['name']] for r in runs]
            row[part] = {'gate_switches':int(sum(x['gate_switches'] for x in i)),
                         'gate_open_fraction':float(np.mean([x['gate_open_fraction'][0] for x in i])),
                         'mean_gain':float(np.mean([x['mean_gain'][0] for x in i]))}
        out[m['name']] = row
    return out

# ---------- stages ----------

def _code_hashes():
    here = Path(__file__).parent
    return {name:hashlib.sha256((here/name).read_bytes()).hexdigest() for name in FROZEN_CODE}


def _seen_names():
    split = s1.load_split()
    return {e['file'] for e in split['test_files']}|{e['file'] for e in fs2.FRESH_RECORDINGS}


def run_development(output, candidates=CANDIDATES, workers=WORKERS, note=None):
    """Development only: the study-01 development recordings, the development synthetic scenes and the buzz scenes."""
    output = s1._fresh(output)
    split = s1.load_split()
    v2 = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
    methods = COMPARATORS+list(candidates)
    started = time.perf_counter()
    paths = [s1.checked_path(e) for e in split['development_files']]
    if any(p.name in _seen_names() for p in paths):
        raise ValueError('A test or fresh recording reached development.')
    draws, wander, scene_tasks = s1.development_scenes()
    buzz, buzz_tasks = fs3.buzz_scenes()
    n = len(paths)
    out = fs2._pool([(_recording_task, (str(p), methods, v2, p.name not in ELECTRICAL)) for p in paths]
                    + [(_scene_task, (*t, methods, v2)) for t in scene_tasks+buzz_tasks], workers)
    records, scenes = out[:n], out[n:]
    names = method_names(methods)
    rec, syn, fams = fs2.summarize(records, scenes, names)
    pick, table, reference = apply_development_rule(rec, syn, records, scenes, candidates)
    result = {'kind':'tone_forecaster_04_development', 'created_utc':datetime.now(timezone.utc).isoformat(),
              'stage':('development only; no study-01 test recording, study-02 fresh recording, synthetic test scene or '
                       'new fresh recording was read'), 'note':note, 'v2':v2,
              'candidates':list(candidates), 'comparators':COMPARATORS, 'rule':DEVELOPMENT_RULE,
              'development_files':[p.name for p in paths], 'release_development_draws':draws,
              'wander_development_draws':wander, 'buzz_development':fs3.BUZZ_DEV, 'buzz_development_draws':buzz,
              'recordings':records, 'scenes':scenes,
              'summary':{'recordings':rec, 'synthetic':syn, 'synthetic_by_family':fams},
              'gate_activity':gate_activity(records, scenes, methods),
              'rule_table':table, 'rule_reference':reference, 'development_pick':pick,
              'runtime_seconds':time.perf_counter()-started, 'workers':workers, 'code_sha256':_code_hashes(),
              'labels':'Reference-signal prediction only. Not acoustic attenuation.'}
    (output/'development.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    from .forecaster_report_04 import write_development_summary
    write_development_summary(output, result)
    return result


SYNTHETIC_TEST = {'standard_seed':20261040, 'standard_repeats':3, 'standard_scene_seeds':'13100+100*repeat+scene index',
                  'wander_seed':20261041, 'wander_repeats':3, 'wander_scene_seeds':'14100+100*repeat+scene index',
                  'buzz_seed':20261042, 'buzz_repeats':3, 'buzz_scene_seeds':'15100+100*repeat+scene index',
                  'parity':1, 'parity_note':'odd 10 Hz bands (development used even)', 'forbidden_within_hz':2.}
SYNTHETIC_NOT_EXCLUDED = (
    'Every frequency a study-04 development scene used is excluded (the study-02 development list and study 03\'s buzz '
    'draws). The study-01, release-study and study-02 synthetic test draws are not excluded: no study-04 choice used '
    'them, and excluding the study-02 test draws as well within 2 Hz leaves no room for the standard and drifting '
    'scenes in odd bands (checked with a draw before this freeze; study 02 met the same limit with study 01\'s draws).')


def development_frequencies_04(wander_dev):
    release = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))
    buzz, _ = fs3.buzz_scenes()
    out = fs2.development_frequencies(release, wander_dev)+[f for g in buzz for fs in g.values() for f in fs]
    return sorted(set(round(float(f), 2) for f in out))


def draw_synthetic_test(syn, forbidden):
    standard, wander = fs2.draw_synthetic_test(syn, forbidden)
    rng = np.random.default_rng(syn['buzz_seed'])
    spec = dict(fs3.BUZZ_DEV, parity=syn['parity'], forbidden_within_hz=syn['forbidden_within_hz'])
    buzz = [fs3.draw_buzz(rng, forbidden, spec) for _ in range(syn['buzz_repeats'])]
    if any(abs(f-b) <= syn['forbidden_within_hz'] for g in buzz for fs in g.values() for f in fs for b in forbidden):
        raise ValueError('Buzz test draw is not fresh.')
    return standard, wander, buzz


def _earlier_audio_names():
    """Every audio file already under external-audio, in any folder."""
    return {p.name for p in (ROOT/'external-audio').rglob('*') if p.is_file() and p.suffix.lower() != '.md'}


def check_fresh_list(fresh):
    """The fresh list must name new files by new authors, with a SHA-1 and size for each."""
    earlier = _earlier_audio_names()|_seen_names()|{e['file'] for e in s1.load_split()['development_files']}
    authors = ' '.join((p.read_text(encoding='utf-8') for p in (ROOT/'external-audio').rglob('SOURCES.md')))
    authors += ' '+' '.join(e['author'] for e in fs2.FRESH_RECORDINGS)
    for e in fresh['recordings']:
        for key in ('file', 'title', 'sha1', 'bytes', 'seconds', 'author', 'licence', 'acoustic'):
            if key not in e:
                raise ValueError(f"{e.get('file')}: '{key}' missing from the fresh list.")
        if e['file'] in earlier:
            raise ValueError(f"{e['file']} was used before; fresh recordings must be new.")
        if e['author'].strip().lower() in authors.lower():
            raise ValueError(f"{e['file']}: its author made an earlier recording.")
    if len({e['author'] for e in fresh['recordings']}) != len(fresh['recordings']):
        raise ValueError('One author per fresh recording.')
    return fresh['recordings']


def _project_path(folder):
    folder = Path(folder).resolve()
    return folder.relative_to(ROOT).as_posix() if folder.is_relative_to(ROOT) else folder.as_posix()


def freeze_protocol(development_folder, output=STUDY/'protocol.json', fresh_list=FRESH_LIST):
    """Write the frozen protocol from a development run, once. Refuses to overwrite."""
    output = Path(output)
    if output.exists():
        raise ValueError('protocol.json already exists; the protocol is frozen once.')
    dev = json.loads((Path(development_folder)/'development.json').read_text(encoding='utf-8'))
    if dev['code_sha256'] != _code_hashes():
        raise ValueError('Code changed after the development run; rerun development before freezing.')
    chosen = next((c for c in dev['candidates'] if c['name'] == dev['development_pick']), None)
    protocol = {'kind':'tone_forecaster_04_frozen_protocol', 'created_utc':datetime.now(timezone.utc).isoformat(),
                'development_run':_project_path(development_folder), 'rule':dev['rule'],
                'rule_table':dev['rule_table'], 'rule_reference':dev['rule_reference'], 'frozen_candidate':chosen,
                'candidates':dev['candidates'], 'comparators':dev['comparators'], 'v2':dev['v2'],
                'primary_question':PRIMARY_QUESTION}
    if chosen is None:
        protocol['decision'] = ('No candidate met the development rule. The joint check (study 02) and v2 are unchanged. '
                                'Nothing is left to test, so no fresh recordings are chosen or downloaded for this study, '
                                'and the primary question is not asked.')
    else:
        raw = Path(fresh_list).read_bytes()
        fresh = json.loads(raw.decode('utf-8'))
        recordings = check_fresh_list(fresh)
        syn = dict(SYNTHETIC_TEST, forbidden_frequencies=development_frequencies_04(dev['wander_development_draws']),
                   not_excluded=SYNTHETIC_NOT_EXCLUDED)
        standard, wander, buzz = draw_synthetic_test(syn, syn['forbidden_frequencies'])
        syn.update(standard_draws=standard, wander_draws=wander, buzz_draws=buzz)
        split = s1.load_split()
        protocol.update(
            decision=f"{chosen['name']} met the development rule and is frozen for the test.",
            fresh_recordings=recordings, fresh_list=_project_path(fresh_list),
            fresh_list_sha256=hashlib.sha256(raw).hexdigest(), fresh_folder=_project_path(FRESH_AUDIO),
            fresh_independence=fresh['independence'], fresh_how_chosen=fresh['how_chosen'],
            fresh_missing_rule=('A recording that cannot be downloaded is reported as missing and is not replaced; a '
                                'present file whose size or SHA-1 differs stops the test.'),
            seen_recordings={'study_01_test':split['test_files'], 'study_02_fresh':fs2.FRESH_RECORDINGS},
            seen_note=('Secondary, not independent: the study-01 test recordings and the study-02 fresh recordings '
                       '(Buzzing_Speakers.ogg among them). Study 02 and 03 read their results; no study-04 choice was '
                       'made on them.'),
            synthetic_test=syn)
    protocol['code_sha256'] = _code_hashes()
    output.write_text(json.dumps(protocol, indent=2), encoding='utf-8')
    return protocol


def test_scene_tasks(protocol):
    syn = protocol['synthetic_test']
    standard, wander, buzz = draw_synthetic_test(syn, syn['forbidden_frequencies'])
    if json.loads(json.dumps([standard, wander, buzz])) != [syn['standard_draws'], syn['wander_draws'], syn['buzz_draws']]:
        raise ValueError('Synthetic test draws differ from the protocol.')
    tasks = []
    for rep, g in enumerate(standard):
        tasks += [(f'{n}#test{rep}', 'standard', s, 13100+100*rep+i, None) for i, (n, s) in enumerate(scene_set(g).items())]
    for rep, g in enumerate(wander):
        tasks += [(f'{n}#test{rep}', 'wander', s, 14100+100*rep+i, None) for i, (n, s) in enumerate(s1.wander_scene_set(g).items())]
    for rep, g in enumerate(buzz):
        tasks += [(f'{n}#test{rep}', 'buzz', s, 15100+100*rep+i, None) for i, (n, s) in enumerate(fs3.buzz_scene_set(g).items())]
    return tasks


def run_test(output=STUDY/'test', protocol_path=STUDY/'protocol.json', fresh_folder=FRESH_AUDIO, workers=WORKERS):
    """Runs once: fresh recordings (primary), fresh synthetic scenes (primary), then seen recordings (secondary)."""
    output = Path(output)
    if output.exists():
        raise ValueError('The test stage has already run (its folder exists); it runs once.')
    protocol = json.loads(Path(protocol_path).read_text(encoding='utf-8'))
    if protocol['frozen_candidate'] is None:
        raise ValueError('No candidate was frozen; there is nothing to test.')
    if protocol['code_sha256'] != _code_hashes():
        raise ValueError('Code changed after the protocol was frozen.')
    fresh = [(e, fs2.fresh_path(e, fresh_folder)) for e in protocol['fresh_recordings']]
    present = [(e, p) for e, p in fresh if p is not None]
    if not present:
        raise ValueError('No fresh recording is present; the test cannot run.')
    seen = ([(s1.checked_path(e), e['file'] not in ELECTRICAL) for e in protocol['seen_recordings']['study_01_test']]
            + [(p, e['acoustic']) for e in protocol['seen_recordings']['study_02_fresh']
               for p in [fs2.fresh_path(e)] if p is not None])
    v2 = protocol['v2']
    methods = protocol['comparators']+protocol['candidates']
    tasks = test_scene_tasks(protocol)
    output.mkdir(parents=True)
    started = time.perf_counter()
    jobs = ([(_recording_task, (str(p), methods, v2, e['acoustic'])) for e, p in present]
            + [(_scene_task, (*t, methods, v2)) for t in tasks]
            + [(_recording_task, (str(p), methods, v2, acoustic)) for p, acoustic in seen])
    out = fs2._pool(jobs, workers)
    n, k = len(present), len(tasks)
    fresh_records, scenes, seen_records = out[:n], out[n:n+k], out[n+k:]
    names = method_names(methods)
    frec, syn, fams = fs2.summarize(fresh_records, scenes, names)
    srec, _, _ = fs2.summarize(seen_records, [], names)
    result = {'kind':'tone_forecaster_04_test', 'created_utc':datetime.now(timezone.utc).isoformat(), 'protocol':protocol,
              'fresh_files':[p.name for _, p in present], 'fresh_missing':[e['file'] for e, p in fresh if p is None],
              'fresh_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for _, p in present},
              'seen_files':[p.name for p, _ in seen], 'fresh_recordings':fresh_records, 'seen_recordings':seen_records,
              'scenes':scenes, 'summary':{'fresh':frec, 'seen':srec, 'synthetic':syn, 'synthetic_by_family':fams},
              'gate_activity':gate_activity(fresh_records, scenes, methods),
              'runtime_seconds':time.perf_counter()-started, 'workers':workers,
              'labels':'Reference-signal prediction only. Not acoustic attenuation.'}
    (output/'test.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    from .forecaster_report_04 import write_test_report
    write_test_report(output.parent, result)
    return result


def run_timing(output, names=('joint', 'gcheck', 'gcheck_fade8', 'joint_fade8'), note=None):
    """Compute time one run at a time in this process (no pool, one thread), on the development recordings.
    Records what else the machine was doing at the start and end. Development material only."""
    import psutil
    output = s1._fresh(output)
    v2 = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
    every = {m['name']:m for m in COMPARATORS+CANDIDATES}
    methods = [every[n] for n in names]

    def load():
        # A process's first cpu_percent reading is always 0, so read every process before and after one second.
        procs = list(psutil.process_iter(['name']))
        for p in procs:
            try:
                p.cpu_percent(None)
            except psutil.Error:
                pass
        total = psutil.cpu_percent(interval=1.)
        busy = []
        for p in procs:
            try:
                if p.pid:
                    busy.append((p.cpu_percent(None), p.info['name']))
            except psutil.Error:
                pass
        busy.sort(reverse=True)
        return {'cpu_percent':total, 'busiest':[f'{n} {c:.0f}%' for c, n in busy[:5]]}
    before = load()
    started = time.perf_counter()
    records = [_recording_task((str(s1.checked_path(e)), methods, v2, e['file'] not in ELECTRICAL))
               for e in s1.load_split()['development_files']]
    result = {'kind':'tone_forecaster_04_timing', 'created_utc':datetime.now(timezone.utc).isoformat(), 'note':note,
              'cpu_count':os.cpu_count(), 'load_before':before, 'load_after':load(),
              'methods':[m['name'] for m in methods],
              'per_recording':[{'file':r['file'], 'methods':{m:{k:v for k, v in r['methods'][m].items()
                                                                if k.endswith('_ms_p99') or k.endswith('_ms_mean') or k.endswith('_ms_max')}
                                                             for m in names}} for r in records],
              'runtime_seconds':time.perf_counter()-started, 'code_sha256':_code_hashes(),
              'labels':'Offline Python, one thread, no pool. Reference-signal prediction only.'}
    (output/'timing.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    from .forecaster_report_04 import write_timing_summary
    write_timing_summary(output, result)
    return result
