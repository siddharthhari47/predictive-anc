"""results-fan-predictability-01: how far ahead can the fan's hum be predicted? Descriptive, no pass bar.

The whole idea rests on one fact: the anti-hum is made from what the laptop
microphone heard some milliseconds ago, so it is only right if the hum can be
predicted that far ahead. This measures that directly on the fan recordings
already on this computer. For each look-ahead it fits a linear predictor on
the first half of a recording (past microphone samples only, through the app's
own causal decimator) and scores it on the second half, which it never saw:
how much of the hum (the band +-5 Hz around its line) would be left over.

Control: the same recording with the hum replaced by a perfectly steady tone
of the same level, so the room noise stays real. Reads audio into memory only,
writes no audio, opens no audio stream (device latencies are read from
Windows' device list, which opens nothing).
"""
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import imageio_ffmpeg
import numpy as np
from scipy import signal
from scipy.io import wavfile

from anc_lab import selector_headroom as h
from anc_lab.antihum import FS, StreamingDecimator

OUT = ROOT/'results-fan-predictability-01'
RATE = 48000
HORIZONS_MS = (5, 10, 20, 50, 100, 200)
ORDER = 400            # 0.2 s of past microphone samples
BAND_HZ = 5.           # the hum = within +-5 Hz of its line
GAP_SECONDS = 1.       # embargo between training targets and test targets
SOURCES = {'sid-recording-7 (6 Nov, Windows Sound Recorder)': Path(r'C:\Users\talk2.000\Documents\Sound Recordings\Recording (7).m4a'),
           'goal1_fan_01 (October, laptop mic)': ROOT/'recordings'/'goal1_fan_01.wav',
           'source-study fan_on (October, laptop mic)': ROOT/'results-source-study-01'/'fan_on.wav'}


def load(path):
    if path.suffix.lower() == '.wav':
        rate, x = wavfile.read(path)
        x = x.astype(float)/(32768. if x.dtype == np.int16 else 1.)
        x = x.mean(axis=1) if x.ndim > 1 else x
        if rate != RATE:
            g = np.gcd(rate, RATE)
            x = signal.resample_poly(x, RATE//g, rate//g)
        return x
    raw = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-i', str(path), '-ac', '1', '-ar', str(RATE), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(float)


def line_of(y):
    f, p = signal.welch(y, FS, nperseg=4*FS)
    level = 10*np.log10(np.maximum(p, 1e-30))
    excess = level-signal.medfilt(level, 2*round(20/(f[1]-f[0]))+1)
    inside = (f >= 35) & (f <= 350)
    k = int(np.argmax(np.where(inside, excess, -np.inf)))
    lo = hi = k
    while lo > 0 and level[lo-1] > level[k]-3:
        lo -= 1
    while hi < len(level)-1 and level[hi+1] > level[k]-3:
        hi += 1
    return float(f[k]), float(excess[k]), float((hi-lo+1)*(f[1]-f[0]))


def leftover_db(y, target, delay):
    """Hum left over (dB, negative = removed) by the best linear predictor of target[n+delay] from y[n-ORDER+1..n]."""
    n = len(y)
    rows = np.arange(ORDER-1, n-delay)
    X = np.lib.stride_tricks.sliding_window_view(y, ORDER)[rows-ORDER+1]
    t = target[rows+delay]
    half = n//2
    train = rows+delay < half
    test = rows >= half+round(GAP_SECONDS*FS)
    A = X[train]
    ridge = 1e-6*np.trace(A.T@A)/ORDER
    w = np.linalg.solve(A.T@A+ridge*np.eye(ORDER), A.T@t[train])
    error = t[test]-X[test]@w
    return float(10*np.log10(np.mean(error**2)/np.mean(t[test]**2)))


def latencies():
    try:
        import sounddevice as sd
        apis = sd.query_hostapis()
        wasapi = [i for i, a in enumerate(apis) if 'WASAPI' in a['name']][0]
        return [{'name': d['name'], 'input_s': d['default_high_input_latency'] if d['max_input_channels'] else None,
                 'output_s': d['default_high_output_latency'] if d['max_output_channels'] else None}
                for d in sd.query_devices() if d['hostapi'] == wasapi]
    except Exception as exc:
        return repr(exc)


def main():
    assert not OUT.exists(), 'Never overwrite a run'
    OUT.mkdir()
    rows = []
    for name, path in SOURCES.items():
        x = load(path)
        y = StreamingDecimator(RATE, FS).process(x[:len(x)-len(x) % 480])
        f0, excess, width = line_of(y)
        sos = signal.butter(4, [f0-BAND_HZ, f0+BAND_HZ], 'bandpass', fs=FS, output='sos')
        hum = signal.sosfiltfilt(sos, y)                    # defines the target only; the predictor sees raw past samples
        steady = np.sqrt(2)*np.std(hum)*np.sin(2*np.pi*f0*np.arange(len(y))/FS+1.)
        control = y-hum+steady
        control_target = signal.sosfiltfilt(sos, control)
        row = {'recording': name, 'seconds': len(y)/FS, 'line_hz': f0, 'line_above_floor_db': excess, 'line_width_3db_hz': width,
               'hum_leftover_db': {}, 'steady_control_leftover_db': {}}
        for ms in HORIZONS_MS:
            d = round(ms*FS/1000)
            row['hum_leftover_db'][ms] = leftover_db(y, hum, d)
            row['steady_control_leftover_db'][ms] = leftover_db(control, control_target, d)
        rows.append(row)
        print(name, round(f0, 2), 'Hz', {ms: round(v, 1) for ms, v in row['hum_leftover_db'].items()},
              'control', {ms: round(v, 1) for ms, v in row['steady_control_leftover_db'].items()}, flush=True)
    result = {'created_utc': datetime.now(timezone.utc).isoformat(), 'kind': 'descriptive, no pass bar',
              'method': {'order_samples': ORDER, 'analysis_rate': FS, 'band_hz': BAND_HZ, 'train': 'first half', 'test': 'second half after a 1 s gap',
                         'predictor': 'ridge least squares, linear in past microphone samples'},
              'recordings': rows, 'windows_reported_latency': latencies(), 'complete': True,
              'code_sha256': h.sha(Path(__file__))}
    h.write_new(OUT/'results.json', result)
    print('done', flush=True)


if __name__ == '__main__':
    main()
