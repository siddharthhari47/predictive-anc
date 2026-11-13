"""Live tune-by-ear: laptop microphone (or the earbuds' own) in, wired earphones out. Research prototype.

Nothing plays until the person using it ticks every readiness box and presses
Start. Output is hard-capped (default 0.05 of digital full scale), fades in and
out, and stops for good after the time limit, on Stop, on a closed window, or
when the audio system drops samples once tuning has begun. A digital cap is not
a loudness calibration: how loud it is depends on the volume setting and the
earphones, which is why the readiness list asks for a low system volume.

The input is the Intel laptop Microphone Array under Windows WASAPI, unless the
user asks for the earbuds' own microphone (`tune --mic earbuds`, which takes an
input Windows names "Headset Microphone (...)"). Both are resolved by name each
time, because the system default input may be a headset and device numbers
change. Bluetooth hands-free microphones are never used: opening one switches
Bluetooth earphones into call mode (mono, telephone-quality sound).
Loudspeaker outputs are refused. No audio is stored: a session file holds the
settings, the questions and answers, device names and counters only.

Timing. The laptop microphone and the earphones are separate devices with
separate clocks (USB earphones always are), so 48 kHz on one is not exactly 48
kHz on the other. A difference of 50 parts per million turns a 100 Hz anti-hum
by about 2 degrees a second against the hum, enough to undo a tuning within a
minute. (The earbuds' own microphone probably runs on the earphones' clock; the
fit below runs either way.) Each stream's sample count is therefore fitted against the system
clock from its callback timestamps (SampleClock), and every output sample is
synthesized for the microphone time at which it is played. Constant offsets in
those timestamps, the earphone delay and the room path are not measured; tuning
absorbs them. If a stream drops or repeats samples after tuning has begun, the
fitted line no longer holds, so the output stops and says so.

The engine runs on a worker thread, never in an audio callback, because one of
its updates can take longer than an audio block.
"""
from collections import deque
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import threading

import numpy as np

from .antihum import DEFAULT_PEAK_CAP, FS, MAX_PEAK_CAP, AntiHumEngine, OutputLimiter, StreamingDecimator, synthesize
from .live_engine import ENGINES
from .tuning import TuningSession, start_presentation

RATE = 48000
ASSOCIATE_HZ = 2.
WARMUP_SECONDS = 3.               # listen before offering tones
MAX_LEAD_SECONDS = .25            # forecasts staler than this are not played (input stalled or fell behind)
LEAD_IN_SECONDS = .3
GAP_SECONDS = .4
START_DRIVE = .25                 # first anti-hum peak: this fraction of the cap
MAX_DRIVE = .8                    # gain never asks for more than this fraction of the cap
GAIN_RANGE = 32.
EARS = {'left':(0,), 'right':(1,), 'both':(0, 1)}
SESSIONS = Path(__file__).resolve().parents[1]/'tuning-sessions'


# ---------------- devices (pure functions of sounddevice's query results) ----------------
def wasapi_devices(hostapis, devices):
    """(inputs, stereo outputs) under Windows WASAPI, as lists of (index, name)."""
    wasapi = [i for i, h in enumerate(hostapis) if 'WASAPI' in h['name']]
    if not wasapi:
        raise LookupError('Windows WASAPI audio is not available on this computer.')
    inputs = [(i, d['name']) for i, d in enumerate(devices) if d['hostapi'] == wasapi[0] and d['max_input_channels'] > 0]
    outputs = [(i, d['name']) for i, d in enumerate(devices) if d['hostapi'] == wasapi[0] and d['max_output_channels'] >= 2]
    return inputs, outputs


def laptop_microphone(inputs):
    """The Intel laptop Microphone Array, never a headset microphone."""
    found = [(i, n) for i, n in inputs if 'microphone array' in n.lower() and 'intel' in n.lower()]
    if not found:
        raise LookupError('No Intel laptop "Microphone Array" under WASAPI. Inputs found: '+'; '.join(n for _, n in inputs))
    return found[0]


