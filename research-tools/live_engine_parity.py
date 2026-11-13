"""Check the app's smoothed engine against the frozen candidate on the 14 stored rooms. Never opens audio devices."""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from anc_lab import engine_candidate as ec
from anc_lab import live_engine as le
from anc_lab.antihum import StreamingDecimator, log_arrays
from anc_lab import smoother_timing as st
from anc_lab.selector_stream_profile import cached_dpss
from anc_lab.tune_app import RATE


def feed(engine, x):
    decimator = StreamingDecimator(RATE, st.FS)
    logged, chunk = [], ec.LIVE_CHUNK
    for k in range(len(x)//chunk):
        y = decimator.process(x[k*chunk:(k+1)*chunk])
        if len(y):
            engine.push(y)
            logged.append((engine.origin_seen, list(engine.components), engine.gate_open))
    return log_arrays(engine.raw.log), logged


rooms = 0
for c, x in ec.rooms():
    with cached_dpss(True):
        frozen_log, frozen_steps = feed(ec.SmoothedEngine(True), x)
    live_log, live_steps = feed(le.SmoothedEngine(True), x)
    st.same(live_log, frozen_log)
    assert live_steps == frozen_steps, c['case_id']
    rooms += 1
    print(json.dumps({'case': c['case_id'], 'blocks': len(live_steps), 'same': True}), flush=True)
assert rooms == 14
print('complete: exact on', rooms, 'rooms')
