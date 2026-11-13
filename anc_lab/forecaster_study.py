"""A better real-tone forecaster: developed on development material only, then tested once.

Why: on the real hum recordings (results-real-hums-01), the frozen v2 tone
forecaster reached a median 2.9 dB at the tones, while a ridge AR adapted on
each file's first 40% reached 6.3 dB. This study tries forecasters that keep
v2's per-tone output (which tune-by-ear needs) but adapt each tone's memory.

Order, enforced in code:
1. results-tone-forecaster-01/split.json declares development and test
   recordings (author groups shuffled with a stated seed), written before any
   new forecaster ran. `declared_split` reproduces it.
2. `run_development` evaluates candidates on development recordings and
   development synthetic scenes only. It refuses any test file.
3. `freeze_protocol` applies the development rule (DEVELOPMENT_RULE, stated
   before the first development run) and writes protocol.json: the chosen
   forecaster, every comparator, the code hashes and fresh synthetic test seeds.
4. `run_test` runs once: it refuses if the test folder exists or the code has
   changed since the freeze, then scores the frozen choice and every comparator
   on the test recordings and freshly drawn synthetic test scenes.

The recordings are NOT independent of earlier work: every file's v2 and AR
scores were read in results-real-hums-01 before the split was declared.

Reference-signal prediction only: no acoustic path, no playback, no ear measurement.
"""
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
from scipy import signal
from threadpoolctl import threadpool_limits

from .assessment import forecast_scores
from .generalization import DEVELOPMENT, HELD_OUT, normalized_prefix
from .predictors import DirectPredictor
from .real_hum_study import ELECTRICAL, PREFIX_FRACTION, load_any, prominent_tones, spectrum, tonal_fraction, tone_band_gain
from .release_study import HIGH, LOW, SPACING, draw_groups, gate_output, in_parity, make_dev_scenes, objective
from .selection_study import (BLOCK, FS, HORIZONS_MS, SECONDS, TEST_GROUPS, TRAIN_END, VAL_END, frequency_extent,
                              horizon_setup, scene_set, synthesize_scene)
from .tone_forecasters import OnlineRidgeAR, ProminentLines, ToneObserverBank, stream_forecasts
from .tone_selection import SelectedToneForecaster, ToneSelector

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT/'external-audio'/'wikimedia-commons-2026-10-16'
REAL_HUMS = ROOT/'results-real-hums-01'/'real_hums.json'
RELEASE_PROTOCOL = ROOT/'results-release-study-01'/'release_protocol.json'
STUDY = ROOT/'results-tone-forecaster-01'
WORKERS = max(1, min(19, (os.cpu_count() or 2)-2))
FROZEN_CODE = ('tone_forecasters.py', 'forecaster_study.py', 'tone_selection.py', 'predictors.py',
               'real_hum_study.py', 'release_study.py', 'selection_study.py', 'assessment.py', 'generalization.py')

# ---------- the declared recording split (reproduces split.json) ----------

SPLIT_SEED, MIN_DEV_TONE_FILES = 20261017, 5
RECORDING_GROUPS = {
    'Gravity Sound':['Air_conditioner_hum_2_Gravity_Sound_.wav', 'Air_conditioner_hum_Gravity_Sound_.wav', 'Fan_Gravity_Sound_.wav'],
    'stephan':['Inside_of_refrigerator.ogg', 'Microwave_oven.ogg', 'Table_ventilator.ogg'],
    'Beeld en Geluid':['Omvormer_en_compressor_van_een_tram_-_SoundCloud_-_Beeld_en_Geluid.ogg',
                       'Ventilator_in_een_tunnel_-_SoundCloud_-_Beeld_en_Geluid.ogg'],
    'Work With Sounds':['WWS_Aircompressor.ogg', 'WWS_Bediadiesellocomotiveidling.ogg', 'WWS_Compressor.ogg'],
    'Antti Luode':['Server_Room_Antti_Luode_.mp3'],
    'Marhesky':['Sistema_de_ventilaci_n.ogg'],
    'Doggo19292':['Sounds_made_by_a_fan.wav'],
    'Hippocampuz':['Ventilador_de_estudio.ogg'],
    'the_riel_thing':['Ventilator_Marsmanplein_120919_05_-_SoundCloud_-_the_riel_thing.ogg'],
}


