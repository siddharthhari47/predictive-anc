"""results-live-listen-03: one 30 s input-only listen through the earbuds' own microphone and the
laptop microphone at the same time. Does the earbuds' call microphone hear the fan's hum, and how
predictable is the hum there? Descriptive; the one rule below was fixed before the listen.

Plays nothing and stores no audio: both takes stay in memory and only numbers are saved, to a new
folder. Both microphones are found by name with the tune app's own functions and opened the way the
app opens them (WASAPI shared, 48 kHz, mono, float32, high latency). They close when the 30 s end.

For each microphone: level; the strongest spectral lines (the listen-02 method); the hum's frequency
and level every 3 s, which shows a noise reducer turning it down; what the app's two detectors
(smoothed, faint) locked on to; and how predictable the hum is 5 to 200 ms ahead (the
fan-predictability-02 method, imported unchanged, with its steady-tone control). Between the two
microphones: coherence at the hum. Near 1 means both heard the same wobbling sound, so the wobble is
in the room and not in one microphone's processing.

Rule, fixed before listening: the hum is the strongest line from 190 to 210 Hz on the laptop
microphone, which heard it 17.6 dB above its local floor on 6 November. A microphone hears the hum
if it has a line within 2 Hz of that frequency at least 6 dB above its local floor. Predictability
is worked out only where the hum is heard.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'research-tools'))

import numpy as np
import sounddevice as sd
from scipy import signal

import fan_predictability_02 as pred
from anc_lab import selector_headroom as h
from anc_lab.antihum import FS, StreamingDecimator
from anc_lab.live_engine import FaintEngine, SmoothedEngine
from anc_lab.tune_app import RATE, pick_microphone, wasapi_devices

SECONDS = 30
OUT = ROOT/'results-live-listen-03'
HUM_SEARCH_HZ = (190., 210.)
HEARS_DB = 6.            # a line this far above its local floor counts as heard
MATCH_HZ = 2.            # the same hum on the other microphone lies within this of the laptop's
CHUNK = 480              # the tune app's live block at 48 kHz: one detector origin per block
SETTLED_S = 10.          # the faint detector needs about 9 s to lock on
CODE = ('research-tools/listen_check_03.py', 'research-tools/fan_predictability_02.py', 'research-tools/fan_predictability.py',
        'anc_lab/tune_app.py', 'anc_lab/live_engine.py', 'anc_lab/faint_tones.py', 'anc_lab/antihum.py')


# ---- capture ----
class Take:
    """Fills a fixed-length buffer from an input stream's callback and keeps the stream's warnings."""
    def __init__(self, samples):
        self.x = np.zeros(samples, np.float32)
        self.filled, self.calls, self.flags = 0, 0, []
        self.channels, self.latency_s, self.open_errors = None, None, []
        self.done = threading.Event()

    def callback(self, indata, frames, time_info, status):
        self.calls += 1
        if status:
            self.flags.append(str(status))
        m = min(frames, len(self.x)-self.filled)
        if m > 0:
            self.x[self.filled:self.filled+m] = indata[:m].mean(axis=1)
            self.filled += m
        if self.filled >= len(self.x):
            self.done.set()


def open_input(index, take):
    """Mono, as the tune app opens it; two channels averaged only if mono is refused."""
    for channels in (1, 2):
        try:
            stream = sd.InputStream(device=index, samplerate=RATE, channels=channels, dtype='float32', latency='high',
                                    callback=take.callback)
            take.channels, take.latency_s = channels, float(stream.latency)
            return stream
        except sd.PortAudioError as exc:
            take.open_errors.append(f'{channels} ch: {exc}')
    raise RuntimeError('Could not open input %s: %s' % (index, '; '.join(take.open_errors)))


def listen(devices, seconds):
    """Both inputs at once, input-only, into memory: {label: Take}. Streams are closed on every path."""
    takes = {label: Take(seconds*RATE) for label in devices}
    streams, started = [], False
    try:
        for label, (index, _) in devices.items():
            streams.append(open_input(index, takes[label]))
        print('Listening for', seconds, 's through:', ' + '.join(name for _, name in devices.values()), flush=True)
        started = True
        for stream in streams:
            stream.start()
        deadline = time.monotonic()+seconds+10
        for take in takes.values():
            take.done.wait(max(deadline-time.monotonic(), 0.))
    finally:
        for stream in streams:
            stream.stop()
            stream.close()
        print('Listening ended; both microphones are closed' if started else 'Did not start listening; microphones closed', flush=True)
    return takes


# ---- analysis (arrays only; opens nothing) ----
def db(power):
    return float(10*np.log10(max(float(power), 1e-30)))


def lines(x):
    """listen-02's line list (30-6000 Hz, 0.25 Hz bins, lines 10 dB over the median of +-50 Hz), safe on silence."""
    f, p = signal.welch(x, RATE, nperseg=RATE*4)
    keep = (f >= 30) & (f <= 6000)
    f, p = f[keep], np.maximum(p[keep], 1e-30)
    level = 10*np.log10(p)
    excess = level-signal.medfilt(level, 401)
    peaks, props = signal.find_peaks(excess, height=10, distance=8, width=(None, None), rel_height=.5)
    order = np.argsort(-excess[peaks])[:8]
    found = [{'hz': float(f[peaks[i]]), 'above_floor_db': float(excess[peaks[i]]), 'width_hz': float(props['widths'][i]*.25),
              'level_db': float(level[peaks[i]])} for i in sorted(order, key=lambda i: f[peaks[i]])]
    return f, level, excess, found


