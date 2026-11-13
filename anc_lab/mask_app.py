"""Live hum masking window: laptop microphone (or the earbuds' own) in, wired earphones out. Research prototype.

Started only by `python -m anc_lab tune --mask` (tune stays the one command that
plays sound). Nothing plays until every readiness box is ticked and Start is
pressed. The engine listens for hums exactly as in the tuner; instead of an
anti-hum, the earphones get soft band noise around each hum it finds
(anc_lab/masking.py). Output goes through the same OutputLimiter: hard peak
cap, fade in and out, time limit. No audio is stored and nothing is saved.
"""
import threading

import numpy as np

from .antihum import DEFAULT_PEAK_CAP, MAX_PEAK_CAP
from .live_engine import ENGINES
from .masking import MaskGenerator
from .tune_app import RATE, LiveRunner, _flagged, earphone_outputs, microphone_label, pick_microphone, wasapi_devices

START_LEVEL = .3


class MaskRunner(LiveRunner):
    """LiveRunner whose output is masking noise. Dropouts are counted but do not stop it: noise has no timing to lose."""
    def __init__(self, rate=RATE, peak_cap=DEFAULT_PEAK_CAP, max_seconds=900., engine=None, level=START_LEVEL, seed=None):
        super().__init__(rate, peak_cap, max_seconds, engine)
        self.masker = MaskGenerator(rate, peak_cap, level, seed)

    def on_output(self, frames, stamp, glitch=False):
        with self.lock:
            if glitch:
                self._glitch('output', self.clock_out)
            out = self.limiter.process(self.masker.render(frames))
            self.peak_out = max(self.peak_out, float(np.max(np.abs(out))) if frames else 0.)
            self.out_count += frames
            return out

    def pump(self):
        super().pump()
        with self.lock:
            if self.snapshot is not None:
                self.masker.update(self.snapshot[3], self.processed/self.rate)

    def set_level(self, level):
        with self.lock:
            self.masker.set_level(level)

    def masked(self):
        with self.lock:
            return self.masker.centres()


def run_mask_window(peak_cap=DEFAULT_PEAK_CAP, max_minutes=15., allow_speaker_endpoint=False, engine='faint', microphone='laptop'):
    """Open the masking window. Nothing plays until every readiness box is ticked and Start is pressed."""
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
    root.title('Hum masker (research prototype)')
    state = {'streams':None, 'runner':None, 'closing':True}
    pad = {'padx':10, 'pady':3, 'sticky':'w'}
    row = iter(range(100))

    ttk.Label(root, text='Research prototype. It plays soft noise around the hum so the hum stands out less. '
                         'It does not cancel anything or make the room quieter.\n'
                         'Nothing here is calibrated for loudness. Take the earphones out if anything is uncomfortable.',
              wraplength=560).grid(row=next(row), column=0, columnspan=4, **pad)
    ttk.Label(root, text=microphone_label(mic[1], microphone), wraplength=560).grid(row=next(row), column=0, columnspan=4, **pad)
    output_names = [n for _, n in outs]
    output = tk.StringVar(value=output_names[0])
    r = next(row)
    ttk.Label(root, text='Earphones:').grid(row=r, column=0, **pad)
    ttk.Combobox(root, textvariable=output, values=output_names, state='readonly', width=60).grid(row=r, column=1, columnspan=3, **pad)
    checks = []
    for text in ('Earphones are in my ears.',
                 'The system volume is low (about a quarter).',
                 'The earphones chosen above are the ones in my ears, not loudspeakers.',
                 'I can take the earphones out at any time.'):
        var = tk.BooleanVar(value=False)
        checks.append(var)
        ttk.Checkbutton(root, text=text, variable=var, command=lambda: refresh()).grid(row=next(row), column=0, columnspan=4, **pad)
    ttk.Label(root, text=f'Output limit: {peak_cap:g} of digital full scale ({20*np.log10(peak_cap):.0f} dBFS); '
                         f'stops by itself after {max_minutes:g} minutes.').grid(row=next(row), column=0, columnspan=4, **pad)
    r = next(row)
    ttk.Label(root, text='Masking level:').grid(row=r, column=0, **pad)
    level = tk.DoubleVar(value=START_LEVEL)
    ttk.Scale(root, from_=0., to=1., variable=level, length=300,
              command=lambda _: state['runner'] and state['runner'].set_level(level.get())).grid(row=r, column=1, columnspan=3, **pad)
    r = next(row)
    start_button = ttk.Button(root, text='Start', command=lambda: start())
    start_button.grid(row=r, column=0, **pad)
    ttk.Button(root, text='Stop (Esc)', command=lambda: stop()).grid(row=r, column=1, **pad)
    status = ttk.Label(root, text='Not started. Nothing is playing.', wraplength=560)
    status.grid(row=next(row), column=0, columnspan=4, **pad)
    ttk.Label(root, text='Tip: raise the level until the hum just stops standing out, not further.',
              wraplength=560).grid(row=next(row), column=0, columnspan=4, **pad)

    def refresh():
        start_button.state(['!disabled'] if all(v.get() for v in checks) and state['streams'] is None else ['disabled'])

    def start():
        if not all(v.get() for v in checks) or state['streams'] is not None:
            return
        device = outs[output_names.index(output.get())]
        runner = MaskRunner(RATE, peak_cap, max_minutes*60, ENGINES[engine](), level.get())

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
        state.update(runner=runner, streams=streams, closing=False)
        threading.Thread(target=work, daemon=True).start()
        runner.limiter.start()
        for s in streams:
            s.start()
        status.config(text='Listening for hum. A faint hum takes about 10 s to be found; nothing plays until then.')
        tick()

    def stop(reason='stopped'):
        if state['runner'] is not None:
            state['runner'].limiter.stop(reason)
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

    def tick():
        runner = state['runner']
        if state['streams'] is None:
            return
        if runner.limiter.stopped:
            stop(runner.limiter.stop_reason)
            return
        tones, _ = runner.tones()
        heard = ', '.join(f'{f:.0f} Hz' for f, _ in tones) or 'none right now'
        masked = runner.masked()
        status.config(text=f"Hums heard: {heard}. "+(f"Masking around: {', '.join(f'{f:.0f} Hz' for f in masked)}." if masked
                                                     else 'Nothing playing yet (waiting for a steady hum).'))
        root.after(250, tick)

    def close_window():
        stop('window closed')
        root.after(900, root.destroy)

    root.bind('<Escape>', lambda e: stop())
    root.protocol('WM_DELETE_WINDOW', close_window)
    refresh()
    root.mainloop()
