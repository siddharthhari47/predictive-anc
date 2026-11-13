"""Real-tone forecasters for the anti-hum engine: per-tone memory chosen from realized error.

Every forecaster here is block-causal. Samples arrive in blocks; at the end of
each block (an "origin") the forecaster may use samples up to that origin only.
Nothing here opens an audio device.

ToneObserverBank, the main candidate
------------------------------------
v2 fits each tone over a fixed 0.3 s window. Real hum tones differ: some are
steady for seconds and drown in broadband noise (a long memory averages the
noise away), others wander in phase and amplitude within a tenth of a second
(only a short memory keeps up). One window cannot suit both.

The bank keeps, for every tone, several phasor trackers with different memories
(time constants from 25 ms to 1.6 s) and lets each tone's own recent record pick
one:

1. Tones come from the frozen v2 selector (optionally also from a looser
   candidate finder, `ProminentLines`).
2. Each memory is a resonator observer, the steady-state form of a Kalman
   tracker for a randomly wandering phasor: every sample, the error between
   the microphone and the sum of all tracked tones nudges each tone's phasor,
   by an amount that sets its memory. A slow frequency loop per tracker keeps
   its frequency on the tone.
3. Every forecast is checked when its target time has passed. Per tone, the
   error near that tone (about +-1.5 Hz, by demodulation and a two-pole
   low-pass) is averaged over about a second for each memory and for "no
   forecast". The tone uses the memory with the lowest error, and is switched
   off when no memory beats "no forecast".
4. The v2 fast release (amplitude halved within 0.1 s) still drops a tone at
   once; the v2 realized-error gate is applied on top, outside this class.

OnlineRidgeAR is a comparator: the same ridge AR as the prefix comparator, but
refitted every second on the latest past samples. It forecasts the whole
waveform, not separate tones, so it cannot drive tune-by-ear.
"""
from collections import deque
import time

import numpy as np
from scipy import ndimage, signal
from sklearn.linear_model import Ridge

from .antihum import V2_RELEASE, V2_SELECTOR
from .predictors import lag_matrix
from .tone_selection import ToneSelector, recent_amplitude

FS, BLOCK = 2000, 20
TAUS = (.025, .05, .1, .2, .4, .8, 1.6)


def phasor_at(x, frequencies, fs=FS):
    """Least-squares phasors (tau = 0 at the last sample) of tones at known frequencies, jointly, plus dc."""
    tau = np.arange(1-len(x), 1)/fs
    angle = 2*np.pi*tau[:, None]*np.asarray(frequencies, float)
    design = np.column_stack([np.sin(angle), np.cos(angle), np.ones(len(tau))])
    coef = np.linalg.lstsq(design, x, rcond=None)[0]
    k = len(frequencies)
    return coef[k:2*k]-1j*coef[:k]


