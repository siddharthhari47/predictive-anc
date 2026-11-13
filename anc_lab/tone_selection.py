"""Causal automatic tone count/confidence selection and a forecast mute gate.

Every decision at sample t uses x[:t+1] only. The selector replaces nothing:
`predictors.estimate_tones` (fixed top-three peaks) is kept unchanged for the
earlier benchmarks and serves as a comparator here.

Detector: Thomson multitaper harmonic F-test on a sliding window. Under the
no-line hypothesis F ~ F(2, 2K-2) at each frequency, so the threshold is a
stated false-alarm level, Bonferroni-corrected for the number of independent
frequencies in the band, not a tuned peak height. A line becomes active only
after it passes repeatedly, and is released after repeated misses.

Gate: a controller-side check that compares the predictor's already-matured
forecasts with zero output. It mutes when recent realized gain is too low.
The predictor (shadow forecast) and the gate stay separate objects.
"""
from collections import deque
import time

import numpy as np
from scipy import signal, stats

from .predictors import ToneTracker


def line_test(segment, fs, nw=4., band=(35., 350.), alpha=1e-3, max_tones=6, nfft_factor=8):
    """Return significant lines in one window, strongest F first.

    Each item is (frequency_hz, f_statistic, complex_amplitude). Spacing between
    reported lines exceeds the taper half-bandwidth W = nw/T; closer tones are
    not resolved by this window and are reported as one line.
    """
    segment = np.asarray(segment, float)
    n = len(segment)
    if n < 64 or float(np.std(segment)) <= 0 or not np.all(np.isfinite(segment)):
        return []
    k = int(round(2*nw))-1
    tapers = signal.windows.dpss(n, nw, Kmax=k)
    nfft = int(2**np.ceil(np.log2(nfft_factor*n)))
    spectra = np.fft.rfft(tapers*(segment-np.mean(segment)), nfft)
    freqs = np.fft.rfftfreq(nfft, 1/fs)
    keep = (freqs >= band[0]) & (freqs <= band[1])
    freqs, spectra = freqs[keep], spectra[:, keep]
    u0 = tapers.sum(axis=1)
    u0_power = float(u0@u0)
    mean = (u0@spectra)/u0_power
    residual = np.sum(np.abs(spectra-np.outer(u0, mean))**2, axis=0)
    floor = 1e-12*max(float(np.max(residual)), 1e-300)
    f_stat = (k-1)*np.abs(mean)**2*u0_power/np.maximum(residual, floor)
    independent = max(1., (band[1]-band[0])*n/fs)
    critical = float(stats.f.isf(alpha/independent, 2, 2*k-2))
    peaks, _ = signal.find_peaks(f_stat, height=critical)
    half_bandwidth = nw*fs/n
    chosen = []
    for i in sorted(peaks, key=lambda i: f_stat[i], reverse=True):
        frequency = float(freqs[i])
        if 0 < i < len(freqs)-1:
            a, b, c = f_stat[i-1], f_stat[i], f_stat[i+1]
            curvature = a-2*b+c
            if curvature < 0:
                frequency += float(.5*(a-c)/curvature)*float(freqs[1]-freqs[0])
        if all(abs(frequency-other[0]) > half_bandwidth for other in chosen):
            chosen.append((frequency, float(f_stat[i]), complex(mean[i])))
        if len(chosen) == max_tones:
            break
    return chosen


class ToneSelector:
    """Online tone count/confidence with acquire/release hysteresis.

    `timeline(x, end)` returns decisions at update times update, 2*update, ...
    Each decision depends only on samples up to that time. Warm-up is one
    analysis window plus `acquire` passing updates.
    """
    def __init__(self, fs, window_seconds=1., nw=4., alpha=1e-3, acquire=2, history=3,
                 release=2, associate_hz=2., update_seconds=.25, band=(35., 350.), max_tones=6):
        if not 1 <= acquire <= history:
            raise ValueError('Need 1 <= acquire <= history.')
        self.fs, self.window = fs, round(window_seconds*fs)
        self.nw, self.alpha, self.acquire, self.history = nw, alpha, acquire, history
        self.release, self.associate_hz, self.band, self.max_tones = release, associate_hz, band, max_tones
        self.step = round(update_seconds*fs)

    def settings(self):
        return {'window_seconds':self.window/self.fs, 'nw':self.nw, 'alpha_family':self.alpha,
                'acquire':self.acquire, 'history':self.history, 'release':self.release,
                'associate_hz':self.associate_hz, 'update_seconds':self.step/self.fs,
                'band_hz':list(self.band), 'max_tones':self.max_tones,
                'warm_up_seconds':(self.window+(self.acquire-1)*self.step)/self.fs}

    def reset(self):
        """Forget all tracks (timeline() calls this; a streaming user calls it once)."""
        self._tracks = []

    def update(self, segment):
        """One causal update from the latest analysis window; returns the active tone set.

        `segment` is the most recent `window` samples. A shorter segment (warm-up)
        counts as an update with no detected lines. Used directly by streaming code.
        """
        if not hasattr(self, '_tracks'):
            self.reset()
        segment = np.asarray(segment, float)
        lines = line_test(segment[-self.window:], self.fs, self.nw, self.band,
                          self.alpha, self.max_tones) if len(segment) >= self.window else []
        tracks, used = self._tracks, set()
        for track in tracks:
            match = None
            for j, line in enumerate(lines):
                if j not in used and abs(line[0]-track['freq']) <= self.associate_hz and (
                        match is None or line[1] > lines[match][1]):
                    match = j
            track['hits'].append(match is not None)
            if match is not None:
                used.add(match)
                track['freq'], track['misses'] = lines[match][0], 0
            else:
                track['misses'] += 1
        for j, line in enumerate(lines):
            if j not in used:
                tracks.append({'freq':line[0], 'hits':deque([True], maxlen=self.history),
                               'misses':0, 'active':False})
        for track in tracks:
            if not track['active'] and sum(track['hits']) >= self.acquire:
                track['active'] = True
            if track['active'] and track['misses'] >= self.release:
                track['active'] = False
        self._tracks = [tr for tr in tracks if tr['active'] or any(tr['hits'])]
        active = sorted((tr['freq'], sum(tr['hits'])/self.history) for tr in self._tracks if tr['active'])
        return active[:self.max_tones]

    def timeline(self, x, end=None):
        """List of (t, active) for update times t < end; active = [(freq, confidence)]."""
        x = np.asarray(x, float)
        end = len(x) if end is None else min(int(end), len(x))
        self.reset()
        decisions, seconds = [], []
        for t in range(self.step-1, end, self.step):
            started = time.perf_counter()
            active = self.update(x[max(0, t-self.window+1):t+1])
            decisions.append((t, active))
            seconds.append(time.perf_counter()-started)
        self.update_seconds_measured = seconds
        return decisions


