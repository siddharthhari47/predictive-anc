"""Frozen offline test of the s30 smoother and taper cache inside the app's LiveRunner. Never opens audio devices.

SmoothedEngine goes in through LiveRunner's existing `engine` argument, so
tune_app.py is unchanged. The live stage plays stored simulated microphones at
real-time pace through the real on_input, on_output and pump code on three
threads, as the audio callbacks and worker would. Output is discarded.
"""
from datetime import datetime, timezone
import argparse
import json
import platform
import threading
import time

import numpy as np
import psutil
from scipy import signal

from . import selector_headroom as h
from . import smoother_timing as st
from . import engine_smoothing as es
from .antihum import AntiHumEngine, BLOCK, StreamingDecimator, ToneSetting, log_arrays
from .selector_stream_profile import cached_dpss
from .tune_app import LiveRunner, RATE

ROOT = h.ROOT
SOURCE = ROOT/'results-smoother-timing-01'
STUDY = ROOT/'results-engine-candidate-01'
CHUNKS = (137, 480, 1024, 1920)
LIVE_CHUNK, OUTPUT_LATENCY, GAIN = 480, .05, .1
REPETITIONS = 2
ARMS = ('v2', 'candidate')
PATH_P99_MS, CALLBACK_P99_MS = 5., 5.
QUIET_PERCENT, MINIMUM_QUIET_RUNS = 5., 24
QUIET_WINDOWS, WINDOW_SECONDS, WAIT_LIMIT_SECONDS = 3, 10, 6*3600
FILES = ['anc_lab/engine_candidate.py', 'tests/test_engine_candidate.py', 'docs/ENGINE_CANDIDATE.md', 'anc_lab/smoother_timing.py',
         'anc_lab/engine_smoothing.py', 'anc_lab/antihum.py', 'anc_lab/tone_selection.py', 'anc_lab/selector_stream_profile.py', 'anc_lab/tune_app.py']


class _RawEngine(AntiHumEngine):
    def __init__(self, keep_log):
        super().__init__(keep_log=keep_log)
        self.smoother, self.smoothed = st.PhasorSmoother(), []
        self.smooth_log = [] if keep_log else None

    def _origin(self, end):
        super()._origin(end)
        self.smoothed = self.smoother.step(self.components, self.gate_open)
        if self.smooth_log is not None:
            self.smooth_log.append((self.origin_seen, self.smoothed, self.gate_open))


class SmoothedEngine:
    """AntiHumEngine for LiveRunner: the renderer's components are smoothed, everything else stays raw."""
    def __init__(self, keep_log=False):
        self.raw = _RawEngine(keep_log)

    def push(self, block):
        self.raw.push(block)

    def strongest(self, count=None):
        return self.raw.strongest(count)

    components = property(lambda self: self.raw.smoothed)
    origin_seen = property(lambda self: self.raw.origin_seen)
    gate_open = property(lambda self: self.raw.gate_open)
    counters = property(lambda self: self.raw.counters)


class TimedEngine:
    """Times each push; everything else passes through."""
    def __init__(self, engine, pushes):
        self.engine, self.times, self.count = engine, np.zeros(pushes), 0

    def push(self, block):
        start = time.perf_counter()
        self.engine.push(block)
        self.times[self.count] = time.perf_counter()-start
        self.count += 1

    def __getattr__(self, name):
        return getattr(self.engine, name)