def declared_split(has_tones):
    """Author groups shuffled with SPLIT_SEED; groups go to development until it holds
    MIN_DEV_TONE_FILES recordings that had reference tones in results-real-hums-01."""
    order = list(RECORDING_GROUPS)
    order = [order[i] for i in np.random.default_rng(SPLIT_SEED).permutation(len(order))]
    dev, count = [], 0
    for name in order:
        if count >= MIN_DEV_TONE_FILES:
            break
        dev.append(name)
        count += sum(has_tones[f] for f in RECORDING_GROUPS[name])
    return {'group_order_after_shuffle':order, 'development_groups':dev,
            'development_files':[f for g in dev for f in RECORDING_GROUPS[g]]+sorted(ELECTRICAL),
            'test_files':[f for g in order if g not in dev for f in RECORDING_GROUPS[g]]}


def load_split(path=STUDY/'split.json'):
    split = json.loads(Path(path).read_text(encoding='utf-8'))
    real = json.loads(REAL_HUMS.read_text(encoding='utf-8'))
    again = declared_split({r['file']:bool(r['reference_tones_hz']) for r in real['files']})
    listed = {'development_files':[e['file'] for e in split['development_files']],
              'test_files':[e['file'] for e in split['test_files']]}
    if listed['development_files'] != again['development_files'] or listed['test_files'] != again['test_files']:
        raise ValueError('split.json does not match the declared rule.')
    return split


def checked_path(entry):
    path = AUDIO/entry['file']
    if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
        raise ValueError(f"{entry['file']} changed since the split was declared.")
    return path

# ---------- synthetic scenes whose tones wander (development and test draws) ----------

WANDER_SIZES = {'slow':2, 'fast':2, 'mixed':3, 'am':2}


def draw_wander(rng, parity, forbidden):
    out = {}
    for key, n in WANDER_SIZES.items():
        for _ in range(100000):
            fs = sorted(round(float(f), 1) for f in rng.uniform(LOW, HIGH, n))
            if (all(in_parity(f, parity) and all(abs(f-b) > 2 for b in forbidden) for f in fs)
                    and all(b-a >= SPACING for a, b in zip(fs, fs[1:]))):
                out[key] = fs
                break
        else:
            raise RuntimeError('Could not draw fresh frequencies.')
    return out


def wander_tone(freq, amp, linewidth_hz, am_depth=0.):
    return {'freq':freq, 'amp':amp, 'start':0., 'stop':float(SECONDS), 'drift_hz_per_s':0.,
            'linewidth_hz':linewidth_hz, 'am_depth':am_depth}


def wander_scene_set(g):
    """Tones whose phase wanders (random walk; Lorentzian line of the stated width) and,
    in one scene, whose amplitude drifts slowly. Real machine hum behaves more like this
    than like the perfectly steady tones of scene_set."""
    return {
        'wander_slow':{'noise':('white', .05), 'tones':[wander_tone(f, a, .1) for f, a in zip(g['slow'], [.4, .2])]},
        'wander_fast':{'noise':('white', .05), 'tones':[wander_tone(f, a, 1.) for f, a in zip(g['fast'], [.4, .2])]},
        'wander_mixed_noisy':{'noise':('white', .2), 'tones':[wander_tone(f, a, w) for f, a, w in
                                                              zip(g['mixed'], [.3, .2, .15], [.05, .5, 2.])]},
        'wander_am_rumble':{'noise':('brown', .3), 'tones':[wander_tone(f, a, .3, .5) for f, a in zip(g['am'], [.25, .15])]},
    }


