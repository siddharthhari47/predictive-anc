"""results-fan-predictability-02: a fairer re-check of 01. Descriptive, no pass bar.

01's steady-tone control replaced everything inside the hum's +-5 Hz band,
the room noise under the hum included, so it was cleaner than any real room
and could not say why the hum itself predicts poorly. Here the control keeps
all of the room noise: a steady tone is added at a nearby frequency with no
hum of its own, as strong over its local noise as the hum's line is over its
own, and predicted exactly like the hum. The run also tries a four-times
longer predictor (0.8 s of history), picks predictor length and
regularization on a validation stretch inside the first half, and scores once
on the second half. It reports how much of the hum band is noise under the
line, which no predictor can remove. Reads audio into memory only, writes no
audio, opens no device.
"""
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'research-tools'))

import numpy as np
from scipy import signal

import fan_predictability as first
from anc_lab import selector_headroom as h
from anc_lab.antihum import FS, StreamingDecimator

OUT = ROOT/'results-fan-predictability-02'
HORIZONS_MS = first.HORIZONS_MS
DELAYS = np.array([round(ms*FS/1000) for ms in HORIZONS_MS])
ORDERS = (400, 1600)                  # 0.2 s and 0.8 s of past microphone samples
RIDGES = (1e-6, 1e-4, 1e-2, 1e-1)     # times the mean input power per tap
BAND = first.BAND_HZ
GAP = round(first.GAP_SECONDS*FS)
CHUNK = 4000


def spectrum(y):
    f, p = signal.welch(y, FS, nperseg=4*FS)
    level = 10*np.log10(np.maximum(p, 1e-30))
    floor = signal.medfilt(level, 2*round(20/(f[1]-f[0]))+1)
    return f, p, 10**(floor/10), level-floor


def band_power(f, p, floor, centre):
    """(power in the +-BAND window, the noise floor's share of it), from the Welch spectrum."""
    inside = np.abs(f-centre) <= BAND
    df = f[1]-f[0]
    return float(p[inside].sum()*df), float(floor[inside].sum()*df)


def clean_frequency(f, excess, f0):
    """A frequency 15-80 Hz from the hum whose +-8 Hz holds no line: smallest peak excess, nearer preferred."""
    candidates = f[(np.abs(f-f0) >= 15) & (np.abs(f-f0) <= 80) & (f >= 30)]
    worst = np.array([excess[np.abs(f-c) <= 8].max() for c in candidates])
    k = int(np.argmin(worst+.02*np.abs(candidates-f0)))
    return float(candidates[k]), float(worst[k])


