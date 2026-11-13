"""Fading tones in and out of the joint band check's output (results-tone-forecaster-05).

Why: in study 03 (results-tone-forecaster-03) 14 of the joint check's 25
development boosts were on scenes where the sound changes suddenly at 9 s (a tone
appears, the tones stop, or one source gives way to another). The study guessed
that the check's 8 s of medians react too slowly. The study-05 diagnosis
(results-tone-forecaster-05/diagnosis) says otherwise:

- An oracle that silences the joint output the instant the sound changes, which
  no causal method can do, still leaves 9 of the 14 boosts. Every fixed output
  setting has 15 to 17.
- The clean synthesized tones themselves, switched on and off with no delay (a
  perfect tracker), have 15.
- The same perfect tracker with a 0.1 s raised-cosine fade at each switch has 5.

So the boosts come from how the output starts and stops a strong tone. The
signal has one edge when a tone starts or stops; an output that switches the
tone in one block adds a second edge to the error, and two edges a few blocks
apart spread the tone's energy into the next third-octave band, most of all when
the tone sits near a band edge.

FadeCheckBank
    The joint check (tone_floors.JointCheckBank) with every tone's output level
    moved by a slew limit instead of a switch. In each output setting, a tone's
    level climbs from 0 to 1 over `fade_in_seconds` while the setting outputs it
    and falls back to 0 over `fade_out_seconds` while it does not, in whole
    blocks; the heard gain is the level shaped by `shape` ('cosine':
    sin^2(pi/2 level), zero slope at both ends; 'linear'; 'step' with one-block
    fades is the joint check exactly). While fading
    out, the tone keeps the memory it last used, and its tracker keeps running.
    A tone the selector drops while still fading out goes on from its last
    phasor and frequency, free-running, until its level reaches zero.
    The band check judges each setting with its fades, as it would be heard.
    `switch_fade_seconds` > 0 also cross-fades the emitted output from one
    setting to the next (and to or from no output) when the check changes its
    choice; 0 switches at once, as the joint check does.
    `start` is the joint check's own start setting, used until the first
    decision (about 6.5 s in). The diagnosis found that on the 5 s development
    mains clip, which never reaches a decision, the start setting (0.1 s floor,
    line-finder tones off) boosts one band by 1.35 dB and a 0.2 s floor does
    not, at about 3 dB of tone gain on that clip.

The trackers, the selector, the line finder, the bank's own per-tone check and
the band check's rule are unchanged. Everything is block-causal: the level at an
origin depends on choices made up to that origin. Nothing here opens an audio
device.
"""
import time

import numpy as np

from .tone_floors import JointCheckBank
from .tone_forecasters import ToneObserverBank

SHAPES = ('step', 'linear', 'cosine')


def shaped(level, shape):
    """Heard gain for a fade level in [0, 1]."""
    level = np.clip(np.asarray(level, float), 0., 1.)
    if shape == 'cosine':
        return np.sin(.5*np.pi*level)**2
    if shape == 'linear':
        return level
    if shape == 'step':
        return (level > 0).astype(float)
    raise ValueError(shape)


def association(anchor, selected, extra, associate_hz, max_tones):
    """Old column per new column after ToneObserverBank._reconcile (None for a new tone), by its own matching rule."""
    wanted = [(f, True) for f in selected]
    for f in extra:
        if all(abs(f-w) > associate_hz for w, _ in wanted):
            wanted.append((f, False))
    wanted = wanted[:max_tones]
    keep, used = [], set()
    for f, _ in wanted:
        near = [k for k in range(len(anchor)) if k not in used and abs(anchor[k]-f) <= associate_hz]
        k = min(near, key=lambda k: abs(anchor[k]-f)) if near else None
        if k is not None:
            used.add(k)
        keep.append(k)
    kept = [k for k in keep if k is not None]
    return kept+[None]*(len(keep)-len(kept))


