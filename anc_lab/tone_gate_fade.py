"""A softer realized-error gate, and a joint band check that judges the gated output (results-tone-forecaster-04).

Why: in study 03 (results-tone-forecaster-03) the joint band check of study 02
(tone_floors.JointCheckBank) had 2 late third-octave boosts on the eight
development buzz scenes without the gate and 7 with it. The v2 gate
(selection_study.apply_gate, from tone_selection.realized_gate) sets a whole
10 ms output block to zero or leaves it alone, per origin, from the forecast's
own error over the last five matured blocks. Each switch is a step in the
output, and a step spreads a tone's energy over neighbouring bands. When the
tones sit above 100 Hz and the lowest bands are nearly empty, a little spread
is a large relative boost there. The joint check measures each setting's error
before the gate, so it cannot see this.

Two remedies, usable apart or together:

Fade (fade_gains, apply_fade, fade_gate_output)
    The gate decides exactly as before (same realized error, same lookback, same
    threshold, from the ungated forecast). Its decision moves a gain instead of
    a switch: up by 1/fade_in_blocks per block while the gate is open, down by
    1/fade_out_blocks while it is shut, between 0 and 1. Inside each output
    block the gain runs smoothly from the previous origin's value to this
    origin's, so the output envelope has no steps. With shape 'cosine' the
    envelope is sin^2(pi/2 * gain), so it also starts and ends each fade with
    zero slope. fade 1/1 with shape 'step' is the v2 gate exactly.
GatedCheckBank
    JointCheckBank whose band check measures each setting's error after the
    gate (and the fade, if one is set), as it will be heard. Each setting gets
    its own copy of the gate, run on that setting's own matured errors with the
    v2 gate's numbers, so the check sees what the switching would add had that
    setting been in use. The bank's emitted output is still ungated: the study
    applies the real gate outside, as for every method.

Everything is block-causal: a gate decision at origin t uses forecasts whose
targets arrived by t, and the gain inside the block issued at t depends only on
decisions up to t. Nothing here opens an audio device.
"""
import time

import numpy as np

from .selection_study import apply_gate
from .tone_floors import JointCheckBank
from .tone_forecasters import ToneObserverBank
from .tone_selection import realized_gate

SHAPES = ('step', 'linear', 'cosine')


def fade_gains(enabled, fade_in_blocks=1, fade_out_blocks=1):
    """Gain per origin (rows) and group (columns) after the slew limit; starts at 0, like a shut gate."""
    enabled = np.asarray(enabled, bool)
    up, down = 1./max(float(fade_in_blocks), 1.), 1./max(float(fade_out_blocks), 1.)
    out = np.zeros(enabled.shape)
    g = np.zeros(enabled.shape[1:])
    for r in range(len(enabled)):
        g = np.clip(np.where(enabled[r], g+up, g-down), 0., 1.)
        out[r] = g
    return out


def envelope(previous, now, block, shape='cosine'):
    """Gain for each sample of one output block: from `previous` (the block before) to `now`, inclusive at the end.

    Broadcasts over leading dimensions: previous and now of shape (...), result (..., block)."""
    previous, now = np.asarray(previous, float), np.asarray(now, float)
    if shape == 'step':
        return np.repeat(now[..., None], block, axis=-1)
    k = np.arange(1, block+1)/block
    lin = previous[..., None]+(now-previous)[..., None]*k
    if shape == 'linear':
        return lin
    if shape == 'cosine':
        return np.sin(.5*np.pi*lin)**2
    raise ValueError(shape)


def apply_fade(shadow, gains, groups, shape='cosine'):
    """Scale each origin's forecast block by its envelope. Rows are origins one block apart, as on the study grid;
    `groups` as selection_study.horizon_setup: (columns, horizons) with the columns in horizon order."""
    out = shadow.copy()
    gains = np.asarray(gains, float)
    for g, (columns, _) in enumerate(groups):
        previous = np.r_[0., gains[:-1, g]]
        out[:, columns] = shadow[:, columns]*envelope(previous, gains[:, g], len(columns), shape)
    return out


class BlockFade:
    """The fade one block at a time, as an engine would run it for one horizon group: step(is_open) once per output
    block returns that block's gain per sample. Same numbers as fade_gains + apply_fade."""
    def __init__(self, block, fade_in_blocks=1, fade_out_blocks=1, shape='cosine'):
        self.block, self.shape = int(block), shape
        self.up, self.down = 1./max(float(fade_in_blocks), 1.), 1./max(float(fade_out_blocks), 1.)
        self.gain = 0.

    def step(self, is_open):
        previous = self.gain
        self.gain = min(1., previous+self.up) if is_open else max(0., previous-self.down)
        return envelope(previous, self.gain, self.block, self.shape)