def fit_and_score(y, target, order):
    """Ridge picked on validation inside the first half, refit on the whole first half, scored once on the second half."""
    n, half = len(y), len(y)//2
    win = np.lib.stride_tricks.sliding_window_view(y, order)
    train = np.arange(order-1, half-DELAYS.max())           # every training target lies in the first half
    split = train[(3*len(train))//4]
    rows = {'fit': train[train < split-GAP], 'val': train[train >= split], 'test': np.arange(half+GAP, n-DELAYS.max())}

    def sums(r_all):
        AtA, Atb, tt = np.zeros((order, order)), np.zeros((order, len(DELAYS))), np.zeros(len(DELAYS))
        for s in range(0, len(r_all), CHUNK):
            r = r_all[s:s+CHUNK]
            X, T = win[r-order+1], target[r[:, None]+DELAYS]
            AtA += X.T@X
            Atb += X.T@T
            tt += (T**2).sum(0)
        return AtA, Atb, tt
    fit, val, test = (sums(rows[k]) for k in ('fit', 'val', 'test'))

    def left_db(W, s):
        AtA, Atb, tt = s
        return 10*np.log10(np.maximum(tt-2*(W*Atb).sum(0)+(W*(AtA@W)).sum(0), 1e-30)/tt)
    scale = np.trace(fit[0])/order
    val_db = {c: left_db(np.linalg.solve(fit[0]+c*scale*np.eye(order), fit[1]), val) for c in RIDGES}
    pick = [min(RIDGES, key=lambda c: val_db[c][k]) for k in range(len(DELAYS))]
    AtA, Atb = fit[0]+val[0], fit[1]+val[1]
    scale = np.trace(AtA)/order
    W = np.stack([np.linalg.solve(AtA+c*scale*np.eye(order), Atb[:, k]) for k, c in enumerate(pick)], 1)
    return {'ridge': pick, 'validation_db': [float(val_db[c][k]) for k, c in enumerate(pick)],
            'test_db': [float(v) for v in left_db(W, test)]}


def line_only(test_db, noise_share):
    """Share of the line itself left over, if the noise under it stays in the error and the rest is line (approximate)."""
    left = 10**(np.array(test_db)/10)-noise_share
    return [float(10*np.log10(v/(1-noise_share))) if v > 0 else None for v in left]


def study(y, target, centre, f, p, floor):
    total, noise = band_power(f, p, floor, centre)
    runs = {order: fit_and_score(y, target, order) for order in ORDERS}
    chosen = [min(ORDERS, key=lambda o: runs[o]['validation_db'][k]) for k in range(len(DELAYS))]
    best = [runs[o]['test_db'][k] for k, o in enumerate(chosen)]
    return {'centre_hz': centre, 'noise_share_db': float(10*np.log10(noise/total)),
            'by_order': {str(o): r for o, r in runs.items()}, 'chosen_order': chosen,
            'leftover_db': dict(zip(HORIZONS_MS, best)),
            'line_only_leftover_db': dict(zip(HORIZONS_MS, line_only(best, noise/total)))}


def main():
    assert not OUT.exists(), 'Never overwrite a run'
    OUT.mkdir()
    rows = []
    for name, path in first.SOURCES.items():
        x = first.load(path)
        y = StreamingDecimator(first.RATE, FS).process(x[:len(x)-len(x) % 480])
        f, p, floor, excess = spectrum(y)
        f0, _, _ = first.line_of(y)
        total, noise = band_power(f, p, floor, f0)
        c, c_excess = clean_frequency(f, excess, f0)
        _, noise_c = band_power(f, p, floor, c)
        amplitude = np.sqrt(2*max(total-noise, 0.)*noise_c/noise)   # same line-over-noise as the hum
        control = y+amplitude*np.sin(2*np.pi*c*np.arange(len(y))/FS+1.)
        hum = study(y, signal.sosfiltfilt(signal.butter(4, [f0-BAND, f0+BAND], 'bandpass', fs=FS, output='sos'), y), f0, f, p, floor)
        fc, pc, floorc, _ = spectrum(control)
        steady = study(control, signal.sosfiltfilt(signal.butter(4, [c-BAND, c+BAND], 'bandpass', fs=FS, output='sos'), control),
                       c, fc, pc, floorc)
        rows.append({'recording': name, 'line_hz': f0, 'line_over_band_noise_db': float(10*np.log10((total-noise)/noise)),
                     'control_hz': c, 'control_site_peak_excess_db': c_excess, 'hum': hum, 'steady_control': steady})
        print(name, f'line {f0:.2f} Hz, line over band noise {rows[-1]["line_over_band_noise_db"]:.1f} dB, control at {c:.2f} Hz', flush=True)
        for label, r in (('hum', hum), ('steady', steady)):
            print(f'  {label:6s} noise share {r["noise_share_db"]:.1f} dB | left', {ms: round(v, 1) for ms, v in r['leftover_db'].items()},
                  '| line only', {ms: (None if v is None else round(v, 1)) for ms, v in r['line_only_leftover_db'].items()},
                  '| orders', r['chosen_order'], flush=True)
    result = {'created_utc': datetime.now(timezone.utc).isoformat(), 'kind': 'descriptive, no pass bar', 'checks': 'results-fan-predictability-01',
              'method': {'orders_samples': ORDERS, 'ridges_times_mean_power': RIDGES, 'analysis_rate': FS, 'band_hz': BAND,
                         'train': 'first half (fit = first three quarters, 1 s gap, validation = last quarter)',
                         'test': 'second half after a 1 s gap, scored once with the validation-chosen ridge and order',
                         'control': 'steady tone added at a nearby frequency with no line, same line-over-band-noise as the hum; all room noise kept'},
              'recordings': rows, 'complete': True, 'code_sha256': h.sha(Path(__file__))}
    h.write_new(OUT/'results.json', result)
    print('done', flush=True)


if __name__ == '__main__':
    main()
