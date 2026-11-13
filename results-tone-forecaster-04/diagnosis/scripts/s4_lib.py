"""Study 04 diagnosis helpers: run each forecaster once per recording or scene, then apply several gates to the same
ungated forecast and score each. Development material only. Imported by the s4_* trial scripts, which put the project
path on sys.path first."""
import json
import time
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

from anc_lab import forecaster_study as s1
from anc_lab import forecaster_study_02 as fs2
from anc_lab import forecaster_study_03 as fs3
from anc_lab.generalization import normalized_prefix
from anc_lab.real_hum_study import ELECTRICAL, PREFIX_FRACTION, load_any, prominent_tones
from anc_lab.release_study import objective
from anc_lab.selection_study import BLOCK, FS, SECONDS, TRAIN_END, VAL_END, horizon_setup, synthesize_scene
from anc_lab.tone_gate_fade import GatedCheckBank, fade_gate_output
from anc_lab.tone_forecasters import stream_forecasts
from anc_lab.tone_selection import SelectedToneForecaster, ToneSelector

fs2.BANK_KINDS.setdefault('gated_check', GatedCheckBank)
V2 = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']


def shadow_of(method, x, grid):
    _, horizons, _ = horizon_setup()
    if method['kind'] == 'v2':
        fc = SelectedToneForecaster(FS, ToneSelector(FS, **V2['selector']), window_seconds=method['window_seconds'],
                                    release_ratio=V2['forecaster']['release_ratio'],
                                    release_window_seconds=V2['forecaster']['release_window_seconds'])
        return fc.predict(x, grid, horizons), {}
    bank = fs2.make_bank(method, V2)
    shadow = stream_forecasts(bank, x, grid, horizons)
    own = 1e3*bank.block_seconds_own
    return shadow, {'own_block_ms_p99':float(np.percentile(own, 99)), 'counters':bank.counters}


def transitions(enabled):
    e = np.asarray(enabled, bool)[:, 0]
    return int(np.sum(e[1:] != e[:-1]))


def run_all(x, grid, methods, gates):
    """preds[f'{method}|{gate}'] over the whole grid, plus info."""
    _, _, groups = horizon_setup()
    preds, info = {'zero':np.zeros((len(grid), len(horizon_setup()[1])))}, {}
    for m in methods:
        shadow, extra = shadow_of(m, x, grid)
        preds[m['name']+'|none'] = shadow
        for gname, fade in gates.items():
            if gname == 'none':
                continue
            out, gains, enabled = fade_gate_output(x, grid, shadow, groups, V2['gate'], fade)
            preds[f"{m['name']}|{gname}"] = out
            extra[f'transitions|{gname}'] = transitions(enabled)
            extra[f'open|{gname}'] = float(np.mean(gains[:, 0]))
        info[m['name']] = extra
    return preds, info


def recording_task(args):
    path, methods, gates = args
    path = Path(path)
    with threadpool_limits(limits=1):
        audio, _ = load_any(path)
        prefix = int(PREFIX_FRACTION*len(audio))
        x = (audio-float(np.mean(audio[:prefix])))/max(float(np.std(audio[:prefix])), 1e-12)
        _, horizons, _ = horizon_setup()
        grid = np.arange(BLOCK*50, len(x)-int(max(horizons)), BLOCK)
        keep = grid >= prefix
        preds, info = run_all(x, grid, methods, gates)
        tones = prominent_tones(x[prefix:])
        return {'file':path.name, 'electrical_not_acoustic':path.name in ELECTRICAL, 'reference_tones_hz':tones,
                'methods':info, 'scores':s1.score_forecasts(x, grid[keep], {k:p[keep] for k, p in preds.items()}, tones)}


def scene_task(args):
    name, family, spec, seed, x, methods, gates = args
    with threadpool_limits(limits=1):
        if x is None:
            raw = synthesize_scene(spec, seed) if family == 'standard' else s1.synthesize_wander(spec, seed)
            x, _ = normalized_prefix(raw, TRAIN_END)
        _, horizons, groups = horizon_setup()
        grid = np.arange(BLOCK*50, SECONDS*FS-int(max(horizons)), BLOCK)
        preds, info = run_all(x, grid, methods, gates)
        late = grid >= VAL_END
        steady = [tn['freq'] for tn in spec['tones'] if not tn['drift_hz_per_s'] and tn['start'] == 0 and tn['stop'] >= SECONDS]
        rows = s1.score_forecasts(x, grid[late], {m:p[late] for m, p in preds.items()}, steady)
        objectives = {m:objective(x, spec, grid, p, groups)[0] for m, p in preds.items() if m != 'zero'}
        return {'scene':name, 'family':family, 'methods':info, 'late_window_scores':rows, 'objective':objectives}