class ProminentLines:
    """Causal candidate lines: Welch spectrum of the latest window, peaks standing
    `prominence_db` above the median of the surrounding +-10 Hz, with acquire/release
    hysteresis. Looser than the selector's F-test: it also passes lines whose amplitude
    or phase wanders within a second. Candidates only; the bank decides whether to use them."""
    def __init__(self, fs=FS, window_seconds=4., segment_seconds=1., prominence_db=10., update_seconds=.5,
                 acquire=2, history=3, release=2, band=(35., 350.), max_lines=6, associate_hz=2., min_spacing_hz=3.):
        self.fs, self.window, self.segment = fs, round(window_seconds*fs), round(segment_seconds*fs)
        self.prominence_db, self.step = prominence_db, round(update_seconds*fs)
        self.acquire, self.history, self.release = acquire, history, release
        self.band, self.max_lines, self.associate_hz, self.min_spacing_hz = band, max_lines, associate_hz, min_spacing_hz
        self.tracks = []

    def settings(self):
        return {'window_seconds':self.window/self.fs, 'segment_seconds':self.segment/self.fs,
                'prominence_db':self.prominence_db, 'update_seconds':self.step/self.fs, 'acquire':self.acquire,
                'history':self.history, 'release':self.release, 'band_hz':list(self.band), 'max_lines':self.max_lines}

    def lines(self, segment):
        if len(segment) < self.window:
            return []
        f, p = signal.welch(segment[-self.window:], self.fs, nperseg=self.segment, nfft=4*self.segment)
        level = 10*np.log10(np.maximum(p, 1e-30))
        half = max(1, round(10/(f[1]-f[0])))
        # Running median over +-10 Hz with edge padding; same values as a sliding-window median, ~30x faster.
        local = ndimage.median_filter(level, size=2*half+1, mode='nearest')
        peaks, _ = signal.find_peaks(level)
        keep = sorted((i for i in peaks if self.band[0] <= f[i] <= self.band[1]
                       and level[i]-local[i] >= self.prominence_db), key=lambda i: -p[i])
        chosen = []
        for i in keep:
            freq = float(f[i])
            if 0 < i < len(f)-1:
                a, b, c = level[i-1], level[i], level[i+1]
                if a-2*b+c < 0:
                    freq += float(.5*(a-c)/(a-2*b+c))*float(f[1]-f[0])
            if all(abs(freq-o) > self.min_spacing_hz for o in chosen):
                chosen.append(freq)
            if len(chosen) == self.max_lines:
                break
        return chosen

    def update(self, segment):
        found, used = self.lines(np.asarray(segment, float)), set()
        for track in self.tracks:
            near = [j for j, f in enumerate(found) if j not in used and abs(f-track['freq']) <= self.associate_hz]
            match = min(near, key=lambda j: abs(found[j]-track['freq'])) if near else None
            track['hits'].append(match is not None)
            if match is None:
                track['misses'] += 1
            else:
                used.add(match)
                track['freq'], track['misses'] = found[match], 0
        for j, f in enumerate(found):
            if j not in used:
                self.tracks.append({'freq':f, 'hits':deque([True], maxlen=self.history), 'misses':0, 'active':False})
        for track in self.tracks:
            if not track['active'] and sum(track['hits']) >= self.acquire:
                track['active'] = True
            if track['active'] and track['misses'] >= self.release:
                track['active'] = False
        self.tracks = [t for t in self.tracks if t['active'] or any(t['hits'])]
        return sorted(t['freq'] for t in self.tracks if t['active'])


