"""Tune-by-ear: the listener's ear finds each hum tone's anti-hum gain and phase.

What matters is the hum at the ear, and no laptop microphone hears that. For
one steady tone the anti-hum needs only two numbers, how loud and how shifted,
and those two absorb everything unknown: the room path from the hum to the ear
compared with the path to the microphone, microphone and earphone sensitivity,
and any constant device delay. A listener can find both with simple choices.

Procedure for one tone (strongest first; tones already tuned stay on):

1. Level, with beats. The anti-hum plays 1 Hz away from the hum, so the two
   drift in and out of step once a second and the hum swells and fades. The
   fades are deepest when the anti-hum is as loud as the hum at the ear,
   whatever the phase. "In which sound do the quiet moments get quieter?"
   Log staircase: compare gain/s with gain*s, move to the winner, take the
   square root of s at each reversal or "same"; stop once s < 1.1 or after 12
   trials.
2. Phase, with slow sweeps. The anti-hum plays 0.25 Hz away, so its phase
   against the hum turns once every 4 s. The listener presses at each quietest
   moment, for 3 turns one way and then 3 turns the other way. Each press gives
   a phase; reaction delay shifts the two directions oppositely, so their
   average cancels it (and any constant playback delay).
3. Fine phase: steady A/B at phase -+30, 15, 8, 4 degrees; move half a step.
4. Fine gain: steady A/B at gain /* 1.3, 1.15, 1.07; move half a step (log).
5. Check: anti-hum off against on, twice, order shuffled. The tone is kept only
   if "on" was quieter both times, or once with "same" the other time;
   otherwise its anti-hum is switched off.

The session never plays anything itself. It hands out presentations (a
ToneSetting and a duration) and takes answers; tune_app.py plays them live and
antihum_study.py plays them through simulated rooms.
"""
from dataclasses import asdict, dataclass, replace

import numpy as np
from scipy import signal

from .antihum import ToneSetting

LEVEL_OFFSET_HZ = 1.
LEVEL_SECONDS = 3.
LEVEL_FIRST_STEP = 2.
LEVEL_LAST_STEP = 1.1
LEVEL_MAX_TRIALS = 12
SWEEP_HZ = .25
SWEEP_TURNS = 3
SWEEP_RETRIES = 1
STEADY_SECONDS = 2.
PHASE_STEPS = (30., 15., 8., 4.)
GAIN_STEPS = (1.3, 1.15, 1.07)
CHECKS = 2

QUESTIONS = {'level':'In which sound do the quiet moments get quieter?',
             'sweep':'Press each time the hum is at its quietest.',
             'phase':'Which is quieter?', 'gain':'Which is quieter?', 'check':'Which is quieter?'}


@dataclass
class Presentation:
    """One sound to play: `setting` for the tone being tuned, for `seconds`.

    The player sets setting.offset_origin_s to the engine time of the first
    output sample, so offset presentations start at the setting's phase.
    """
    label: str
    setting: ToneSetting
    seconds: float


@dataclass
class Step:
    kind: str
    question: str
    presentations: list
    choices: tuple


def circular_mean_deg(angles):
    angles = np.deg2rad(np.asarray(angles, float))
    return float(np.degrees(np.angle(np.mean(np.exp(1j*angles)))) % 360)


def start_presentation(presentation, engine_time):
    """Copy of the presentation's setting with its offset origin at `engine_time`."""
    return replace(presentation.setting, offset_origin_s=float(engine_time))


