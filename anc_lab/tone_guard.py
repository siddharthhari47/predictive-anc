"""A band guard for the tone observer bank: a tone may not make any third-octave band louder.

FAILED EXPERIMENT, kept so the development trial in
results-tone-forecaster-02/diagnosis can be reproduced. Not a study candidate.
It does not work because the bank's trackers are joint: all tones of one memory
share one residual, so a tone's effect cannot be judged by leaving that tone
out (a neighbour's phasor may only make sense together with it), and switching
single tones on and off made jumps that spread energy of their own. In the development trial (margin
0.5 dB) it cut the mean synthetic objective from 7.7 to 0.8 dB and made one
band of the clean 60 Hz mains hum 27 dB louder.
tone_floors.JointCheckBank replaces it by judging whole output settings.

Why: in results-tone-forecaster-01 the observer bank with the line finder
predicted the tones better than v2 but made a few third-octave bands slightly
louder, which its frozen bar did not allow. Diagnosis on development material
(results-tone-forecaster-02) found two causes:

- On a very clean hum, the shortest memories (25 and 50 ms) let the broadband
  noise near a tone into its forecast. At the forecast horizon that noise is
  wrongly phased, and it lands in nearly empty neighbouring bands.
- Each tone's check spans about +-44 Hz, so it credits the tone with what its
  neighbours do and cannot see a single band getting louder.

GuardedToneBank checks what the bar measures. For each forecast horizon group
and each tone it keeps the last two seconds of matured forecasts and computes,
by FFT, the third-octave band powers of the error with the tone left out and
with the tone forecast by each memory. A memory is allowed only if no band is
louder with it than without the tone by more than `margin_db`. The tone keeps
the bank's choice when that is allowed, takes the best allowed memory by the
bank's own check otherwise, and is switched off when none is allowed. Each
horizon group gets its own choice, because a tone that helps at 20 ms can hurt
at 120 ms. The guard only removes or swaps memories; it never turns a tone on.

Optional floors on the memory (`min_tau_seconds`, and `min_tau_lines_seconds`
for tones that only the line finder found) are simpler alternatives to the band
check and can be combined with it.

Block-causal like the bank: every number comes from forecasts whose targets have
arrived. Nothing here opens an audio device.
"""
from collections import deque
import time

import numpy as np
from scipy import signal

from .tone_forecasters import ToneObserverBank

THIRD_OCTAVES_HZ = 1000*2**(np.arange(-14, -4)/3)       # 39.4 ... 315 Hz, as the study's bar