def synthesize_wander(spec, seed):
    rng = np.random.default_rng(seed)
    n = SECONDS*FS
    kind, level = spec['noise']
    noise = rng.standard_normal(n)
    if kind == 'brown':
        noise = signal.lfilter([1.], [1., -.98], noise)
    audio = level*noise/np.std(noise)
    t = np.arange(n)/FS
    pole = np.exp(-1/FS)
    for tn in spec['tones']:
        walk = np.cumsum(rng.normal(0., np.sqrt(2*np.pi*tn['linewidth_hz']/FS), n))
        envelope = np.ones(n)
        if tn['am_depth']:
            slow = signal.lfilter([1-pole], [1., -pole], rng.standard_normal(n))
            envelope = np.maximum(1+tn['am_depth']*slow/np.std(slow), .1)
        audio += tn['amp']*envelope*np.sin(2*np.pi*tn['freq']*t+walk+rng.uniform(-np.pi, np.pi))
    return audio

# ---------- methods ----------

DEV_CANDIDATES = [
    {'name':'v2_fit0.6', 'kind':'v2', 'window_seconds':.6},
    {'name':'v2_fit1.2', 'kind':'v2', 'window_seconds':1.2},
    {'name':'bank_narrow', 'kind':'bank', 'nb_tau':.1},
    {'name':'bank_mid', 'kind':'bank', 'nb_tau':.02},
    {'name':'bank_wide', 'kind':'bank', 'nb_tau':0.},
    {'name':'bank_narrow_lines', 'kind':'bank', 'nb_tau':.1, 'lines':True},
    {'name':'bank_wide_lines', 'kind':'bank', 'nb_tau':0., 'lines':True},
]
COMPARATORS = [
    {'name':'v2', 'kind':'v2', 'window_seconds':.3},
    {'name':'prefix_ar', 'kind':'prefix_ar'},
    {'name':'online_ar', 'kind':'online_ar'},
]
DEVELOPMENT_RULE = (
    'Among the gated candidates (v2 with longer fit windows, and the observer-bank variants), pick the one with the '
    'highest median, over development acoustic recordings that have reference tones, of the tone-bin gain averaged '
    'over both horizons. Eligible only if, on development material: (a) whole-band boosts (whole 35-350 Hz band '
    'below -0.5 dB at either horizon, any development recording) are no more than v2 + gate has; (b) third-octave '
    'boosts (a third-octave band 1 dB or more louder, any development recording and horizon) are no more than v2 + '
    'gate has; (c) the median whole-band gain over development acoustic recordings, averaged over both horizons, is at '
    'least v2 + gate\'s minus 0.1 dB; (d) the mean synthetic development objective (release-study objective) is at least '
    'v2 + gate\'s minus 0.5 dB and its synthetic windows below -0.5 dB are no more than v2 + gate has; (e) the '
    'compute time it adds per 10 ms block, excluding the tone-selector update that v2 also runs, is below 5 ms at the '
    '99th percentile (offline Python, one thread, measured under the parallel pool). AR methods are comparators, not candidates: they '
    'give no per-tone output, which tune-by-ear needs. If no candidate is eligible, v2 stays.')


def make_bank(method, v2):
    return ToneObserverBank(FS, BLOCK, ToneSelector(FS, **v2['selector']), nb_tau=method['nb_tau'],
                            release={'ratio':v2['forecaster']['release_ratio'],
                                     'seconds':v2['forecaster']['release_window_seconds']},
                            release_long_seconds=v2['forecaster']['window_seconds'],
                            candidates=ProminentLines() if method.get('lines') else None)