class TuningSession:
    """State machine for tuning one tone by ear. next_step() -> play it -> answer() or presses()."""
    def __init__(self, frequency, start_gain, min_gain=None, max_gain=None, sweep_turns=SWEEP_TURNS, seed=0):
        if start_gain <= 0:
            raise ValueError('Start gain must be positive.')
        self.frequency, self.gain, self.phase = float(frequency), float(start_gain), 0.
        self.min_gain = float(min_gain or start_gain/32)
        self.max_gain = float(max_gain or start_gain*32)
        self.gain = float(np.clip(self.gain, self.min_gain, self.max_gain))
        self.sweep_turns = sweep_turns
        self.stage, self.step_ratio, self.last_direction, self.trials = 'level', LEVEL_FIRST_STEP, 0, 0
        self.sweeps, self.sweep_attempts, self.fine_index = [], 0, 0
        self.check_on_first = list(np.random.default_rng(seed).integers(0, 2, CHECKS).astype(bool))
        self.check_answers, self.flags, self.log = [], [], []
        self.listening_seconds, self.gain_before_check = 0., None
        self._current = None

    @property
    def done(self):
        return self.stage == 'done'

    def setting(self, gain=None, phase=None, offset=0.):
        return ToneSetting(self.frequency, self.gain if gain is None else float(gain),
                           float((self.phase if phase is None else phase) % 360), float(offset))

    def next_step(self):
        if self._current is not None:
            return self._current
        if self.stage == 'level':
            s = self.step_ratio
            shown = [Presentation('A', self.setting(self.gain/s, 0., LEVEL_OFFSET_HZ), LEVEL_SECONDS),
                     Presentation('B', self.setting(self.gain*s, 0., LEVEL_OFFSET_HZ), LEVEL_SECONDS)]
        elif self.stage == 'sweep':
            direction = 1 if not self.sweeps else -1
            shown = [Presentation('sweep', self.setting(offset=direction*SWEEP_HZ), self.sweep_turns/SWEEP_HZ)]
        elif self.stage == 'phase':
            d = PHASE_STEPS[self.fine_index]
            shown = [Presentation('A', self.setting(phase=self.phase-d), STEADY_SECONDS),
                     Presentation('B', self.setting(phase=self.phase+d), STEADY_SECONDS)]
        elif self.stage == 'gain':
            r = GAIN_STEPS[self.fine_index]
            shown = [Presentation('A', self.setting(self.gain/r), STEADY_SECONDS),
                     Presentation('B', self.setting(self.gain*r), STEADY_SECONDS)]
        elif self.stage == 'check':
            on, off = self.setting(), self.setting(gain=0.)
            first, second = (on, off) if self.check_on_first[len(self.check_answers)] else (off, on)
            shown = [Presentation('A', first, STEADY_SECONDS), Presentation('B', second, STEADY_SECONDS)]
        else:
            return None
        choices = ('presses',) if self.stage == 'sweep' else ('A', 'B', 'same')
        self._current = Step(self.stage, QUESTIONS[self.stage], shown, choices)
        self.listening_seconds += sum(p.seconds for p in shown)
        return self._current

    def _record(self, answer):
        step, self._current = self._current, None
        self.log.append({'kind':step.kind, 'presented':[{'label':p.label, **asdict(p.setting), 'seconds':p.seconds}
                                                         for p in step.presentations], 'answer':answer})
        return step

    def answer(self, choice):
        if self._current is None or self._current.kind == 'sweep' or choice not in ('A', 'B', 'same'):
            raise ValueError('No A/B question is waiting, or the answer is not A, B or same.')
        kind = self._record(choice).kind
        if kind == 'level':
            self.trials += 1
            if choice == 'same':
                self.step_ratio = float(np.sqrt(self.step_ratio))
            else:
                direction = -1 if choice == 'A' else 1
                if self.last_direction and direction != self.last_direction:
                    self.step_ratio = float(np.sqrt(self.step_ratio))
                self.last_direction = direction
                self._set_gain(self.gain*self.step_ratio**direction)
            if self.step_ratio < LEVEL_LAST_STEP or self.trials >= LEVEL_MAX_TRIALS:
                self.stage = 'sweep'
        elif kind == 'phase':
            self.phase = (self.phase+{'A':-.5, 'B':.5, 'same':0.}[choice]*PHASE_STEPS[self.fine_index]) % 360
            self._next_fine(PHASE_STEPS, 'gain')
        elif kind == 'gain':
            self._set_gain(self.gain*GAIN_STEPS[self.fine_index]**{'A':-.5, 'B':.5, 'same':0.}[choice])
            self._next_fine(GAIN_STEPS, 'check')
        else:
            on_first = self.check_on_first[len(self.check_answers)]
            self.check_answers.append('same' if choice == 'same' else 'on' if (choice == 'A') == on_first else 'off')
            if len(self.check_answers) == CHECKS:
                self.gain_before_check = self.gain
                if 'off' in self.check_answers or 'on' not in self.check_answers:
                    self.flags.append('no benefit heard: switched off')
                    self.gain = 0.
                self.stage = 'done'

    def presses(self, times):
        """Press times in seconds from the start of the sweep presentation, as heard."""
        if self._current is None or self._current.kind != 'sweep':
            raise ValueError('No sweep is waiting.')
        p = self._record([float(t) for t in times]).presentations[0]
        offset = p.setting.offset_hz
        phases = [(p.setting.phase_deg+360*offset*t) % 360 for t in times if 0 <= t <= p.seconds]
        if not phases and self.sweep_attempts < SWEEP_RETRIES:
            self.sweep_attempts += 1
            return
        self.sweeps.append((1 if offset > 0 else -1, phases))
        self.sweep_attempts = 0
        if len(self.sweeps) < 2:
            return
        means = [circular_mean_deg(ph) for _, ph in self.sweeps if ph]
        if not means:
            self.flags.append('no quiet moment found: switched off')
            self.gain, self.stage = 0., 'done'
            return
        if len(means) == 1:
            self.flags.append('one sweep direction only (reaction delay not cancelled)')
        self.phase = circular_mean_deg(means)
        self.stage, self.fine_index = 'phase', 0

    def _set_gain(self, gain):
        if gain > self.max_gain*1.0001 and 'gain limit reached (raise the volume a little)' not in self.flags:
            self.flags.append('gain limit reached (raise the volume a little)')
        self.gain = float(np.clip(gain, self.min_gain, self.max_gain))

    def _next_fine(self, steps, following):
        self.fine_index += 1
        if self.fine_index == len(steps):
            self.stage, self.fine_index = following, 0

    def result(self):
        return ToneSetting(self.frequency, self.gain, self.phase % 360)

    def summary(self):
        return {'frequency':self.frequency, 'gain':self.gain, 'phase_deg':self.phase % 360,
                'kept':self.gain > 0, 'gain_before_check':self.gain_before_check, 'flags':list(self.flags),
                'questions':sum(1 for e in self.log if e['kind'] != 'sweep'),
                'sweeps':sum(1 for e in self.log if e['kind'] == 'sweep'),
                'presses':sum(len(e['answer']) for e in self.log if e['kind'] == 'sweep'),
                'listening_seconds':self.listening_seconds}


