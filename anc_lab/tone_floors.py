"""Memory floors and a joint band check for the tone observer bank (results-tone-forecaster-02).

Why: in results-tone-forecaster-01 the observer bank with the line finder
(bank_wide_lines + gate) predicted the tones better than v2 + gate but made a few
third-octave bands at least 1 dB louder, which its frozen bar did not allow.
Diagnosis on development material (results-tone-forecaster-02/diagnosis) found:

- The bank checks each tone only near that tone. Its shortest memories (25 and
  50 ms) follow the broadband noise near a tone, so the tone's phasor jumps from
  one 10 ms block to the next. Each jump spreads energy over other bands, where
  the per-tone check cannot see it. On a clean 60 Hz mains hum this made four
  bands up to 6.5 dB louder.
- The line finder adds weak or spurious lines. All trackers of one memory share
  one residual, so a tracker next to a real tone can carry a large phasor that
  only cancels against its neighbour's.
- A per-tone band guard (tone_guard.py) failed: because the trackers are joint,
  a tone's effect cannot be judged by leaving that tone out, and switching single
  tones on and off spread energy of its own.
- A fixed floor of 0.1 s (0.2 s for line-finder tones) removed most of the
  splatter but cost drifting tones about 7 dB: those need the short memories.

Remedies (output only; the bank's trackers and its own per-tone check are
unchanged, so every variant sees the same tones and the same checked errors):

FloorToneBank
    `min_tau_seconds` / `min_tau_lines_seconds`: a fixed minimum memory, for all
    tones / for tones that only the line finder found. `lean_db`: after warm-up a
    tone takes the longest memory whose checked error is within `lean_db` of the
    best one's, so a short memory must be clearly better before it is used.
JointCheckBank
    Checks what the bar measures, for the whole output at once. Ten output
    settings (an extra minimum memory of 0, 0.05, 0.1, 0.2 or 0.4 s for every
    tone, with line-finder tones on or off) are formed at every origin. When the
    targets arrive, each setting's error and the signal itself go into a 4 s
    buffer (the bar's own resolution: 0.25 Hz bins), and every 0.5 s the band
    powers of each error are compared with the signal's. Per horizon group the
    output uses, from the median over the last 16 checks, the setting with the
    lowest total error among those that make no band louder than no output by
    more than `margin_db`. No output is always allowed. When every setting
    boosts some band (drifting tones do this to v2 as well), the settings within
    `tie_db` of the least-boosting one stay allowed, so a small unavoidable boost
    does not silence a useful forecast. The output changes setting only when
    the current one is no longer allowed or another is `switch_db` better, since
    each change is a jump of its own. Until the first decision (about 6.5 s:
    a full buffer and five checks) the output uses `start`: a 0.1 s floor with
    the line-finder tones off.
    A setting is a complete output, so the joint trackers are judged as they
    would actually be heard, not one tone at a time. Medians, not running means:
    a tone locking on is a one-off jump that fills a few windows with splatter,
    and it must not decide on its own.

The diagnosis and the development trials of every variant are kept in
results-tone-forecaster-02/diagnosis.

Block-causal like the bank: every number comes from forecasts whose targets have
arrived. Nothing here opens an audio device.
"""
from collections import deque
import time

import numpy as np
from scipy import signal

from .tone_forecasters import ToneObserverBank

THIRD_OCTAVES_HZ = 1000*2**(np.arange(-14, -4)/3)       # 39.4 ... 315 Hz, as the study's bar


