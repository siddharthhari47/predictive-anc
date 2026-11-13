"""Study 03: a ceiling on the joint band check's tie fallback (results-tone-forecaster-03).

Why: study 02's joint band check + gate passed its frozen test narrowly. Two
third-octave boosts were left, both on one fresh file (Buzzing_Speakers.ogg) in
two nearly empty low bands. The post-test reading named the check's tie
fallback, which has no ceiling, as the likely cause, without re-running anything.
This study asks whether a ceiling on that fallback (tone_cap.CappedCheckBank)
removes the remaining boosts without losing the tone gain over v2.

Order, enforced in code:
1. Diagnosis and design used development material only: the study-01
   development recordings, the 44 development synthetic scenes, and a new
   development family drawn for this study (BUZZ_DEV): a wandering buzz above
   100 Hz over nearly empty low bands, the shape of the study-02 failure. That
   shape comes from the post-test notes; no audio or score from that file, from
   the other study-02 fresh files or from the study-01 test files was used. The
   trials are kept in results-tone-forecaster-03/diagnosis.
2. `run_development` scores the capped candidates and every comparator on that
   material and applies DEVELOPMENT_RULE, written after the trials and before
   this formal run.
3. `freeze_protocol` writes protocol.json once. When no candidate meets the rule,
   the protocol records that and nothing is left to test, so no fresh recordings
   are chosen or downloaded. A test stage (fresh recordings chosen by Commons
   metadata, downloaded only with the user's approval, and fresh synthetic draws)
   would have to be written and frozen before any candidate could be tested.

Reference-signal prediction only: no acoustic path, no playback, no ear measurement.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from . import forecaster_study as s1
from . import forecaster_study_02 as fs2
from .generalization import HELD_OUT
from .real_hum_study import ELECTRICAL
from .release_study import in_parity
from .selection_study import TEST_GROUPS, frequency_extent
from .tone_cap import CappedCheckBank

ROOT = s1.ROOT
STUDY = ROOT/'results-tone-forecaster-03'
STUDY_02 = ROOT/'results-tone-forecaster-02'
WORKERS = fs2.WORKERS
FROZEN_CODE = fs2.FROZEN_CODE+('tone_cap.py', 'forecaster_study_03.py', 'forecaster_report_03.py')

# Study 02's run_methods looks bank kinds up in its own table (forecaster_study_02.py is frozen, so it is not
# edited). Registering here also registers in every worker, since workers import this module to run its tasks.
fs2.BANK_KINDS.setdefault('capped', CappedCheckBank)

# ---------- methods ----------

CAPS_DB = (.5, 1., 2., 3.)
CANDIDATES = [{'name':f'cap{c:g}', 'kind':'capped', 'nb_tau':0., 'lines':True, 'options':{'cap_db':c}} for c in CAPS_DB]
COMPARATORS = fs2.COMPARATORS+[{'name':'joint', 'kind':'joint', 'nb_tau':0., 'lines':True, 'options':{}}]
DEVELOPMENT_RULE = (
    'Written after the diagnostic trials on development material (results-tone-forecaster-03/diagnosis) and before '
    'the formal development run. Candidates, all gated: the joint band check of study 02 with its tie fallback capped '
    'at 0.5 dB (the fallback switched off), 1, 2 and 3 dB; above the cap only no output is allowed. Development '
    'material: the eight study-01 development recordings, the 44 development synthetic scenes and the 8 new buzz '
    'scenes. A boost is a third-octave band 1 dB or more louder; a near-boost 0.5 dB or more; both are counted over '
    'development recordings (either horizon) plus late synthetic windows. Eligible only if: (a) the boosts go down: '
    'fewer boosts than joint + gate; (b) no more near-boosts than joint + gate; (c) no more whole-band boosts (whole '
    '35-350 Hz band below -0.5 dB on a development recording) than joint + gate; (d) the tone gain over v2 is kept: '
    'the median, over development acoustic recordings with reference tones, of the tone-bin gain averaged over both '
    'horizons is at least v2 + gate\'s plus half of the amount by which joint + gate exceeds v2 + gate; (e) the median '
    'whole-band gain over development acoustic recordings, averaged over both horizons, is at least joint + gate\'s '
    'minus 0.1 dB; (f) the mean synthetic objective is at least joint + gate\'s minus 0.5 dB and its synthetic windows '
    'below -0.5 dB are no more than joint + gate has; (g) its own compute time per 10 ms block at the 99th percentile, '
    'worst run, is within 0.5 ms of joint + gate\'s in the same run (the capped check does the same work). Among '
    'eligible candidates, pick the one with the fewest boosts, then the fewest near-boosts, then the higher tone-bin '
    'median. If none is eligible, nothing is frozen: the joint check and v2 are unchanged, and there is nothing to '
    'test on fresh recordings.')
PRIMARY_QUESTION = (
    'Only if a candidate is frozen. On fresh recordings the project has never used: (1) are the boosts gone: does the '
    'frozen candidate + gate have no third-octave boost (a band 1 dB or more louder, any fresh recording, either '
    'horizon), and fewer than joint + gate? (2) Is the tone gain kept: is its median tone-bin gain at 20 ms, over the '
    'fresh acoustic recordings with reference tones, above v2 + gate\'s? Answered separately.')


def _recording_task(args):
    return fs2._recording_task(args)


def _scene_task(args):
    return fs2._scene_task(args)

# ---------- the buzz development family ----------

BUZZ_DEV = {'seed':20261019, 'repeats':2, 'scene_seeds':'12100+100*repeat+scene index', 'parity':0,
            'parity_note':'even 10 Hz bands, as all development scenes', 'band_hz':[102., 315.],
            'fundamental_hz':[102., 157.], 'spacing_hz':15., 'forbidden_within_hz':2., 'white_floor':.01,
            'floor_note':('A white floor of 0.01 against tones of 0.4 and 0.2 leaves the 39 and 50 Hz bands about 50 dB '
                          'below the 35-350 Hz power, as in the study-02 failure.')}


def buzz_forbidden():
    """Frequencies the buzz development draws keep away from: every synthetic test frequency used so far
    (selection-study test groups, held-out groups and study 02's synthetic test draws)."""
    p2 = json.loads((STUDY_02/'protocol.json').read_text(encoding='utf-8'))['synthetic_test']
    out = (frequency_extent(TEST_GROUPS)+[f for g in HELD_OUT.values() for f in g]
           + [f for g in p2['standard_draws'] for f in frequency_extent(g)]+[f for g in p2['wander_draws'] for fs in g.values() for f in fs])
    return sorted(set(round(float(f), 2) for f in out))


def draw_buzz(rng, forbidden, spec=BUZZ_DEV):
    far = spec['forbidden_within_hz']

    def pick(lo, hi, n):
        for _ in range(100000):
            fs = sorted(round(float(f), 1) for f in rng.uniform(lo, hi, n))
            if (all(in_parity(f, spec['parity']) and all(abs(f-b) > far for b in forbidden) for f in fs)
                    and all(b-a >= spec['spacing_hz'] for a, b in zip(fs, fs[1:]))):
                return fs
        raise RuntimeError('Could not draw development buzz frequencies.')
    for _ in range(100000):
        f0 = pick(*spec['fundamental_hz'], 1)[0]
        if all(abs(2*f0-b) > far for b in forbidden):
            break
    else:
        raise RuntimeError('Could not draw a development buzz fundamental.')
    lo, hi = spec['band_hz']
    return {'steady':pick(lo, hi, 2), 'wander':pick(lo, hi, 2), 'harmonic':[f0, round(2*f0, 1)], 'am':pick(lo, hi, 2)}


def buzz_scene_set(g, floor=BUZZ_DEV['white_floor']):
    """Wandering tones above 100 Hz over a quiet white floor (synthesized by forecaster_study.synthesize_wander)."""
    w = s1.wander_tone
    return {'buzz_steady':{'noise':('white', floor), 'tones':[w(f, a, .1) for f, a in zip(g['steady'], [.4, .2])]},
            'buzz_wander':{'noise':('white', floor), 'tones':[w(f, a, 1.) for f, a in zip(g['wander'], [.4, .2])]},
            'buzz_harmonic':{'noise':('white', floor), 'tones':[w(f, a, .3) for f, a in zip(g['harmonic'], [.4, .25])]},
            'buzz_am':{'noise':('white', floor), 'tones':[w(f, a, .3, .5) for f, a in zip(g['am'], [.4, .2])]}}


def buzz_scenes():
    rng = np.random.default_rng(BUZZ_DEV['seed'])
    forbidden = buzz_forbidden()
    draws = [draw_buzz(rng, forbidden) for _ in range(BUZZ_DEV['repeats'])]
    tasks = [(f'{n}#dev{rep}', 'buzz', spec, 12100+100*rep+i, None)
             for rep, g in enumerate(draws) for i, (n, spec) in enumerate(buzz_scene_set(g).items())]
    return draws, tasks

# ---------- the development rule ----------

def _counts(rec, syn, m):
    return {'boosts':len(rec[m]['third_octave_boosts'])+syn[m]['late_third_octave_boosts'],
            'near_boosts':len(rec[m]['near_boosts'])+syn[m]['late_near_boosts'],
            'recording_boosts':len(rec[m]['third_octave_boosts']), 'recording_near_boosts':len(rec[m]['near_boosts']),
            'synthetic_late_boosts':syn[m]['late_third_octave_boosts'], 'synthetic_late_near_boosts':syn[m]['late_near_boosts'],
            'whole_band_boosts':len(rec[m]['whole_band_boosts']),
            'tone_bin_median_db':rec[m]['median_tone_bin_both_horizons_db'],
            'whole_band_median_db':rec[m]['median_whole_band_both_horizons_db'],
            'synthetic_objective_db':syn[m]['mean_objective_db'],
            'synthetic_windows_below_minus_half_db':syn[m]['windows_below_minus_half_db']}


def apply_development_rule(rec, syn, records, scenes, candidates):
    def p99(name):
        return max(r['methods'][name]['own_block_ms_p99'] for r in records+scenes)
    j, v2 = _counts(rec, syn, 'joint_gated'), _counts(rec, syn, 'v2_gated')
    tone_needed = v2['tone_bin_median_db']+.5*(j['tone_bin_median_db']-v2['tone_bin_median_db'])
    table = []
    for c in candidates:
        n = _counts(rec, syn, c['name']+'_gated')
        checks = {'a_fewer_boosts':n['boosts'] < j['boosts'],
                  'b_near_boosts':n['near_boosts'] <= j['near_boosts'],
                  'c_whole_band_boosts':n['whole_band_boosts'] <= j['whole_band_boosts'],
                  'd_tone_gain_kept':n['tone_bin_median_db'] >= tone_needed,
                  'e_whole_band':n['whole_band_median_db'] >= j['whole_band_median_db']-.1,
                  'f_synthetic':(n['synthetic_objective_db'] >= j['synthetic_objective_db']-.5
                                 and n['synthetic_windows_below_minus_half_db'] <= j['synthetic_windows_below_minus_half_db']),
                  'g_time':p99(c['name']) <= p99('joint')+.5}
        table.append(dict(candidate=c['name'], cap_db=c['options']['cap_db'], tone_bin_needed_db=tone_needed,
                          p99_block_ms=p99(c['name']), checks=checks, eligible=all(checks.values()), **n))
    eligible = [t for t in table if t['eligible']]
    pick = min(eligible, key=lambda t: (t['boosts'], t['near_boosts'], -t['tone_bin_median_db']))['candidate'] if eligible else None
    reference = {name:dict(p99_block_ms=p99(name) if name != 'v2' else None, **_counts(rec, syn, name+'_gated'))
                 for name in ('joint', 'v2', 'bank_wide_lines')}
    return pick, table, reference


def cap_activity(records, scenes, candidates):
    """How often each cap acted, summed over runs: decisions, fallback in force, cap binding, only no output allowed."""
    out = {}
    for c in candidates:
        row = {}
        for part, runs in (('recordings', records), ('scenes', scenes)):
            k = [r['methods'][c['name']]['counters'] for r in runs]
            row[part] = {key:int(sum(sum(x[key]) for x in k)) for key in
                         ('decisions', 'fallback_decisions', 'capped_decisions', 'silent_decisions', 'setting_switches')}
        out[c['name']] = row
    return out

# ---------- stages ----------

def _code_hashes():
    here = Path(__file__).parent
    return {name:hashlib.sha256((here/name).read_bytes()).hexdigest() for name in FROZEN_CODE}


def run_development(output, candidates=CANDIDATES, workers=WORKERS, note=None):
    """Development only: the study-01 development recordings, the development synthetic scenes and the buzz scenes."""
    output = s1._fresh(output)
    split = s1.load_split()
    v2 = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
    methods = COMPARATORS+list(candidates)
    started = time.perf_counter()
    paths = [s1.checked_path(e) for e in split['development_files']]
    seen = {e['file'] for e in split['test_files']}|{e['file'] for e in fs2.FRESH_RECORDINGS}
    if any(p.name in seen for p in paths):
        raise ValueError('A test or fresh recording reached development.')
    draws, wander, scene_tasks = s1.development_scenes()
    buzz, buzz_tasks = buzz_scenes()
    n = len(paths)
    out = fs2._pool([(_recording_task, (str(p), methods, v2, p.name not in ELECTRICAL)) for p in paths]
                    + [(_scene_task, (*t, methods, v2)) for t in scene_tasks+buzz_tasks], workers)
    records, scenes = out[:n], out[n:]
    names = fs2.method_names(methods)
    rec, syn, fams = fs2.summarize(records, scenes, names)
    pick, table, reference = apply_development_rule(rec, syn, records, scenes, candidates)
    result = {'kind':'tone_forecaster_03_development', 'created_utc':datetime.now(timezone.utc).isoformat(),
              'stage':('development only; no study-01 test recording, study-02 fresh recording, synthetic test scene or '
                       'new fresh recording was read'), 'note':note, 'v2':v2,
              'candidates':list(candidates), 'comparators':COMPARATORS, 'rule':DEVELOPMENT_RULE,
              'development_files':[p.name for p in paths], 'release_development_draws':draws,
              'wander_development_draws':wander, 'buzz_development':BUZZ_DEV, 'buzz_development_draws':buzz,
              'recordings':records, 'scenes':scenes,
              'summary':{'recordings':rec, 'synthetic':syn, 'synthetic_by_family':fams},
              'cap_activity':cap_activity(records, scenes, candidates),
              'rule_table':table, 'rule_reference':reference, 'development_pick':pick,
              'runtime_seconds':time.perf_counter()-started, 'code_sha256':_code_hashes(),
              'labels':'Reference-signal prediction only. Not acoustic attenuation.'}
    (output/'development.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    from .forecaster_report_03 import write_development_summary
    write_development_summary(output, result)
    return result


def _project_path(folder):
    folder = Path(folder).resolve()
    return folder.relative_to(ROOT).as_posix() if folder.is_relative_to(ROOT) else folder.as_posix()


def freeze_protocol(development_folder, output=STUDY/'protocol.json'):
    """Write the frozen protocol from a development run. Refuses to overwrite.

    Only the no-candidate outcome can be frozen as written: a frozen candidate needs a test stage (fresh
    recordings chosen by metadata, fresh synthetic draws), which must be written and reviewed first."""
    output = Path(output)
    if output.exists():
        raise ValueError('protocol.json already exists; the protocol is frozen once.')
    dev = json.loads((Path(development_folder)/'development.json').read_text(encoding='utf-8'))
    if dev['code_sha256'] != _code_hashes():
        raise ValueError('Code changed after the development run; rerun development before freezing.')
    if dev['development_pick'] is not None:
        raise ValueError(f"{dev['development_pick']} met the rule: write the test stage (fresh recordings chosen by "
                         'Commons metadata, fresh synthetic draws) and rerun development before freezing.')
    protocol = {'kind':'tone_forecaster_03_frozen_protocol', 'created_utc':datetime.now(timezone.utc).isoformat(),
                'development_run':_project_path(development_folder), 'rule':dev['rule'],
                'rule_table':dev['rule_table'], 'rule_reference':dev['rule_reference'], 'frozen_candidate':None,
                'decision':('No capped candidate met the development rule. The joint check (study 02) and v2 are '
                            'unchanged. Nothing is left to test, so no fresh recordings are chosen or downloaded for '
                            'this study, and the primary question below is not asked.'),
                'primary_question':PRIMARY_QUESTION, 'comparators':dev['comparators'], 'candidates':dev['candidates'],
                'code_sha256':_code_hashes()}
    output.write_text(json.dumps(protocol, indent=2), encoding='utf-8')
    return protocol
