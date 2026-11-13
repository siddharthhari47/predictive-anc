"""Checks for the anti-hum engine, output limiter, tune-by-ear procedure, room simulation and live runner.

No test opens an audio device.
"""
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np
from scipy import signal

from anc_lab.antihum import (BLOCK, FS, V2_SELECTOR, AntiHumEngine, OutputLimiter, StreamingDecimator, ToneSetting,
                             log_arrays, replay)
from anc_lab.antihum_study import PROTOCOL, RoomPlayer, modal_irs, run_tune_by_ear_study
from anc_lab.real_hum_study import ogg_audio_only, run_real_hum_study
from anc_lab.tone_selection import SelectedToneForecaster, ToneSelector
from anc_lab.tune_app import (LiveRunner, SampleClock, earbud_microphone, earphone_outputs, laptop_microphone,
                              microphone_label, pick_microphone, wasapi_devices)
from anc_lab.tuning import SWEEP_HZ, Presentation, SimulatedListener, TuningSession, run_session, start_presentation

RATE = 48000


def hum(seconds, freqs=((120.3, .01, .7),), noise=1e-4, fs=FS, seed=0):
    t = np.arange(round(seconds*fs))/fs
    x = sum(a*np.cos(2*np.pi*f*t+p) for f, a, p in freqs)
    return x+noise*np.random.default_rng(seed).standard_normal(len(t))


class TwoClockSim:
    """Microphone and earphones on separate clocks (system clock = true time), callbacks in time order.

    The ear hears the hum 2.1 ms later and 0.8 times as loud as the microphone; the
    reported callback stamps carry constant errors and 1 ms jitter.
    """
    def __init__(self, runner, ppm_in=100., ppm_out=-100., f=120.3, block=480, seed=0):
        self.runner, self.f, self.block = runner, f, block
        self.rng = np.random.default_rng(seed)
        self.r_in, self.r_out = RATE*(1+ppm_in*1e-6), RATE*(1+ppm_out*1e-6)
        self.a_in, self.a_out = .0123, .0371
        self.j = self.k = 0
        self.out = []

    def hum_mic(self, tau):
        return .01*np.cos(2*np.pi*self.f*tau+.7)

    def hum_ear(self, tau):
        return .008*np.cos(2*np.pi*self.f*(tau-.0021)+.7)

    def ear_time(self, k):
        return self.a_out+np.asarray(k)/self.r_out+.001

    def run_until(self, t_end):
        while True:
            t_in = self.a_in+(self.j+self.block-1)/self.r_in+.002     # after its last sample is captured
            t_out = self.a_out+self.k/self.r_out-.02                  # 20 ms before its first sample plays
            if min(t_in, t_out) > t_end:
                return
            if t_in <= t_out:
                tau = self.a_in+(self.j+np.arange(self.block))/self.r_in
                x = self.hum_mic(tau)+1e-4*self.rng.standard_normal(self.block)
                self.runner.on_input(x, tau[0]+.004+1e-3*self.rng.standard_normal())
                self.runner.pump()
                self.j += self.block
            else:
                stamp = self.a_out+self.k/self.r_out-.006+1e-3*self.rng.standard_normal()
                self.out.append(self.runner.on_output(self.block, stamp))
                self.k += self.block

    def output(self):
        y = np.concatenate(self.out)
        tau = self.ear_time(np.arange(len(y)))
        return tau, self.hum_ear(tau), y


def quadrature_runner():
    """Left plays the tone at phase 0, right at 90 degrees: any setting is a mix of the two."""
    runner = LiveRunner()
    runner.set_tone('left', ToneSetting(120.3, 1., 0.))
    runner.set_tone('right', ToneSetting(120.3, 1., 90.))
    runner.limiter.start()
    return runner