class GuardedToneBank(ToneObserverBank):
    """ToneObserverBank whose per-tone choice must also pass a per-band check, per horizon group.

    margin_db=None turns the band check off (floors only). components(group) gives the
    tones of one horizon group; forecast(horizons) uses the nearest group for each horizon.
    """
    def __init__(self, *args, guard_delays_ms=(20., 120.), margin_db=.2, window_seconds=2., update_seconds=.5,
                 average_seconds=4., warmup_seconds=1., lines_wait=True, min_tau_seconds=0., min_tau_lines_seconds=0.,
                 bands_hz=THIRD_OCTAVES_HZ, **kwargs):
        super().__init__(*args, **kwargs)
        self.guard_h = [round(d*self.fs/1000)+np.arange(1, self.block+1) for d in guard_delays_ms]
        self.centres = np.array([h.mean() for h in self.guard_h])
        self.keep = max(self.keep, int(max(h[-1] for h in self.guard_h))+2*self.block)
        self.margin_db = margin_db
        self.ratio = 10**(margin_db/10) if margin_db is not None else None
        self.window = self.block*max(1, round(window_seconds*self.fs/self.block))
        self.update = max(1, round(update_seconds*self.fs/self.block))      # matured blocks between band checks
        self.avg = float(np.exp(-update_seconds/average_seconds))
        self.warmup = round(warmup_seconds*self.fs)                          # samples of a tone's matured forecasts
        self.lines_wait = lines_wait
        self.floor = float(min_tau_seconds)
        self.floor_lines = max(min_tau_seconds, min_tau_lines_seconds)
        self.bands_hz = np.asarray(bands_hz, float)
        f = np.fft.rfftfreq(self.window, 1/self.fs)
        self.bands = np.array([(f >= c*2**(-1/6)) & (f < c*2**(1/6)) for c in self.bands_hz], float)   # (bands, bins)
        self.taper = signal.windows.hann(self.window, sym=False)
        groups = len(self.guard_h)
        self.ids, self.next_id = np.zeros(0, int), 0
        self.gpending = [deque() for _ in range(groups)]
        self.residual = [np.zeros(self.window) for _ in range(groups)]      # error of the bank's own output (circular)
        self.streams = [{} for _ in range(groups)]  # id -> (n+1, window): each memory's forecast of the tone, then its output
        self.age = [{} for _ in range(groups)]      # id -> matured samples
        self.stats = [{} for _ in range(groups)]    # id -> [band power without the tone (bands,), with each memory (n, bands)]
        self.write, self.matured = [0]*groups, [0]*groups
        self.group_choice = [np.zeros(0, int) for _ in range(groups)]
        self.group_components = [[] for _ in range(groups)]
        self.counters.update({'guard_switched':[0]*groups, 'guard_off':[0]*groups, 'guard_waiting':[0]*groups,
                              'floor_switched':0, 'floor_off':0})
        self.timing['guard'] = 0.

    def settings(self):
        out = super().settings()
        out['guard'] = {'horizon_groups':[[int(h[0]), int(h[-1])] for h in self.guard_h], 'margin_db':self.margin_db,
                        'window_seconds':self.window/self.fs, 'update_seconds':self.update*self.block/self.fs,
                        'average_seconds':float(-self.update*self.block/self.fs/np.log(self.avg)),
                        'warmup_seconds':self.warmup/self.fs, 'lines_wait':self.lines_wait,
                        'min_tau_seconds':float(self.floor), 'min_tau_lines_seconds':float(self.floor_lines),
                        'bands_hz':[round(float(c), 2) for c in self.bands_hz]}
        return out

    # ---- stable tone ids (the guard's records follow a tone, not a column) ----
    def _reconcile(self):
        """Same matching as the bank's _reconcile (kept tones first, in wanted order, then new ones)."""
        old = self.anchor.copy()
        wanted = [(f, True) for f in self.selected]
        for f in self.extra:
            if all(abs(f-w) > self.associate_hz for w, _ in wanted):
                wanted.append((f, False))
        used, kept, new = set(), [], 0
        for f, _ in wanted[:self.max_tones]:
            near = [k for k in range(len(old)) if k not in used and abs(old[k]-f) <= self.associate_hz]
            if near:
                k = min(near, key=lambda k: abs(old[k]-f))
                used.add(k)
                kept.append(k)
            else:
                new += 1
        super()._reconcile()
        self.ids = np.concatenate([self.ids[kept], np.arange(self.next_id, self.next_id+new)]).astype(int)
        self.next_id += new

    # ---- matured forecasts -> band powers ----
    def _mature(self):
        super()._mature()
        if self.ratio is None:
            return
        started = time.perf_counter()
        for g in range(len(self.guard_h)):
            self._guard_mature(g)
        self.timing['guard'] += time.perf_counter()-started

    def _guard_mature(self, g):
        h, queue = self.guard_h[g], self.gpending[g]
        while queue and queue[0][0]+h[-1] <= self.seen-1:
            origin, ids, members, output = queue.popleft()
            target = self.history[len(self.history)-(self.seen-1-origin)-1+h]
            at = slice(self.write[g], self.write[g]+self.block)
            self.residual[g][at] = target-output.sum(axis=0)
            streams, age, present = self.streams[g], self.age[g], set(ids.tolist())
            for i in [i for i in streams if i not in present]:      # tone dropped: its records go
                del streams[i], age[i]
                self.stats[g].pop(i, None)
            for col, i in enumerate(ids.tolist()):
                if i not in streams:
                    streams[i], age[i] = np.zeros((self.n+1, self.window)), 0
                streams[i][:self.n, at] = members[:, col]
                streams[i][self.n, at] = output[col]
                age[i] += self.block
            self.write[g] = (self.write[g]+self.block) % self.window
            self.matured[g] += 1
            # Groups take turns, so one block never carries every group's FFT.
            if (self.matured[g]+g*self.update//len(self.guard_h)) % self.update == 0:
                self._band_check(g)

    def _band_check(self, g):
        ids = [i for i in self.streams[g] if self.age[g][i] >= self.warmup]
        if not ids:
            return
        stack = np.vstack([self.residual[g][None]]+[self.streams[g][i] for i in ids])
        spec = np.fft.rfft(np.roll(stack, -self.write[g], axis=1)*self.taper, axis=1)
        tones = spec[1:].reshape(len(ids), self.n+1, -1)
        left_out = spec[0]+tones[:, self.n]                                   # error had the tone been off
        without = (np.abs(left_out)**2)@self.bands.T                          # (tones, bands)
        with_memory = (np.abs(left_out[:, None]-tones[:, :self.n])**2)@self.bands.T   # (tones, n, bands)
        stats = self.stats[g]
        for row, i in enumerate(ids):
            s = stats.get(i)
            if s is None:
                stats[i] = [without[row], with_memory[row]]
            else:
                s[0] = self.avg*s[0]+(1-self.avg)*without[row]
                s[1] = self.avg*s[1]+(1-self.avg)*with_memory[row]

    # ---- per-group choice ----
    def _guarded(self, g):
        choice = self.choice.copy()
        for j in np.nonzero(choice >= 0)[0]:
            allowed = self.taus >= (self.floor if self.from_selector[j] else self.floor_lines)-1e-9
            floor_only = True
            if self.ratio is not None:
                s = self.stats[g].get(int(self.ids[j]))
                if s is None:
                    if self.lines_wait and not self.from_selector[j]:
                        choice[j] = -1
                        self.counters['guard_waiting'][g] += 1
                        continue
                else:
                    allowed &= np.all(s[1] <= self.ratio*s[0], axis=1)
                    floor_only = False
            if allowed[choice[j]]:
                continue
            ok = np.zeros(self.n, bool)
            if self.checks[j] >= self.min_checks:
                ok = allowed & (self.power[:self.n, j] <= self.off_ratio*self.power[self.n, j])
            if ok.any():
                choice[j] = int(np.flatnonzero(ok)[np.argmin(self.power[:self.n, j][ok])])
            elif self.checks[j] < self.min_checks and allowed.any():
                choice[j] = int(np.flatnonzero(allowed)[0])                   # warm-up: shortest allowed memory
            else:
                choice[j] = -1
            key = ('floor_' if floor_only else 'guard_')+('switched' if choice[j] >= 0 else 'off')
            if floor_only:
                self.counters[key] += 1
            else:
                self.counters[key][g] += 1
        return choice

    def _choose(self):
        super()._choose()
        started = time.perf_counter()
        k = len(self.anchor)
        p = self.c*np.exp(-1j*self.omega)
        for g, h in enumerate(self.guard_h):
            choice = self._guarded(g) if k else np.zeros(0, int)
            members = np.real(p[:, :, None]*np.exp(1j*self.omega[:, :, None]*h))      # (n, k, block)
            output = np.zeros((k, self.block))
            on = np.nonzero(choice >= 0)[0]
            output[on] = members[choice[on], on]
            if self.ratio is not None:
                self.gpending[g].append((self.seen-1, self.ids.copy(), members, output))
            self.group_choice[g] = choice
            self.group_components[g] = [(float(self.omega[b, j]*self.fs/(2*np.pi)), complex(p[b, j]))
                                        for j, b in enumerate(choice) if b >= 0]
        self.timing['guard'] += time.perf_counter()-started

    # ---- output ----
    def components(self, group=0):
        """[(frequency Hz, complex phasor at the origin sample)] for the tones forecast now in one horizon group."""
        return list(self.group_components[group])

    def forecast(self, horizons):
        h = np.asarray(horizons, float)
        nearest = np.argmin(np.abs(h[:, None]-self.centres[None]), axis=1)
        out = np.zeros(len(h))
        for g, comps in enumerate(self.group_components):
            pick = nearest == g
            for f, p in comps:
                out[pick] += np.real(p*np.exp(2j*np.pi*f*h[pick]/self.fs))
        return out

    def state(self):
        out = super().state()
        out['group_choice_tau_seconds'] = [[float(self.taus[b]) if b >= 0 else None for b in c] for c in self.group_choice]
        return out