def run_methods(x, grid, keep, methods, v2, train_end):
    """Forecasts at grid[keep] for each method. Online methods run causally over the whole grid."""
    _, horizons, groups = horizon_setup()
    preds, info = {'zero':np.zeros((int(keep.sum()), len(horizons)))}, {}
    for m in methods:
        started, extra = time.perf_counter(), {}
        if m['kind'] in ('v2', 'bank'):
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
                         'counters':bank.counters,
                         'seconds_by_part':{k:round(v, 4) for k, v in bank.timing.items()},
                         'settings':bank.settings()}
            gated, enabled = gate_output(x, grid, shadow, groups, v2['gate'])
            preds[m['name']+'_ungated'], preds[m['name']+'_gated'] = shadow[keep], gated[keep]
            extra['gate_open_fraction'] = enabled[keep].mean(axis=0).tolist()
        elif m['kind'] == 'prefix_ar':
            model = DirectPredictor('ridge_ar', horizons, seed=7).fit(x, train_end)
            preds[m['name']] = model.predict(x, grid[keep], horizons)
        elif m['kind'] == 'online_ar':
            ar = OnlineRidgeAR(FS, horizons)
            preds[m['name']] = ar.predict(x, grid[keep], horizons)
            extra = {'refits':ar.fit_count, 'settings':ar.settings()}
        else:
            raise ValueError(m['kind'])
        extra['seconds'] = time.perf_counter()-started
        info[m['name']] = extra
    return preds, info

# ---------- scoring ----------

THIRD_OCTAVES_HZ = 1000*2**(np.arange(-14, -4)/3)       # 39.4 ... 315 Hz; edges span 35-354 Hz


def third_octave_changes(target, forecast, fs=FS):
    """Level change per third-octave band if the forecast were subtracted (dB; positive = louder)."""
    f, pa = spectrum(np.ravel(target), fs)
    _, pe = spectrum(np.ravel(target-forecast), fs)
    out = []
    for c in THIRD_OCTAVES_HZ:
        band = (f >= c*2**(-1/6)) & (f < c*2**(1/6))
        out.append(float(10*np.log10(max(pe[band].sum(), 1e-30)/max(pa[band].sum(), 1e-30))))
    return out


def score_forecasts(x, origins, preds, tones):
    _, _, groups = horizon_setup()
    rows = []
    for (cols, hz), ms in zip(groups, HORIZONS_MS):
        target = x[origins[:, None]+hz]
        for m, p in preds.items():
            s = forecast_scores(target, p[:, cols], FS)
            changes = third_octave_changes(target, p[:, cols])
            rows.append({'method':m, 'horizon_start_ms':ms, 'band_gain_db':s['band_prediction_gain_db'],
                         'tone_band_gain_db':tone_band_gain(target, p[:, cols], tones),
                         'third_octave_change_db':changes, 'max_third_octave_change_db':max(changes),
                         'third_octave_boosts_over_1db':int(sum(c >= 1. for c in changes))})
    return rows


def _recording_task(args):
    path, methods, v2 = args
    path = Path(path)
    with threadpool_limits(limits=1):
        audio, info = load_any(path)
        prefix = int(PREFIX_FRACTION*len(audio))
        mean, scale = float(np.mean(audio[:prefix])), max(float(np.std(audio[:prefix])), 1e-12)
        x = (audio-mean)/scale
        _, horizons, _ = horizon_setup()
        grid = np.arange(BLOCK*50, len(x)-int(max(horizons)), BLOCK)
        keep = grid >= prefix
        preds, method_info = run_methods(x, grid, keep, methods, v2, prefix)
        tones = prominent_tones(x[prefix:])
        fraction = tonal_fraction(x[prefix:], tones)
        return {'file':path.name, 'electrical_not_acoustic':path.name in ELECTRICAL, 'audio':info,
                'analysed_seconds':len(x)/FS, 'prefix_seconds':prefix/FS, 'test_seconds':(len(x)-prefix)/FS,
                'reference_tones_hz':tones, 'reference_tone_band_power_fraction':fraction,
                'tone_only_ceiling_db':float(-10*np.log10(max(1-fraction, 1e-6))),
                'methods':method_info, 'scores':score_forecasts(x, grid[keep], preds, tones)}


