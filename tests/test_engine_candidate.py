import unittest

import numpy as np

from anc_lab import engine_candidate as ec
from anc_lab import engine_smoothing as es
from anc_lab import smoother_timing as st
from anc_lab.antihum import AntiHumEngine, FS
from anc_lab.selector_stream_profile import cached_dpss
from anc_lab.tune_app import LiveRunner, RATE


def hum(seconds=4., seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(round(seconds*RATE))/RATE
    return .1*np.sin(2*np.pi*120.3*t)+.05*np.sin(2*np.pi*181.*t+1)+.01*rng.standard_normal(len(t))


class Candidate(unittest.TestCase):
    def test_raw_stays_raw_and_smooth_matches_offline(self):
        x = hum()
        reference, _ = ec.run_offline(x, len(x), False)
        expected = es.smooth_arrays(reference, st.ALPHA)
        self.assertTrue(np.isfinite(reference['frequency']).any())
        for chunk in (137, 480, 1920):
            raw, smooth = ec.run_offline(x, chunk, True)
            rows = len(raw['seen'])
            st.same(raw, {k: v[:rows] for k, v in reference.items()})
            st.same(smooth, {k: v[:rows] for k, v in expected.items()})

    def test_several_origins_in_one_push_step_the_smoother_each_time(self):
        engine = ec.SmoothedEngine(True)
        engine.push(hum()[::RATE//FS])
        self.assertEqual(engine.raw.smoother.origin, engine.origin_seen//ec.BLOCK)

    def test_runner_snapshot_is_smoothed_but_tone_list_and_gate_are_raw(self):
        x = hum()
        engine = ec.SmoothedEngine()
        runner = LiveRunner(engine=engine)
        runner.limiter.start()
        for k in range(0, len(x)-479, 480):
            runner.on_input(x[k:k+480], k/RATE)
            runner.pump()
        _, components, gate, strongest = runner.snapshot
        self.assertEqual(components, engine.raw.smoothed)
        self.assertEqual(gate, engine.raw.gate_open)
        self.assertEqual(strongest, engine.raw.strongest())
        self.assertNotEqual(components, engine.raw.components)

    def test_one_taper_in_the_cache(self):
        x = hum()
        with cached_dpss(True) as cache:
            ec.run_offline(x, 480, True)
        self.assertEqual(len(cache), 1)

    def test_short_session_runs_clean(self):
        x = hum(1.5)
        reference, _ = ec.run_offline(x, len(x), False)
        with cached_dpss(True):
            times, report, logs = ec.session(x, [120.3], 'candidate')
        self.assertEqual(report['errors'], [])
        self.assertEqual(report['stale_blocks'], 0)
        self.assertFalse(report['worker_alive'])
        self.assertEqual(len(times['push_ms']), report['blocks'])
        st.same(logs[0], {k: v[:len(logs[0]['seen'])] for k, v in reference.items()})

    def test_rule(self):
        def run(push, output, quiet, clean=True):
            return {'push_ms': {'p99': push, 'max': push}, 'output_ms': {'p99': output, 'max': output}, 'queue_ms': {'max': 1.},
                    'quiet_qualified': quiet, 'clean': clean, 'stale_blocks': 0}
        self.assertEqual(ec.decide([run(1., 1., True)]*24+[run(9., 1., False)]*4)['result'], 'pass')
        self.assertEqual(ec.decide([run(1., 1., True)]*23+[run(1., 1., False)]*5)['result'], 'inconclusive')
        self.assertEqual(ec.decide([run(6., 1., True)]+[run(1., 1., False)]*27)['result'], 'fail')
        self.assertEqual(ec.decide([run(1., 6., True)]*28)['result'], 'fail')
        self.assertEqual(ec.decide([run(1., 1., True)]*27+[run(1., 1., False, False)])['result'], 'fail')


if __name__ == '__main__':
    unittest.main()