def hum_at(f, level, excess, centre=None):
    """The strongest line from 190 to 210 Hz, or within MATCH_HZ of `centre`, and whether it is heard."""
    inside = ((f >= HUM_SEARCH_HZ[0]) & (f <= HUM_SEARCH_HZ[1])) if centre is None else (np.abs(f-centre) <= MATCH_HZ)
    k = np.flatnonzero(inside)[int(np.argmax(excess[inside]))]
    return {'hz': float(f[k]), 'above_floor_db': float(excess[k]), 'level_db': float(level[k]), 'heard': bool(excess[k] >= HEARS_DB)}


def every_3_s(x):
    """Broadband level and the 190-210 Hz peak in each 3 s stretch (listen-02's track, plus the level)."""
    rows, seg = [], 3*RATE
    for s in range(0, len(x)-seg+1, seg):
        g, q = signal.periodogram(x[s:s+seg]*signal.windows.hann(seg), RATE, nfft=seg*8)
        band = (g > HUM_SEARCH_HZ[0]) & (g < HUM_SEARCH_HZ[1])
        j = int(np.argmax(q[band]))
        rows.append({'start_s': s/RATE, 'rms_dbfs': db(np.mean(x[s:s+seg]**2)), 'hum_hz': float(g[band][j]), 'hum_level_db': db(q[band][j])})
    return rows