def earbud_microphone(inputs):
    """The earbuds' own microphone, used only when asked for (`--mic earbuds`). Wired and USB earbuds
    appear as "Headset Microphone (...)". Never the laptop array, and never a Bluetooth hands-free
    input ("Headset (...)" or "... Hands-Free ..."): opening one puts Bluetooth earphones into call mode."""
    def wanted(name):
        n = name.lower()
        return 'headset microphone' in n and 'microphone array' not in n and 'hands-free' not in n and 'hands free' not in n
    found = [(i, n) for i, n in inputs if wanted(n)]
    if not found:
        raise LookupError('No earbud microphone ("Headset Microphone (...)") under WASAPI; are the earbuds plugged in? '
                          'Bluetooth hands-free microphones are left out on purpose. Inputs found: '+'; '.join(n for _, n in inputs))
    return found[0]


MICROPHONES = {'laptop':laptop_microphone, 'earbuds':earbud_microphone}


def pick_microphone(inputs, microphone='laptop'):
    """The input the user chose: 'laptop' (the default) or 'earbuds'."""
    if microphone not in MICROPHONES:
        raise ValueError(f'Unknown microphone {microphone!r}; choose one of {sorted(MICROPHONES)}.')
    return MICROPHONES[microphone](inputs)


def microphone_label(name, microphone='laptop'):
    """The window's line saying which microphone is listening."""
    if microphone == 'earbuds':
        return (f"Microphone: {name} (WASAPI), the earbuds' own microphone. It is not inside the ear, "
                'and a microphone made for calls may filter out steady noise such as a fan.')
    return f'Microphone: {name} (WASAPI)'


def earphone_outputs(outputs, allow_speaker_endpoint=False):
    """Outputs that may be earphones, likely ones first. Loudspeakers are left out unless allowed
    (some laptops route the headphone jack through an endpoint named "Speakers")."""
    allowed = [(i, n) for i, n in outputs if allow_speaker_endpoint or 'speaker' not in n.lower()]
    likely = lambda name: any(w in name.lower() for w in ('earphone', 'headphone', 'headset', 'earbud'))
    return sorted(allowed, key=lambda d: not likely(d[1]))


def _lookup(settings):
    def setting_for(frequency):
        near = [s for s in settings if abs(s.frequency-frequency) <= ASSOCIATE_HZ]
        return min(near, key=lambda s: abs(s.frequency-frequency)) if near else None
    return setting_for


class SampleClock:
    """Straight line from a stream's sample count to the system clock, fitted to callback timestamps.

    The slope starts at the nominal rate and moves only as far as the data justify
    (prior: within `prior_ppm`; timestamp jitter `jitter_s`), so the first seconds
    stay sensible. Running sums (Welford) keep the fit exact over long sessions.
    """
    def __init__(self, rate, prior_ppm=200., jitter_s=2e-3):
        self.rate, self.prior, self.jitter = rate, prior_ppm*1e-6/rate, jitter_s
        self.reset()

    def reset(self):
        self.n, self.t0, self.mx, self.mt, self.sxx, self.sxt = 0, None, 0., 0., 0., 0.

    def add(self, index, stamp):
        if self.t0 is None:
            self.t0 = float(stamp)
        x, t = float(index), float(stamp)-self.t0
        self.n += 1
        dx = x-self.mx
        self.mx += dx/self.n
        self.mt += (t-self.mt)/self.n
        self.sxx += dx*(x-self.mx)
        self.sxt += dx*(t-self.mt)

    def seconds_per_sample(self):
        data, prior = self.sxx/self.jitter**2, 1/self.prior**2
        return (self.sxt/self.jitter**2+prior/self.rate)/(data+prior)

    def time_of(self, index):
        return self.t0+self.mt+(index-self.mx)*self.seconds_per_sample()

    def index_at(self, stamp):
        return self.mx+(stamp-self.t0-self.mt)/self.seconds_per_sample()

    def ppm(self):
        """How much faster than nominal the stream runs, against the system clock."""
        return (1/(self.seconds_per_sample()*self.rate)-1)*1e6 if self.n else None