def development_tasks(include=('standard', 'wander', 'buzz')):
    _, _, scene_tasks = s1.development_scenes()
    _, buzz_tasks = fs3.buzz_scenes()
    tasks = [t for t in scene_tasks if t[1] in include]
    return tasks+(buzz_tasks if 'buzz' in include else [])


def development_paths():
    split = s1.load_split()
    return [s1.checked_path(e) for e in split['development_files']]


def summarize(records, scenes):
    """Per prediction key: recording boosts / near-boosts / tone & band medians; synthetic late boosts / objective."""
    keys = sorted({s['method'] for r in records+scenes for s in (r.get('scores') or r.get('late_window_scores'))})
    out = {}
    for k in keys:
        row = {}
        if records:
            rs = [(r, s) for r in records for s in r['scores'] if s['method'] == k]
            acoustic = [r for r in records if not r['electrical_not_acoustic']]
            tonal = [r for r in acoustic if r['reference_tones_hz']]
            tone = [np.mean([s['tone_band_gain_db'] for s in r['scores'] if s['method'] == k]) for r in tonal]
            band = [np.mean([s['band_gain_db'] for s in r['scores'] if s['method'] == k]) for r in acoustic]
            row.update(rec_boosts=[(r['file'][:18], s['horizon_start_ms'], round(s['max_third_octave_change_db'], 2))
                                   for r, s in rs if s['max_third_octave_change_db'] >= 1.],
                       rec_near=int(sum(s['max_third_octave_change_db'] >= .5 for _, s in rs)),
                       rec_whole_band_boosts=int(sum(s['band_gain_db'] < -.5 for _, s in rs)),
                       tone_median=float(np.median(tone)) if tone else None, band_median=float(np.median(band)))
        if scenes:
            late = [(sc['scene'], s) for sc in scenes for s in sc['late_window_scores'] if s['method'] == k]
            objs = [sc['objective'][k] for sc in scenes if k in sc['objective']]
            row.update(syn_boosts=[(n.split('#')[0], s['horizon_start_ms'], round(s['max_third_octave_change_db'], 2))
                                   for n, s in late if s['max_third_octave_change_db'] >= 1.],
                       syn_near=int(sum(s['max_third_octave_change_db'] >= .5 for _, s in late)),
                       objective=float(np.mean(objs)) if objs else None)
        out[k] = row
    return out


def print_summary(summary, verbose=True):
    for k, r in summary.items():
        parts = [f'{k:28s}']
        if 'rec_boosts' in r:
            parts.append(f"rec {len(r['rec_boosts']):2d}/{r['rec_near']:2d} wb {r['rec_whole_band_boosts']} "
                         f"tone {r['tone_median'] if r['tone_median'] is None else round(r['tone_median'], 2)} "
                         f"band {r['band_median']:.2f}")
        if 'syn_boosts' in r:
            parts.append(f"syn {len(r['syn_boosts']):2d}/{r['syn_near']:2d} obj {r['objective'] if r['objective'] is None else round(r['objective'], 2)}")
        print('  '.join(parts))
        if verbose:
            bl = r.get('rec_boosts', [])+r.get('syn_boosts', [])
            if bl:
                print('      ', bl)


def save(path, payload):
    Path(path).write_text(json.dumps(payload, allow_nan=False), encoding='utf-8')


def timer():
    started = time.perf_counter()
    return lambda: time.perf_counter()-started


def scene_task_windows(args):
    """As scene_task, also keeping each key's synthetic windows below -0.5 dB (added for trial 3)."""
    name, family, spec, seed, x, methods, gates = args
    with threadpool_limits(limits=1):
        if x is None:
            raw = synthesize_scene(spec, seed) if family == 'standard' else s1.synthesize_wander(spec, seed)
            x, _ = normalized_prefix(raw, TRAIN_END)
        _, horizons, groups = horizon_setup()
        grid = np.arange(BLOCK*50, SECONDS*FS-int(max(horizons)), BLOCK)
        preds, info = run_all(x, grid, methods, gates)
        late = grid >= VAL_END
        steady = [tn['freq'] for tn in spec['tones'] if not tn['drift_hz_per_s'] and tn['start'] == 0 and tn['stop'] >= SECONDS]
        rows = s1.score_forecasts(x, grid[late], {m:p[late] for m, p in preds.items()}, steady)
        objectives, windows = {}, {}
        for m, p in preds.items():
            if m == 'zero':
                continue
            value, gains = objective(x, spec, grid, p, groups)
            objectives[m], windows[m] = value, int(sum(g < -.5 for g in gains))
        return {'scene':name, 'family':family, 'methods':info, 'late_window_scores':rows, 'objective':objectives,
                'windows_below_minus_half_db':windows}
