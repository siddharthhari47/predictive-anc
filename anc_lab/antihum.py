"""Anti-hum output engine: block-causal, per-tone gain and phase, hard output cap.

Nothing in this module opens an audio device. `tune_app.py` does, and only when
the user starts it and confirms they are ready.

How it works, per audio block:
1. Microphone samples (already at the 2 kHz analysis rate) are appended to a
   short history.
2. Every 0.25 s the frozen v2 tone selector updates its tone set from the last
   second (past samples only).
3. Every 10 ms, tones whose amplitude halved within the last 0.1 s are dropped,
   and the rest are fitted over the last 0.3 s (frequency refinement, then
   amplitude and phase, as ToneTracker does).
4. The v2 realized-error gate mutes everything while recent forecasts at the
   microphone were worse than predicting nothing (by more than 1 dB).
5. Output for the time `lead` after the newest microphone sample is synthesized
   from those fits: for each tone with a user setting, minus gain times the tone,
   shifted by the setting's phase. Tones without a setting are not played.

Gain and phase per tone come from tuning (tuning.py). They absorb everything
the engine cannot know: microphone and earphone sensitivity, the room path from
the hum to the ear compared with the path to the microphone, and constant
device delay. A change after tuning (moving the head, Bluetooth delay drift)
is not corrected.

The digital output cap is not an SPL calibration. How loud a digital level is
depends on the device, its volume setting and the earphones.
"""
from collections import deque
from dataclasses import asdict, dataclass

import numpy as np
from scipy import signal

from .predictors import ToneTracker
from .tone_selection import ToneSelector, recent_amplitude

FS = 2000
DEFAULT_PEAK_CAP = .05        # -26 dBFS
MAX_PEAK_CAP = .2             # -14 dBFS; refused above this
V2_SELECTOR = {'alpha':1e-2, 'acquire':2, 'history':3, 'release':4}   # results-release-study-01 v2
V2_FIT_SECONDS = .3
V2_RELEASE = {'ratio':.5, 'seconds':.1}
# Realized-error gate; v2 gates every horizon on the 20 ms group (shared_group 0).
V2_GATE = {'min_gain_db':-1., 'lookback':5, 'min_matured':3, 'horizon_ms':20.}
BLOCK = 20                    # analysis samples per origin (10 ms)


class OutputLimiter:
    """Last stage before any audio device: fade in/out, hard peak cap, time limit.

    Starts silent. `start()` fades in, `stop()` fades out; once stopped (by the
    user, the time limit, or a non-finite sample) it stays silent for good.
    """
    def __init__(self, fs, peak_cap=DEFAULT_PEAK_CAP, fade_seconds=.5, max_seconds=600.):
        if not 0 < peak_cap <= MAX_PEAK_CAP:
            raise ValueError(f'Peak cap must be in (0, {MAX_PEAK_CAP}] (digital full scale = 1).')
        if not 0 < max_seconds <= 3600:
            raise ValueError('Maximum duration must be at most one hour.')
        self.fs, self.peak_cap = fs, float(peak_cap)
        self.fade_samples = max(1, round(fade_seconds*fs))
        self.max_samples = round(max_seconds*fs)
        self.level, self.target, self.stopped = 0., 0., False
        self.samples_out = self.clipped_samples = self.nonfinite_blocks = 0
        self.stop_reason = None

    def start(self):
        if not self.stopped:
            self.target = 1.

    def stop(self, reason='stopped'):
        self.target, self.stopped = 0., True
        self.stop_reason = self.stop_reason or reason

    def process(self, block):
        block = np.asarray(block, float)
        if not np.all(np.isfinite(block)):
            self.nonfinite_blocks += 1
            self.stop('non-finite output')
            self.level = 0.
            block = np.zeros_like(block)
        if self.samples_out+len(block) >= self.max_samples-self.fade_samples:
            self.stop('time limit')
        step = 1/self.fade_samples
        ramp = np.clip(self.level+np.sign(self.target-self.level)*step*np.arange(1, len(block)+1),
                       min(self.level, self.target), max(self.level, self.target))
        self.level = float(ramp[-1]) if len(block) else self.level
        out = block*(ramp[:, None] if block.ndim == 2 else ramp)   # (samples,) or (samples, channels)
        over = np.abs(out) > self.peak_cap
        self.clipped_samples += int(np.sum(over))
        self.samples_out += len(block)
        return np.clip(out, -self.peak_cap, self.peak_cap)