class EngineTests(unittest.TestCase):
    def test_engine_matches_offline_v2_forecaster(self):
        x = hum(6., ((88., .3, .2), (141., .2, 1.)), noise=.01)
        engine, origins, forecasts = AntiHumEngine(), [], []
        horizons = np.arange(1, 41)
        for i in range(0, len(x), BLOCK):
            engine.push(x[i:i+BLOCK])
            if engine.seen > 2*FS:
                origins.append(engine.origin_seen-1)
                forecasts.append(engine.shadow_forecast(horizons))
        offline = SelectedToneForecaster(FS, ToneSelector(FS, **V2_SELECTOR), window_seconds=.3, release_ratio=.5,
                                         release_window_seconds=.1).predict(x, origins, horizons)
        self.assertGreater(np.min(np.max(np.abs(offline), axis=1)), .1)   # both tones forecast at every origin
        np.testing.assert_allclose(np.array(forecasts), offline, atol=1e-9)

    def test_engine_is_silent_without_settings(self):
        engine = AntiHumEngine()
        for i in range(0, 4*FS, BLOCK):
            engine.push(hum(4.)[i:i+BLOCK])
            self.assertFalse(np.any(engine.render(BLOCK)))
        self.assertTrue(engine.components)

    def test_replay_matches_live_render(self):
        x = hum(4., ((97., .05, .3),), noise=1e-3)
        settings = [ToneSetting(97., .8, 33., .25, 1.)]
        engine = AntiHumEngine(keep_log=True)
        engine.settings = list(settings)
        live = []
        for i in range(0, len(x), BLOCK):
            engine.push(x[i:i+BLOCK])
            live.append(engine.render(BLOCK, FS, .03))
        np.testing.assert_allclose(replay(log_arrays(engine.log), settings, .03), np.array(live), atol=1e-12)

    def test_ideal_path_cancels(self):
        x = hum(6., noise=1e-4)
        delay = 40                                           # output index = origin + delay
        engine = AntiHumEngine()
        engine.set_tone(ToneSetting(120.3, 1., 0.))
        out = np.zeros(len(x)+BLOCK+delay)
        for i in range(0, len(x), BLOCK):
            engine.push(x[i:i+BLOCK])
            out[engine.seen+delay:engine.seen+delay+BLOCK] = engine.render(BLOCK, FS, (1+delay)/FS)
        part = slice(3*FS, len(x))
        self.assertGreater(10*np.log10(np.sum(x[part]**2)/np.sum((x[part]+out[part])**2)), 30.)

    def test_decimator_reports_newest_sample_age(self):
        decimator, seen, picked = StreamingDecimator(RATE), 0, 0
        for n in (7, 24, 1, 100, 960, 13):
            out = decimator.process(np.zeros(n))
            seen, picked = seen+n, picked+len(out)
            newest = picked*decimator.ratio-1                 # input index of the newest output sample
            self.assertEqual(decimator.newest_age, seen-1-newest)


class LimiterTests(unittest.TestCase):
    def test_cap_fades_and_refusals(self):
        with self.assertRaises(ValueError):
            OutputLimiter(RATE, .25)
        with self.assertRaises(ValueError):
            OutputLimiter(RATE, .05, max_seconds=4000)
        limiter = OutputLimiter(RATE, .05, fade_seconds=.1)
        self.assertFalse(np.any(limiter.process(np.ones(480))))  # silent until started
        limiter.start()
        ramp = limiter.process(np.full(9600, .01))
        self.assertTrue(np.all(np.diff(ramp[:4800]) >= 0) and ramp[0] < .001 and abs(ramp[-1]-.01) < 1e-12)
        loud = limiter.process(np.ones((480, 2)))
        self.assertEqual(loud.shape, (480, 2))
        self.assertLessEqual(np.max(np.abs(loud)), .05)
        self.assertGreater(limiter.clipped_samples, 0)
        bad = limiter.process(np.array([0., np.nan, 0.]))
        self.assertTrue(limiter.stopped and not np.any(bad) and limiter.stop_reason == 'non-finite output')
        limiter.start()
        self.assertFalse(np.any(limiter.process(np.ones(480))))  # stays stopped for good

    def test_time_limit_stops(self):
        limiter = OutputLimiter(RATE, .05, fade_seconds=.01, max_seconds=1.)
        limiter.start()
        out = np.concatenate([limiter.process(np.full(4800, .01)) for _ in range(12)])
        self.assertTrue(limiter.stopped and limiter.stop_reason == 'time limit')
        self.assertFalse(np.any(out[RATE:]))