def active_at(decisions, t):
    """Most recent decision made at or before sample t (empty before the first)."""
    times = [d[0] for d in decisions]
    i = np.searchsorted(times, t, side='right')-1
    return decisions[i][1] if i >= 0 else []


def recent_amplitude(x, t, frequency, samples, fs):
    """Least-squares sinusoid amplitude at a known frequency over x[t-samples+1:t+1]."""
    observed = x[max(0, t-samples+1):t+1]
    tau = np.arange(1-len(observed), 1)/fs
    angle = 2*np.pi*frequency*tau
    design = np.column_stack([np.sin(angle), np.cos(angle), np.ones(len(tau))])
    coef = np.linalg.lstsq(design, observed, rcond=None)[0]
    return float(np.hypot(coef[0], coef[1]))


class SelectedToneForecaster:
    """Shadow forecaster: tone tracker on the selector's current tone set, else zero.

    Optional fast release (release_ratio not None): at every origin, a tone whose
    amplitude over the latest release_window_seconds has fallen below
    release_ratio times its amplitude over the tracker window is dropped from
    that origin's forecast. Both amplitudes use samples up to the origin only.
    Default (None) reproduces the first study exactly.
    """
    def __init__(self, fs, selector, window_seconds=.6, release_ratio=None, release_window_seconds=.1):
        self.fs, self.selector, self.window_seconds = fs, selector, window_seconds
        self.release_ratio, self.release_window_seconds = release_ratio, release_window_seconds

    def settings(self):
        return {'tracker_window_seconds':self.window_seconds, 'release_ratio':self.release_ratio,
                'release_window_seconds':self.release_window_seconds if self.release_ratio is not None else None}

    def predict(self, x, origins, horizons, decisions=None):
        origins = np.asarray(origins)
        if decisions is None:
            decisions = self.selector.timeline(x, int(np.max(origins))+1)
        out = np.zeros((len(origins), len(horizons)))
        self.tone_counts, self.fast_drops, started = [], 0, time.perf_counter()
        long_samples = round(self.window_seconds*self.fs)
        short_samples = round(self.release_window_seconds*self.fs)
        for row, t in enumerate(origins):
            freqs = [f for f, _ in active_at(decisions, t)]
            if freqs and self.release_ratio is not None:
                kept = [f for f in freqs if recent_amplitude(x, t, f, short_samples, self.fs)
                        >= self.release_ratio*recent_amplitude(x, t, f, long_samples, self.fs)]
                self.fast_drops += len(freqs)-len(kept)
                freqs = kept
            self.tone_counts.append(len(freqs))
            if freqs:
                tracker = ToneTracker(self.fs, freqs, self.window_seconds)
                out[row] = tracker.predict(x, [t], horizons)[0]
        self.predict_seconds_per_origin = (time.perf_counter()-started)/max(len(origins), 1)
        self.decisions = decisions
        return out


def realized_gate(x, origins, forecast, horizon_groups, min_gain_db=0., lookback=25, min_matured=10,
                  shared_group=None):
    """Mute decision per origin and horizon group from already-matured forecasts.

    At origin t a past forecast made at s is usable only when s+max(group) <= t.
    With shared_group=g, every group is gated by group g's realized error (the
    shortest horizon matures first, so it reacts soonest). Default None gates
    each group on its own errors, as in the first study.
    Returns a boolean array (origins x groups), True = output enabled.
    """
    origins = np.asarray(origins)
    enabled = np.zeros((len(origins), len(horizon_groups)), bool)
    sources = range(len(horizon_groups)) if shared_group is None else [shared_group]
    decided = {}
    for g in sources:
        columns, horizons = horizon_groups[g]
        horizons = np.asarray(horizons)
        targets = x[origins[:, None]+horizons]
        error = np.sum((targets-forecast[:, columns])**2, axis=1)
        reference = np.sum(targets**2, axis=1)
        matured_until = origins+int(np.max(horizons))
        result = np.zeros(len(origins), bool)
        for row, t in enumerate(origins):
            usable = np.nonzero(matured_until[:row] <= t)[0][-lookback:]
            if len(usable) < min_matured:
                continue
            gain = 10*np.log10(max(reference[usable].sum(), 1e-30)/max(error[usable].sum(), 1e-30))
            result[row] = gain >= min_gain_db
        decided[g] = result
    for g in range(len(horizon_groups)):
        enabled[:, g] = decided[g if shared_group is None else shared_group]
    return enabled