# ---------------- everything between the audio callbacks and the engine ----------------
class LiveRunner:
    """Engine, clocks, presentations and output limiter. Opens no device (testable offline).

    on_input() and on_output() are called from the two audio callbacks and only
    hold the lock briefly; pump() runs the engine on the worker thread; play(),
    set_tone(), heard_engine_time(), tones() and state() are for the window.
    """
    def __init__(self, rate=RATE, peak_cap=DEFAULT_PEAK_CAP, max_seconds=900., engine=None):
        self.rate = rate
        self.decimator = StreamingDecimator(rate, FS)
        self.engine = engine or AntiHumEngine()
        self.limiter = OutputLimiter(rate, peak_cap, max_seconds=max_seconds)
        self.clock_in, self.clock_out = SampleClock(rate), SampleClock(rate)
        self.fixed = ([], [])                 # tuned settings per output channel
        self.schedule = []                    # (channels, setting, start, end, label)
        self.lock = threading.Lock()
        self.waiting = threading.Event()      # set when microphone audio is queued
        self._queue = deque()
        self.in_count = self.out_count = self.processed = 0
        self.armed = False                    # from the first presentation on, a dropout ends the session
        self.glitches = {'input':0, 'output':0}
        self.ignored_glitches = {'input':0, 'output':0}
        self.snapshot = None                  # (origin input index, components, gate open, strongest)
        self.engine_counters = {}
        self.lead_range = [np.inf, -np.inf]
        self.stale_blocks = 0
        self.peak_out = 0.
        self._gate_level = 0.

    # ---- audio callbacks ----
    def on_input(self, mono, stamp, glitch=False):
        """Microphone block; `stamp` is the system time of its first sample."""
        with self.lock:
            if glitch:
                self._glitch('input', self.clock_in)
            self.clock_in.add(self.in_count, stamp)
            self.in_count += len(mono)
            self._queue.append(np.array(mono, float))
        self.waiting.set()

    def on_output(self, frames, stamp, glitch=False):
        """`frames` x 2 earphone samples; `stamp` is the system time at which the first is played."""
        with self.lock:
            if glitch:
                self._glitch('output', self.clock_out)
            self.clock_out.add(self.out_count, stamp)
            out = np.zeros((frames, 2))
            gate = False
            if self.snapshot is not None and frames:
                origin, components, gate, _ = self.snapshot
                lead = (self.input_index(self.out_count)-origin)/self.rate
                self.lead_range = [min(self.lead_range[0], lead), max(self.lead_range[1], lead)]
                if lead > MAX_LEAD_SECONDS:
                    gate = False
                    self.stale_blocks += 1
                # Output sample spacing in microphone samples (the two clocks differ slightly).
                spacing = self.clock_out.seconds_per_sample()/self.clock_in.seconds_per_sample()
                cuts = {0, frames}
                for _, _, start, end, _ in self.schedule:
                    cuts |= {k-self.out_count for k in (start, end) if 0 < k-self.out_count < frames}
                cuts = sorted(cuts)
                for a, b in zip(cuts[:-1], cuts[1:]):
                    index = self.out_count+a
                    for channel in (0, 1):
                        settings = self._settings(channel, index)
                        if settings:
                            out[a:b, channel] = synthesize(components, _lookup(settings), origin/self.rate, b-a,
                                                           self.rate/spacing, (self.input_index(index)-origin)/self.rate)
            target = float(gate)
            ramp = self._gate_level+(target-self._gate_level)*np.arange(1, frames+1)/max(frames, 1)
            self._gate_level = target
            out = self.limiter.process(out*ramp[:, None])
            self.peak_out = max(self.peak_out, float(np.max(np.abs(out))) if frames else 0.)
            self.out_count += frames
            self.schedule = [p for p in self.schedule if p[3] > self.out_count]
            return out

    def _glitch(self, kind, clock):
        if self.armed:
            self.glitches[kind] += 1
            self.limiter.stop(f'the audio system dropped or repeated {kind} samples, so the timing changed; start again to retune')
        else:
            self.ignored_glitches[kind] += 1
            clock.reset()

    # ---- worker thread ----
    def pump(self):
        """Run queued microphone audio through the engine, oldest first."""
        while True:
            with self.lock:
                if not self._queue:
                    return
                chunk = self._queue.popleft()
            analysis = self.decimator.process(chunk)
            if len(analysis):
                self.engine.push(analysis)
            with self.lock:
                self.processed += len(chunk)
                if self.engine.origin_seen:
                    # The decimator keeps every ratio-th input sample, starting at ratio-1.
                    self.snapshot = (self.engine.origin_seen*self.decimator.ratio-1, list(self.engine.components),
                                     bool(self.engine.gate_open), self.engine.strongest())
                self.engine_counters = dict(self.engine.counters)

    # ---- time ----
    def input_index(self, k):
        """Microphone sample index recorded when output sample k is played (both clocks fitted)."""
        return self.clock_in.index_at(self.clock_out.time_of(k))

    def engine_time(self, k):
        return self.input_index(k)/self.rate

    def heard_engine_time(self, stream_time):
        """Engine time of what the earphones play at system time `stream_time` (for press times)."""
        with self.lock:
            return self.clock_in.index_at(stream_time)/self.rate if self.clock_in.n else None

    # ---- window ----
    def _settings(self, channel, index):
        settings = list(self.fixed[channel])
        for channels, setting, start, end, _ in self.schedule:
            if channel in channels and start <= index < end:
                settings = [s for s in settings if abs(s.frequency-setting.frequency) > ASSOCIATE_HZ]+[setting]
        return settings

    def play(self, ear, presentations, lead_in_s=LEAD_IN_SECONDS, gap_s=GAP_SECONDS):
        """Queue presentations back to back: [(label, first output index, end index, engine time at start)]."""
        with self.lock:
            if not (self.clock_in.n and self.clock_out.n):
                raise RuntimeError('Both audio streams must be running before anything is played.')
            self.armed = True
            start = self.out_count+round(lead_in_s*self.rate)
            timeline = []
            for p in presentations:
                end = start+round(p.seconds*self.rate)
                begin = self.engine_time(start)
                self.schedule.append((EARS[ear], start_presentation(p, begin), start, end, p.label))
                timeline.append((p.label, start, end, begin))
                start = end+round(gap_s*self.rate)
            return timeline

    def set_tone(self, ear, setting):
        with self.lock:
            self.armed = True
            for channel in EARS[ear]:
                self.fixed[channel][:] = [s for s in self.fixed[channel] if abs(s.frequency-setting.frequency) > ASSOCIATE_HZ]+[setting]

    def tones(self):
        with self.lock:
            return (self.snapshot[3], self.snapshot[2]) if self.snapshot else ([], False)

    def state(self):
        with self.lock:
            spacing = (self.clock_out.seconds_per_sample()/self.clock_in.seconds_per_sample()
                       if self.clock_in.n and self.clock_out.n else None)
            return {'seconds_heard':self.in_count/self.rate, 'seconds_processed':self.processed/self.rate,
                    'seconds_played':self.out_count/self.rate, 'glitches':dict(self.glitches),
                    'ignored_glitches_before_tuning':dict(self.ignored_glitches), 'stopped':self.limiter.stopped,
                    'stop_reason':self.limiter.stop_reason, 'clipped_samples':self.limiter.clipped_samples,
                    'peak_out':self.peak_out, 'stale_blocks':self.stale_blocks,
                    'forecast_lead_s':self.lead_range if np.isfinite(self.lead_range[0]) else None,
                    'microphone_clock_ppm_vs_system':self.clock_in.ppm(), 'earphone_clock_ppm_vs_system':self.clock_out.ppm(),
                    'microphone_vs_earphone_ppm':None if spacing is None else (spacing-1)*1e6,
                    'engine_counters':dict(self.engine_counters)}