def at_48k(mic):
    return signal.resample_poly(mic, RATE//st.FS, 1)


def run_offline(x, chunk, candidate):
    """Logs of the engine fed through the app's decimator, one chunk at a time."""
    engine = SmoothedEngine(True) if candidate else AntiHumEngine(keep_log=True)
    decimator = StreamingDecimator(RATE, st.FS)
    for k in range(0, len(x)-len(x) % chunk, chunk):
        y = decimator.process(x[k:k+chunk])
        if len(y):
            engine.push(y)
    return (log_arrays(engine.raw.log), log_arrays(engine.raw.smooth_log)) if candidate else (log_arrays(engine.log), None)


def rooms():
    p = h.read(SOURCE/'protocol.json')
    for c in p['cases']:
        path = SOURCE/'inputs'/(c['case_id']+'.npz')
        assert h.sha(path) == h.read(SOURCE/'parity'/(c['case_id']+'.json'))['input_sha256']
        with np.load(path) as a:
            yield c, at_48k(a['mic'].copy())


def tones_of(raw):
    return [float(f) for f in np.nanmedian(raw['frequency'], axis=0) if np.isfinite(f)][:3] if np.isfinite(raw['frequency']).any() else []


def session(x, tones, arm):
    """One paced run of the real runner. The three loops mirror the app's callbacks and worker."""
    n = len(x)//LIVE_CHUNK
    engine = TimedEngine(SmoothedEngine(True) if arm == 'candidate' else AntiHumEngine(keep_log=True), n+1)
    runner = LiveRunner(engine=engine)
    for f in tones:
        runner.set_tone('both', ToneSetting(f, GAIN))
    runner.limiter.start()
    times = {k: np.zeros(n) for k in ('input_ms', 'output_ms', 'input_late_ms', 'output_late_ms', 'queue_ms')}
    errors, closing, sounding = [], threading.Event(), [0]
    clock = time.perf_counter
    start = clock()+.2

    def wait(deadline):
        delay = deadline-clock()
        if delay > 0:
            time.sleep(delay)
        return (clock()-deadline)*1e3

    def guarded(job):
        def run():
            try:
                job()
            except Exception as exc:
                errors.append(repr(exc))
        return run

    def heard():
        for k in range(n):
            times['input_late_ms'][k] = wait(start+(k+1)*LIVE_CHUNK/RATE)
            t0 = clock()
            runner.on_input(x[k*LIVE_CHUNK:(k+1)*LIVE_CHUNK], start+k*LIVE_CHUNK/RATE)
            times['input_ms'][k] = (clock()-t0)*1e3

    def play():
        for k in range(n):
            deadline = start+k*LIVE_CHUNK/RATE
            times['output_late_ms'][k] = wait(deadline)
            t0 = clock()
            out = runner.on_output(LIVE_CHUNK, deadline+OUTPUT_LATENCY)
            times['output_ms'][k] = (clock()-t0)*1e3
            times['queue_ms'][k] = (runner.in_count-runner.processed)/RATE*1e3
            sounding[0] += bool(np.any(out))

    def work():
        while not closing.is_set():
            runner.waiting.wait(.05)
            runner.waiting.clear()
            runner.pump()

    worker = threading.Thread(target=guarded(work), daemon=True)
    drivers = [threading.Thread(target=guarded(job), daemon=True) for job in (heard, play)]
    worker.start()
    for t in drivers:
        t.start()
    for t in drivers:
        t.join()
    settle = clock()+2
    while runner.processed < runner.in_count and clock() < settle:
        time.sleep(.01)
    closing.set()
    runner.waiting.set()
    worker.join(2)
    times['push_ms'] = engine.times[:engine.count]*1e3
    state = runner.state()
    report = {'errors': errors, 'stale_blocks': state['stale_blocks'], 'stopped': bool(state['stopped']), 'glitches': state['glitches'],
              'forecast_lead_s': state['forecast_lead_s'], 'sounding_blocks': sounding[0], 'blocks': n, 'worker_alive': worker.is_alive()}
    inner = engine.engine.raw if arm == 'candidate' else engine.engine
    logs = (log_arrays(inner.log), log_arrays(inner.smooth_log) if arm == 'candidate' else None)
    return times, report, logs


# ---------------- protocol ----------------
def freeze():
    assert not STUDY.exists(), 'Never overwrite a run'
    cases = h.read(SOURCE/'protocol.json')['cases']
    protocol = {
        'created_utc': datetime.now(timezone.utc).isoformat(), 'kind': 'offline_paced_engine_candidate',
        'question': 'With the s30 smoother and taper cache in the real LiveRunner, is the output right and does everything keep time at real-time pace?',
        'inputs': 'The stored 30 s simulated microphones of results-smoother-timing-01, resampled to 48 kHz. Seen data. No new media and no audio device.',
        'cases': cases, 'alpha': st.ALPHA, 'chunks': CHUNKS,
        'arms': {'v2': 'AntiHumEngine, uncached, as the app runs today.', 'candidate': 'SmoothedEngine with cached_dpss around the run. Gate, tone list and raw components stay raw.'},
        'output_rule': 'At every chunk size, candidate raw log and gate equal plain AntiHumEngine, and candidate smoothed log equals engine_smoothing.smooth_arrays of that raw log (rtol 1e-8, atol 1e-9). Any mismatch stops the study.',
        'live': {'schedule': f'{REPETITIONS} repetitions, declared order then reverse, arm order alternates. Three threads: input and output loops every {LIVE_CHUNK} samples, and the app worker loop. No pinning and no thread limits, as the app.',
                 'output_stamp_latency_s': OUTPUT_LATENCY, 'settings': f'Up to 3 median tones of the room at gain {GAIN} on both ears, so on_output really synthesizes. Output is discarded.'},
        'quiet': {'wait': f'{QUIET_WINDOWS} windows of {WINDOW_SECONDS} s in a row at or under {QUIET_PERCENT}% before starting, for at most {WAIT_LIMIT_SECONDS} s; then the preflight of one more window.',
                  'per_run': f'A run is quiet if preflight passed and estimated background CPU is at or under {QUIET_PERCENT}%.', 'do_not_stop_other_work': True},
        'decision': {'each_arm': 'Decided separately; v2 is the control, candidate is the question.',
                     'clean': 'Every run, quiet or not: no thread error, no stale block, no limiter stop, no glitch, logs equal the offline reference.',
                     'timing': f'Every quiet run: push p99 < {PATH_P99_MS} ms and on_output p99 < {CALLBACK_P99_MS} ms.',
                     'result': f'Fail if clean fails or any quiet run misses timing. Pass needs clean, timing and at least {MINIMUM_QUIET_RUNS} of 28 quiet runs. Otherwise inconclusive.'},
        'descriptive': 'on_input time, thread lateness, queue depth, forecast lead, slowest blocks, not-quiet runs.',
        'caveats': 'Thread loops stand in for PortAudio callbacks and the output latency is assumed. The 5 ms bars are reserves, not measured needs. No physical ANC is claimed.',
        'code_sha256': {name: h.sha(ROOT/name) for name in FILES}, 'source_protocol_sha256': h.sha(SOURCE/'protocol.json'),
    }
    STUDY.mkdir()
    h.write_new(STUDY/'protocol.json', protocol)
    h.write_new(STUDY/'frozen.json', {'sha256': h.sha(STUDY/'protocol.json')})
    print(json.dumps({'protocol_sha256': h.sha(STUDY/'protocol.json')}), flush=True)


def verified():
    p = h.read(STUDY/'protocol.json')
    assert h.sha(STUDY/'protocol.json') == h.read(STUDY/'frozen.json')['sha256']
    for name, digest in p['code_sha256'].items():
        assert h.sha(ROOT/name) == digest, name
    return p


def output():
    p = verified()
    (STUDY/'output').mkdir()
    rows = []
    for c, x in rooms():
        reference, _ = run_offline(x, len(x), False)
        expected = es.smooth_arrays(reference, st.ALPHA)
        for chunk in CHUNKS:
            with cached_dpss(True) as cache:
                raw, smooth = run_offline(x, chunk, True)
                assert len(cache) == 1, 'Taper cache must hold one window length'
            cut = {k: v[:len(raw['seen'])] for k, v in reference.items()}
            st.same(raw, cut)
            st.same(smooth, {k: v[:len(raw['seen'])] for k, v in expected.items()})
            rows.append({'case_id': c['case_id'], 'chunk': chunk, 'origins': len(raw['seen']),
                         'largest_phasor_difference': float(np.max(np.abs(smooth['phasor']-expected['phasor'][:len(raw['seen'])])))})
        print(json.dumps(rows[-1]), flush=True)
    assert len(rows) == len(p['cases'])*len(CHUNKS)
    h.write_new(STUDY/'output/complete.json', {'passed': True, 'rows': rows, 'largest_phasor_difference': max(r['largest_phasor_difference'] for r in rows),
                                               'completed_utc': datetime.now(timezone.utc).isoformat()})


def decide(subset):
    quiet = [r for r in subset if r['quiet_qualified']]
    clean = all(r['clean'] for r in subset)
    timing = all(r['push_ms']['p99'] < PATH_P99_MS and r['output_ms']['p99'] < CALLBACK_P99_MS for r in quiet)
    result = 'fail' if not clean or not timing else 'pass' if len(quiet) >= MINIMUM_QUIET_RUNS else 'inconclusive'
    return {'result': result, 'runs': len(subset), 'quiet_runs': len(quiet), 'clean': clean, 'quiet_timing_met': timing,
            'push_p99_quiet_worst_ms': max((r['push_ms']['p99'] for r in quiet), default=None), 'output_p99_quiet_worst_ms': max((r['output_ms']['p99'] for r in quiet), default=None),
            'worst_queue_ms': max(r['queue_ms']['max'] for r in subset), 'worst_push_ms': max(r['push_ms']['max'] for r in subset),
            'worst_output_ms': max(r['output_ms']['max'] for r in subset), 'stale_blocks': sum(r['stale_blocks'] for r in subset)}


def busy_seconds(cpu):
    return sum(cpu)-getattr(cpu, 'idle', 0)-getattr(cpu, 'iowait', 0)


def wait_for_quiet():
    start, streak = time.time(), 0
    while time.time()-start < WAIT_LIMIT_SECONDS:
        streak = streak+1 if psutil.cpu_percent(interval=WINDOW_SECONDS) <= QUIET_PERCENT else 0
        if streak == QUIET_WINDOWS:
            return time.time()-start
    raise SystemExit('No quiet window before the limit; nothing was timed.')


def live():
    p = verified()
    assert h.read(STUDY/'output/complete.json')['passed']
    stage = STUDY/'live'
    stage.mkdir()
    waited = wait_for_quiet()
    preflight = float(psutil.cpu_percent(interval=WINDOW_SECONDS))
    quiet = preflight <= QUIET_PERCENT
    environment = {'platform': platform.platform(), 'python': platform.python_version(), 'logical_cpus': psutil.cpu_count(), 'waited_seconds': waited,
                   'preflight_percent': preflight, 'quiet_preflight': quiet, 'started_utc': datetime.now(timezone.utc).isoformat(), 'protocol_sha256': h.sha(STUDY/'protocol.json')}
    h.write_new(stage/'environment.json', environment)
    prepared = [(c, x, run_offline(x, len(x), False)[0]) for c, x in rooms()]
    proc, rows = psutil.Process(), []
    for repetition in range(REPETITIONS):
        for i, (c, x, reference) in enumerate(prepared if repetition == 0 else prepared[::-1]):
            for arm in ARMS if (i+repetition) % 2 == 0 else ARMS[::-1]:
                before, own, start = psutil.cpu_times(), proc.cpu_times(), time.perf_counter()
                with cached_dpss(arm == 'candidate'):
                    times, report, logs = session(x, tones_of(reference), arm)
                elapsed, after, own_after = time.perf_counter()-start, psutil.cpu_times(), proc.cpu_times()
                own_seconds = own_after.user+own_after.system-own.user-own.system
                background = max(0., (busy_seconds(after)-busy_seconds(before)-own_seconds)/(elapsed*psutil.cpu_count())*100)
                match = True
                try:
                    rows_seen = len(logs[0]['seen'])
                    st.same(logs[0], {k: v[:rows_seen] for k, v in reference.items()})
                    if arm == 'candidate':
                        expected = es.smooth_arrays(reference, st.ALPHA)
                        st.same(logs[1], {k: v[:rows_seen] for k, v in expected.items()})
                except AssertionError:
                    match = False
                name = f"{c['case_id']}-r{repetition+1}-{arm}"
                np.savez_compressed(stage/(name+'.npz'), **times)
                clean = match and not report['errors'] and not report['stale_blocks'] and not report['stopped'] and not any(report['glitches'].values()) and not report['worker_alive']
                row = {'case_id': c['case_id'], 'arm': arm, 'repetition': repetition+1, **report, 'match': match, 'clean': clean,
                       'background_cpu_percent': background, 'quiet_qualified': bool(quiet and background <= QUIET_PERCENT),
                       **{k: st.stat(v) for k, v in times.items()}}
                h.write_new(stage/(name+'.json'), row)
                rows.append(row)
                print(json.dumps({'completed': len(rows), 'case': c['case_id'], 'arm': arm, 'clean': clean, 'push_p99': round(row['push_ms']['p99'], 3),
                                  'output_p99': round(row['output_ms']['p99'], 3), 'queue_max': round(row['queue_ms']['max'], 1), 'background': round(background, 1)}), flush=True)
    summary = {arm: decide([r for r in rows if r['arm'] == arm]) for arm in ARMS}
    h.write_new(stage/'results.json', {'environment': environment, 'runs': rows, 'summary': summary, 'completed_utc': datetime.now(timezone.utc).isoformat()})
    h.write_new(STUDY/'SUMMARY.json', summary)
    print(json.dumps(summary, indent=1), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['freeze', 'output', 'live'])
    {'freeze': freeze, 'output': output, 'live': live}[parser.parse_args().stage]()