class StreamingDecimator:
    """Integer-ratio decimation with filter state carried across blocks (causal)."""
    def __init__(self, in_fs, out_fs=FS):
        if in_fs % out_fs:
            raise ValueError('Input rate must be an integer multiple of the analysis rate.')
        self.ratio = in_fs//out_fs
        self.sos = signal.butter(8, .8*out_fs/2, fs=in_fs, output='sos')
        self.zi = np.zeros((self.sos.shape[0], 2))
        self.phase = 0
        self.newest_age = 0           # input samples between the newest output sample and the newest input

    def process(self, block):
        filtered, self.zi = signal.sosfilt(self.sos, np.asarray(block, float), zi=self.zi)
        picks = np.arange((self.ratio-1-self.phase) % self.ratio, len(filtered), self.ratio)
        self.phase = (self.phase+len(filtered)) % self.ratio
        self.newest_age = len(filtered)-1-int(picks[-1]) if len(picks) else self.newest_age+len(filtered)
        return filtered[picks]


@dataclass
class ToneSetting:
    """User setting for one tone: gain and phase applied to the anti-hum.

    offset_hz plays the anti-hum slightly off the tone's frequency, so its phase
    against the hum rotates slowly. Tuning uses this for beats and sweeps.
    """
    frequency: float
    gain: float = 0.
    phase_deg: float = 0.
    offset_hz: float = 0.
    offset_origin_s: float = 0.     # engine time at which the extra rotation is zero


def synthesize(components, setting_for, now, samples, out_fs, lead_seconds):
    """Minus the tuned tones, for times now + lead + i/out_fs (now = newest input sample time).

    Shared by the live engine and by offline replays of stored components.
    """
    t = lead_seconds+np.arange(samples)/out_fs
    out = np.zeros(samples)
    for frequency, phasor in components:
        setting = setting_for(frequency)
        if setting is None or setting.gain <= 0:
            continue
        rotation = np.deg2rad(setting.phase_deg)+2*np.pi*setting.offset_hz*(now+t-setting.offset_origin_s)
        out -= setting.gain*np.real(phasor*np.exp(1j*(2*np.pi*frequency*t+rotation)))
    return out