class TuningTests(unittest.TestCase):
    def test_tuning_converges_with_simulated_listener(self):
        f, ear_gain, ear_phase = 110., .5, 140.
        rng = np.random.default_rng(3)
        clock = {'t':0.}

        def play(presentation):
            n = round(presentation.seconds*FS)
            t = clock['t']+np.arange(n)/FS
            s = start_presentation(presentation, clock['t'])
            clock['t'] += n/FS+.4
            anti = -s.gain*np.cos(2*np.pi*f*t+np.deg2rad(s.phase_deg)+2*np.pi*s.offset_hz*(t-s.offset_origin_s))
            return ear_gain*np.cos(2*np.pi*f*t+np.deg2rad(ear_phase))+anti+.003*rng.standard_normal(n)
        session = run_session(TuningSession(f, .15, seed=1), play, SimulatedListener(FS, 1., seed=2))
        result = session.result()
        self.assertTrue(session.done and result.gain > 0)
        self.assertLess(abs(20*np.log10(result.gain/ear_gain)), 2.)
        self.assertLess(abs((result.phase_deg-ear_phase+180) % 360-180), 15.)


class RoomTests(unittest.TestCase):
    def test_modal_room_is_causal_with_expected_decay(self):
        dims, rt60, source, receiver = [4.3, 3.7, 2.6], .35, [1., 1.2, 1.1], [3.1, 2.4, 1.3]
        (h,), modes = modal_irs(dims, rt60, source, [receiver])
        self.assertGreater(modes, 1000)
        arrival = PROTOCOL['room']['modelling_delay_samples']+np.linalg.norm(np.subtract(receiver, source))/343.*FS
        energy = np.cumsum(h**2)/np.sum(h**2)
        self.assertLess(energy[int(arrival)-12], .01)        # (almost) nothing before the sound can arrive
        decay = 10*np.log10(np.maximum(1-energy, 1e-12)+1e-12)
        a, b = np.argmax(decay < -5), np.argmax(decay < -25)
        estimated = 60*(b-a)/FS/20
        self.assertLess(abs(estimated/rt60-1), .3)

    def test_room_player_never_reaches_held_out_audio(self):
        scene = {'warm':100, 'prefix':2100}
        player = RoomPlayer(scene, .03, [])
        with self.assertRaises(ValueError):
            player(Presentation('A', ToneSetting(100., 1.), 1.5))