def _scene_task(args):
    """One synthetic scene. `x` is given for the release-study development scenes (already
    synthesized with that study's seeds); otherwise the scene is synthesized from `seed`."""
    name, family, spec, seed, x, methods, v2 = args
    with threadpool_limits(limits=1):
        if x is None:
            raw = synthesize_scene(spec, seed) if family == 'standard' else synthesize_wander(spec, seed)
            x, _ = normalized_prefix(raw, TRAIN_END)
        _, horizons, groups = horizon_setup()
        grid = np.arange(BLOCK*50, SECONDS*FS-int(max(horizons)), BLOCK)
        preds, method_info = run_methods(x, grid, np.ones(len(grid), bool), methods, v2, TRAIN_END)
        late = grid >= VAL_END
        # Tone bins only for tones that stay put for the whole scene.
        steady = [tn['freq'] for tn in spec['tones'] if not tn['drift_hz_per_s'] and tn['start'] == 0 and tn['stop'] >= SECONDS]
        rows = score_forecasts(x, grid[late], {m:p[late] for m, p in preds.items()}, steady)
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

def _score(record, method, ms, key):
    return next(s[key] for s in record['scores'] if s['method'] == method and s['horizon_start_ms'] == ms)


def recording_summary(records, methods):
    acoustic = [r for r in records if not r['electrical_not_acoustic']]
    tonal = [r for r in acoustic if r['reference_tones_hz']]
    out = {}
    for m in methods:
        tone = {ms:[_score(r, m, ms, 'tone_band_gain_db') for r in tonal] for ms in HORIZONS_MS}
        band = {ms:[_score(r, m, ms, 'band_gain_db') for r in acoustic] for ms in HORIZONS_MS}
        out[m] = {
            'tone_files':len(tonal), 'acoustic_files':len(acoustic),
            'median_tone_bin_db':{f'{ms:g}':float(np.median(v)) if v else None for ms, v in tone.items()},
            'median_tone_bin_both_horizons_db':float(np.median(np.mean([tone[ms] for ms in HORIZONS_MS], axis=0))) if tonal else None,
            'median_whole_band_db':{f'{ms:g}':float(np.median(v)) for ms, v in band.items()},
            'median_whole_band_both_horizons_db':float(np.median(np.mean([band[ms] for ms in HORIZONS_MS], axis=0))),
            'whole_band_boosts':[{'file':r['file'], 'horizon_start_ms':ms, 'band_gain_db':_score(r, m, ms, 'band_gain_db')}
                                 for r in records for ms in HORIZONS_MS if _score(r, m, ms, 'band_gain_db') < -.5],
            'third_octave_boosts':[{'file':r['file'], 'horizon_start_ms':ms,
                                    'bands_over_1db':_score(r, m, ms, 'third_octave_boosts_over_1db'),
                                    'max_change_db':_score(r, m, ms, 'max_third_octave_change_db')}
                                   for r in records for ms in HORIZONS_MS
                                   if _score(r, m, ms, 'third_octave_boosts_over_1db') > 0]}
    return out


def scene_summary(scenes, methods):
    out = {}
    for m in methods:
        late = [s for sc in scenes for s in sc['late_window_scores'] if s['method'] == m]
        objs = [sc['objective'][m] for sc in scenes if m in sc['objective']]
        tone = [s['tone_band_gain_db'] for s in late if s['tone_band_gain_db'] is not None]
        out[m] = {'mean_objective_db':float(np.mean([o['objective_db'] for o in objs])) if objs else None,
                  'windows_below_minus_half_db':int(sum(o['windows_below_minus_half_db'] for o in objs)) if objs else None,
                  'late_mean_whole_band_db':float(np.mean([s['band_gain_db'] for s in late])),
                  'late_min_whole_band_db':float(np.min([s['band_gain_db'] for s in late])),
                  'late_whole_band_below_minus_half_db':int(sum(s['band_gain_db'] < -.5 for s in late)),
                  'late_median_tone_bin_db':float(np.median(tone)) if tone else None,
                  'late_third_octave_boosts':int(sum(s['third_octave_boosts_over_1db'] > 0 for s in late))}
    by_family = {}
    for fam in sorted({sc['family'] for sc in scenes}):
        sub = [sc for sc in scenes if sc['family'] == fam]
        by_family[fam] = {m:{'mean_objective_db':float(np.mean([sc['objective'][m]['objective_db'] for sc in sub]))
                             if all(m in sc['objective'] for sc in sub) else None,
                             'late_mean_whole_band_db':float(np.mean([s['band_gain_db'] for sc in sub
                                                                       for s in sc['late_window_scores'] if s['method'] == m]))}
                          for m in methods}
    return out, by_family


