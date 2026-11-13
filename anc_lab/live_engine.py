"""The engines the live tuner can run. Never opens audio devices.

`smoothed` is the s30 smoother and taper cache tested in the real LiveRunner by
results-engine-candidate-01 and -02: one frozen fail and one pass on the 5 ms
reserve, output exact both times. `v2` is the plain AntiHumEngine, kept as the
fallback. The smoother is copied from smoother_timing, which is frozen and
pulls in study code; tests/test_live_engine.py holds the two equal.
"""
import cmath

from scipy import signal

from .antihum import BLOCK, FS, AntiHumEngine
from .faint_tones import CombinedSelector

ALPHA = .3                        # s30: about 5.7 Hz, the band edge set by a 30 ms lead
ASSOCIATE_HZ = 2.
MAX_GAP = 10


class PhasorSmoother:
    """Causal phase-locked smoothing of each tone's phasor, one origin at a time."""
    def __init__(self, alpha=ALPHA, block=BLOCK, fs=FS):
        self.alpha = alpha
        self.turn = 2j*cmath.pi*block/fs
        self.states = []              # [frequency, smoothed phasor, origin number]
        self.origin = 0
        self.previous_gate = True     # no earlier origin: nothing to clear

    def step(self, components, gate_open):
        """Smoothed [(frequency, phasor)] for this origin; call once per origin, in order."""
        k, alpha = self.origin, self.alpha
        states = [] if not self.previous_gate else [s for s in self.states if k-s[2] <= MAX_GAP]
        out, new = [], []
        for frequency, phasor in components:
            if phasor == 0:
                out.append((frequency, phasor))
                continue
            match = None
            if states:
                i = min(range(len(states)), key=lambda n: abs(states[n][0]-frequency))
                if abs(states[i][0]-frequency) <= ASSOCIATE_HZ:
                    match = states.pop(i)
            smoothed = phasor
            if match is not None:
                smoothed = alpha*phasor+(1-alpha)*match[1]*cmath.exp(self.turn*match[0]*(k-match[2]))
            out.append((frequency, smoothed))
            new.append([frequency, smoothed, k])
        self.states = states+new
        self.previous_gate = bool(gate_open)
        self.origin = k+1
        return out


class _RawEngine(AntiHumEngine):
    def __init__(self, keep_log, selector=None):
        super().__init__(selector=selector, keep_log=keep_log)
        self.smoother, self.smoothed = PhasorSmoother(), []

    def _origin(self, end):
        super()._origin(end)
        self.smoothed = self.smoother.step(self.components, self.gate_open)


class SmoothedEngine:
    """The renderer's components are smoothed; the gate, tone list and raw log stay raw."""
    def __init__(self, keep_log=False, selector=None):
        self.raw = _RawEngine(keep_log, selector)
        self.tapers = {}

    def _dpss(self, *args, **kwargs):
        key = (args, tuple(sorted(kwargs.items())))
        if key not in self.tapers:
            self.tapers[key] = self._original_dpss(*args, **kwargs)
            self.tapers[key].setflags(write=False)
        return self.tapers[key]

    def push(self, block):
        # The tone detector asks scipy for the same tapers every window. Only the
        # worker thread reaches it, so swapping scipy's function here is safe.
        self._original_dpss, signal.windows.dpss = signal.windows.dpss, self._dpss
        try:
            self.raw.push(block)
        finally:
            signal.windows.dpss = self._original_dpss

    def strongest(self, count=None):
        return self.raw.strongest(count)

    components = property(lambda self: self.raw.smoothed)
    origin_seen = property(lambda self: self.raw.origin_seen)
    gate_open = property(lambda self: self.raw.gate_open)
    counters = property(lambda self: self.raw.counters)


def FaintEngine(keep_log=False):
    """The smoothed engine with the faint-tone detector added (results-faint-tones-02)."""
    return SmoothedEngine(keep_log, CombinedSelector())


ENGINES = {'faint': FaintEngine, 'smoothed': SmoothedEngine, 'v2': AntiHumEngine}
