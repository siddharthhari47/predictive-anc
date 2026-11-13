"""Frozen offline timing of the s30 phase-locked smoother in a streaming engine loop. Never opens audio devices.

engine_smoothing.smooth_arrays works on a finished log. The live engine would
need the same arithmetic one origin at a time, so PhasorSmoother is that step.
It wraps the unchanged AntiHumEngine: engine.components stay raw, so the
realized-error gate is untouched, and only the phasors handed to the renderer
are smoothed. Output must match smooth_arrays before any time is believed.
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import cmath
import json
import platform
import time

import numpy as np
import psutil
from threadpoolctl import threadpool_info, threadpool_limits

from . import selector_headroom as h
from . import tuning_fresh_02  # noqa: F401  (applies the second study's paths and seed)
from . import tuning_fresh as tf
from . import engine_smoothing as es
from .antihum import AntiHumEngine, BLOCK, FS, ToneSetting, log_arrays, synthesize
from .selector_stream_profile import cached_dpss

ROOT = h.ROOT
STUDY = ROOT/'results-smoother-timing-01'
ALPHA = es.ALPHAS['s30']
INPUT_SECONDS = 30
REPETITIONS = 2
VARIANTS = ('live', 'cached_dpss')
OUTPUT_FS, OUTPUT_SAMPLES, LEAD = 48000, 480, .03
SMOOTHER_P99_MS, PATH_P99_MS, BLOCK_MS = .5, 5., BLOCK/FS*1e3
QUIET_PERCENT = 5.
FILES = ['anc_lab/smoother_timing.py', 'tests/test_smoother_timing.py', 'docs/SMOOTHER_TIMING.md', 'anc_lab/engine_smoothing.py',
         'anc_lab/antihum.py', 'anc_lab/tuning_fresh.py', 'anc_lab/tuning_fresh_02.py', 'anc_lab/selector_stream_profile.py']


class PhasorSmoother:
    """One-origin-at-a-time equivalent of engine_smoothing.smooth_arrays."""
    def __init__(self, alpha=ALPHA, block=BLOCK, fs=FS, associate_hz=es.ASSOCIATE_HZ, max_gap=es.MAX_GAP):
        self.alpha, self.associate_hz, self.max_gap = alpha, associate_hz, max_gap
        self.turn = 2j*cmath.pi*block/fs
        self.states = []              # [frequency, smoothed phasor, origin number]
        self.origin = 0
        self.previous_gate = True     # no earlier origin: nothing to clear

    def step(self, components, gate_open):
        """Smoothed [(frequency, phasor)] for this origin; call once per origin, in order."""
        k, alpha = self.origin, self.alpha
        states = [] if not self.previous_gate else [s for s in self.states if k-s[2] <= self.max_gap]
        out, new = [], []
        for frequency, phasor in components:
            if phasor == 0:
                out.append((frequency, phasor))
                continue
            match = None
            if states:
                i = min(range(len(states)), key=lambda n: abs(states[n][0]-frequency))
                if abs(states[i][0]-frequency) <= self.associate_hz:
                    match = states.pop(i)
            smoothed = phasor
            if match is not None:
                smoothed = alpha*phasor+(1-alpha)*match[1]*cmath.exp(self.turn*match[0]*(k-match[2]))
            out.append((frequency, smoothed))
            new.append([frequency, smoothed, k])
        self.states = states+new
        self.previous_gate = bool(gate_open)
        self.origin = k+1
        return out


def rooms():
    """First eligible room of every eligible source in the second fresh test."""
    first = {}
    for c in h.read(tf.STUDY/'rooms.json')['eligible_cases']:
        first.setdefault(c['source_id'], c)
    return [first[s] for s in sorted(first)]


def stat(x):
    x = np.asarray(x, float)
    return {'count': len(x), 'mean': float(x.mean()), 'p50': float(np.percentile(x, 50)), 'p95': float(np.percentile(x, 95)),
            'p99': float(np.percentile(x, 99)), 'max': float(x.max()), 'over_5ms': int(np.sum(x > 5)), 'over_10ms': int(np.sum(x > 10))}


def backlog_ms(wall):
    """Largest queue behind real time if one block arrives every 10 ms and the worker does nothing else."""
    lag = peak = 0.
    for w in wall:
        lag = max(0., lag+w-BLOCK_MS)
        peak = max(peak, lag)
    return peak


def run_stream(mic, cache):
    """The timed loop. Returns times per origin and every output, collected outside the timed sections."""
    n = len(mic)//BLOCK
    times = np.zeros((n, 3))
    engine, smoother = AntiHumEngine(), PhasorSmoother()
    raw, smooth, gate = [], [], []
    clock = time.perf_counter
    with cached_dpss(cache):
        for row in range(n):
            chunk = mic[row*BLOCK:(row+1)*BLOCK]
            t0 = clock()
            engine.push(chunk)
            t1 = clock()
            components = smoother.step(engine.components, engine.gate_open)
            t2 = clock()
            synthesize(components, lambda f: ToneSetting(f, gain=.1), engine.origin_seen/FS, OUTPUT_SAMPLES, OUTPUT_FS, LEAD)
            t3 = clock()
            times[row] = t1-t0, t2-t1, t3-t2
            raw.append((engine.origin_seen, list(engine.components), engine.gate_open))
            smooth.append((engine.origin_seen, components, engine.gate_open))
    return times*1e3, log_arrays(raw), log_arrays(smooth)


def same(a, b):
    k = min(a['frequency'].shape[1], b['frequency'].shape[1])
    assert a['frequency'].shape[1] == b['frequency'].shape[1], 'tone columns differ'
    np.testing.assert_array_equal(a['seen'], b['seen'])
    np.testing.assert_array_equal(a['gate'], b['gate'])
    np.testing.assert_allclose(a['frequency'][:, :k], b['frequency'][:, :k], rtol=1e-8, atol=1e-9, equal_nan=True)
    np.testing.assert_allclose(a['phasor'][:, :k], b['phasor'][:, :k], rtol=1e-8, atol=1e-9)


# ---------------- protocol ----------------
def freeze():
    assert not STUDY.exists(), 'Never overwrite a timing run'
    chosen = rooms()
    protocol = {
        'created_utc': datetime.now(timezone.utc).isoformat(), 'kind': 'offline_streaming_smoother_timing',
        'question': 'Does the s30 smoother fit the engine worker loop, and does the whole loop fit its block?',
        'inputs': f'Simulated room microphone, first {INPUT_SECONDS} s, first eligible room of each of the 14 eligible sources of results-tuning-fresh-02. Seen recordings, no new media.',
        'cases': chosen, 'alpha': ALPHA,
        'variants': {'live': 'Detector as the app runs it today, tapers recomputed.', 'cached_dpss': 'Same output, tapers cached in a scoped research cache.'},
        'schedule': f'{REPETITIONS} serial repetitions, declared order then reverse; variant order alternates. One logical processor, numerical threads limited to one.',
        'parity': 'engine_smoothing.smooth_arrays applied to the engine log is the reference. Raw and smoothed outputs must match on every room and variant first (rtol 1e-8, atol 1e-9, exact gate), and again after each timed run.',
        'timed': {'engine_push': 'AntiHumEngine.push for one 10 ms block', 'smoother_step': 'PhasorSmoother.step', 'path': 'push plus smoother, per block',
                  'synthesis': f'synthesize for {OUTPUT_SAMPLES} samples at {OUTPUT_FS} Hz, gain on every tone. Descriptive, it belongs to the output callback.'},
        'not_timed': 'Decimation, locks, the window, audio callbacks, device transport and any acoustic path.',
        'quiet': {'preflight_attempts': 3, 'seconds_per_attempt': 10, 'maximum_system_cpu_percent': QUIET_PERCENT, 'during_max_background_percent': QUIET_PERCENT,
                  'processor': 'least busy permitted logical CPU in the last window, ties by index', 'do_not_stop_other_work': True},
        'decision': {'smoother': f'Pass if smoother_step p99 < {SMOOTHER_P99_MS} ms in every run. Contention only slows it, so a pass under load stands; a miss under load is inconclusive.',
                     'path': f'Pass or fail on path p99 < {PATH_P99_MS} ms in every run, only if every run is quiet; otherwise inconclusive, diagnostic only. Same bar as results-selector-timing-01.',
                     'variants': 'Decided separately for each variant. live is the one that describes the app today.',
                     'backlog': 'Largest queue behind real time is reported per run, not part of the rule. The app refuses to play forecasts older than 250 ms.'},
        'caveats': 'One machine, one schedule, CPython on Windows. Not a complete app schedule, no device was opened, and no physical ANC is claimed.',
        'code_sha256': {name: h.sha(ROOT/name) for name in FILES},
        'rooms_sha256': h.sha(tf.STUDY/'rooms.json'), 'fresh_protocol_sha256': h.sha(tf.STUDY/'protocol.json'),
    }
    STUDY.mkdir()
    h.write_new(STUDY/'protocol.json', protocol)
    h.write_new(STUDY/'frozen.json', {'sha256': h.sha(STUDY/'protocol.json')})
    print(json.dumps({'protocol_sha256': h.sha(STUDY/'protocol.json'), 'rooms': len(chosen)}), flush=True)


def verified():
    p = h.read(STUDY/'protocol.json')
    assert h.sha(STUDY/'protocol.json') == h.read(STUDY/'frozen.json')['sha256']
    for name, digest in p['code_sha256'].items():
        assert h.sha(ROOT/name) == digest, name
    assert h.sha(tf.STUDY/'rooms.json') == p['rooms_sha256']
    return p


# ---------------- parity ----------------
def parity_task(args):
    c, entry, download, decoder = args
    with threadpool_limits(limits=1):
        with cached_dpss(True):
            dry, _, _ = tf.dry_signal(entry, download, decoder)
            _, scene = tf.build_room(dry, c['seed'])
        mic = np.array(scene['mic'][:INPUT_SECONDS*FS])
        checks = {}
        for variant in VARIANTS:
            _, raw, smooth = run_stream(mic, variant == 'cached_dpss')
            rows = len(raw['seen'])
            stored = {k: v[:rows] for k, v in scene['arrays'].items()}
            width = max(raw['frequency'].shape[1], stored['frequency'].shape[1])
            pad = lambda a: {**a, 'frequency': np.pad(a['frequency'], ((0, 0), (0, width-a['frequency'].shape[1])), constant_values=np.nan),
                             'phasor': np.pad(a['phasor'], ((0, 0), (0, width-a['phasor'].shape[1])))}
            same(pad(raw), pad(stored))
            reference = es.smooth_arrays(pad(stored), ALPHA)
            same(pad(smooth), reference)
            checks[variant] = {'origins': rows, 'largest_phasor_difference': float(np.max(np.abs(pad(smooth)['phasor']-reference['phasor'])))}
    path = STUDY/'inputs'/(c['case_id']+'.npz')
    np.savez_compressed(path, mic=mic, frequency=raw['frequency'], phasor=raw['phasor'], smoothed=smooth['phasor'], gate=raw['gate'], seen=raw['seen'])
    result = {'case_id': c['case_id'], 'tone_origins': int(np.sum(~np.isnan(raw['frequency']).all(axis=1))), 'checks': checks, 'input_sha256': h.sha(path)}
    h.write_new(STUDY/'parity'/(c['case_id']+'.json'), result)
    return result


def parity():
    p = verified()
    (STUDY/'parity').mkdir(exist_ok=False)
    (STUDY/'inputs').mkdir(exist_ok=False)
    entries = {e['id']: e for e in tf.verified()['sources']}
    downloads = {d['id']: d for d in h.read(tf.STUDY/'download/manifest.json')['files']}
    decoder = h.read(tf.STUDY/'protocol.json')['decoder']['path']
    rows = []
    with ProcessPoolExecutor(7) as pool:
        for job in as_completed([pool.submit(parity_task, (c, entries[c['source_id']], downloads[c['source_id']], decoder)) for c in p['cases']]):
            rows.append(job.result())
            print(json.dumps({'parity': rows[-1]['case_id'], 'complete': len(rows), 'of': len(p['cases'])}), flush=True)
    h.write_new(STUDY/'parity/complete.json', {'passed': True, 'rooms': len(rows), 'variants': len(VARIANTS),
                                               'largest_phasor_difference': max(c['largest_phasor_difference'] for r in rows for c in r['checks'].values()),
                                               'completed_utc': datetime.now(timezone.utc).isoformat()})


# ---------------- benchmark ----------------
def busy_seconds(cpu):
    return sum(cpu)-getattr(cpu, 'idle', 0)-getattr(cpu, 'iowait', 0)


def decide(subset):
    quiet = all(r['quiet_qualified'] for r in subset)
    step, path = [all(r[k]['p99'] < bar for r in subset) for k, bar in (('smoother_step_ms', SMOOTHER_P99_MS), ('path_ms', PATH_P99_MS))]
    return {'runs': len(subset), 'all_quiet': quiet,
            'smoother': 'pass' if step else 'fail' if quiet else 'inconclusive_contended',
            'path': ('pass' if path else 'fail') if quiet else 'inconclusive_contended',
            'worst_smoother_p99_ms': max(r['smoother_step_ms']['p99'] for r in subset), 'worst_smoother_max_ms': max(r['smoother_step_ms']['max'] for r in subset),
            'worst_path_p99_ms': max(r['path_ms']['p99'] for r in subset), 'median_path_p99_ms': float(np.median([r['path_ms']['p99'] for r in subset])),
            'worst_block_ms': max(r['path_ms']['max'] for r in subset), 'blocks': sum(r['path_ms']['count'] for r in subset),
            'over_5ms_blocks': sum(r['path_ms']['over_5ms'] for r in subset), 'over_10ms_blocks': sum(r['path_ms']['over_10ms'] for r in subset),
            'worst_backlog_ms': max(r['backlog_ms'] for r in subset)}


def benchmark():
    p = verified()
    assert h.read(STUDY/'parity/complete.json')['passed']
    stage = STUDY/'timing'
    stage.mkdir(exist_ok=False)
    proc = psutil.Process()
    affinity, windows, quiet = proc.cpu_affinity(), [], False
    for attempt in range(p['quiet']['preflight_attempts']):
        samples = [psutil.cpu_percent(interval=1, percpu=True) for _ in range(p['quiet']['seconds_per_attempt'])]
        means = np.mean(samples, axis=0)
        system = float(means.mean())
        quiet = system <= QUIET_PERCENT
        windows.append({'attempt': attempt+1, 'system_mean_percent': system, 'qualifies': quiet})
        print('Quiet preflight', attempt+1, round(system, 2), 'percent', quiet, flush=True)
        if quiet:
            break
    cpu = min(affinity, key=lambda i: (means[i], i))
    environment = {'platform': platform.platform(), 'python': platform.python_version(), 'logical_cpus': psutil.cpu_count(), 'physical_cores': psutil.cpu_count(logical=False),
                   'selected_logical_cpu': cpu, 'quiet_preflight': quiet, 'preflight_windows': windows, 'threadpools': threadpool_info(),
                   'started_utc': datetime.now(timezone.utc).isoformat(), 'protocol_sha256': h.sha(STUDY/'protocol.json')}
    h.write_new(stage/'environment.json', environment)
    rows = []
    try:
        proc.cpu_affinity([cpu])
        with threadpool_limits(limits=1):
            for repetition in range(REPETITIONS):
                cases = p['cases'] if repetition == 0 else list(reversed(p['cases']))
                for i, c in enumerate(cases):
                    with np.load(STUDY/'inputs'/(c['case_id']+'.npz')) as a:
                        stored = {k: a[k].copy() for k in a.files}
                    assert h.sha(STUDY/'inputs'/(c['case_id']+'.npz')) == h.read(STUDY/'parity'/(c['case_id']+'.json'))['input_sha256']
                    order = VARIANTS if (i+repetition) % 2 == 0 else VARIANTS[::-1]
                    for variant in order:
                        before, own, start = psutil.cpu_times(), proc.cpu_times(), time.perf_counter()
                        times, raw, smooth = run_stream(stored['mic'], variant == 'cached_dpss')
                        elapsed, after, own_after = time.perf_counter()-start, psutil.cpu_times(), proc.cpu_times()
                        own_seconds = own_after.user+own_after.system-own.user-own.system
                        background = max(0., (busy_seconds(after)-busy_seconds(before)-own_seconds)/(elapsed*psutil.cpu_count())*100)
                        np.testing.assert_allclose(raw['phasor'], stored['phasor'], rtol=1e-8, atol=1e-9)
                        np.testing.assert_allclose(smooth['phasor'], stored['smoothed'], rtol=1e-8, atol=1e-9)
                        name = f"{c['case_id']}-r{repetition+1}-{variant}"
                        np.savez_compressed(stage/(name+'.npz'), times_ms=times)
                        path = times[:, 0]+times[:, 1]
                        row = {'case_id': c['case_id'], 'variant': variant, 'repetition': repetition+1, 'engine_push_ms': stat(times[:, 0]), 'smoother_step_ms': stat(times[:, 1]),
                               'path_ms': stat(path), 'synthesis_ms': stat(times[:, 2]), 'backlog_ms': backlog_ms(path), 'elapsed_seconds': elapsed,
                               'estimated_background_cpu_percent': background, 'quiet_qualified': bool(quiet and background <= QUIET_PERCENT), 'parity_passed': True}
                        h.write_new(stage/(name+'.json'), row)
                        rows.append(row)
                        print(json.dumps({'completed': len(rows), 'of': len(p['cases'])*REPETITIONS*len(VARIANTS), 'case': c['case_id'], 'variant': variant,
                                          'path_p99': round(row['path_ms']['p99'], 3), 'smoother_p99': round(row['smoother_step_ms']['p99'], 5), 'background': round(background, 1)}), flush=True)
    finally:
        proc.cpu_affinity(affinity)
    summary = {v: decide([r for r in rows if r['variant'] == v]) for v in VARIANTS}
    summary['synthesis_p99_ms_worst'] = max(r['synthesis_ms']['p99'] for r in rows)
    h.write_new(stage/'results.json', {'environment': environment, 'runs': rows, 'summary': summary, 'completed_utc': datetime.now(timezone.utc).isoformat()})
    h.write_new(STUDY/'SUMMARY.json', summary)
    print(json.dumps(summary, indent=1), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['freeze', 'parity', 'benchmark'])
    {'freeze': freeze, 'parity': parity, 'benchmark': benchmark}[parser.parse_args().stage]()
