"""Two 30 s input-only listens, shared then exclusive WASAPI, to see whether Windows processing hides the hum.

Plays nothing and stores no audio: each take stays in memory and only numbers
are saved, to a new folder. The Intel laptop Microphone Array is resolved by name.
"""
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
OUT = Path(__file__).resolve().parents[1]/'results-live-listen-02'


def take(device, exclusive):
    """One take as float mono, or the reason it could not open."""
    if not exclusive:
        x = sd.rec(SECONDS*RATE, samplerate=RATE, channels=1, dtype='float32', device=device)
        sd.wait()
        return x[:, 0].astype(float), {'channels': 1, 'dtype': 'float32'}
    errors = []
    for channels in (1, 2, 4):
        for dtype in ('float32', 'int32', 'int16'):
            try:
                x = sd.rec(SECONDS*RATE, samplerate=RATE, channels=channels, dtype=dtype, device=device,
                           extra_settings=sd.WasapiSettings(exclusive=True))
                sd.wait()
                scale = {'float32': 1., 'int32': 2.**31, 'int16': 2.**15}[dtype]
                return x[:, 0].astype(float)/scale, {'channels': channels, 'dtype': dtype}
            except Exception as exc:
                errors.append(f'{channels} ch {dtype}: {exc}')
    return None, {'errors': errors}


def describe(x):
    f, p = signal.welch(x, RATE, nperseg=RATE*4)
    keep = (f >= 30) & (f <= 6000)
    f, p = f[keep], p[keep]
    excess = 10*np.log10(p)-signal.medfilt(10*np.log10(p), 401)
    peaks, props = signal.find_peaks(excess, height=10, distance=8, width=(None, None), rel_height=.5)
    order = np.argsort(-excess[peaks])[:8]
    lines = [{'hz': float(f[peaks[i]]), 'above_floor_db': float(excess[peaks[i]]), 'half_width_hz': float(props['widths'][i]*.25),
              'level_db': float(10*np.log10(p[peaks[i]]))} for i in sorted(order, key=lambda i: f[peaks[i]])]
    track = []
    seg = 3*RATE
    for s in range(0, len(x)-seg+1, seg):
        g, q = signal.periodogram(x[s:s+seg]*signal.windows.hann(seg), RATE, nfft=seg*8)
        band = (g > 190) & (g < 210)
        j = np.argmax(q[band])
        track.append({'start_s': s/RATE, 'hz': float(g[band][j]), 'level_db': float(10*np.log10(q[band][j]))})
    dec, eng, hits = StreamingDecimator(RATE, FS), SmoothedEngine(), {}
    for k in range(len(x)//480):
        d = dec.process(x[k*480:(k+1)*480])
        if len(d):
            eng.push(d)
            for fr, _ in eng.strongest():
                hits[str(round(fr))] = hits.get(str(round(fr)), 0)+1
    return {'rms_dbfs': float(20*np.log10(np.sqrt(np.mean(x**2))+1e-12)), 'peak_dbfs': float(20*np.log10(np.abs(x).max()+1e-12)),
            'lines': lines, 'track_190_210': track, 'detector': eng.counters, 'detector_tones': hits}


def main():
    assert not OUT.exists(), 'Never overwrite a run'
    inputs, _ = wasapi_devices(sd.query_hostapis(), sd.query_devices())
    mic = laptop_microphone(inputs)
    result = {'utc': datetime.now(timezone.utc).isoformat(), 'device': mic[1], 'seconds_each': SECONDS, 'audio_stored': False}
    for name, exclusive in (('shared', False), ('exclusive', True)):
        print('Listening', name, 'for', SECONDS, 's', flush=True)
        x, how = take(mic[0], exclusive)
        result[name] = {'opened': x is not None, **how, **(describe(x) if x is not None else {})}
    print('Listening ended', flush=True)
    OUT.mkdir()
    (OUT/'listen.json').write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))


if __name__ == '__main__':
    main()