def session_record(devices, runner, sessions, cap, engine):
    """What a saved session holds: settings, questions and answers, devices, counters. Never audio."""
    return {'kind':'tune_by_ear_live_session', 'saved_utc':datetime.now(timezone.utc).isoformat(),
            'audio_stored':False, 'peak_cap':cap, 'spl_calibrated':False, 'devices':devices, 'engine':engine,
            'settings':{'left':[asdict(s) for s in runner.fixed[0]], 'right':[asdict(s) for s in runner.fixed[1]]},
            'tones':[{'ear':ear, **session.summary(), 'log':session.log} for ear, session in sessions], 'runner':runner.state()}


def _flagged(flags):
    return bool(flags.input_overflow or flags.input_underflow or flags.output_underflow or flags.output_overflow)


# ---------------- window ----------------
def run_window(peak_cap=DEFAULT_PEAK_CAP, max_minutes=15., allow_speaker_endpoint=False, engine='smoothed', microphone='laptop'):
    """Open the tuner window. Nothing plays until every readiness box is ticked and Start is pressed."""
    import tkinter as tk
    from tkinter import ttk
    import sounddevice as sd

    if not 0 < peak_cap <= MAX_PEAK_CAP:
        raise ValueError(f'Peak cap must be in (0, {MAX_PEAK_CAP}].')
    if not 0 < max_minutes <= 30:
        raise ValueError('Session length must be at most 30 minutes.')
    inputs, outputs = wasapi_devices(sd.query_hostapis(), sd.query_devices())
    mic = pick_microphone(inputs, microphone)
    outs = earphone_outputs(outputs, allow_speaker_endpoint)
    if not outs:
        raise LookupError('No earphone output found under WASAPI (loudspeakers are refused).')

    root = tk.Tk()
    root.title('Hum tuner (research prototype)')
    state = {'streams':None, 'runner':None, 'worker':None, 'closing':True, 'session':None, 'step':None, 'timeline':[],
             'presses':[], 'sessions':[], 'devices':None, 'ear':tk.StringVar(value='left')}
    pad = {'padx':10, 'pady':3, 'sticky':'w'}
    row = iter(range(100))

    ttk.Label(root, text='Research prototype. It plays a quiet anti-hum into your earphones while you answer questions.\n'
                         'Nothing here is calibrated for loudness. Take the earphones out if anything is uncomfortable.',
              wraplength=560).grid(row=next(row), column=0, columnspan=4, **pad)
    ttk.Label(root, text=microphone_label(mic[1], microphone), wraplength=560).grid(row=next(row), column=0, columnspan=4, **pad)
    output_names = [n for _, n in outs]
    output = tk.StringVar(value=output_names[0])
    r = next(row)
    ttk.Label(root, text='Earphones:').grid(row=r, column=0, **pad)
    ttk.Combobox(root, textvariable=output, values=output_names, state='readonly', width=60).grid(row=r, column=1, columnspan=3, **pad)
    r = next(row)
    ttk.Label(root, text='Tune for:').grid(row=r, column=0, **pad)
    for k, ear in enumerate(('left', 'right', 'both')):
        ttk.Radiobutton(root, text=f'{ear} ear' if ear != 'both' else 'both ears together', value=ear,
                        variable=state['ear']).grid(row=r, column=1+k, **pad)
    checks = []
    for text in ('Wired earphones are in my ears, and their own noise cancelling (if any) is switched off.',
                 'The system volume is low (about a quarter).',
                 'The earphones chosen above are the ones in my ears, not loudspeakers.',
                 'I can take the earphones out at any time.'):
        var = tk.BooleanVar(value=False)
        checks.append(var)
        ttk.Checkbutton(root, text=text, variable=var, command=lambda: refresh()).grid(row=next(row), column=0, columnspan=4, **pad)
    ttk.Label(root, text=f'Output limit: {peak_cap:g} of digital full scale ({20*np.log10(peak_cap):.0f} dBFS); '
                         f'stops by itself after {max_minutes:g} minutes.').grid(row=next(row), column=0, columnspan=4, **pad)
    r = next(row)
    start_button = ttk.Button(root, text='Start', command=lambda: start())
    start_button.grid(row=r, column=0, **pad)
    ttk.Button(root, text='Stop (Esc)', command=lambda: stop()).grid(row=r, column=1, **pad)
    tune_button = ttk.Button(root, text='Tune the strongest untuned tone', command=lambda: tune_next())
    tune_button.grid(row=r, column=2, columnspan=2, **pad)
    status = ttk.Label(root, text='Not started. Nothing is playing.', wraplength=560)
    status.grid(row=next(row), column=0, columnspan=4, **pad)
    question = ttk.Label(root, text='', font=('Segoe UI', 12, 'bold'), wraplength=560)
    question.grid(row=next(row), column=0, columnspan=4, **pad)
    r = next(row)
    answer_buttons = {c:ttk.Button(root, text=t, command=lambda c=c: answer(c))
                      for c, t in (('A', 'A (key a)'), ('B', 'B (key b)'), ('same', 'Same (key s)'))}
    for k, b in enumerate(answer_buttons.values()):
        b.grid(row=r, column=k, **pad)
    again = ttk.Button(root, text='Play again', command=lambda: play_step())
    again.grid(row=r, column=3, **pad)
    press_button = ttk.Button(root, text='Quietest now (space bar)', command=lambda: press())
    press_button.grid(row=next(row), column=0, columnspan=2, **pad)
    results = ttk.Label(root, text='', wraplength=560, justify='left')
    results.grid(row=next(row), column=0, columnspan=4, **pad)
    save_button = ttk.Button(root, text='Save settings (no audio)', command=lambda: save())
    save_button.grid(row=next(row), column=0, columnspan=2, **pad)

    def enable(widget, on):
        widget.state(['!disabled'] if on else ['disabled'])

    def running():
        return state['streams'] is not None and not state['runner'].limiter.stopped

    def refresh():
        enable(start_button, all(v.get() for v in checks) and state['streams'] is None)
        enable(tune_button, running() and state['session'] is None and state['runner'].processed >= WARMUP_SECONDS*RATE)
        step = state['step']
        heard = running() and step is not None and state['runner'].out_count >= state['timeline'][-1][2]
        for b in answer_buttons.values():
            enable(b, heard and step.kind != 'sweep')
        enable(again, heard and step.kind != 'sweep')
        enable(press_button, running() and step is not None and step.kind == 'sweep')
        enable(save_button, bool(state['sessions']))

    def start():
        if not all(v.get() for v in checks) or state['streams'] is not None:
            return
        device = outs[output_names.index(output.get())]
        runner = LiveRunner(RATE, peak_cap, max_minutes*60, ENGINES[engine]())

        def heard(indata, frames, time_info, flags):
            runner.on_input(indata[:, 0], time_info.inputBufferAdcTime or time_info.currentTime, _flagged(flags))

        def play(outdata, frames, time_info, flags):
            try:
                outdata[:] = runner.on_output(frames, time_info.outputBufferDacTime or time_info.currentTime, _flagged(flags))
            except Exception:
                outdata.fill(0)
                raise sd.CallbackAbort
        streams = []
        try:
            streams.append(sd.InputStream(device=mic[0], samplerate=RATE, channels=1, dtype='float32', latency='high', callback=heard))
            streams.append(sd.OutputStream(device=device[0], samplerate=RATE, channels=2, dtype='float32', latency='high', callback=play))
        except Exception as exc:
            for s in streams:
                s.close()
            status.config(text=f'Could not open the microphone or the earphones: {exc}. Nothing is playing.')
            return

        def work():
            while not state['closing']:
                runner.waiting.wait(.05)
                runner.waiting.clear()
                runner.pump()
        state.update(runner=runner, streams=streams, closing=False, sessions=[], session=None, step=None,
                     devices={'microphone':microphone, 'input':mic[1], 'output':device[1], 'host_api':'Windows WASAPI', 'rate':RATE,
                              'reported_latency_s':{'input':streams[0].latency, 'output':streams[1].latency}})
        state['worker'] = threading.Thread(target=work, daemon=True)
        state['worker'].start()
        results.config(text='')
        runner.limiter.start()
        for s in streams:
            s.start()
        status.config(text='Listening for hum. The anti-hum stays silent until you tune a tone.')
        tick()

    def stop(reason='stopped'):
        if state['runner'] is not None:
            state['runner'].limiter.stop(reason)
        state['step'], state['session'] = None, None
        question.config(text='')
        if state['streams'] is not None:
            root.after(800, close_streams)

    def close_streams():
        if state['streams'] is not None:
            for s in state['streams']:
                s.stop()
                s.close()
            state['streams'], state['closing'] = None, True
            status.config(text=f"Stopped ({state['runner'].limiter.stop_reason}). Nothing is playing.")
        refresh()

    def tune_next():
        runner, ear = state['runner'], state['ear'].get()
        done = [session.frequency for e, session in state['sessions'] if set(EARS[e]) & set(EARS[ear])]
        tones, _ = runner.tones()
        tones = [(f, a) for f, a in tones if all(abs(f-d) > ASSOCIATE_HZ for d in done)]
        if not tones:
            status.config(text='No untuned steady tone is being detected right now.')
            return
        f, amplitude = tones[0]
        start_gain = START_DRIVE*peak_cap/amplitude
        state['session'] = TuningSession(f, start_gain, min_gain=start_gain/GAIN_RANGE, max_gain=MAX_DRIVE*peak_cap/amplitude,
                                         seed=int(np.random.default_rng().integers(1 << 30)))
        state['tuning_ear'] = ear
        status.config(text=f'Tuning the tone near {f:.1f} Hz ({ear}).')
        next_step()

    def next_step():
        session = state['session']
        if session.done:
            state['runner'].set_tone(state['tuning_ear'], session.result())
            state['sessions'].append((state['tuning_ear'], session))
            state['session'], state['step'] = None, None
            question.config(text='')
            results.config(text='\n'.join(
                f"{e}: {s.frequency:.1f} Hz "+('kept' if s.gain > 0 else 'switched off')
                +f" ({s.summary()['questions']} answers, {s.listening_seconds:.0f} s)"+(f" [{'; '.join(s.flags)}]" if s.flags else '')
                for e, s in state['sessions']))
            refresh()
            return
        state['step'] = session.next_step()
        play_step()

    def play_step():
        step = state['step']
        if step is None or not running():
            return
        state['timeline'] = state['runner'].play(state['tuning_ear'], step.presentations)
        state['presses'] = []
        question.config(text=step.question)

    def press():
        step = state['step']
        if step is None or step.kind != 'sweep' or not running():
            return
        heard_at = state['runner'].heard_engine_time(state['streams'][1].time)
        if heard_at is not None:
            state['presses'].append(heard_at-state['timeline'][0][3])

    def answer(choice):
        step = state['step']
        if step is None or step.kind == 'sweep' or state['runner'].out_count < state['timeline'][-1][2]:
            return
        state['session'].answer(choice)
        next_step()

    def save():
        SESSIONS.mkdir(exist_ok=True)
        path = SESSIONS/f"tune-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        record = session_record(state['devices'], state['runner'], state['sessions'], peak_cap, engine)
        with path.open('x', encoding='utf-8') as handle:
            json.dump(record, handle, indent=1, default=lambda v: v.item() if isinstance(v, np.generic) else str(v))
        status.config(text=f'Saved {path} (settings and answers only, no audio).')

    def tick():
        runner = state['runner']
        if state['streams'] is None:
            return
        if runner.limiter.stopped:
            stop(runner.limiter.stop_reason)
            return
        step = state['step']
        if step is not None and step.kind == 'sweep' and runner.out_count >= state['timeline'][-1][2]+round(.5*RATE):
            state['session'].presses(state['presses'])
            next_step()
        elif step is not None:
            playing = [label for label, a, b, _ in state['timeline'] if a <= runner.out_count < b]
            question.config(text=step.question+(f'   Now playing: {playing[0]}' if playing else ''))
        elif state['session'] is None:
            tones, gate = runner.tones()
            found = ', '.join(f'{f:.1f} Hz' for f, _ in tones) or (
                'none yet (a faint hum takes about 10 s)' if engine == 'faint' else 'none yet')
            status.config(text=f"Listening. Steady tones heard by the microphone: {found}. "
                               f"Anti-hum {'allowed' if gate else 'held off'} by the safety gate.")
        refresh()
        root.after(100, tick)

    def close_window():
        stop('window closed')
        root.after(900, root.destroy)

    root.bind('<space>', lambda e: press())
    for key, choice in (('a', 'A'), ('b', 'B'), ('s', 'same')):
        root.bind(key, lambda e, c=choice: answer(c))
    root.bind('<Escape>', lambda e: stop())
    root.protocol('WM_DELETE_WINDOW', close_window)
    refresh()
    root.mainloop()