def fade_gate_output(x, grid, shadow, groups, gate, fade):
    """As release_study.gate_output, with the gate's decision faded. Returns (output, gains, enabled)."""
    enabled = realized_gate(x, grid, shadow, groups, gate['min_gain_db'], gate['lookback'], gate['min_matured'],
                            gate['shared_group'])
    if fade is None:
        return apply_gate(shadow, enabled, groups), enabled.astype(float), enabled
    gains = fade_gains(enabled, fade['in_blocks'], fade['out_blocks'])
    return apply_fade(shadow, gains, groups, fade.get('shape', 'cosine')), gains, enabled


class GatedCheckBank(JointCheckBank):
    """JointCheckBank whose band check judges each setting after its own copy of the realized-error gate
    (optionally faded). `gate` holds the v2 gate's numbers; `fade` is None (hard) or {in_blocks, out_blocks, shape}."""
    def __init__(self, *args, gate=None, fade=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.gate = dict(gate or {'min_gain_db':-1., 'lookback':5, 'min_matured':3, 'shared_group':0})
        self.fade = dict(fade) if fade else None
        groups, m = len(self.group_h), len(self.options)
        self.gate_source = [g if self.gate['shared_group'] is None else int(self.gate['shared_group']) for g in range(groups)]
        lookback = int(self.gate['lookback'])
        # Per source group: matured (target energy, each setting's ungated error energy) of the last `lookback` origins.
        self.gate_ref = [np.zeros(lookback) for _ in range(groups)]
        self.gate_err = [np.zeros((lookback, m)) for _ in range(groups)]
        self.gate_count = [0]*groups
        self.gain_now = [np.zeros(m) for _ in range(groups)]                 # per setting, after the fade
        self.counters.update({'internal_gate_open_blocks':[[0]*m for _ in range(groups)]})
        self.timing['gated_check'] = 0.

    def settings(self):
        out = super().settings()
        out['joint_check']['judged_after_gate'] = {'gate':self.gate, 'fade':self.fade}
        return out

    def _mature(self):
        ToneObserverBank._mature(self)
        started = time.perf_counter()
        groups = len(self.group_h)
        lookback = len(self.gate_ref[0])
        for g, h in enumerate(self.group_h):
            queue, buf = self.gqueue[g], self.buffer[g]
            while queue and queue[0][0]+h[-1] <= self.seen-1:
                origin, outputs, heard = queue.popleft()
                target = self.history[len(self.history)-(self.seen-1-origin)-1+h]
                if g in self.gate_source:
                    i = self.gate_count[g] % lookback
                    self.gate_ref[g][i] = float(target@target)
                    err = target[None, :]-outputs
                    self.gate_err[g][i] = np.einsum('sb,sb->s', err, err)
                    self.gate_count[g] += 1
                at = slice(self.write[g], self.write[g]+self.block)
                buf[0, at] = target
                buf[1:, at] = target-heard
                self.write[g] = (self.write[g]+self.block) % self.window
                self.filled[g] = min(self.window, self.filled[g]+self.block)
                self.matured[g] += 1
                if self.filled[g] == self.window and (self.matured[g]+g*self.update//groups) % self.update == 0:
                    self._band_check(g)
        self.timing['joint'] += time.perf_counter()-started
        self.timing['gated_check'] += time.perf_counter()-started

    def _gate_open(self, g):
        """Per setting: the realized-error gate's decision now, from the source group's last matured origins."""
        src = self.gate_source[g]
        if min(self.gate_count[src], len(self.gate_ref[src])) < int(self.gate['min_matured']):
            return np.zeros(len(self.options), bool)
        # Slots not yet written hold zeros, so whole-buffer sums are sums over the matured origins.
        ref = max(float(self.gate_ref[src].sum()), 1e-30)
        err = np.maximum(self.gate_err[src].sum(axis=0), 1e-30)
        return 10*np.log10(ref/err) >= float(self.gate['min_gain_db'])

    def _choose(self):
        ToneObserverBank._choose(self)
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
            is_open = self._gate_open(g)
            for s in np.flatnonzero(is_open):
                self.counters['internal_gate_open_blocks'][g][s] += 1
            previous = self.gain_now[g]
            if self.fade is None:
                now = is_open.astype(float)
                env = envelope(previous, now, self.block, 'step')
            else:
                up, down = 1./max(float(self.fade['in_blocks']), 1.), 1./max(float(self.fade['out_blocks']), 1.)
                now = np.clip(np.where(is_open, previous+up, previous-down), 0., 1.)
                env = envelope(previous, now, self.block, self.fade.get('shape', 'cosine'))
            self.gain_now[g] = now
            self.gqueue[g].append((self.seen-1, outputs, outputs*env))
            a = self.active[g]
            self.group_components[g] = self._emit(picks[a-1]) if a else []
            self.counters['setting_histogram'][g][a] += 1
        self.output_choice = picks[self.active[0]-1] if self.active[0] else np.full(k, -1)
        self.components_now = self.group_components[0]
        elapsed = time.perf_counter()-started
        self.timing['joint'] += elapsed
        self.timing['gated_check'] += elapsed
