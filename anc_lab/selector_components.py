"""Offline component view of the unchanged L2 chooser, for tuning integration.

No audio devices and no live-engine changes. The extra least-squares fit is
diagnostic overhead and is deliberately outside the frozen timing benchmark.
Only the two tested horizon groups are supported; arbitrary leads are rejected.
"""
from dataclasses import dataclass
import numpy as np

from .predictors import ToneTracker
from .tone_selection import recent_amplitude
from .selector_stream_profile import ForecastChain
from .selection_study import FS, BLOCK


def selected_components(past, active, config):
    """Expose the same v2 local fit, including its separate DC coefficient."""
    t = len(past) - 1
    freqs = [f for f, _ in active]
    long_n = round(config['window_seconds'] * FS)
    if freqs and config['release_ratio'] is not None:
        short_n = round(config['release_window_seconds'] * FS)
        freqs = [f for f in freqs if recent_amplitude(past, t, f, short_n, FS)
                 >= config['release_ratio'] * recent_amplitude(past, t, f, long_n, FS)]
    if not freqs:
        return (), 0.0
    freq, coef = ToneTracker(FS, freqs, config['window_seconds']).fit(past[max(0, t-long_n+1):t+1])
    k = len(freq)
    return tuple((float(f), complex(c, -s)) for f, s, c in zip(freq, coef[:k], coef[k:2*k])), float(coef[-1])


def wave(components, horizons, dc=0.0):
    h = np.asarray(horizons, float)
    result = np.full(len(h), dc, float)
    for frequency, phasor in components:
        result += np.real(phasor * np.exp(2j*np.pi*frequency*h/FS))
    return result


class _GateCapture:
    def __init__(self, delegate):
        self.delegate = delegate
        self.enabled = np.zeros(2, bool)

    def step(self, *args):
        output, enabled = self.delegate.step(*args)
        self.enabled = enabled.copy()
        return output, enabled


@dataclass
class ComponentFrame:
    # Phasors refer to reference sample index origin. Horizons count samples
    # after it: 41..60 and 241..260, not arbitrary 20 or 120 ms scalar leads.
    origin: int
    horizons: tuple
    v2: tuple
    dc: float
    fade: tuple
    gates: np.ndarray
    previous_gates: np.ndarray
    mix_weights: tuple  # group -> (BLOCK, 3), arms v2/fade/zero
    selected: tuple
    ghosts: int

    def reconstruct(self):
        """Reference forecasts including hard gates, DC and exact chooser fades."""
        result = {name: [] for name in ('v2_gated', 'fade0.1_linear_gated', 'causal_L2')}
        for group, h in enumerate(self.horizons):
            v2 = wave(self.v2, h, self.dc) * self.gates[0]
            fade = wave(self.fade[group], h) * self.gates[1]
            mixed = np.sum(self.mix_weights[group].T * np.stack([v2, fade, np.zeros(BLOCK)]), axis=0)
            for name, values in zip(result, (v2, fade, mixed)):
                result[name].append(values)
        return {name: np.concatenate(values) for name, values in result.items()}

    def anti_noise(self, settings, group, method='causal_L2', gate_rendering='hard', associate_hz=2.0):
        """Tuned negative tone waveform, excluding DC; does not play sound.

        Hard gate preserves the reference convention apart from deliberate DC
        removal. Block ramp is an explicitly different rendering candidate.
        Neither mode has a simulated-ear validation merely by existing here.
        Each frequency keeps its own setting even while two predictors mix.
        """
        if group not in (0, 1):
            raise ValueError('Only the tested 20/120 ms horizon groups are supported')
        if method not in ('v2_gated', 'fade0.1_linear_gated', 'causal_L2'):
            raise ValueError(method)
        if gate_rendering not in ('hard', 'block_ramp'):
            raise ValueError(gate_rendering)
        h = self.horizons[group]
        arms = np.zeros((3, BLOCK))
        for arm, components in enumerate((self.v2, self.fade[group])):
            for frequency, phasor in components:
                near = [s for s in settings if abs(s.frequency-frequency) <= associate_hz]
                if not near:
                    continue
                setting = min(near, key=lambda s: abs(s.frequency-frequency))
                if setting.gain <= 0:
                    continue
                rotation = (np.deg2rad(setting.phase_deg) + 2*np.pi*setting.offset_hz
                            * ((self.origin+h)/FS-setting.offset_origin_s))
                arms[arm] -= setting.gain*np.real(phasor*np.exp(2j*np.pi*frequency*h/FS+1j*rotation))
            if gate_rendering == 'hard':
                arms[arm] *= self.gates[arm]
            else:
                previous, target = float(self.previous_gates[arm]), float(self.gates[arm])
                arms[arm] *= previous+(target-previous)*np.arange(1, BLOCK+1)/BLOCK
        if method == 'v2_gated':
            return arms[0]
        if method == 'fade0.1_linear_gated':
            return arms[1]
        return np.sum(self.mix_weights[group].T*arms, axis=0)


class ComponentForecastChain(ForecastChain):
    """Observe the validated chain without changing its forecasting decisions."""
    def __init__(self, protocol, first_sample):
        super().__init__(protocol, first_sample)
        self.gate = _GateCapture(self.gate)
        self.frame = None

    def push(self, block, profile=False):
        if profile:
            raise ValueError('Component diagnostics must not enter the frozen timing benchmark')
        previous = self.gate.enabled.copy()
        expected = super().push(block)
        if expected is None:
            return None
        components, dc = selected_components(self.history, self.active, self.v2['forecaster'])
        weights = []
        for mixer in self.mixers:
            elapsed_before_render = mixer.elapsed-BLOCK
            alpha = np.clip((elapsed_before_render+np.arange(1, BLOCK+1))/mixer.fade_n, 0., 1.)
            weights.append(mixer.start[None, :]+alpha[:, None]*(mixer.goal-mixer.start)[None, :])
        self.frame = ComponentFrame(
            self.origin, tuple(h.copy() for _, h in self.groups), components, dc,
            tuple(tuple(group) for group in self.bank.group_components),
            self.gate.enabled.copy(), previous, tuple(weights),
            tuple(m.selected for m in self.mixers), len(self.bank.ghosts))
        return expected