def detectors(x, hum_hz):
    """What the app's smoothed and faint engines list, block by block, as the live window would see it."""
    out = {}
    for name, make in (('smoothed', SmoothedEngine), ('faint', FaintEngine)):
        dec, eng, hits = StreamingDecimator(RATE, FS), make(), {}
        held, held_after, blocks_after, first_s = 0, 0, 0, None
        for k in range(len(x)//CHUNK):
            d = dec.process(x[k*CHUNK:(k+1)*CHUNK])
            if not len(d):
                continue
            eng.push(d)
            t = (k+1)*CHUNK/RATE
            tones = eng.strongest()
            for fr, _ in tones:
                hits[str(round(fr))] = hits.get(str(round(fr)), 0)+1
            on_hum = any(abs(fr-hum_hz) <= MATCH_HZ for fr, _ in tones)
            held += on_hum
            if on_hum and first_s is None:
                first_s = t
            if t > SETTLED_S:
                blocks_after += 1
                held_after += on_hum
        out[name] = {'counters': dict(eng.counters), 'tones_by_rounded_hz': hits, 'blocks_on_hum': held,
                     'first_on_hum_s': first_s, 'share_on_hum_after_10_s': held_after/max(blocks_after, 1)}
    return out


def bandpass(y, centre):
    return signal.sosfiltfilt(signal.butter(4, [centre-pred.BAND, centre+pred.BAND], 'bandpass', fs=FS, output='sos'), y)


def predictability(x, hum_hz):
    """fan-predictability-02 on this take: the hum band and the steady control, each fitted on the first half."""
    y = StreamingDecimator(RATE, FS).process(x[:len(x)-len(x) % CHUNK])
    f, p, floor, excess = pred.spectrum(y)
    near = np.flatnonzero(np.abs(f-hum_hz) <= MATCH_HZ)
    f0 = float(f[near[int(np.argmax(excess[near]))]])
    total, noise = pred.band_power(f, p, floor, f0)
    c, c_excess = pred.clean_frequency(f, excess, f0)
    _, noise_c = pred.band_power(f, p, floor, c)
    amplitude = np.sqrt(2*max(total-noise, 0.)*noise_c/noise)
    control = y+amplitude*np.sin(2*np.pi*c*np.arange(len(y))/FS+1.)
    hum = pred.study(y, bandpass(y, f0), f0, f, p, floor)
    fc, pc, floorc, _ = pred.spectrum(control)
    steady = pred.study(control, bandpass(control, c), c, fc, pc, floorc)
    return {'line_hz': f0, 'line_over_band_noise_db': db(total-noise)-db(noise) if total > noise else None,
            'control_hz': c, 'control_site_peak_excess_db': c_excess, 'hum': hum, 'steady_control': steady}


def coherence(xa, xb, hum_hz):
    """Magnitude-squared coherence of the two takes at 2 kHz, 4 s segments, at the hum and around it."""
    n = min(len(xa), len(xb))
    n -= n % CHUNK
    segments = (n*FS//RATE-4*FS)//(2*FS)+1
    if segments < 8:                  # a cut-short take: too few segments for coherence to mean anything
        return f'not worked out: only {max(segments, 0)} segments of 4 s in both takes'
    ya, yb = (StreamingDecimator(RATE, FS).process(v[:n]) for v in (xa, xb))
    f, c = signal.coherence(ya, yb, FS, nperseg=4*FS)
    k = int(np.argmin(np.abs(f-hum_hz)))
    around = (f >= 100) & (f <= 300) & (np.abs(f-hum_hz) > 5)
    return {'at_hum': float(c[k]), 'best_within_2_hz': float(c[np.abs(f-hum_hz) <= MATCH_HZ].max()),
            'median_100_300_hz_away_from_hum': float(np.median(c[around])), 'segments': int(segments)}


def guarded(fn, *args):
    """One part failing must not lose the rest: the takes are not stored, so there is no second try."""
    try:
        return fn(*args)
    except Exception as exc:
        return {'error': f'{type(exc).__name__}: {exc}'}


def one_microphone(x, hum_hz):
    r = {'rms_dbfs': db(np.mean(x**2)), 'peak_dbfs': float(20*np.log10(np.abs(x).max()+1e-12)),
         'exact_zero_share': float(np.mean(x == 0)), 'near_full_scale_share': float(np.mean(np.abs(x) >= .999))}
    f, level, excess, r['lines'] = lines(x)
    r['hum'] = hum_at(f, level, excess, hum_hz)
    r['every_3_s'] = guarded(every_3_s, x)
    r['detectors'] = guarded(detectors, x, hum_hz)
    r['predictability'] = guarded(predictability, x, hum_hz) if r['hum']['heard'] else 'not worked out: the hum is not heard here'
    return r


def analyse(xs):
    """xs = {'earbuds': array, 'laptop': array} at 48 kHz."""
    out = {}
    laptop = guarded(lambda x: hum_at(*lines(x)[:3]), xs['laptop'])
    out['rule_hum'] = laptop
    hum_hz = laptop.get('hz')
    if hum_hz is None:
        return {**out, 'note': 'could not find the hum frequency on the laptop microphone'}
    for label in ('earbuds', 'laptop'):
        out[label] = guarded(one_microphone, xs[label], hum_hz)
    out['coherence'] = guarded(coherence, xs['earbuds'], xs['laptop'], hum_hz)
    return out


def clean(v):
    """JSON-safe: numpy scalars to Python, NaN and infinity to null."""
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if isinstance(v, np.ndarray):
        return clean(v.tolist())
    if isinstance(v, np.generic):
        v = v.item()
    if isinstance(v, float) and not np.isfinite(v):
        return None
    return v


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--earbud-anc', choices=['off', 'on', 'not reported'], default='not reported',
                    help="the earbuds' own noise cancelling during the listen, as the user reported it")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(errors='replace')      # device names can hold characters the console lacks
    assert not OUT.exists(), 'Never overwrite a run'
    devices_all = sd.query_devices()
    inputs, _ = wasapi_devices(sd.query_hostapis(), devices_all)
    devices = {'earbuds': pick_microphone(inputs, 'earbuds'), 'laptop': pick_microphone(inputs, 'laptop')}
    started = datetime.now(timezone.utc).isoformat()
    takes = listen(devices, SECONDS)
    result = {'created_utc': started, 'kind': 'descriptive; one rule fixed before listening', 'seconds': SECONDS,
              'audio_stored': False, 'played_anything': False, 'earbud_anc_reported': args.earbud_anc,
              'rule': {'hum': 'strongest line 190-210 Hz on the laptop microphone', 'heard_if_above_floor_db': HEARS_DB,
                       'same_hum_within_hz': MATCH_HZ, 'floor': 'median of the dB spectrum over +-50 Hz, 0.25 Hz bins'},
              'devices': {label: {'name': name, 'index': index,
                                  'default_samplerate': devices_all[index]['default_samplerate'],
                                  'max_input_channels': devices_all[index]['max_input_channels']}
                          for label, (index, name) in devices.items()},
              'capture': {label: {'samples': t.filled, 'expected': SECONDS*RATE, 'callbacks': t.calls, 'channels_opened': t.channels,
                                  'open_errors': t.open_errors, 'stream_latency_s': t.latency_s,
                                  'status_flag_count': len(t.flags), 'status_flags_first': t.flags[:10]}
                          for label, t in takes.items()},
              'sounddevice': sd.__version__, 'portaudio': sd.get_portaudio_version()[1]}
    result.update(analyse({label: t.x[:t.filled].astype(float) for label, t in takes.items()}))
    del takes
    result['code_sha256'] = {p: h.sha(ROOT/p) for p in CODE}
    result['complete'] = True
    OUT.mkdir()
    h.write_new(OUT/'listen.json', clean(result))
    print('saved', OUT/'listen.json', flush=True)
    for label in ('earbuds', 'laptop'):
        r = result.get(label, {})
        if 'hum' in r:
            print(f"{label:8s} level {r['rms_dbfs']:.1f} dBFS | hum {r['hum']['hz']:.2f} Hz, {r['hum']['above_floor_db']:.1f} dB over floor,",
                  'heard' if r['hum']['heard'] else 'NOT heard', flush=True)
        else:
            print(label, r, flush=True)


if __name__ == '__main__':
    main()