class ToneObserverBank:
    """Per-tone phasor trackers with several memories; each tone's realized error picks one.

    push(samples) adds analysis-rate samples; every `block` samples is an origin.
    After a push that ends on an origin, components() / forecast(horizons) describe
    the forecast made at that origin (tau = 0 at the newest sample).
    """
    def __init__(self, fs=FS, block=BLOCK, selector=None, taus=TAUS, default_tau=.1, freq_loop=4.,
                 check_delay_ms=20., nb_tau=.1, power_tau=1., warmup_seconds=.3, off_margin_db=0.,
                 release=V2_RELEASE, release_long_seconds=.3, candidates=None, max_tones=8,
                 associate_hz=2., recenter_hz=1., keep_seconds=None):
        self.fs, self.block = fs, block
        self.selector = selector or ToneSelector(fs, **V2_SELECTOR)
        self.selector.reset()
        self.candidates = candidates
        self.taus = np.asarray(taus, float)
        self.n = len(self.taus)
        self.gain = 2/(self.taus*fs)                       # observer memory: time constant tau
        self.loop = block/(freq_loop*self.taus*fs)         # frequency loop: time constant freq_loop*tau
        self.default = int(np.argmin(np.abs(self.taus-default_tau)))
        self.check = round(check_delay_ms*fs/1000)+np.arange(1, block+1)
        # nb_tau = 0: no extra low-pass, so the check spans the block average's ~+-44 Hz around each tone.
        self.nb_tau = nb_tau
        self.lp, self.pw = (np.exp(-block/(nb_tau*fs)) if nb_tau > 0 else 0.), np.exp(-block/(power_tau*fs))
        self.min_checks = max(1, round(warmup_seconds*fs/block))
        self.off_ratio = 10**(-off_margin_db/10)
        self.release, self.release_long = release, round(release_long_seconds*fs)
        self.release_short = round(release['seconds']*fs) if release else 0
        self.max_tones, self.associate_hz, self.recenter_hz = max_tones, associate_hz, recenter_hz
        windows = [self.selector.window, self.release_long, round(.3*fs)]
        if candidates is not None:
            windows.append(candidates.window)
        self.keep = round(keep_seconds*fs) if keep_seconds else max(windows)+2*block+int(self.check[-1])
        self.history = np.zeros(0)
        self.seen = 0
        self.next_update = self.selector.step
        self.next_candidates = candidates.step if candidates is not None else None
        self.selected, self.extra = [], []
        # Per tone (columns): anchor frequency (Hz), source, per-memory angular frequency and phasor prior.
        self.anchor = np.zeros(0)
        self.from_selector = np.zeros(0, bool)
        self.omega = np.zeros((self.n, 0))
        self.c = np.zeros((self.n, 0), complex)            # prior for the next sample: tone value = Re(c)
        self.p_prev = np.zeros((self.n, 0), complex)
        self.z1 = np.zeros((self.n+1, 0), complex)          # rows: memories, then "no forecast"
        self.z2 = np.zeros((self.n+1, 0), complex)
        self.power = np.zeros((self.n+1, 0))
        self.checks = np.zeros(0, int)
        self.choice = np.zeros(0, int)                       # memory index, or -1 = off
        self.pending = deque()
        self.components_now = []
        self.counters = {'origins':0, 'origins_with_output':0, 'fast_drops':0, 'tones_off_by_check':0,
                         'choice_histogram':[0]*(self.n+1)}
        self.timing = {'observe':0., 'origin':0., 'selector':0., 'candidates':0.}

    def settings(self):
        return {'taus_seconds':self.taus.tolist(), 'default_tau_seconds':float(self.taus[self.default]),
                'frequency_loop_multiple':float(self.block/(self.loop[0]*self.taus[0]*self.fs)),
                'check_horizons':[int(self.check[0]), int(self.check[-1])],
                'check_lowpass_seconds':float(self.nb_tau),
                'error_average_seconds':float(-self.block/self.fs/np.log(self.pw)),
                'warmup_checks':self.min_checks, 'off_margin_db':float(-10*np.log10(self.off_ratio)),
                'release':self.release, 'release_long_seconds':self.release_long/self.fs,
                'candidates':self.candidates.settings() if self.candidates is not None else None,
                'selector':self.selector.settings(), 'max_tones':self.max_tones}

    # ---- input ----
    def push(self, samples):
        samples = np.asarray(samples, float)
        start = 0
        while start < len(samples):
            room = self.block-self.seen % self.block
            part = samples[start:start+room]
            self._observe(part)
            self.history = np.concatenate([self.history, part])[-self.keep:]
            self.seen += len(part)
            start += len(part)
            if self.seen % self.block == 0:
                self._origin()

    def _observe(self, part):
        started = time.perf_counter()
        if self.c.shape[1]:
            rot = np.exp(1j*self.omega)
            g = self.gain[:, None]
            c = self.c
            for v in part:
                c = (c+g*(v-c.real.sum(axis=1))[:, None])*rot
            self.c = c
        self.timing['observe'] += time.perf_counter()-started

    def _window(self, end_seen, length):
        """Samples received up to `end_seen` (a count), at most `length` of them."""
        end = len(self.history)-(self.seen-end_seen)
        return self.history[max(0, end-length):end]

    # ---- per origin ----
    def _origin(self):
        started = time.perf_counter()
        changed = False
        while self.next_update <= self.seen:
            t0 = time.perf_counter()
            self.selected = [f for f, _ in self.selector.update(self._window(self.next_update, self.selector.window))]
            self.timing['selector'] += time.perf_counter()-t0
            self.next_update += self.selector.step
            changed = True
        if self.candidates is not None:
            while self.next_candidates <= self.seen:
                t0 = time.perf_counter()
                self.extra = self.candidates.update(self._window(self.next_candidates, self.candidates.window))
                self.timing['candidates'] += time.perf_counter()-t0
                self.next_candidates += self.candidates.step
                changed = True
        if changed:
            self._reconcile()
        self._frequency_loop()
        self._mature()
        self._choose()
        self.counters['origins'] += 1
        self.counters['origins_with_output'] += int(bool(self.components_now))
        self.timing['origin'] += time.perf_counter()-started

    def _reconcile(self):
        """Match the wanted tone set to tracked tones (within associate_hz); start new trackers from a 0.3 s fit."""
        wanted = [(f, True) for f in self.selected]
        for f in self.extra:
            if all(abs(f-w) > self.associate_hz for w, _ in wanted):
                wanted.append((f, False))
        wanted = wanted[:self.max_tones]
        keep, used = [], set()
        for f, sel in wanted:
            near = [k for k in range(len(self.anchor)) if k not in used and abs(self.anchor[k]-f) <= self.associate_hz]
            k = min(near, key=lambda k: abs(self.anchor[k]-f)) if near else None
            if k is not None:
                used.add(k)
            keep.append((f, sel, k))
        cols = [k for _, _, k in keep if k is not None]
        new = [(f, sel) for f, sel, k in keep if k is None]
        order = cols+[None]*len(new)
        anchor = np.array([f for f, _, k in keep if k is not None]+[f for f, _ in new])
        from_sel = np.array([s for _, s, k in keep if k is not None]+[s for _, s in new], bool)

        def take(a, fill):
            parts = [a[..., k] if k is not None else np.full(a.shape[:-1], fill, a.dtype) for k in order]
            return np.stack(parts, axis=-1) if parts else np.zeros(a.shape[:-1]+(0,), a.dtype)

        omega, c, p_prev = take(self.omega, 0.), take(self.c, 0j), take(self.p_prev, 0j)
        z1, z2, power, checks = take(self.z1, 0j), take(self.z2, 0j), take(self.power, 0.), take(self.checks, 0)
        if new:
            j0 = len(cols)
            freqs = anchor[j0:]
            p0 = phasor_at(self._window(self.seen, round(.3*self.fs)), freqs, self.fs)
            w = 2*np.pi*freqs/self.fs
            omega[:, j0:] = w
            c[:, j0:] = p0*np.exp(1j*w)                  # prior for the next sample
            p_prev[:, j0:] = 0
        # Re-seat any memory whose frequency wandered more than recenter_hz from the anchor.
        far = np.abs(omega*self.fs/(2*np.pi)-anchor) > self.recenter_hz
        omega[far] = np.broadcast_to(2*np.pi*anchor/self.fs, omega.shape)[far]
        self.anchor, self.from_selector, self.omega, self.c, self.p_prev = anchor, from_sel, omega, c, p_prev
        self.z1, self.z2, self.power, self.checks = z1, z2, power, checks

    def _frequency_loop(self):
        """Nudge each memory's frequency by the rotation its phasor showed since the last origin."""
        if not self.c.shape[1]:
            return
        p = self.c*np.exp(-1j*self.omega)                  # posterior at the origin sample
        ok = (np.abs(p) > 0) & (np.abs(self.p_prev) > 0)
        turn = np.angle(p*np.conj(self.p_prev*np.exp(1j*self.omega*self.block)))
        self.omega = self.omega+np.where(ok, self.loop[:, None]*turn/self.block, 0.)
        self.p_prev = p

    def _mature(self):
        """Realized error near each tone, per memory and for no forecast, from forecasts whose targets are in."""
        last = int(self.check[-1])
        while self.pending and self.pending[0][0]+last <= self.seen-1:
            origin, member_forecasts = self.pending.popleft()
            target = self.history[len(self.history)-(self.seen-1-origin)-1+self.check]
            if not len(self.anchor):
                continue
            errors = np.vstack([target-member_forecasts, target])          # (n+1, block)
            t = origin+self.check
            demod = np.exp(-2j*np.pi*np.outer(t, self.anchor)/self.fs)     # (block, tones)
            d = errors@demod/self.block
            self.z1 = self.lp*self.z1+(1-self.lp)*d
            self.z2 = self.lp*self.z2+(1-self.lp)*self.z1
            fresh = self.checks == 0
            level = np.abs(self.z2)**2
            self.power = np.where(fresh, level, self.pw*self.power+(1-self.pw)*level)
            self.checks += 1

    def _choose(self):
        k = len(self.anchor)
        p = self.c*np.exp(-1j*self.omega)
        choice = np.full(k, -1)
        for j in range(k):
            if self.checks[j] < self.min_checks:
                choice[j] = self.default if self.from_selector[j] else -1
            else:
                best = int(np.argmin(self.power[:self.n, j]))
                if self.power[best, j] <= self.off_ratio*self.power[self.n, j]:
                    choice[j] = best
                else:
                    self.counters['tones_off_by_check'] += 1
        if self.release and k:
            past = self.history
            for j in np.nonzero(choice >= 0)[0]:
                f = self.anchor[j]
                if recent_amplitude(past, len(past)-1, f, self.release_short, self.fs) < \
                        self.release['ratio']*recent_amplitude(past, len(past)-1, f, self.release_long, self.fs):
                    choice[j] = -1
                    self.counters['fast_drops'] += 1
        for j in range(k):
            self.counters['choice_histogram'][choice[j] if choice[j] >= 0 else self.n] += 1
        self.choice = choice
        self.components_now = [(float(self.omega[b, j]*self.fs/(2*np.pi)), complex(p[b, j]))
                               for j, b in enumerate(choice) if b >= 0]
        # Every memory's full forecast at the check horizons, to be scored when the targets arrive.
        if k:
            rot = np.exp(1j*self.omega[:, :, None]*self.check)                # (n, k, block)
            members = np.real(np.sum(p[:, :, None]*rot, axis=1))
        else:
            members = np.zeros((self.n, self.block))
        self.pending.append((self.seen-1, members))

    # ---- output ----
    def components(self):
        """[(frequency Hz, complex phasor at the origin sample)] for the tones forecast now."""
        return list(self.components_now)

    def forecast(self, horizons):
        h = np.asarray(horizons, float)
        out = np.zeros(len(h))
        for f, p in self.components_now:
            out += np.real(p*np.exp(2j*np.pi*f*h/self.fs))
        return out

    def state(self):
        return {'anchors_hz':self.anchor.tolist(), 'from_selector':self.from_selector.tolist(),
                'choice_tau_seconds':[float(self.taus[b]) if b >= 0 else None for b in self.choice],
                'counters':self.counters}