def erb_hz(frequency):
    """Equivalent rectangular bandwidth of the auditory filter (Glasberg and Moore)."""
    return 24.7*(4.37*frequency/1000+1)


class SimulatedListener:
    """Stand-in listener for offline tests. It hears the simulated ear signal in one auditory band.

    Modelled: an ERB-wide band around the tone (so everything else in that band
    masks it), 20 ms loudness smoothing, judgement noise of `sigma_db` per
    presentation, "same" when two levels differ by less than `same_db`, a
    reaction delay and occasional missed presses. Not modelled: hearing
    thresholds, attention, fatigue, learning, and the fact that real listeners
    may not single out one low pitch among several. Assumes they can.
    """
    def __init__(self, fs, sigma_db=1., seed=0, same_db=1., reaction_s=(.25, .05), miss=.1,
                 settle_s=.3, tail_s=.1, smooth_s=.02, quiet_percentile=5., press_window_db=1.):
        self.fs, self.sigma = fs, float(sigma_db)
        self.rng = np.random.default_rng(seed)
        self.same_db, self.reaction, self.miss = same_db, reaction_s, miss
        self.settle, self.tail = round(settle_s*fs), round(tail_s*fs)
        self.smooth, self.quiet_percentile, self.press_window = max(1, round(smooth_s*fs)), quiet_percentile, press_window_db

    def envelope_db(self, x, frequency):
        """Smoothed band level (dB) over the judged part of a presentation, and the first judged sample."""
        half = erb_hz(frequency)/2
        sos = signal.butter(2, [max(20., frequency-half), min(frequency+half, .45*self.fs)], 'bandpass',
                            fs=self.fs, output='sos')
        band = signal.sosfiltfilt(sos, np.asarray(x, float))
        power = np.convolve(band**2, np.ones(self.smooth)/self.smooth, mode='same')
        end = len(x)-self.tail
        return 10*np.log10(np.maximum(power[self.settle:end], 1e-30)), self.settle

    def level(self, kind, x, frequency):
        env, _ = self.envelope_db(x, frequency)
        if kind == 'level':
            return float(np.percentile(env, self.quiet_percentile))
        return float(10*np.log10(np.mean(10**(env/10))))

    def compare(self, kind, frequency, a, b):
        la = self.level(kind, a, frequency)+self.rng.normal(0, self.sigma)
        lb = self.level(kind, b, frequency)+self.rng.normal(0, self.sigma)
        if abs(la-lb) < self.same_db:
            return 'same'
        return 'A' if la < lb else 'B'

    def press(self, frequency, x, offset_hz):
        """Press times (s from the presentation start): one per turn, near that turn's quietest moment."""
        env, first = self.envelope_db(x, frequency)
        period = round(self.fs/abs(offset_hz))
        times = []
        for start in range(0, len(x), period):
            lo, hi = max(start, first)-first, min(start+period, first+len(env))-first
            if hi-lo < period//4 or self.rng.random() < self.miss:
                continue
            seg = env[lo:hi]
            candidates = np.nonzero(seg <= seg.min()+self.press_window+self.sigma)[0]
            moment = (first+lo+self.rng.choice(candidates))/self.fs
            times.append(moment+max(.1, self.rng.normal(*self.reaction)))
        return times


def run_session(session, play, listener):
    """Drive a session to the end. play(presentation) -> simulated ear signal for it."""
    while not session.done:
        step = session.next_step()
        signals = [play(p) for p in step.presentations]
        if step.kind == 'sweep':
            session.presses(listener.press(session.frequency, signals[0], step.presentations[0].setting.offset_hz))
        else:
            session.answer(listener.compare(step.kind, session.frequency, *signals))
    return session
