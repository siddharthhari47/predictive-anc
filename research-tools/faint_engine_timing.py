"""results-faint-engine-timing-01: does the faint engine keep time inside the app's real LiveRunner? Never opens audio devices.

Same method and bars as results-engine-candidate-01/-02: the stored 30 s
simulated rooms are played at real-time pace through the real on_input,
on_output and pump code on three threads, as the audio callbacks and worker
would, and the output is thrown away. Two arms, both the app's own engines from
anc_lab/live_engine.py: `smoothed` (today's default, the control) and `faint`
(smoothed plus the faint-hum detector, the question). Stages run in order in one
call: freeze the protocol, check output offline, wait for a quiet machine, time.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import platform
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import psutil

from anc_lab import engine_candidate as ec
from anc_lab import selector_headroom as h
from anc_lab import smoother_timing as st
from anc_lab.antihum import StreamingDecimator, ToneSetting, log_arrays
from anc_lab.live_engine import FaintEngine, SmoothedEngine
from anc_lab.tune_app import LiveRunner, RATE

STUDY = ROOT/'results-faint-engine-timing-01'
ARMS = {'smoothed': SmoothedEngine, 'faint': FaintEngine}
CHUNKS = (137, 480, 1024, 1920)
LIVE_CHUNK, OUTPUT_LATENCY, GAIN, REPETITIONS = ec.LIVE_CHUNK, ec.OUTPUT_LATENCY, ec.GAIN, 2
PATH_P99_MS, CALLBACK_P99_MS, QUIET_PERCENT, MINIMUM_QUIET_RUNS = 5., 5., 5., 24
GPU_SAMPLE_SECONDS, GPU_LIMIT_SECONDS = 60, 6*3600
FILES = ['research-tools/faint_engine_timing.py', 'anc_lab/live_engine.py', 'anc_lab/faint_tones.py', 'anc_lab/antihum.py',
         'anc_lab/tone_selection.py', 'anc_lab/tune_app.py', 'anc_lab/engine_candidate.py']


def offline(x, chunk, arm):
    engine, decimator = ARMS[arm](True), StreamingDecimator(RATE, st.FS)
    for k in range(0, len(x)-len(x) % chunk, chunk):
        y = decimator.process(x[k:k+chunk])
        if len(y):
            engine.push(y)
    return log_arrays(engine.raw.log)


def session(x, tones, arm):
    """One paced run of the real runner (copied from engine_candidate.session, engine chosen by arm)."""
    n = len(x)//LIVE_CHUNK
    engine = ec.TimedEngine(ARMS[arm](True), n+1)
    runner = LiveRunner(engine=engine)
    for f in tones:
        runner.set_tone('both', ToneSetting(f, GAIN))
    runner.limiter.start()
    times = {k: np.zeros(n) for k in ('input_ms', 'output_ms', 'input_late_ms', 'output_late_ms', 'queue_ms')}
    errors, closing, sounding, clock = [], threading.Event(), [0], time.perf_counter
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
              'forecast_lead_s': state['forecast_lead_s'], 'sounding_blocks': sounding[0], 'blocks': n, 'worker_alive': worker.is_alive(),
              'origins_with_tones': engine.engine.counters['origins_with_tones']}
    return times, report, log_arrays(engine.engine.raw.log)


def gpu_clear():
    start, streak = time.time(), 0
    while time.time()-start < GPU_LIMIT_SECONDS:
        busy = subprocess.run(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'], capture_output=True, text=True, timeout=30).stdout.strip()
        streak = 0 if busy else streak+1
        if streak == 2:
            return True, time.time()-start
        time.sleep(GPU_SAMPLE_SECONDS)
    return False, time.time()-start


def decide(subset):
    quiet = [r for r in subset if r['quiet_qualified']]
    clean = all(r['clean'] for r in subset)
    timing = all(r['push_ms']['p99'] < PATH_P99_MS and r['output_ms']['p99'] < CALLBACK_P99_MS for r in quiet)
    result = 'fail' if not clean or not timing else 'pass' if len(quiet) >= MINIMUM_QUIET_RUNS else 'inconclusive'
    return {'result': result, 'runs': len(subset), 'quiet_runs': len(quiet), 'clean': clean, 'quiet_timing_met': timing,
            'quiet_runs_under_bar': sum(r['push_ms']['p99'] < PATH_P99_MS and r['output_ms']['p99'] < CALLBACK_P99_MS for r in quiet),
            'push_p99_range_quiet_ms': [min((r['push_ms']['p99'] for r in quiet), default=None), max((r['push_ms']['p99'] for r in quiet), default=None)],
            'output_p99_quiet_worst_ms': max((r['output_ms']['p99'] for r in quiet), default=None),
            'worst_queue_ms': max(r['queue_ms']['max'] for r in subset), 'worst_push_ms': max(r['push_ms']['max'] for r in subset),
            'blocks_over_5ms': sum(r['push_ms']['over_5ms'] for r in subset), 'blocks_over_10ms': sum(r['push_ms']['over_10ms'] for r in subset),
            'stale_blocks': sum(r['stale_blocks'] for r in subset)}


def main():
    assert not STUDY.exists(), 'Never overwrite a run'
    STUDY.mkdir()
    sys.stdout = sys.stderr = open(STUDY/'live.log', 'a', buffering=1)
    cases = h.read(ec.SOURCE/'protocol.json')['cases']
    protocol = {
        'created_utc': datetime.now(timezone.utc).isoformat(), 'kind': 'offline_paced_engine_timing',
        'question': 'With the faint-hum detector added, does the app engine still keep time in the real LiveRunner at real-time pace?',
        'inputs': 'The 14 stored 30 s simulated microphones of results-smoother-timing-01, resampled to 48 kHz, as in results-engine-candidate-01/-02. Seen data.',
        'cases': [c['case_id'] for c in cases], 'chunks': CHUNKS,
        'arms': {'smoothed': 'live_engine.SmoothedEngine, the app default (control).', 'faint': 'live_engine.FaintEngine: smoothed plus CombinedSelector (question).'},
        'output_rule': 'Offline, each arm fed at every chunk size gives the same raw log as the same arm fed whole (rtol 1e-8, atol 1e-9); live runs give that log too. Any offline mismatch stops the study.',
        'live': f'{REPETITIONS} repetitions, declared order then reverse, arm order alternates; up to 3 median tones per room at gain {GAIN} on both ears; output discarded.',
        'quiet': f'GPU free of compute jobs for two 60 s samples, then three 10 s windows at or under {QUIET_PERCENT}% CPU and a preflight window; a run is quiet if preflight passed and background CPU during it was at or under {QUIET_PERCENT}%.',
        'decision': {'each_arm': 'Decided separately with the engine-candidate rule; faint is the question.',
                     'clean': 'Every run: no thread error, stale block, limiter stop or glitch, and the log equals offline.',
                     'timing': f'Every quiet run: push p99 < {PATH_P99_MS} ms and on_output p99 < {CALLBACK_P99_MS} ms.',
                     'result': f'Fail if clean fails or any quiet run misses timing; pass needs at least {MINIMUM_QUIET_RUNS} of 28 quiet runs; otherwise inconclusive.'},
        'caveats': 'Thread loops stand in for PortAudio callbacks. 30 s rooms: the faint detector needs about 9 s to lock, so it is fully active for about the last two thirds of each run. The 5 ms bar is a reserve, not a measured need. One run on one machine.',
        'code_sha256': {name: h.sha(ROOT/name) for name in FILES}}
    h.write_new(STUDY/'protocol.json', protocol)
    print('protocol frozen', flush=True)

    prepared = []
    for c, x in ec.rooms():
        reference = {arm: offline(x, len(x), arm) for arm in ARMS}
        for arm in ARMS:
            for chunk in CHUNKS:
                log = offline(x, chunk, arm)
                st.same(log, {k: v[:len(log['seen'])] for k, v in reference[arm].items()})
        prepared.append((c, x, reference, ec.tones_of(reference['smoothed'])))
        print('output exact', c['case_id'], flush=True)
    h.write_new(STUDY/'output_complete.json', {'passed': True, 'cases': len(prepared), 'chunks': CHUNKS})

    clear, gpu_wait = gpu_clear()
    if not clear:
        print('GPU never cleared; nothing was timed.', flush=True)
        return
    waited = ec.wait_for_quiet()
    preflight = float(psutil.cpu_percent(interval=ec.WINDOW_SECONDS))
    quiet = preflight <= QUIET_PERCENT
    battery, freq = psutil.sensors_battery(), psutil.cpu_freq()
    environment = {'platform': platform.platform(), 'python': platform.python_version(), 'logical_cpus': psutil.cpu_count(),
                   'gpu_waited_seconds': gpu_wait, 'cpu_waited_seconds': waited, 'preflight_percent': preflight, 'quiet_preflight': quiet,
                   'plugged_in': battery.power_plugged if battery else None, 'cpu_mhz': freq.current if freq else None,
                   'started_utc': datetime.now(timezone.utc).isoformat()}
    h.write_new(STUDY/'environment.json', environment)
    stage, proc, rows = STUDY/'live', psutil.Process(), []
    stage.mkdir()
    names = list(ARMS)
    for repetition in range(REPETITIONS):
        for i, (c, x, reference, tones) in enumerate(prepared if repetition == 0 else prepared[::-1]):
            for arm in names if (i+repetition) % 2 == 0 else names[::-1]:
                before, own, start = psutil.cpu_times(), proc.cpu_times(), time.perf_counter()
                times, report, log = session(x, tones, arm)
                elapsed, after, own_after = time.perf_counter()-start, psutil.cpu_times(), proc.cpu_times()
                own_seconds = own_after.user+own_after.system-own.user-own.system
                background = max(0., (ec.busy_seconds(after)-ec.busy_seconds(before)-own_seconds)/(elapsed*psutil.cpu_count())*100)
                try:
                    st.same(log, {k: v[:len(log['seen'])] for k, v in reference[arm].items()})
                    match = True
                except AssertionError:
                    match = False
                clean = match and not report['errors'] and not report['stale_blocks'] and not report['stopped'] \
                    and not any(report['glitches'].values()) and not report['worker_alive']
                name = f"{c['case_id']}-r{repetition+1}-{arm}"
                np.savez_compressed(stage/(name+'.npz'), **times)
                row = {'case_id': c['case_id'], 'arm': arm, 'repetition': repetition+1, **report, 'match': match, 'clean': clean,
                       'background_cpu_percent': background, 'quiet_qualified': bool(quiet and background <= QUIET_PERCENT),
                       **{k: st.stat(v) for k, v in times.items()}}
                h.write_new(stage/(name+'.json'), row)
                rows.append(row)
                print(json.dumps({'completed': len(rows), 'case': c['case_id'], 'arm': arm, 'clean': clean, 'push_p99': round(row['push_ms']['p99'], 3),
                                  'queue_max': round(row['queue_ms']['max'], 1), 'background': round(background, 1)}), flush=True)
    summary = {arm: decide([r for r in rows if r['arm'] == arm]) for arm in ARMS}
    h.write_new(STUDY/'results.json', {'environment': environment, 'runs': rows, 'summary': summary, 'complete': True,
                                       'completed_utc': datetime.now(timezone.utc).isoformat()})
    print(json.dumps(summary, indent=1), flush=True)
    print('FAINT', summary['faint']['result'].upper(), flush=True)


if __name__ == '__main__':
    main()