class AntiHumEngine:
    """Block-causal anti-hum synthesizer with the frozen v2 tone choice, release and gate.

    Silent unless a tone has a setting with gain > 0 and the realized-error gate
    is open. Every BLOCK analysis samples is one "origin": the selector updates
    when due, tones that faded in the last 0.1 s are dropped (fast release), the
    rest are fitted over the last 0.3 s, and the gate compares the forecasts made
    30 ms or more ago with what the microphone then heard. All of this uses
    samples up to the origin only, exactly as results-release-study-01 v2 does.
    """
    def __init__(self, fs=FS, selector=None, fit_seconds=V2_FIT_SECONDS, release=V2_RELEASE, gate=V2_GATE,
                 history_seconds=1.2, associate_hz=2., max_tones=3, block=BLOCK, keep_log=False):
        self.fs, self.block = fs, block
        self.selector = selector or ToneSelector(fs, **V2_SELECTOR)
        self.selector.reset()
        self.fit = round(fit_seconds*fs)
        self.release, self.gate = release, gate
        self.release_short = round(release['seconds']*fs) if release else 0
        self.gate_horizons = round(gate['horizon_ms']*fs/1000)+np.arange(1, block+1)
        self.history = np.zeros(0)
        self.keep = max(round(history_seconds*fs), self.selector.window, self.fit)+block
        self.associate_hz, self.max_tones = associate_hz, max_tones
        self.seen = 0                 # analysis samples received
        self.origin_seen = 0          # samples received up to the latest origin
        self.active = []              # [(frequency, confidence)] from the selector
        self.components = []          # [(frequency, complex phasor at the origin sample)]
        self.dc = 0.
        self.settings = []            # [ToneSetting]
        self.next_update = self.selector.step
        self.gate_open = False
        self._pending = deque()       # (origin_seen, shadow forecast at the gate horizons)
        self._matured = deque(maxlen=gate['lookback'])
        self._gate_level = 0.
        self.counters = {'origins':0, 'origins_with_tones':0, 'origins_gate_open_with_tones':0, 'fast_drops':0}
        self.log = [] if keep_log else None

    # ---- input ----
    def push(self, block):
        """Add microphone samples at the analysis rate (oldest first); any length."""
        block = np.asarray(block, float)
        self.history = np.concatenate([self.history, block])
        self.seen += len(block)
        while self.origin_seen+self.block <= self.seen:
            self.origin_seen += self.block
            self._origin(len(self.history)-(self.seen-self.origin_seen))
        self.history = self.history[-self.keep:]

    @property
    def origin_age_seconds(self):
        """How much newer the newest received sample is than the latest origin."""
        return (self.seen-self.origin_seen)/self.fs

    def _index(self, absolute):
        return absolute-(self.seen-len(self.history))

    def _origin(self, end):
        while self.next_update <= self.origin_seen:
            # The selector sees the window ending at its update time (past samples only).
            e = end-(self.origin_seen-self.next_update)
            self.active = self.selector.update(self.history[max(0, e-self.selector.window):e])
            self.next_update += self.selector.step
        freqs = [f for f, _ in self.active]
        if freqs and self.release:
            past = self.history[:end]
            kept = [f for f in freqs if recent_amplitude(past, end-1, f, self.release_short, self.fs)
                    >= self.release['ratio']*recent_amplitude(past, end-1, f, self.fit, self.fs)]
            self.counters['fast_drops'] += len(freqs)-len(kept)
            freqs = kept
        if freqs:
            freq, coef = ToneTracker(self.fs, freqs, self.fit/self.fs).fit(self.history[max(0, end-self.fit):end])
            k = len(freq)
            # s*sin(w tau) + c*cos(w tau) = Re{(c - j s) e^{j w tau}}, tau = 0 at the origin sample.
            self.components = [(float(f), complex(c, -s)) for f, s, c in zip(freq, coef[:k], coef[k:2*k])]
            self.dc = float(coef[-1])
        else:
            self.components, self.dc = [], 0.
        # Realized-error gate (v2: shared 20 ms group, lookback 5, at least 3 matured, -1 dB).
        last = int(self.gate_horizons[-1])
        while self._pending and self._pending[0][0]+last <= self.origin_seen:
            origin, forecast = self._pending.popleft()
            target = self.history[self._index(origin-1+self.gate_horizons)]
            self._matured.append((float(np.sum(target**2)), float(np.sum((target-forecast)**2))))
        if len(self._matured) >= self.gate['min_matured']:
            ref, err = (sum(v) for v in zip(*self._matured))
            self.gate_open = bool(10*np.log10(max(ref, 1e-30)/max(err, 1e-30)) >= self.gate['min_gain_db'])
        else:
            self.gate_open = False
        self._pending.append((self.origin_seen, self.shadow_forecast(self.gate_horizons)))
        self.counters['origins'] += 1
        if self.components:
            self.counters['origins_with_tones'] += 1
            self.counters['origins_gate_open_with_tones'] += int(self.gate_open)
        if self.log is not None:
            self.log.append((self.origin_seen, list(self.components), self.gate_open))

    def shadow_forecast(self, horizons):
        """Ungated microphone forecast at integer horizons after the origin (tones + dc, as ToneTracker)."""
        h = np.asarray(horizons)/self.fs
        out = np.full(len(h), self.dc)
        for f, p in self.components:
            out += np.real(p*np.exp(2j*np.pi*f*h))
        return out

    def strongest(self, count=None):
        """Current tones, strongest first: [(frequency, amplitude at the microphone)]."""
        ranked = sorted(((f, abs(p)) for f, p in self.components), key=lambda fa: -fa[1])
        return ranked[:count or self.max_tones]

    # ---- settings ----
    def setting_for(self, frequency):
        near = [s for s in self.settings if abs(s.frequency-frequency) <= self.associate_hz]
        return min(near, key=lambda s: abs(s.frequency-frequency)) if near else None

    def set_tone(self, setting):
        self.settings = [s for s in self.settings if abs(s.frequency-setting.frequency) > self.associate_hz]+[setting]

    # ---- output ----
    def render(self, samples, out_fs=None, lead_seconds=.02):
        """Anti-hum for `samples` output samples starting `lead_seconds` after the latest origin sample.

        A gate change fades over the rendered block instead of switching abruptly.
        """
        out = synthesize(self.components, self.setting_for, self.origin_seen/self.fs, samples,
                         out_fs or self.fs, lead_seconds)
        target = float(self.gate_open)
        ramp = self._gate_level+(target-self._gate_level)*np.arange(1, samples+1)/max(samples, 1)
        self._gate_level = target
        return out*ramp

    def state(self):
        return {'seen_seconds':self.seen/self.fs, 'active':self.active, 'gate_open':bool(self.gate_open),
                'components':[(f, abs(p), float(np.degrees(np.angle(p)))) for f, p in self.components],
                'settings':[asdict(s) for s in self.settings], 'counters':dict(self.counters)}