class FloorToneBank(ToneObserverBank):
    """ToneObserverBank whose output memory per tone obeys a floor and, optionally, a lean toward longer memories."""
    def __init__(self, *args, min_tau_seconds=0., min_tau_lines_seconds=0., lean_db=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.floor = float(min_tau_seconds)
        self.floor_lines = float(max(min_tau_seconds, min_tau_lines_seconds))
        self.lean_db = lean_db
        self.lean_ratio = 10**(lean_db/10) if lean_db is not None else None
        self.output_choice = np.zeros(0, int)
        self.counters.update({'output_moved':0, 'output_off':0})

    def settings(self):
        out = super().settings()
        out['output_rule'] = {'min_tau_seconds':self.floor, 'min_tau_lines_seconds':self.floor_lines,
                              'lean_db':self.lean_db}
        return out

    def _tone_floor(self, extra=0., lines=True):
        """Per-tone minimum memory in seconds; line-finder tones get inf (never output) when lines is False."""
        floor = np.maximum(np.where(self.from_selector, self.floor, self.floor_lines), extra)
        return floor if lines else np.where(self.from_selector, floor, np.inf)

    def _pick(self, base, floor):
        """Move the bank's choice `base` (memory per tone, -1 = off) to obey `floor` (seconds per tone) and the lean.

        A tone the bank switched off stays off. In warm-up (too few checks) a tone keeps
        the bank's default memory or the shortest allowed one above it."""
        n, k = self.n, len(base)
        cols = np.arange(k)
        allowed = self.taus[:, None] >= floor[None, :]-1e-9                          # (n, k)
        warm = self.checks >= self.min_checks
        ok = allowed & (self.power[:n] <= self.off_ratio*self.power[n]) & warm[None, :]
        masked = np.where(ok, self.power[:n], np.inf)
        best = np.argmin(masked, axis=0)
        if self.lean_ratio is not None:
            near = ok & (self.power[:n] <= self.lean_ratio*masked[best, cols])
            best = np.where(near.any(axis=0), n-1-np.argmax(near[::-1], axis=0), best)
        repick = np.where(ok.any(axis=0), best, -1)
        start = allowed & (np.arange(n)[:, None] >= self.default)
        warm_pick = np.where(start.any(axis=0), np.argmax(start, axis=0), -1)
        on = base >= 0
        keep = on & allowed[np.clip(base, 0, None), cols] & (~warm if self.lean_ratio is not None else True)
        return np.where(~on, -1, np.where(keep, base, np.where(warm, repick, warm_pick))).astype(int)

    def _emit(self, choice):
        p = self.c*np.exp(-1j*self.omega)
        return [(float(self.omega[b, j]*self.fs/(2*np.pi)), complex(p[b, j])) for j, b in enumerate(choice) if b >= 0]

    def _choose(self):
        super()._choose()
        choice = self._pick(self.choice, self._tone_floor()) if len(self.choice) else np.zeros(0, int)
        self.counters['output_moved'] += int(np.sum((choice >= 0) & (choice != self.choice)))
        self.counters['output_off'] += int(np.sum((choice < 0) & (self.choice >= 0)))
        self.output_choice = choice
        self.components_now = self._emit(choice)

    def state(self):
        out = super().state()
        out['output_tau_seconds'] = [float(self.taus[b]) if b >= 0 else None for b in self.output_choice]
        return out


class JointCheckBank(FloorToneBank):
    """Per horizon group, the output setting with the lowest realized error among those that make
    no third-octave band louder than no output by more than `margin_db`.

    Settings: every (extra minimum memory in `levels_seconds`, line-finder tones on/off) pair, plus
    no output. components(group) gives the tones of one horizon group; forecast(horizons) uses the
    nearest group for each horizon."""
    def __init__(self, *args, group_delays_ms=(20., 120.), levels_seconds=(0., .05, .1, .2, .4), margin_db=.5,
                 tie_db=.25, switch_db=.2, window_seconds=4., update_seconds=.5, history_checks=16,
                 min_checks_to_decide=5, start=(.1, False), bands_hz=THIRD_OCTAVES_HZ, **kwargs):
        super().__init__(*args, **kwargs)
        self.group_h = [round(d*self.fs/1000)+np.arange(1, self.block+1) for d in group_delays_ms]
        self.centres = np.array([h.mean() for h in self.group_h])
        self.keep = max(self.keep, int(max(h[-1] for h in self.group_h))+2*self.block)
        self.options = [(float(level), lines) for lines in (True, False) for level in levels_seconds]
        self.margin_db, self.tie_db, self.switch_db = float(margin_db), float(tie_db), float(switch_db)
        self.window =self.block*max(1, round(window_seconds*self.fs/self.block))
        self.update = max(1, round(update_seconds*self.fs/self.block))      # matured blocks between band checks
        self.min_decide = int(min_checks_to_decide)
        self.bands_hz = np.asarray(bands_hz, float)
        f = np.fft.rfftfreq(self.window, 1/self.fs)
        self.bands = np.array([(f >= c*2**(-1/6)) & (f < c*2**(1/6)) for c in self.bands_hz], float)   # (bands, bins)
        self.taper = signal.windows.hann(self.window, sym=False)
        groups, m = len(self.group_h), len(self.options)
        self.gqueue = [deque() for _ in range(groups)]
        # Row 0: the signal (error with no output); row s+1: the error with setting s. Circular in time.
        self.buffer = [np.zeros((m+1, self.window)) for _ in range(groups)]
        self.write, self.filled, self.matured = [0]*groups, [0]*groups, [0]*groups
        # Per check: band level and total level of each setting's error, dB over no output. The decision
        # uses medians over the last `history_checks` checks, so a one-off jump (a tone locking on, say)
        # that fills a few windows does not decide; a boost that persists does.
        self.history_db = [deque(maxlen=int(history_checks)) for _ in range(groups)]
        self.start = self.options.index((float(start[0]), bool(start[1])))+1
        self.active = [self.start]*groups                                  # 0 = no output, s+1 = setting s
        self.group_components = [[] for _ in range(groups)]
        self.counters.update({'setting_switches':[0]*groups, 'setting_histogram':[[0]*(m+1) for _ in range(groups)],
                              'band_checks':[0]*groups})
        self.timing['joint'] = 0.

    def settings(self):
        out = super().settings()
        out['joint_check'] = {'horizon_groups':[[int(h[0]), int(h[-1])] for h in self.group_h],
                              'settings':[{'extra_min_tau_seconds':l, 'line_finder_tones':s} for l, s in self.options],
                              'margin_db':self.margin_db, 'tie_db':self.tie_db, 'switch_db':self.switch_db,
                              'window_seconds':self.window/self.fs, 'update_seconds':self.update*self.block/self.fs,
                              'history_checks':self.history_db[0].maxlen, 'min_checks_to_decide':self.min_decide,
                              'start_setting':self.options[self.start-1], 'bands_hz':[round(float(c), 2) for c in self.bands_hz]}
        return out

    # ---- matured settings -> band powers -> active setting ----
    def _mature(self):
        super()._mature()
        started = time.perf_counter()
        groups = len(self.group_h)
        for g, h in enumerate(self.group_h):
            queue, buf = self.gqueue[g], self.buffer[g]
            while queue and queue[0][0]+h[-1] <= self.seen-1:
                origin, outputs = queue.popleft()
                target = self.history[len(self.history)-(self.seen-1-origin)-1+h]
                at = slice(self.write[g], self.write[g]+self.block)
                buf[0, at] = target
                buf[1:, at] = target-outputs
                self.write[g] = (self.write[g]+self.block) % self.window
                self.filled[g] = min(self.window, self.filled[g]+self.block)
                self.matured[g] += 1
                # Groups take turns, so one block never carries every group's FFT.
                if self.filled[g] == self.window and (self.matured[g]+g*self.update//groups) % self.update == 0:
                    self._band_check(g)
        self.timing['joint'] += time.perf_counter()-started

    def _band_check(self, g):
        # The buffer is circular: roll the taper onto it instead of rolling the buffer. A circular
        # shift changes only the phase of the spectrum, so the band powers are the same.
        spec = np.fft.rfft(self.buffer[g]*np.roll(self.taper, self.write[g]), axis=1)
        p = (spec.real**2+spec.imag**2)@self.bands.T                              # (settings+1, bands)
        floor = 1e-12*max(float(p[0].sum()), 1e-30)
        bands_db = 10*np.log10(np.maximum(p, floor)/np.maximum(p[0], floor))
        total = np.maximum(p.sum(axis=1), floor)
        total_db = 10*np.log10(total/total[0])
        self.history_db[g].append((bands_db, total_db))
        self.counters['band_checks'][g] += 1
        if len(self.history_db[g]) < self.min_decide:
            return
        louder = np.median([b for b, _ in self.history_db[g]], axis=0).max(axis=1)   # worst band, dB over no output
        total = np.median([t for _, t in self.history_db[g]], axis=0)
        # When every setting makes some band louder than the margin (drifting tones do this to v2 as
        # well), the settings closest to the least-boosting one stay eligible, rather than no output.
        ok = louder <= max(self.margin_db, louder[1:].min()+self.tie_db)
        ok[0] = True
        best = int(np.flatnonzero(ok)[np.argmin(total[ok])])
        now = self.active[g]
        if ok[now] and total[now] <= total[best]+self.switch_db:
            return
        self.counters['setting_switches'][g] += int(best != now)
        self.active[g] = best

    # ---- output ----
    def _choose(self):
        ToneObserverBank._choose(self)                         # the bank's own choice and check bookkeeping
        started = time.perf_counter()
        k = len(self.anchor)
        p = self.c*np.exp(-1j*self.omega)
        picks = [self._pick(self.choice, self._tone_floor(level, lines)) if k else np.zeros(0, int)
                 for level, lines in self.options]
        cols = np.arange(k)
        for g, h in enumerate(self.group_h):
            members = np.real(p[:, :, None]*np.exp(1j*self.omega[:, :, None]*h))      # (n, k, block)
            outputs = np.zeros((len(self.options), self.block))
            for s, pick in enumerate(picks):
                on = pick >= 0
                outputs[s] = members[pick[on], cols[on]].sum(axis=0)
            self.gqueue[g].append((self.seen-1, outputs))
            a = self.active[g]
            self.group_components[g] = self._emit(picks[a-1]) if a else []
            self.counters['setting_histogram'][g][a] += 1
        self.output_choice = picks[self.active[0]-1] if self.active[0] else np.full(k, -1)
        self.components_now = self.group_components[0]
        self.timing['joint'] += time.perf_counter()-started

    def components(self, group=0):
        """[(frequency Hz, complex phasor at the origin sample)] for the tones forecast now in one horizon group."""
        return list(self.group_components[group])

    def forecast(self, horizons):
        h = np.asarray(horizons, float)
        nearest = np.argmin(np.abs(h[:, None]-self.centres[None]), axis=1)
        out = np.zeros(len(h))
        for g, comps in enumerate(self.group_components):
            pick = nearest == g
            for f, ph in comps:
                out[pick] += np.real(ph*np.exp(2j*np.pi*f*h[pick]/self.fs))
        return out

    def state(self):
        out = super().state()
        out['active_setting'] = [None if a == 0 else {'extra_min_tau_seconds':self.options[a-1][0],
                                                      'line_finder_tones':self.options[a-1][1]} for a in self.active]
        return out