class FadeCheckBank(JointCheckBank):
    """JointCheckBank whose tones fade in and out of every output setting, and whose emitted output can cross-fade."""
    def __init__(self, *args, fade_in_seconds=.1, fade_out_seconds=.1, shape='cosine', switch_fade_seconds=0.,
                 **kwargs):
        super().__init__(*args, **kwargs)
        if shape not in SHAPES:
            raise ValueError(shape)
        self.fade_in = max(1, round(fade_in_seconds*self.fs/self.block))
        self.fade_out = max(1, round(fade_out_seconds*self.fs/self.block))
        self.switch_fade = max(1, round(switch_fade_seconds*self.fs/self.block))
        self.shape = shape
        # Levels are whole steps of 1/full, so a fade lands exactly on 0 and on 1.
        self.full = self.fade_in*self.fade_out
        m = len(self.options)
        self.steps = np.zeros((m, 0), int)               # fade level x full per setting (rows) and tracked tone (columns)
        self.last = np.zeros((m, 0), int)                # memory each setting last used for each tone, -1 = none
        self.ghosts = []                                 # [setting, radians per sample, phasor at the coming origin, steps]
        self.mix = [np.eye(m+1, dtype=int)[self.start]*self.switch_fade for _ in self.group_h]   # x switch_fade; 0 = no output
        self.counters.update({'ghosts':0, 'fading_tone_blocks':0})

    def settings(self):
        out = super().settings()
        out['fades'] = {'fade_in_seconds':self.fade_in*self.block/self.fs,
                        'fade_out_seconds':self.fade_out*self.block/self.fs, 'shape':self.shape,
                        'switch_fade_seconds':self.switch_fade*self.block/self.fs if self.switch_fade > 1 else 0.}
        return out

    @property
    def level(self):
        """Fade level in [0, 1] per setting (rows) and tracked tone (columns)."""
        return self.steps/self.full

    def _reconcile(self):
        old_anchor, old_omega, old_c = self.anchor.copy(), self.omega.copy(), self.c.copy()
        super()._reconcile()
        order = association(old_anchor, self.selected, self.extra, self.associate_hz, self.max_tones)
        m = len(self.options)
        steps, last = np.zeros((m, len(order)), int), np.full((m, len(order)), -1)
        for i, k in enumerate(order):
            if k is not None:
                steps[:, i], last[:, i] = self.steps[:, k], self.last[:, k]
        # A dropped tone still fading out goes on from its last phasor, free-running.
        for k in sorted(set(range(len(old_anchor)))-{k for k in order if k is not None}):
            for s in np.flatnonzero((self.steps[:, k] > 0) & (self.last[:, k] >= 0)):
                b = self.last[s, k]
                w = float(old_omega[b, k])
                self.ghosts.append([int(s), w, complex(old_c[b, k]*np.exp(-1j*w)), int(self.steps[s, k])])
                self.counters['ghosts'] += 1
        self.steps, self.last = steps, last

    def _choose(self):
        ToneObserverBank._choose(self)                         # the bank's own choice and check bookkeeping
        started = time.perf_counter()
        k, m = len(self.anchor), len(self.options)
        p = self.c*np.exp(-1j*self.omega)
        picks = np.array([self._pick(self.choice, self._tone_floor(level, lines)) if k else np.zeros(0, int)
                          for level, lines in self.options]).reshape(m, k)
        on = picks >= 0
        self.last = np.where(on, picks, self.last)
        # Up one fade_in-th of the way per block while on, down one fade_out-th while off.
        self.steps = np.clip(self.steps+np.where(on, self.fade_out, -self.fade_in), 0, self.full)
        self.steps[self.last < 0] = 0
        gain = shaped(self.level, self.shape)
        self.counters['fading_tone_blocks'] += int(np.sum((self.steps > 0) & (self.steps < self.full)))
        for ghost in self.ghosts:
            ghost[3] -= self.fade_in
        self.ghosts = [gh for gh in self.ghosts if gh[3] > 0]
        cols = np.arange(k)
        b = np.clip(self.last, 0, None)
        live = gain > 0
        omega = np.take_along_axis(self.omega, b, axis=0) if k else np.zeros((m, 0))           # (m, k) radians/sample
        phasor = (np.take_along_axis(p, b, axis=0) if k else np.zeros((m, 0), complex))*gain
        # Per setting: (radians per sample, phasor at the origin) of every tone it outputs now, tracked then ghosts.
        tones = [[(omega[s, j], phasor[s, j]) for j in cols[live[s]]] for s in range(m)]
        for s, w, ph, lv in self.ghosts:
            tones[s].append((w, ph*float(shaped(lv/self.full, self.shape))))
        comps = [[(float(w*self.fs/(2*np.pi)), complex(ph)) for w, ph in t] for t in tones]
        for g, h in enumerate(self.group_h):
            outputs = np.zeros((m, self.block))
            for s in range(m):
                for w, ph in tones[s]:
                    outputs[s] += np.real(ph*np.exp(1j*w*h))
            self.gqueue[g].append((self.seen-1, outputs))
            target = np.eye(m+1, dtype=int)[self.active[g]]*self.switch_fade
            self.mix[g] = self.mix[g]+np.clip(target-self.mix[g], -1, 1)
            weights = shaped(self.mix[g]/self.switch_fade, self.shape if self.switch_fade > 1 else 'step')
            self.group_components[g] = [(f, ph*float(weights[a])) for a in np.flatnonzero(weights[1:] > 0)+1
                                        for f, ph in comps[a-1]]
            self.counters['setting_histogram'][g][self.active[g]] += 1
        for gh in self.ghosts:
            gh[2] *= np.exp(1j*gh[1]*self.block)
        self.output_choice = picks[self.active[0]-1] if self.active[0] else np.full(k, -1)
        self.components_now = self.group_components[0]
        self.timing['joint'] += time.perf_counter()-started

    def state(self):
        out = super().state()
        out['fade_levels'] = self.level.tolist()
        out['ghosts'] = len(self.ghosts)
        return out
