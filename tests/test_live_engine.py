import unittest

import numpy as np
from scipy import signal

from anc_lab import engine_candidate as ec
from anc_lab import engine_smoothing as es
from anc_lab import live_engine as le
from anc_lab import smoother_timing as st
from anc_lab.antihum import AntiHumEngine, FS, StreamingDecimator, ToneSetting, log_arrays
from anc_lab.tune_app import LiveRunner, RATE, session_record


def hum(seconds=4., seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(round(seconds*RATE))/RATE
    return .1*np.sin(2*np.pi*120.3*t)+.05*np.sin(2*np.pi*181.*t+1)+.01*rng.standard_normal(len(t))


def feed(engine, x, chunk=480):
    decimator = StreamingDecimator(RATE, FS)
    for k in range(0, len(x)-len(x) % chunk, chunk):
        y = decimator.process(x[k:k+chunk])
        if len(y):
            engine.push(y)


class LiveEngine(unittest.TestCase):
    def test_constants_match_the_frozen_study(self):
        self.assertEqual(le.ALPHA, st.ALPHA)
        self.assertEqual(le.ASSOCIATE_HZ, es.ASSOCIATE_HZ)
        self.assertEqual(le.MAX_GAP, es.MAX_GAP)

    def test_every_origin_matches_the_tested_candidate(self):
        x = hum()
        tested, live = ec.SmoothedEngine(True), le.SmoothedEngine(True)
        feed(tested, x)
        feed(live, x)
        st.same(log_arrays(live.raw.log), log_arrays(tested.raw.log))
        self.assertEqual(live.components, tested.components)
        self.assertEqual(live.raw.smoother.states, tested.raw.smoother.states)
        self.assertEqual(live.strongest(), tested.strongest())

    def test_rendered_output_matches_the_tested_candidate(self):
        x = hum()
        outs = []
        for engine in (ec.SmoothedEngine(), le.SmoothedEngine()):
            runner = LiveRunner(engine=engine)
            runner.set_tone('both', ToneSetting(120.3, .1))
            runner.limiter.start()
            for k in range(len(x)//480):
                runner.on_input(x[k*480:(k+1)*480], k*480/RATE)
                runner.pump()
            outs.append(runner.on_output(480, len(x)/RATE))
        self.assertTrue(np.any(outs[0]))
        np.testing.assert_array_equal(outs[0], outs[1])

    def test_tapers_are_cached_once_and_scipy_is_restored(self):
        original = signal.windows.dpss
        engine = le.SmoothedEngine()
        feed(engine, hum())
        self.assertEqual(len(engine.tapers), 1)
        self.assertIs(signal.windows.dpss, original)

    def test_scipy_is_restored_when_a_push_fails(self):
        original = signal.windows.dpss
        engine = le.SmoothedEngine()
        with self.assertRaises(Exception):
            engine.push(None)
        self.assertIs(signal.windows.dpss, original)

    def test_runner_default_stays_v2_and_fallback_is_listed(self):
        self.assertIsInstance(LiveRunner().engine, AntiHumEngine)
        self.assertIs(le.ENGINES['v2'], AntiHumEngine)
        self.assertIs(le.ENGINES['smoothed'], le.SmoothedEngine)

    def test_saved_session_names_the_engine(self):
        record = session_record({}, LiveRunner(), [], .05, 'smoothed')
        self.assertEqual(record['engine'], 'smoothed')
        self.assertFalse(record['audio_stored'])


if __name__ == '__main__':
    unittest.main()
