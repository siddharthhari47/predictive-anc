"""30 s input-only check of what the tuner can hear. Plays nothing and stores no audio.

The Intel laptop Microphone Array is resolved by name. The audio stays in
memory; only levels, spectral peaks and the engine's tone reports are saved,
to a new folder. Written for Sid's 6 November request (fan on, voices nearby).
"""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import sounddevice as sd
from scipy import signal

from anc_lab.antihum import FS, StreamingDecimator
from anc_lab.live_engine import SmoothedEngine
from anc_lab.tune_app import RATE, laptop_microphone, wasapi_devices

SECONDS = 30
OUT = Path(__file__).resolve().parents[1]/'results-live-listen-01'


def main():
    assert not OUT.exists(), 'Never overwrite a run'
    inputs, _ = wasapi_devices(sd.query_hostapis(), sd.query_devices())
    mic = laptop_microphone(inputs)
    print('Listening on', mic[1], 'for', SECONDS, 's', flush=True)
    x = sd.rec(SECONDS*RATE, samplerate=RATE, channels=1, dtype='float32', device=mic[0])
    sd.wait()
    x = x[:, 0].astype(float)
    print('Listening ended', flush=True)

    decimator, engine = StreamingDecimator(RATE, FS), SmoothedEngine()
    y, seen, gate = [], Counter(), 0
    for k in range(len(x)//480):
        d = decimator.process(x[k*480:(k+1)*480])
        if len(d):
            y.append(d)
            engine.push(d)
            tones = engine.strongest()
            for f, _ in tones:
                seen[round(f)] += 1
            gate += engine.gate_open
    y = np.concatenate(y)
    origins = engine.counters['origins']
    f, p = signal.welch(y, FS, nperseg=FS*4)
    band = (f >= 35) & (f <= 350)
    floor = np.median(p[band])
    peaks, _ = signal.find_peaks(10*np.log10(p[band]/floor), height=6, distance=4)
    order = np.argsort(-p[band][peaks])[:8]
    result = {
        'utc': datetime.now(timezone.utc).isoformat(), 'device': mic[1], 'seconds': SECONDS, 'audio_stored': False,
        'rms_dbfs': float(20*np.log10(np.sqrt(np.mean(x**2))+1e-12)), 'peak_dbfs': float(20*np.log10(np.max(np.abs(x))+1e-12)),
        'spectral_peaks_35_350': [{'hz': float(f[band][peaks][i]), 'above_median_db': float(10*np.log10(p[band][peaks][i]/floor))} for i in order],
        'engine_origins': origins, 'origins_with_tones': engine.counters['origins_with_tones'], 'gate_open_fraction': gate/max(origins, 1),
        'engine_tones_rounded_hz': dict(seen.most_common(8)),
    }
    OUT.mkdir()
    (OUT/'listen.json').write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))


if __name__ == '__main__':
    main()