class LiveRunnerTests(unittest.TestCase):
    def test_sample_clock_finds_rate_and_starts_from_nominal(self):
        rng = np.random.default_rng(0)
        clock = SampleClock(RATE)
        clock.add(0, 5.)
        self.assertAlmostEqual(clock.ppm(), 0.)
        true_rate = RATE*(1+80e-6)
        for k in range(1, 3000):
            clock.add(480*k, 5.+480*k/true_rate+1e-3*rng.standard_normal())
        self.assertLess(abs(clock.ppm()-80.), 5.)
        self.assertLess(abs(clock.time_of(480*3000)-(5.+480*3000/true_rate)), 1e-4)

    def test_tuning_survives_clock_mismatch(self):
        runner = quadrature_runner()
        sim = TwoClockSim(runner)
        sim.run_until(25.)
        tau, h, y = sim.output()
        early, late = ((tau >= lo) & (tau < lo+2) for lo in (4, 22))
        coef, *_ = np.linalg.lstsq(y[early], -h[early], rcond=None)   # the best setting found early ...
        attenuation = 10*np.log10(np.sum(h[late]**2)/np.sum((h[late]+y[late]@coef)**2))
        self.assertGreater(attenuation, 15.)                           # ... still cancels 18 s later
        self.assertLess(abs(runner.state()['microphone_vs_earphone_ppm']-200.), 15.)
        self.assertEqual(runner.state()['stale_blocks'], 0)

    def test_sweep_presses_find_the_cancelling_phase(self):
        oracle = quadrature_runner()
        sim = TwoClockSim(oracle)
        sim.run_until(31.)
        tau, h, y = sim.output()
        w = (tau >= 5) & (tau < 30)
        (a, b), *_ = np.linalg.lstsq(y[w], -h[w], rcond=None)
        best = np.degrees(np.arctan2(b, a)) % 360
        runner = LiveRunner()                                          # same input, so the same engine states
        runner.limiter.start()
        sim = TwoClockSim(runner)
        sim.run_until(4.)
        session = TuningSession(runner.tones()[0][0][0], float(np.hypot(a, b)))
        session.stage = 'sweep'
        for _ in range(2):
            label, start, end, begin = runner.play('left', session.next_step().presentations)[0]
            sim.run_until(sim.ear_time(end)+.5)
            tau, h, y = sim.output()
            power = np.convolve((h[start:end]+y[start:end, 0])**2, np.ones(9600)/9600, mode='same')
            turn = round(RATE/SWEEP_HZ)
            quietest = [s+int(np.argmin(power[s:s+turn])) for s in range(0, len(power)-turn+1, turn)]
            session.presses([runner.heard_engine_time(tau[start+i])-begin for i in quietest])
        self.assertEqual(session.stage, 'phase')
        self.assertLess(abs((session.phase-best+180) % 360-180), 3.)

    def test_dropouts_reset_before_tuning_and_stop_after(self):
        runner = LiveRunner()
        runner.limiter.start()
        runner.on_output(480, 1., glitch=True)
        self.assertEqual(runner.ignored_glitches['output'], 1)
        self.assertFalse(runner.limiter.stopped)
        with self.assertRaises(RuntimeError):
            runner.play('left', [Presentation('A', ToneSetting(100., .1), 1.)])
        runner.on_input(np.zeros(480), 1.)
        runner.pump()
        runner.play('left', [Presentation('A', ToneSetting(100., .1), 1.)])
        runner.on_input(np.zeros(480), 1.01, glitch=True)
        self.assertTrue(runner.limiter.stopped and runner.glitches['input'] == 1)

    def test_runner_output_is_capped_and_silent_untuned(self):
        runner = LiveRunner(peak_cap=.02)
        runner.limiter.start()
        sim = TwoClockSim(runner)
        sim.hum_mic = lambda tau: .5*np.cos(2*np.pi*120.3*tau)
        sim.run_until(3.)
        self.assertFalse(np.any(sim.output()[2]))
        runner.set_tone('both', ToneSetting(120.3, 1., 0.))
        sim.run_until(5.)
        self.assertLessEqual(np.max(np.abs(sim.output()[2])), .02)
        self.assertGreater(runner.limiter.clipped_samples, 0)


