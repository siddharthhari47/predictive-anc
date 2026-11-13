"""A second tone detector for faint, slightly wobbly hums, such as a fan heard by a laptop mic.

The frozen detector (`tone_selection.line_test`) is a harmonic F-test: it asks
whether one window holds a phase-coherent sinusoid. A fan's hum that wanders by
about 2 Hz is not coherent over the window, so it fails that test even when it
stands well above the noise (results-faint-tones-02 measures this on Sid's
recording). This detector asks a different question: is there a narrow peak in
the averaged power spectrum, well above the local floor, that stays at the same
frequency for several seconds? Noise peaks and voices move or fade; a hum does
not, so the long hold requirement carries most of the protection.

`FaintSelector` has the same interface as `ToneSelector` (window, step,
reset, update, settings). `CombinedSelector` reports the frozen F-test tones
first and adds faint ones not already listed. Every decision uses past samples
only. Nothing here opens an audio device.
"""
from collections import deque

import numpy as np
from scipy import signal

from .antihum import FS, V2_SELECTOR
from .tone_selection import ToneSelector

# Frozen by results-faint-tones-01/protocol.json (rerun as -02) before its test cases were scored.
FAINT = {'window_seconds':4., 'segment_seconds':1., 'floor_hz':20., 'min_db':7., 'max_width_hz':6.,
         'history':24, 'acquire':20, 'release':8, 'associate_hz':2., 'update_seconds':.25,
         'band':(35., 350.), 'max_tones':3}


def faint_lines(segment, fs=FS, segment_seconds=1., floor_hz=20., min_db=7., max_width_hz=6.,
                band=(35., 350.), max_tones=3):
    """Narrow spectral peaks at least `min_db` above the local median floor, highest first.

    Each item is (frequency_hz, height_db). Welch average of Hann segments with
    half overlap; the floor is a running median of the log spectrum over
    +-floor_hz, so a peak a few hertz wide barely moves it.
    """
    segment = np.asarray(segment, float)
    n = round(segment_seconds*fs)
    if len(segment) < 2*n or float(np.std(segment)) <= 0 or not np.all(np.isfinite(segment)):
        return []
    f, p = signal.welch(segment, fs, nperseg=n, noverlap=n//2)
    level = 10*np.log10(np.maximum(p, 1e-30))
    df = float(f[1]-f[0])
    excess = level-signal.medfilt(level, 2*round(floor_hz/df)+1)
    inside = (f >= band[0]) & (f <= band[1])
    peaks, props = signal.find_peaks(np.where(inside, excess, -np.inf), height=min_db,
                                     distance=max(1, round(2/df)))
    if not len(peaks):
        return []
    lines = []
    for i in peaks:
        # Width where the peak stays within 3 dB of its top (half power).
        lo = hi = i
        while lo > 0 and level[lo-1] > level[i]-3:
            lo -= 1
        while hi < len(level)-1 and level[hi+1] > level[i]-3:
            hi += 1
        if (hi-lo+1)*df > max_width_hz:
            continue
        frequency = float(f[i])
        if 0 < i < len(f)-1:
            a, b, c = level[i-1], level[i], level[i+1]
            curvature = a-2*b+c
            if curvature < 0:
                frequency += float(.5*(a-c)/curvature)*df
        lines.append((frequency, float(excess[i])))
    return sorted(lines, key=lambda line: -line[1])[:max_tones]


class FaintSelector:
    """Long-hold tracking of `faint_lines`: a line must be found in `acquire` of the last `history` updates."""
    def __init__(self, fs=FS, window_seconds=4., segment_seconds=1., floor_hz=20., min_db=7., max_width_hz=6.,
                 history=24, acquire=20, release=8, associate_hz=2., update_seconds=.25, band=(35., 350.), max_tones=3):
        if not 1 <= acquire <= history:
            raise ValueError('Need 1 <= acquire <= history.')
        self.fs, self.window, self.step = fs, round(window_seconds*fs), round(update_seconds*fs)
        self.line_settings = {'segment_seconds':segment_seconds, 'floor_hz':floor_hz, 'min_db':min_db,
                              'max_width_hz':max_width_hz, 'band':band, 'max_tones':max_tones}
        self.history, self.acquire, self.release = history, acquire, release
        self.associate_hz, self.max_tones = associate_hz, max_tones
        self.reset()

    def settings(self):
        return {'window_seconds':self.window/self.fs, 'update_seconds':self.step/self.fs, 'history':self.history,
                'acquire':self.acquire, 'release':self.release, 'associate_hz':self.associate_hz,
                **{k:(list(v) if isinstance(v, tuple) else v) for k, v in self.line_settings.items()},
                'warm_up_seconds':(self.window+(self.acquire-1)*self.step)/self.fs}

    def reset(self):
        self._tracks = []

    def update(self, segment):
        segment = np.asarray(segment, float)
        lines = faint_lines(segment[-self.window:], self.fs, **self.line_settings) if len(segment) >= self.window else []
        used = set()
        for track in self._tracks:
            match = None
            for j, (frequency, height) in enumerate(lines):
                if j not in used and abs(frequency-track['freq']) <= self.associate_hz and (
                        match is None or height > lines[match][1]):
                    match = j
            track['hits'].append(match is not None)
            if match is not None:
                used.add(match)
                track['freq'], track['misses'] = lines[match][0], 0
            else:
                track['misses'] += 1
        for j, (frequency, _) in enumerate(lines):
            if j not in used:
                self._tracks.append({'freq':frequency, 'hits':deque([True], maxlen=self.history),
                                     'misses':0, 'active':False})
        for track in self._tracks:
            if not track['active'] and sum(track['hits']) >= self.acquire:
                track['active'] = True
            if track['active'] and track['misses'] >= self.release:
                track['active'] = False
        self._tracks = [t for t in self._tracks if t['active'] or any(t['hits'])]
        active = sorted((t['freq'], sum(t['hits'])/self.history) for t in self._tracks if t['active'])
        return active[:self.max_tones]


class CombinedSelector:
    """The frozen v2 F-test selector first, then faint tones it has not listed."""
    def __init__(self, fs=FS, faint=None):
        self.strict = ToneSelector(fs, **V2_SELECTOR)
        self.faint = FaintSelector(fs, **(FAINT if faint is None else faint))
        if self.strict.step != self.faint.step:
            raise ValueError('Both detectors must update together.')
        self.fs, self.step = fs, self.strict.step
        self.window = max(self.strict.window, self.faint.window)
        self.max_tones = self.strict.max_tones

    def settings(self):
        return {'strict':self.strict.settings(), 'faint':self.faint.settings()}

    def reset(self):
        self.strict.reset()
        self.faint.reset()

    def update(self, segment):
        segment = np.asarray(segment, float)
        strict = self.strict.update(segment)     # it reads only its own last window
        faint = self.faint.update(segment)
        # Strict tones keep their places; faint ones only fill free slots. (results-faint-tones-02
        # sorted the union by frequency and then cut it, which dropped a strict tone in one room.)
        merged = list(strict)[:self.max_tones]
        for frequency, confidence in faint:
            if len(merged) < self.max_tones and all(abs(frequency-f) > self.faint.associate_hz for f, _ in merged):
                merged.append((frequency, confidence))
        return merged
