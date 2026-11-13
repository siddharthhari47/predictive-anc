"""Study 05: fading tones in and out of the joint band check's output (results-tone-forecaster-05).

Why: study 03 (results-tone-forecaster-03) found that 14 of the joint check's 25
development boosts sit on scenes where the sound changes suddenly at 9 s, and
one more on the 5 s mains clip before the check's first decision. It guessed
that the check's 8 s of medians react too slowly. The study-05 diagnosis
(results-tone-forecaster-05/diagnosis, development material only) found that a
faster check cannot fix the change scenes: an oracle that goes silent the
instant the sound changes still leaves 9 of the 14, and the clean tones
themselves, switched on and off with no delay, have 15. The boosts come from
the output starting and stopping a strong tone in one block. Fading each tone
in and out (tone_react.FadeCheckBank) is the remedy tested here. The start case
is a property of the start setting, not of speed: a 0.2 s floor avoids it on
that clip.

Order, enforced in code:
1. Diagnosis and design used development material only: the study-01
   development recordings, the 44 development synthetic scenes and study 03's 8
   buzz scenes.
2. `run_development` scores the candidates and every comparator on that
   material and applies DEVELOPMENT_RULE, written after the trials and before
   the formal run.
3. `freeze_protocol` writes protocol.json once, with the code hashes. With no
   eligible candidate it records that and nothing is tested. With one, it also
   freezes the fresh recordings (FRESH_RECORDINGS, chosen from Commons metadata
   only) and draws the synthetic test frequencies.
4. `run_test` runs once, after the fresh recordings are downloaded (with the
   user's approval) into FRESH_AUDIO, and refuses if the test folder exists,
   the code changed or a file differs from the protocol.

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
from . import forecaster_study_03 as fs3
from .real_hum_study import ELECTRICAL
from .selection_study import frequency_extent, scene_set
from .tone_react import FadeCheckBank

ROOT = s1.ROOT
STUDY = ROOT/'results-tone-forecaster-05'
FRESH_AUDIO = ROOT/'external-audio'/'wikimedia-commons-fresh-05'
WORKERS = fs2.WORKERS
FROZEN_CODE = fs3.FROZEN_CODE+('tone_react.py', 'forecaster_study_05.py', 'forecaster_report_05.py')
CHANGE_SCENES = ('tone_appears_9s', 'tones_stop_9s', 'source_change_9s')

# Study 02's run_methods looks bank kinds up in its own table (frozen, so not edited). Registering here also
# registers in every worker, since workers import this module to run its tasks.
fs2.BANK_KINDS.setdefault('react', FadeCheckBank)

# ---------- methods ----------


def react(name, **options):
    return {'name':name, 'kind':'react', 'nb_tau':0., 'lines':True, 'options':options}


CANDIDATES = [react('fade0.05', fade_in_seconds=.05, fade_out_seconds=.05),
              react('fade0.1', fade_in_seconds=.1, fade_out_seconds=.1),
              react('fade0.2', fade_in_seconds=.2, fade_out_seconds=.2),
              react('fade0.1_linear', fade_in_seconds=.1, fade_out_seconds=.1, shape='linear'),
              react('fade0.1_switch0.3', fade_in_seconds=.1, fade_out_seconds=.1, switch_fade_seconds=.3),
              react('fade0.1_start0.2', fade_in_seconds=.1, fade_out_seconds=.1, start=[.2, False])]
COMPARATORS = fs3.COMPARATORS
DEVELOPMENT_RULE = (
    'Written after the diagnostic trials on development material (results-tone-forecaster-05/diagnosis) and before '
    'the formal development run. Candidates, all gated: the joint band check of study 02 with each tone fading in and '
    'out of every output setting instead of switching: raised-cosine fades of 0.05, 0.1 and 0.2 s; a 0.1 s linear '
    'fade; a 0.1 s fade plus a 0.3 s cross-fade when the check changes its setting; and a 0.1 s fade with a 0.2 s '
    'start floor instead of 0.1 s. Development material: the eight study-01 development recordings, the 44 '
    'development synthetic scenes and study 03\'s 8 buzz scenes. A boost is a third-octave band 1 dB or more louder; '
    'a near-boost 0.5 dB or more; both are counted over development recordings (either horizon) plus late synthetic '
    'windows. The change scenes are tone_appears_9s, tones_stop_9s and source_change_9s. Eligible only if: (a) fewer '
    'boosts than joint + gate; (b) fewer boosts on the change scenes than joint + gate; (c) no more near-boosts than '
    'joint + gate; (d) no more whole-band boosts (whole 35-350 Hz band below -0.5 dB on a development recording) than '
    'joint + gate; (e) the tone gain over v2 is kept: the median, over development acoustic recordings with reference '
    'tones, of the tone-bin gain averaged over both horizons is at least v2 + gate\'s plus half of the amount by which '
    'joint + gate exceeds v2 + gate; (f) the median whole-band gain over development acoustic recordings, averaged '
    'over both horizons, is at least joint + gate\'s minus 0.1 dB; (g) the mean synthetic objective is at least joint '
    '+ gate\'s minus 0.5 dB and its synthetic windows below -0.5 dB are no more than joint + gate has; (h) its own '
    'compute time per 10 ms block at the 99th percentile, median over runs, is within 0.5 ms of joint\'s in the same '
    'run. Study 03 used the worst run instead, which swings with the shared machine\'s load: in the study-05 trial the '
    'fade code with one-block fades (the joint check\'s own forecasts) was 2.5 ms slower than the joint check on its '
    'worst run, while timed side by side in one process, after the output step was made an array step, it is about '
    '0.1 ms slower on average and 0.3-0.4 ms at the median 99th percentile (diagnosis timing01, timing02). Among '
    'eligible candidates, pick the one with the fewest boosts, then the fewest '
    'near-boosts, then the higher tone-bin median. If none is eligible, nothing is frozen: the joint check and v2 are '
    'unchanged, and there is nothing to test.')
PRIMARY_QUESTION = (
    'Only if a candidate is frozen. On fresh material the project has never used: (1) does the frozen candidate + gate '
    'have fewer late boost windows (a band 1 dB or more louder, either horizon) than joint + gate on the fresh '
    'synthetic change scenes? (2) On the fresh recordings, does it have no more third-octave boosts and no more '
    'whole-band boosts than joint + gate? (3) Is its median tone-bin gain at 20 ms, over the fresh acoustic recordings '
    'with reference tones, above v2 + gate\'s? Answered separately. Secondary, reported but not part of the question: '
    'the whole-band gain against joint + gate, which the fades raised on two development recordings.')


def _recording_task(args):
    return fs2._recording_task(args)


def _scene_task(args):
    return fs2._scene_task(args)

# ---------- the development rule ----------


def change_scene_boosts(scenes, method, threshold=1.):
    """Late windows (both horizons) with a band `threshold` dB or more louder, on the sudden-change scenes only."""
    return int(sum(s['max_third_octave_change_db'] >= threshold for sc in scenes if sc['scene'].split('#')[0] in CHANGE_SCENES
                   for s in sc['late_window_scores'] if s['method'] == method))


def _counts(rec, syn, scenes, m):
    return dict(fs3._counts(rec, syn, m), change_scene_boosts=change_scene_boosts(scenes, m))


def apply_development_rule(rec, syn, records, scenes, candidates):
    def p99(name):
        return float(np.median([r['methods'][name]['own_block_ms_p99'] for r in records+scenes]))
    j, v2 = _counts(rec, syn, scenes, 'joint_gated'), _counts(rec, syn, scenes, 'v2_gated')
    tone_needed = v2['tone_bin_median_db']+.5*(j['tone_bin_median_db']-v2['tone_bin_median_db'])
    table = []
    for c in candidates:
        n = _counts(rec, syn, scenes, c['name']+'_gated')
        checks = {'a_fewer_boosts':n['boosts'] < j['boosts'],
                  'b_fewer_change_boosts':n['change_scene_boosts'] < j['change_scene_boosts'],
                  'c_near_boosts':n['near_boosts'] <= j['near_boosts'],
                  'd_whole_band_boosts':n['whole_band_boosts'] <= j['whole_band_boosts'],
                  'e_tone_gain_kept':n['tone_bin_median_db'] >= tone_needed,
                  'f_whole_band':n['whole_band_median_db'] >= j['whole_band_median_db']-.1,
                  'g_synthetic':(n['synthetic_objective_db'] >= j['synthetic_objective_db']-.5
                                 and n['synthetic_windows_below_minus_half_db'] <= j['synthetic_windows_below_minus_half_db']),
                  'h_time':p99(c['name']) <= p99('joint')+.5}
        table.append(dict(candidate=c['name'], options=c['options'], tone_bin_needed_db=tone_needed,
                          p99_block_ms=p99(c['name']), checks=checks, eligible=all(checks.values()), **n))
    eligible = [t for t in table if t['eligible']]
    pick = min(eligible, key=lambda t: (t['boosts'], t['near_boosts'], -t['tone_bin_median_db']))['candidate'] if eligible else None
    reference = {name:dict(p99_block_ms=p99(name) if name != 'v2' else None, **_counts(rec, syn, scenes, name+'_gated'))
                 for name in ('joint', 'v2', 'bank_wide_lines')}
    return pick, table, reference


def fade_activity(records, scenes, candidates):
    """Per candidate, summed over runs: tones dropped while still fading out (ghosts), blocks with a tone mid-fade."""
    out = {}
    for c in candidates:
        out[c['name']] = {part:{key:int(sum(r['methods'][c['name']]['counters'][key] for r in runs))
                                for key in ('ghosts', 'fading_tone_blocks')}
                          for part, runs in (('recordings', records), ('scenes', scenes))}
    return out

# ---------- fresh test material: frozen before any download ----------

FRESH_RECORDINGS = [
    {'file':'Ventilador.ogg', 'title':'File:Ventilador.ogg', 'sha1':'84b94581ae006dc547c725379a5ea1d4217b26e1',
     'bytes':148132, 'seconds':18.4, 'author':'Armartinell', 'licence':'CC BY-SA 4.0', 'acoustic':True,
     'note':'A fan; the description says the clip includes switching it on and off.'},
    {'file':'Akkuschrauber_–_Cordless_Screwdriver.ogg', 'title':'File:Akkuschrauber – Cordless Screwdriver.ogg',
     'sha1':'fef3b7832aaeba1cb37ed6c2768a480c32a6ba2d', 'bytes':1789738, 'seconds':39.3, 'author':'Maximilian Schönherr',
     'licence':'CC BY-SA 4.0', 'acoustic':True,
     'note':'An electric motor; the description says switched on, low, higher and maximum power, then shutdown.'},
    {'file':'ÖBB_Taurus_Start-Up.ogg', 'title':'File:ÖBB Taurus Start-Up.ogg', 'sha1':'2be522bc0e5b69ae31f6122bd288ad56d1d74475',
     'bytes':445281, 'seconds':17.0, 'author':'3LM6wjuS', 'licence':'CC BY-SA 4.0', 'acoustic':True,
     'note':'Start-up of an electric locomotive.'},
    {'file':'Son_démarrage_Mp14-8.ogg', 'title':'File:Son démarrage Mp14-8.ogg', 'sha1':'025d33a0f369d1c87546a3dd9a04cc44e25885b5',
     'bytes':347102, 'seconds':25.4, 'author':'Lodaï', 'licence':'CC BY-SA 4.0', 'acoustic':True,
     'note':'Start-up of a Paris metro train.'},
    {'file':'Elektrorasur-01.ogg', 'title':'File:Elektrorasur-01.ogg', 'sha1':'06b7d6ea9cdb7ed36de0efaf2b09af4232a29ab1',
     'bytes':546625, 'seconds':20.0, 'author':'Priwo', 'licence':'Public domain', 'acoustic':True},
    {'file':'Propeller-plane-flying-steady-01.wav', 'title':'File:Propeller-plane-flying-steady-01.wav',
     'sha1':'ac14ff5431e8986507dee2353f745a1feae102e3', 'bytes':5761156, 'seconds':20.0, 'author':'Versatile Virtuoso',
     'licence':'CC BY-SA 4.0', 'acoustic':True},
    {'file':'Sewerage_pumping_station_(Starnberg-Leutstetten_PW83)_c.ogg',
     'title':'File:Sewerage pumping station (Starnberg-Leutstetten PW83) c.ogg', 'sha1':'01f9c17e7ab81cde924ab3ae7e8ed0ac66eeef89',
     'bytes':1000693, 'seconds':99.9, 'author':'PaulSch', 'licence':'CC0', 'acoustic':True,
     'note':'Pumping and flushing, recorded outside the building.'},
    {'file':'Noise-Pollution-Filters-Bird-Communities-Based-on-Vocal-Frequency-pone.0027052.s001.ogg',
     'title':'File:Noise-Pollution-Filters-Bird-Communities-Based-on-Vocal-Frequency-pone.0027052.s001.ogg',
     'sha1':'47a3e0bed15145750a15d630dd8c3e73f471284d', 'bytes':124059, 'seconds':15.1, 'author':'Francis C, Ortega C, Cruz A',
     'licence':'CC BY 2.5', 'acoustic':True, 'note':'Background noise 100 m from a gas compressor exhaust (PLOS ONE supplement).'},
]
FRESH_INDEPENDENCE = (
    'Independent of all earlier work in this project: the eight recordings were chosen on 19 Oct 2026 by their Commons '
    'title, description, length, licence and author only, from a metadata search kept in '
    'results-tone-forecaster-05/fresh-metadata. None was downloaded, played or analysed before this protocol was frozen. '
    'No author also made a development recording, a study-01 recording or a study-02 fresh recording, and none comes '
    'from the Work With Sounds collection that supplied three development recordings. Four were chosen because their '
    'descriptions say the sound starts, stops or changes speed (the fan, the screwdriver and the two train start-ups), '
    'since this study is about sudden changes and starts.')
SYNTHETIC_TEST = {'standard_seed':20261022, 'standard_repeats':6, 'standard_scene_seeds':'13100+100*repeat+scene index',
                  'wander_seed':20261023, 'wander_repeats':3, 'wander_scene_seeds':'14100+100*repeat+scene index',
                  'parity':1, 'parity_note':'odd 10 Hz bands (development used even)', 'forbidden_within_hz':2.}


def fresh_problems(entries=None):
    """Why listed fresh recordings would not be fresh: the file is already under external-audio (outside this study's
    own folder), its author made an earlier recording, or study 04 listed it for its own test."""
    entries = FRESH_RECORDINGS if entries is None else entries
    audio = ROOT/'external-audio'
    elsewhere = [p for p in audio.rglob('*') if p.is_file() and FRESH_AUDIO not in p.parents]
    local = {p.name for p in elsewhere if p.suffix.lower() != '.md'}
    credits = ' '.join(p.read_text(encoding='utf-8') for p in elsewhere if p.name == 'SOURCES.md').lower()
    credits += ' '+' '.join(e['author'] for e in fs2.FRESH_RECORDINGS).lower()
    study04 = ROOT/'results-tone-forecaster-04'/'fresh-metadata'/'fresh_recordings.json'
    taken = {e.get('file') for e in json.loads(study04.read_text(encoding='utf-8'))} if study04.exists() else set()
    problems = []
    for e in entries:
        if e['file'] in local:
            problems.append(f"{e['file']} is already under external-audio")
        if e['author'].lower() in credits:
            problems.append(f"{e['file']}: {e['author']} made an earlier recording")
        if e['file'] in taken:
            problems.append(f"{e['file']} is on study 04's fresh list")
    return problems


def synthetic_forbidden(wander_dev):
    """Every development frequency (studies 01-03) and study 03's buzz draws."""
    release = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))
    buzz = [f for g in fs3.buzz_scenes()[0] for fs in g.values() for f in fs]
    return sorted(set(fs2.development_frequencies(release, wander_dev)+[round(float(f), 2) for f in buzz]))