def stream_forecasts(forecaster, x, grid, horizons):
    """Feed x in blocks from the start; return the forecast made at each grid origin (rows x horizons).

    Origin t = forecast made after receiving x[:t+1]. Grid origins must be one
    block apart (or a multiple); the stream starts at sample (grid[0]+1) % block,
    so that block ends fall on the origins (the forecaster ignores at most
    block-1 leading samples)."""
    grid = np.asarray(grid)
    block = forecaster.block
    start = int(grid[0]+1) % block
    if np.any((grid+1-start) % block):
        raise ValueError('Grid origins must be whole blocks apart.')
    out = np.zeros((len(grid), len(horizons)))
    rows = {int(t):i for i, t in enumerate(grid)}
    started, durations, selector = time.perf_counter(), [], []
    timing = getattr(forecaster, 'timing', {})
    for end in range(start+block, int(grid[-1])+2, block):
        t0, s0 = time.perf_counter(), timing.get('selector', 0.)
        forecaster.push(x[end-block:end])
        durations.append(time.perf_counter()-t0)
        selector.append(timing.get('selector', 0.)-s0)
        row = rows.get(end-1)
        if row is not None:
            out[row] = forecaster.forecast(horizons)
    forecaster.stream_seconds = time.perf_counter()-started
    # One push = one block of input. The selector update (every 0.25 s) is the same work v2 does;
    # block_seconds_own excludes it, so it is the cost this forecaster adds.
    forecaster.block_seconds = np.asarray(durations)
    forecaster.block_seconds_own = forecaster.block_seconds-np.asarray(selector)
    return out