def method_names(methods):
    names = ['zero']
    for m in methods:
        names += [m['name']+'_ungated', m['name']+'_gated'] if m['kind'] in ('v2', 'bank') else [m['name']]
    return names


def apply_development_rule(rec, syn, records, scenes, candidates):
    timing = {}
    for c in candidates:
        if c['kind'] == 'bank':
            timing[c['name']] = max(r['methods'][c['name']]['own_block_ms_p99'] for r in records+scenes)
        else:
            # v2-style refit per origin: its mean per-origin cost (no per-block spread is recorded).
            timing[c['name']] = max(r['methods'][c['name']]['forecast_ms_per_origin'] for r in records+scenes)
    base, base_syn = rec['v2_gated'], syn['v2_gated']
    table = []
    for c in candidates:
        m = c['name']+'_gated'
        r, s = rec[m], syn[m]
        checks = {'a_whole_band_boosts':len(r['whole_band_boosts']) <= len(base['whole_band_boosts']),
                  'b_third_octave_boosts':len(r['third_octave_boosts']) <= len(base['third_octave_boosts']),
                  'c_whole_band':r['median_whole_band_both_horizons_db'] >= base['median_whole_band_both_horizons_db']-.1,
                  'd_synthetic':(s['mean_objective_db'] >= base_syn['mean_objective_db']-.5 and
                                 s['windows_below_minus_half_db'] <= base_syn['windows_below_minus_half_db']),
                  'e_time':timing[c['name']] < 5.}
        table.append({'candidate':c['name'], 'tone_bin_median_db':r['median_tone_bin_both_horizons_db'],
                      'whole_band_median_db':r['median_whole_band_both_horizons_db'],
                      'synthetic_objective_db':s['mean_objective_db'], 'p99_block_ms':timing[c['name']],
                      'checks':checks, 'eligible':all(checks.values())})
    eligible = [t for t in table if t['eligible']]
    pick = max(eligible, key=lambda t: t['tone_bin_median_db'])['candidate'] if eligible else None
    return pick, table

# ---------- stages ----------

def _code_hashes():
    here = Path(__file__).parent
    return {name:hashlib.sha256((here/name).read_bytes()).hexdigest() for name in FROZEN_CODE}


def _fresh(output):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output folder must be new or empty; earlier results are preserved.')
    output.mkdir(parents=True, exist_ok=True)
    return output


def development_scenes():
    """Release-study development scenes (36) plus wandering-tone development scenes (2 draws x 4)."""
    draws, standard = make_dev_scenes()
    rng = np.random.default_rng(61)
    forbidden = frequency_extent(TEST_GROUPS)+[f for g in HELD_OUT.values() for f in g]
    wander = [draw_wander(rng, 0, forbidden) for _ in range(2)]
    tasks = [(name, 'standard', spec, 'release-study development seed', x) for name, (spec, x) in standard.items()]
    for rep, g in enumerate(wander):
        for i, (name, spec) in enumerate(wander_scene_set(g).items()):
            tasks.append((f'{name}#dev{rep}', 'wander', spec, 6100+100*rep+i, None))
    return draws, wander, tasks


