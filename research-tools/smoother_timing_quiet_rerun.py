"""Repeat the frozen smoother timing in a new folder once the machine has been quiet. Never opens audio devices.

The frozen module, protocol, rule and inputs are reused unchanged: only the
output folder differs, and verified() still checks every hash. Written after
results-smoother-timing-01 and not part of its protocol. Nothing here stops
other work; if no quiet window arrives before the limit, nothing is timed.
"""
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psutil

from anc_lab import selector_headroom as h
from anc_lab import smoother_timing as st

SOURCE = st.ROOT/'results-smoother-timing-01'
TARGET = st.ROOT/'results-smoother-timing-02'
SAMPLE_SECONDS, QUIET_SAMPLES, LIMIT_SECONDS = 10, 3, 6*3600


def wait_for_quiet():
    """True after QUIET_SAMPLES windows in a row at or under the frozen limit."""
    start, streak, samples = time.time(), 0, 0
    while time.time()-start < LIMIT_SECONDS:
        load = psutil.cpu_percent(interval=SAMPLE_SECONDS)
        samples += 1
        streak = streak+1 if load <= st.QUIET_PERCENT else 0
        if samples % 30 == 0 or streak == QUIET_SAMPLES:
            print('Waiting', samples, 'load', load, 'streak', streak, flush=True)
        if streak == QUIET_SAMPLES:
            return True, time.time()-start
    return False, time.time()-start


def main():
    assert not TARGET.exists(), 'Never overwrite a timing run'
    TARGET.mkdir()
    sys.stdout = sys.stderr = open(TARGET/'benchmark.log', 'a', buffering=1)
    for name in ('protocol.json', 'frozen.json'):
        shutil.copy2(SOURCE/name, TARGET/name)
    for name in ('parity', 'inputs'):
        shutil.copytree(SOURCE/name, TARGET/name)
    st.STUDY = TARGET
    st.verified()
    quiet, waited = wait_for_quiet()
    h.write_new(TARGET/'rerun.json', {'source': SOURCE.name, 'launcher_sha256': h.sha(Path(__file__)), 'protocol_sha256': h.sha(TARGET/'protocol.json'),
                                      'waited_seconds': waited, 'quiet_window_found': quiet, 'started_utc': datetime.now(timezone.utc).isoformat()})
    if quiet:
        st.benchmark()
    else:
        print('No quiet window before the limit; nothing was timed.', flush=True)


if __name__ == '__main__':
    main()