def log_arrays(log, max_tones=None):
    """Engine log -> arrays: seen (n,), frequency (n, k), phasor (n, k), gate (n,). Missing tones: nan / 0."""
    k = max_tones or max([len(c) for _, c, _ in log]+[1])
    seen = np.array([s for s, _, _ in log], int)
    freq = np.full((len(log), k), np.nan)
    phasor = np.zeros((len(log), k), complex)
    for row, (_, components, _) in enumerate(log):
        for j, (f, p) in enumerate(components[:k]):
            freq[row, j], phasor[row, j] = f, p
    return {'seen':seen, 'frequency':freq, 'phasor':phasor, 'gate':np.array([g for _, _, g in log], bool)}


def replay(arrays, settings, lead_seconds, fs=FS, block=BLOCK, associate_hz=2., rows=None):
    """What render(block, fs, lead) would have produced after each logged origin (rows x block).

    The engine never hears its own output here (earphone-to-microphone leakage is
    not modelled), so a silent run plus replay equals live rendering exactly.
    """
    rows = np.arange(len(arrays['seen'])) if rows is None else np.asarray(rows)
    freq, phasor = arrays['frequency'][rows], arrays['phasor'][rows]
    out = np.zeros((len(rows), block))
    t = lead_seconds+np.arange(block)/fs
    now = arrays['seen'][rows]/fs
    if settings:
        sf = np.array([s.frequency for s in settings])
        distance = np.abs(np.nan_to_num(freq, nan=-1e9)[..., None]-sf)
        nearest = np.argmin(distance, axis=-1)
        matched = np.take_along_axis(distance, nearest[..., None], -1)[..., 0] <= associate_hz
        pick = lambda name: np.array([getattr(s, name) for s in settings], float)[nearest]
        gain = np.where(matched, pick('gain'), 0.)
        gain = np.where(gain > 0, gain, 0.)
        rotation = (np.deg2rad(pick('phase_deg'))[..., None]
                    + 2*np.pi*pick('offset_hz')[..., None]*(now[:, None, None]+t-pick('offset_origin_s')[..., None]))
        wave = np.real(phasor[..., None]*np.exp(1j*(2*np.pi*np.nan_to_num(freq)[..., None]*t+rotation)))
        out = -np.sum(gain[..., None]*wave, axis=1)
    gate = arrays['gate'].astype(float)
    previous = np.concatenate([[0.], gate])[rows]
    ramp = previous[:, None]+(gate[rows]-previous)[:, None]*np.arange(1, block+1)/block
    return out*ramp