def run_development(output, candidates=DEV_CANDIDATES, workers=WORKERS, note=None):
    """Development only: development recordings and development synthetic scenes.
    `note` records what changed since an earlier development run."""
    output = _fresh(output)
    split = load_split()
    v2 = json.loads(RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
    methods = COMPARATORS+list(candidates)
    started = time.perf_counter()
    paths = [checked_path(e) for e in split['development_files']]
    test_names = {e['file'] for e in split['test_files']}
    if any(p.name in test_names for p in paths):
        raise ValueError('A test recording reached development.')
    draws, wander, scene_tasks = development_scenes()
    with ProcessPoolExecutor(workers) as pool:
        rec_jobs = [pool.submit(_recording_task, (str(p), methods, v2)) for p in paths]
        scene_jobs = [pool.submit(_scene_task, (*t, methods, v2)) for t in scene_tasks]
        records = [j.result() for j in rec_jobs]
        scenes = [j.result() for j in scene_jobs]
    names = method_names(methods)
    rec, syn = recording_summary(records, names), scene_summary(scenes, names)
    pick, table = apply_development_rule(rec, syn[0], records, scenes, candidates)
    result = {'kind':'tone_forecaster_development', 'created_utc':datetime.now(timezone.utc).isoformat(),
              'stage':'development only; no test recording or test scene was read', 'note':note, 'v2':v2,
              'candidates':list(candidates), 'comparators':COMPARATORS, 'rule':DEVELOPMENT_RULE,
              'development_files':[p.name for p in paths], 'release_development_draws':draws,
              'wander_development_draws':wander, 'recordings':records, 'scenes':scenes,
              'summary':{'recordings':rec, 'synthetic':syn[0], 'synthetic_by_family':syn[1]},
              'rule_table':table, 'development_pick':pick, 'runtime_seconds':time.perf_counter()-started,
              'code_sha256':_code_hashes(),
              'labels':'Reference-signal prediction only. Not acoustic attenuation.'}
    (output/'development.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    from .forecaster_report import write_development_summary
    write_development_summary(output, result)
    return result


def freeze_protocol(development_folder, output=STUDY/'protocol.json'):
    """Write the frozen protocol from a development run. Refuses to overwrite."""
    output = Path(output)
    if output.exists():
        raise ValueError('protocol.json already exists; the protocol is frozen once.')
    dev = json.loads((Path(development_folder)/'development.json').read_text(encoding='utf-8'))
    if dev['code_sha256'] != _code_hashes():
        raise ValueError('Code changed after the development run; rerun development before freezing.')
    split = load_split()
    pick = dev['development_pick']
    chosen = next((c for c in dev['candidates'] if c['name'] == pick), None)
    # Secondary: the same forecaster without the line finder shows how much of any gain comes from the extra lines.
    ablations = [c for c in dev['candidates'] if chosen and chosen.get('lines') and c['kind'] == chosen['kind']
                 and c.get('nb_tau') == chosen.get('nb_tau') and not c.get('lines')]
    release = json.loads(RELEASE_PROTOCOL.read_text(encoding='utf-8'))
    forbidden = ([f for g in release['development_draws']+release['test_draws'] for f in frequency_extent(g)]
                 + [f for g in dev['wander_development_draws'] for fs in g.values() for f in fs]
                 + frequency_extent(TEST_GROUPS)+[f for g in DEVELOPMENT for f in g]+[f for g in HELD_OUT.values() for f in g])
    protocol = {'kind':'tone_forecaster_frozen_protocol', 'created_utc':datetime.now(timezone.utc).isoformat(),
                'development_run':str(Path(development_folder).relative_to(ROOT)), 'rule':dev['rule'],
                'rule_table':dev['rule_table'], 'frozen_candidate':chosen,
                'frozen_candidate_note':None if chosen else 'No candidate met the rule; v2 stays and the test reports comparators only.',
                'comparators':dev['comparators'], 'ablations':ablations,
                'ablation_note':'Secondary, not part of the primary question: the frozen candidate without its line finder.',
                'v2':dev['v2'],
                'test_files':split['test_files'], 'independence':split['independence'],
                'synthetic_test':{'standard_seed':20261018, 'standard_repeats':3, 'standard_scene_seeds':'8100+100*repeat+scene index',
                                  'wander_seed':20261019, 'wander_repeats':3, 'wander_scene_seeds':'9100+100*repeat+scene index',
                                  'parity':'odd 10 Hz bands (development used even)', 'forbidden_within_hz':2.,
                                  'forbidden_frequencies':sorted(set(round(f, 2) for f in forbidden))},
                'primary_question':('On the test recordings that have reference tones, does the frozen candidate (gated) '
                                    'raise the median tone-bin gain at 20 ms above v2 + gate, toward the prefix-adapted AR, '
                                    'without more whole-band or third-octave boosts than v2 + gate?'),
                'code_sha256':_code_hashes()}
    output.write_text(json.dumps(protocol, indent=2), encoding='utf-8')
    return protocol


def test_scene_tasks(protocol):
    syn = protocol['synthetic_test']
    forbidden = syn['forbidden_frequencies']
    rng = np.random.default_rng(syn['standard_seed'])
    standard = [draw_groups(rng, 1, forbidden) for _ in range(syn['standard_repeats'])]
    rng = np.random.default_rng(syn['wander_seed'])
    wander = [draw_wander(rng, 1, forbidden) for _ in range(syn['wander_repeats'])]
    for g in standard:
        if any(abs(a-b) <= 2 for a in frequency_extent(g) for b in forbidden):
            raise ValueError('Test draw is not fresh.')
    tasks = []
    for rep, g in enumerate(standard):
        tasks += [(f'{n}#test{rep}', 'standard', s, 8100+100*rep+i, None) for i, (n, s) in enumerate(scene_set(g).items())]
    for rep, g in enumerate(wander):
        tasks += [(f'{n}#test{rep}', 'wander', s, 9100+100*rep+i, None) for i, (n, s) in enumerate(wander_scene_set(g).items())]
    return standard, wander, tasks


def run_test(output=STUDY/'test', protocol_path=STUDY/'protocol.json', workers=WORKERS):
    """Runs once on the test recordings and fresh synthetic test scenes."""
    output = Path(output)
    if output.exists():
        raise ValueError('The test stage has already run (its folder exists); it runs once.')
    protocol = json.loads(Path(protocol_path).read_text(encoding='utf-8'))
    if protocol['code_sha256'] != _code_hashes():
        raise ValueError('Code changed after the protocol was frozen.')
    split = load_split()
    if [e['file'] for e in split['test_files']] != [e['file'] for e in protocol['test_files']]:
        raise ValueError('Test files differ from the protocol.')
    paths = [checked_path(e) for e in protocol['test_files']]
    v2 = protocol['v2']
    methods = (protocol['comparators']+protocol['ablations']
               +([protocol['frozen_candidate']] if protocol['frozen_candidate'] else []))
    output.mkdir(parents=True)
    started = time.perf_counter()
    standard, wander, tasks = test_scene_tasks(protocol)
    with ProcessPoolExecutor(workers) as pool:
        rec_jobs = [pool.submit(_recording_task, (str(p), methods, v2)) for p in paths]
        scene_jobs = [pool.submit(_scene_task, (*t, methods, v2)) for t in tasks]
        records = [j.result() for j in rec_jobs]
        scenes = [j.result() for j in scene_jobs]
    names = method_names(methods)
    syn = scene_summary(scenes, names)
    result = {'kind':'tone_forecaster_test', 'created_utc':datetime.now(timezone.utc).isoformat(),
              'protocol':protocol, 'test_files':[p.name for p in paths], 'synthetic_standard_draws':standard,
              'synthetic_wander_draws':wander, 'recordings':records, 'scenes':scenes,
              'summary':{'recordings':recording_summary(records, names), 'synthetic':syn[0], 'synthetic_by_family':syn[1]},
              'runtime_seconds':time.perf_counter()-started,
              'labels':'Reference-signal prediction only. Not acoustic attenuation.'}
    (output/'test.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    return result