class DeviceTests(unittest.TestCase):
    hostapis = [{'name':'MME'}, {'name':'Windows WASAPI'}]
    devices = [{'name':'Microphone Array (Intel Smart Sound)', 'hostapi':0, 'max_input_channels':2, 'max_output_channels':0},
               {'name':'Headset Microphone (USB earbuds)', 'hostapi':1, 'max_input_channels':1, 'max_output_channels':0},
               {'name':'Microphone Array (Intel® Smart Sound Technology)', 'hostapi':1, 'max_input_channels':2, 'max_output_channels':0},
               {'name':'Speakers (Realtek(R) Audio)', 'hostapi':1, 'max_input_channels':0, 'max_output_channels':2},
               {'name':'Headset Earphone (USB earbuds)', 'hostapi':1, 'max_input_channels':0, 'max_output_channels':2}]

    def test_picks_intel_array_under_wasapi_and_refuses_speakers(self):
        inputs, outputs = wasapi_devices(self.hostapis, self.devices)
        self.assertEqual(laptop_microphone(inputs)[0], 2)
        self.assertEqual(earphone_outputs(outputs), [(4, 'Headset Earphone (USB earbuds)')])
        self.assertEqual([i for i, _ in earphone_outputs(outputs, allow_speaker_endpoint=True)], [4, 3])

    def test_no_laptop_microphone_is_an_error(self):
        inputs, _ = wasapi_devices(self.hostapis, self.devices[:2])
        with self.assertRaises(LookupError):
            laptop_microphone(inputs)
        with self.assertRaises(LookupError):
            wasapi_devices([{'name':'MME'}], self.devices[:1])

    def test_earbud_microphone_only_when_asked(self):
        inputs, _ = wasapi_devices(self.hostapis, self.devices)
        self.assertEqual(pick_microphone(inputs)[0], 2)
        self.assertEqual(pick_microphone(inputs, 'earbuds'), (1, 'Headset Microphone (USB earbuds)'))
        with self.assertRaises(ValueError):
            pick_microphone(inputs, 'default')
        self.assertEqual(microphone_label('Microphone Array (Intel)'), 'Microphone: Microphone Array (Intel) (WASAPI)')
        self.assertIn("earbuds' own microphone", microphone_label('Headset Microphone (USB earbuds)', 'earbuds'))

    def test_earbud_microphone_refuses_bluetooth_hands_free_and_the_laptop_array(self):
        bluetooth = [{'name':name, 'hostapi':1, 'max_input_channels':1, 'max_output_channels':0}
                     for name in ('Headset (Buds Hands-Free AG Audio)', 'Headset (Buds)', 'Headset Microphone (Buds Hands-Free)')]
        inputs, _ = wasapi_devices(self.hostapis, [self.devices[2], *bluetooth])
        with self.assertRaisesRegex(LookupError, 'Inputs found'):
            earbud_microphone(inputs)
        self.assertEqual(laptop_microphone(inputs)[0], 0)

    def test_mic_choice_reaches_both_windows_and_defaults_to_the_laptop(self):
        from anc_lab.cli import main
        cases = [(['tune'], 'anc_lab.tune_app.run_window', 'laptop', 'smoothed'),
                 (['tune', '--mic', 'earbuds', '--engine', 'faint'], 'anc_lab.tune_app.run_window', 'earbuds', 'faint'),
                 (['tune', '--mask', '--mic', 'earbuds'], 'anc_lab.mask_app.run_mask_window', 'earbuds', 'faint')]
        for argv, window, microphone, engine in cases:
            with self.subTest(argv=argv), mock.patch('sys.argv', ['anc-lab', *argv]), mock.patch(window) as opened:
                main()
                opened.assert_called_once()
                self.assertEqual(opened.call_args.kwargs['microphone'], microphone)
                self.assertEqual(opened.call_args.args[3], engine)


class GuardTests(unittest.TestCase):
    def test_ogg_skeleton_pages_are_removed(self):
        def page(serial, body, first=False):
            return b'OggS'+bytes([0, 2 if first else 0])+bytes(8)+serial+bytes(8)+bytes([1, len(body)])+body
        skeleton, audio = page(b'SKEL', b'fishead\x00'+bytes(20), True), page(b'AUDI', b'\x01vorbis'+bytes(10), True)
        rest = page(b'AUDI', bytes(30))
        data, stripped = ogg_audio_only(skeleton+audio+page(b'SKEL', bytes(5))+rest)
        self.assertTrue(stripped)
        self.assertEqual(data, audio+rest)
        with self.assertRaises(ValueError):
            ogg_audio_only(b'RIFF'+bytes(40))

    def test_studies_refuse_non_empty_output(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)/'old'
            out.mkdir()
            (out/'kept.txt').write_text('earlier result')
            with self.assertRaises(ValueError):
                run_real_hum_study(folder, out)
            with self.assertRaises(ValueError):
                run_tune_by_ear_study(folder, Path(folder)/'missing.json', out)
            self.assertEqual((out/'kept.txt').read_text(), 'earlier result')


if __name__ == '__main__':
    unittest.main()
