"""Why the candidate's engine step is slower in the real runner. Descriptive, no pass or fail. Never opens audio devices.

Written after results-engine-candidate-01. Same candidate, same stored rooms,
frozen modules imported unchanged. One factor changes at a time:

  tight   one thread, no waiting between blocks (like the earlier timing)
  paced   one thread, sleeping to each 10 ms deadline (idle core, cold caches)
  runner  the real three-thread session
  free/one  numerical threads as the app has them, or limited to one
  fast    runner with Python's lock handover at 0.5 ms instead of 5 ms

Wall time against the worker's own CPU time separates waiting from extra work.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import psutil
from threadpoolctl import threadpool_info, threadpool_limits

from anc_lab import engine_candidate as ec
from anc_lab import selector_headroom as h
from anc_lab import smoother_timing as st
from anc_lab.antihum import StreamingDecimator
from anc_lab.selector_stream_profile import cached_dpss
from anc_lab.tune_app import RATE

STUDY = ec.ROOT/'results-runner-slowdown-01'
CONDITIONS = ('tight-free', 'tight-one', 'paced-free', 'paced-one', 'runner-free', 'runner-one', 'runner-one-fast')
CHUNK = ec.LIVE_CHUNK


class CpuTimedEngine(ec.TimedEngine):
    def __init__(self, engine, pushes):
        super().__init__(engine, pushes)
        self.cpu = 0.

    def push(self, block):
        before = time.thread_time()
        super().push(block)
        self.cpu += time.thread_time()-before


def alone(x, paced):
    """Decimate and push on this one thread, as the worker does, without the callbacks."""
    n = len(x)//CHUNK
    engine = CpuTimedEngine(ec.SmoothedEngine(True), n+1)
    decimator = StreamingDecimator(RATE, st.FS)
    start = time.perf_counter()+.2
    for k in range(n):
        if paced:
            delay = start+(k+1)*CHUNK/RATE-time.perf_counter()
            if delay > 0:
                time.sleep(delay)
        y = decimator.process(x[k*CHUNK:(k+1)*CHUNK])
        if len(y):
            engine.push(y)
    return engine.times[:engine.count]*1e3, engine.cpu


def run(x, tones, condition):
    place, *rest = condition.split('-')
    limits = 1 if rest[0] == 'one' else None
    with threadpool_limits(limits=limits), cached_dpss(True):
        if place == 'runner':
            sys.setswitchinterval(.0005 if rest[-1] == 'fast' else .005)
            try:
                engines = []
                class Keep(CpuTimedEngine):
                    def __init__(self, engine, pushes):
                        super().__init__(engine, pushes)
                        engines.append(self)
                original, ec.TimedEngine = ec.TimedEngine, Keep
                try:
                    times, report, _ = ec.session(x, tones, 'candidate')
                finally:
                    ec.TimedEngine = original
                assert not report['errors'] and not report['stale_blocks'], report
                return times['push_ms'], engines[0].cpu
            finally:
                sys.setswitchinterval(.005)
        return alone(x, place == 'paced')


def main():
    assert not STUDY.exists(), 'Never overwrite a run'
    STUDY.mkdir()
    sys.stdout = sys.stderr = open(STUDY/'run.log', 'a', buffering=1)
    prepared = [(c, x, ec.tones_of(ec.run_offline(x, len(x), False)[0])) for c, x in ec.rooms()]
    waited = ec.wait_for_quiet()
    h.write_new(STUDY/'environment.json', {'tool_sha256': h.sha(Path(__file__)), 'waited_seconds': waited, 'logical_cpus': psutil.cpu_count(), 'threadpools': threadpool_info(),
                                           'candidate_protocol_sha256': h.sha(ec.STUDY/'protocol.json'), 'started_utc': datetime.now(timezone.utc).isoformat()})
    proc, rows = psutil.Process(), []
    for i, (c, x, tones) in enumerate(prepared):
        for j in range(len(CONDITIONS)):           # order rotates room by room
            condition = CONDITIONS[(i+j) % len(CONDITIONS)]
            before, own, start = psutil.cpu_times(), proc.cpu_times(), time.perf_counter()
            times, cpu = run(x, tones, condition)
            elapsed, after, own_after = time.perf_counter()-start, psutil.cpu_times(), proc.cpu_times()
            own_seconds = own_after.user+own_after.system-own.user-own.system
            background = max(0., (ec.busy_seconds(after)-ec.busy_seconds(before)-own_seconds)/(elapsed*psutil.cpu_count())*100)
            np.savez_compressed(STUDY/f"{c['case_id']}-{condition}.npz", push_ms=times)
            rows.append({'case_id': c['case_id'], 'condition': condition, 'order': j, 'push_ms': st.stat(times), 'worker_cpu_ms_per_push': cpu*1e3/len(times),
                         'process_cpu_seconds': own_seconds, 'elapsed_seconds': elapsed, 'background_cpu_percent': background})
            print(json.dumps({'done': len(rows), 'condition': condition, 'mean': round(rows[-1]['push_ms']['mean'], 3), 'p99': round(rows[-1]['push_ms']['p99'], 3), 'background': round(background, 1)}), flush=True)
    h.write_new(STUDY/'results.json', {'runs': rows, 'completed_utc': datetime.now(timezone.utc).isoformat()})
    print('complete', flush=True)


if __name__ == '__main__':
    main()