class OnlineRidgeAR:
    """Ridge AR (128 lags, as the prefix comparator) refitted every `refit_seconds` on the latest
    `train_seconds` of past samples. A forecast at origin t uses the latest model whose last
    training target is at or before t. Whole-waveform forecast; no per-tone output."""
    def __init__(self, fs, horizons, lags=128, train_seconds=20., refit_seconds=1., min_train_seconds=2.,
                 alpha=3., stride=2):
        self.fs, self.horizons, self.lags = fs, np.asarray(horizons), lags
        self.train, self.refit, self.min_train = round(train_seconds*fs), round(refit_seconds*fs), round(min_train_seconds*fs)
        self.alpha, self.stride = alpha, stride

    def settings(self):
        return {'lags':self.lags, 'train_seconds':self.train/self.fs, 'refit_seconds':self.refit/self.fs,
                'min_train_seconds':self.min_train/self.fs, 'ridge_alpha':self.alpha, 'stride':self.stride}

    def _fit(self, x, until):
        """Model from targets x[s+h] <= x[until-1] only."""
        hmax = int(np.max(self.horizons))
        last = until-1-hmax
        first = max(self.lags-1, until-self.train)
        if last-first < self.min_train-hmax:
            return None
        origins = np.arange(first, last+1, self.stride)
        mean, scale = float(np.mean(x[first-self.lags+1:until])), max(float(np.std(x[first-self.lags+1:until])), 1e-8)
        X = (lag_matrix(x, origins, self.lags)-mean)/scale
        Y = (x[origins[:, None]+self.horizons]-mean)/scale
        return Ridge(alpha=self.alpha).fit(X, Y), mean, scale

    def predict(self, x, origins, horizons):
        columns = np.searchsorted(self.horizons, horizons)
        origins = np.asarray(origins)
        out = np.zeros((len(origins), len(horizons)))
        started, fits = time.perf_counter(), 0
        model, model_until = None, -1
        for row, t in enumerate(origins):
            until = (int(t+1)//self.refit)*self.refit
            if until != model_until:
                model, model_until = self._fit(x, until), until
                fits += 1
            if model is not None:
                ridge, mean, scale = model
                y = ridge.predict((lag_matrix(x, [t], self.lags)-mean)/scale)[0]
                out[row] = y[columns]*scale+mean
        self.fit_count, self.predict_seconds = fits, time.perf_counter()-started
        return out