def test_scene_tasks(protocol):
    syn = protocol['synthetic_test']
    standard, wander = fs2.draw_synthetic_test(syn, syn['forbidden_frequencies'])
    if json.loads(json.dumps([standard, wander])) != [syn['standard_draws'], syn['wander_draws']]:
        raise ValueError('Synthetic test draws differ from the protocol.')
    tasks = []
    for rep, g in enumerate(standard):
        tasks += [(f'{n}#test{rep}', 'standard', s, 13100+100*rep+i, None) for i, (n, s) in enumerate(scene_set(g).items())]
    for rep, g in enumerate(wander):
        tasks += [(f'{n}#test{rep}', 'wander', s, 14100+100*rep+i, None) for i, (n, s) in enumerate(s1.wander_scene_set(g).items())]
    return tasks

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
    seen = ({e['file'] for e in split['test_files']}|{e['file'] for e in fs2.FRESH_RECORDINGS}
            | {e['file'] for e in FRESH_RECORDINGS})
    if any(p.name in seen for p in paths):
        raise ValueError('A test or fresh recording reached development.')
    draws, wander, scene_tasks = s1.development_scenes()
    buzz, buzz_tasks = fs3.buzz_scenes()
    n = len(paths)
    out = fs2._pool([(_recording_task, (str(p), methods, v2, p.name not in ELECTRICAL)) for p in paths]
                    + [(_scene_task, (*t, methods, v2)) for t in scene_tasks+buzz_tasks], workers)
    records, scenes = out[:n], out[n:]
    names = fs2.method_names(methods)
    rec, syn, fams = fs2.summarize(records, scenes, names)
    pick, table, reference = apply_development_rule(rec, syn, records, scenes, candidates)
    result = {'kind':'tone_forecaster_05_development', 'created_utc':datetime.now(timezone.utc).isoformat(),
              'stage':('development only; no study-01 test recording, study-02 fresh recording, synthetic test scene or '
                       'new fresh recording was read'), 'note':note, 'v2':v2,
              'candidates':list(candidates), 'comparators':COMPARATORS, 'rule':DEVELOPMENT_RULE,
              'development_files':[p.name for p in paths], 'release_development_draws':draws,
              'wander_development_draws':wander, 'buzz_development':fs3.BUZZ_DEV, 'buzz_development_draws':buzz,
              'recordings':records, 'scenes':scenes,
              'summary':{'recordings':rec, 'synthetic':syn, 'synthetic_by_family':fams},
              'fade_activity':fade_activity(records, scenes, candidates),
              'rule_table':table, 'rule_reference':reference, 'development_pick':pick,
              'runtime_seconds':time.perf_counter()-started, 'code_sha256':_code_hashes(),
              'labels':'Reference-signal prediction only. Not acoustic attenuation.'}
    (output/'development.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    from .forecaster_report_05 import write_development_summary
    write_development_summary(output, result)
    return result


def _project_path(folder):
    folder = Path(folder).resolve()
    return folder.relative_to(ROOT).as_posix() if folder.is_relative_to(ROOT) else folder.as_posix()


def freeze_protocol(development_folder, output=STUDY/'protocol.json'):
    """Write the frozen protocol from a development run. Refuses to overwrite, and refuses after a code change."""
    output = Path(output)
    if output.exists():
        raise ValueError('protocol.json already exists; the protocol is frozen once.')
    dev = json.loads((Path(development_folder)/'development.json').read_text(encoding='utf-8'))
    if dev['code_sha256'] != _code_hashes():
        raise ValueError('Code changed after the development run; rerun development before freezing.')
    chosen = next((c for c in dev['candidates'] if c['name'] == dev['development_pick']), None)
    protocol = {'kind':'tone_forecaster_05_frozen_protocol', 'created_utc':datetime.now(timezone.utc).isoformat(),
                'development_run':_project_path(development_folder), 'rule':dev['rule'],
                'rule_table':dev['rule_table'], 'rule_reference':dev['rule_reference'], 'frozen_candidate':chosen,
                'primary_question':PRIMARY_QUESTION, 'comparators':dev['comparators'], 'candidates':dev['candidates'],
                'code_sha256':_code_hashes()}
    if chosen is None:
        protocol['decision'] = ('No candidate met the development rule. The joint check (study 02) and v2 are unchanged. '
                                'Nothing is left to test, so no fresh recordings are chosen or downloaded for this study, '
                                'and the primary question is not asked.')
    else:
        if not FRESH_RECORDINGS:
            raise ValueError('A candidate met the rule but no fresh recordings are listed; choose them from Commons '
                             'metadata, rerun development, then freeze.')
        if fresh_problems():
            raise ValueError('Fresh list problems: '+'; '.join(fresh_problems()))
        syn = dict(SYNTHETIC_TEST, forbidden_frequencies=synthetic_forbidden(dev['wander_development_draws']),
                   not_excluded=('Study 02\'s synthetic test draws are not excluded: every odd-band frequency lies within '
                                 '2 Hz of one of them, so excluding them leaves no room (checked before this freeze). No '
                                 'study-05 choice used them; the scenes here have new seeds, so new noise and phases.'))
        standard, wander = fs2.draw_synthetic_test(syn, syn['forbidden_frequencies'])
        syn.update(standard_draws=standard, wander_draws=wander)
        protocol.update(decision=f"{chosen['name']} met the development rule and is frozen for one test.",
                        v2=dev['v2'], fresh_recordings=FRESH_RECORDINGS, fresh_folder=_project_path(FRESH_AUDIO),
                        fresh_independence=FRESH_INDEPENDENCE,
                        fresh_missing_rule=('A recording that cannot be downloaded is reported as missing and is not '
                                            'replaced; a present file whose size or SHA-1 differs stops the test.'),
                        synthetic_test=syn)
    output.write_text(json.dumps(protocol, indent=2), encoding='utf-8')
    return protocol


def run_test(output=STUDY/'test', protocol_path=STUDY/'protocol.json', fresh_folder=FRESH_AUDIO, workers=WORKERS):
    """Runs once: the fresh recordings (primary) and the fresh synthetic scenes."""
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
    methods = protocol['comparators']+[protocol['frozen_candidate']]
    tasks = test_scene_tasks(protocol)
    output.mkdir(parents=True)
    started = time.perf_counter()
    out = fs2._pool([(_recording_task, (str(p), methods, protocol['v2'], e['acoustic'])) for e, p in present]
                    + [(_scene_task, (*t, methods, protocol['v2'])) for t in tasks], workers)
    records, scenes = out[:len(present)], out[len(present):]
    names = fs2.method_names(methods)
    rec, syn, fams = fs2.summarize(records, scenes, names)
    result = {'kind':'tone_forecaster_05_test', 'created_utc':datetime.now(timezone.utc).isoformat(), 'protocol':protocol,
              'fresh_files':[p.name for _, p in present], 'fresh_missing':[e['file'] for e, p in fresh if p is None],
              'fresh_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for _, p in present},
              'fresh_recordings':records, 'scenes':scenes,
              'change_scene_boosts':{m:change_scene_boosts(scenes, m) for m in names if m.endswith('gated')},
              'summary':{'fresh':rec, 'synthetic':syn, 'synthetic_by_family':fams},
              'runtime_seconds':time.perf_counter()-started,
              'labels':'Reference-signal prediction only. Not acoustic attenuation.'}
    (output/'test.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    from .forecaster_report_05 import write_test_report
    write_test_report(output.parent, result)
    return result
