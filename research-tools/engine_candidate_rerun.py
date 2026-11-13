"""Repeat the frozen engine candidate test in a new folder once the GPU job has ended. Never opens audio devices.

The frozen module, protocol, rule and inputs are reused unchanged: only the
output folder differs, and verified() still checks every hash. Written after
results-runner-slowdown-01 and not part of the protocol. The GPU wait is extra,
so that the frozen quiet check cannot pass during a lull in training. Nothing
here stops other work; if the machine never clears, nothing is timed.
"""
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psutil

from anc_lab import engine_candidate as ec
from anc_lab import selector_headroom as h

SOURCE = ec.ROOT/'results-engine-candidate-01'
TARGET = ec.ROOT/'results-engine-candidate-02'
GPU_SAMPLE_SECONDS, GPU_LIMIT_SECONDS = 60, 24*3600


def text_of(*command):
    return subprocess.run(command, capture_output=True, text=True, timeout=30).stdout.strip()


def gpu_jobs():
    return text_of('nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader')


def wait_for_gpu():
    """True once no compute job has been on the GPU for two samples in a row."""
    start, streak = time.time(), 0
    while time.time()-start < GPU_LIMIT_SECONDS:
        streak = 0 if gpu_jobs() else streak+1
        if streak == 2:
            return True, time.time()-start
        time.sleep(GPU_SAMPLE_SECONDS)
    return False, time.time()-start


def machine_state():
    battery, frequency = psutil.sensors_battery(), psutil.cpu_freq()
    return {'plugged_in': battery.power_plugged if battery else None, 'battery_percent': battery.percent if battery else None,
            'cpu_mhz': frequency.current if frequency else None, 'power_scheme': text_of('powercfg', '/getactivescheme')}


def main():
    assert not TARGET.exists(), 'Never overwrite a run'
    TARGET.mkdir()
    sys.stdout = sys.stderr = open(TARGET/'live.log', 'a', buffering=1)
    for name in ('protocol.json', 'frozen.json'):
        shutil.copy2(SOURCE/name, TARGET/name)
    ec.STUDY = TARGET
    ec.verified()
    ec.output()
    clear, waited = wait_for_gpu()
    h.write_new(TARGET/'rerun.json', {'source': SOURCE.name, 'launcher_sha256': h.sha(Path(__file__)), 'protocol_sha256': h.sha(TARGET/'protocol.json'),
                                      'gpu_waited_seconds': waited, 'gpu_clear': clear, 'machine': machine_state(), 'started_utc': datetime.now(timezone.utc).isoformat()})
    if clear:
        ec.live()
        print('complete', flush=True)
    else:
        print('GPU never cleared before the limit; nothing was timed.', flush=True)


if __name__ == '__main__':
    main()
