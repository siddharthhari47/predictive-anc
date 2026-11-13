import unittest
import json
from dataclasses import asdict
import numpy as np
from anc_lab.tuning_accuracy_diagnostic import (coefficients, projected_effect,
    check_probabilities, keep_probability, numbers_equal, TraceListener, TraceSession, trace_tuning)
from anc_lab import antihum_study as room
from anc_lab.tuning import SimulatedListener, Presentation
from anc_lab.antihum import FS


class TuningAccuracyChecks(unittest.TestCase):
    def test_phase_flag_is_not_equivalent_to_harm(self):
        t = np.arange(2000)/2000
        x = np.column_stack([np.cos(2*np.pi*100*t), np.sin(2*np.pi*100*t)])
        opt = coefficients(1., 0.)
        # At 70 degrees a small enough gain still reduces the controllable energy.
        small = coefficients(.3, 70.)
        self.assertGreater(projected_effect(x, opt, small, 0, 2000), 0.)
        self.assertLess(projected_effect(x, opt, coefficients(1., 70.), 0, 2000), 0.)
        self.assertAlmostEqual(projected_effect(x, opt, coefficients(1., 30.), 0, 2000),
                               -20*np.log10(2*np.sin(np.pi/12)), places=10)

    def test_prefix_effect_ignores_suffix(self):
        x = np.random.default_rng(2).normal(size=(2000, 2))
        a, b = coefficients(1., 0.), coefficients(.8, 10.)
        before = projected_effect(x, a, b, 100, 1000)
        x[1000:] = 10000
        self.assertEqual(before, projected_effect(x, a, b, 100, 1000))

    def test_gaussian_noise_is_per_presentation_and_two_checks_require_on(self):
        p = check_probabilities(0.)
        self.assertAlmostEqual(p['on'], .23975006109347674)
        self.assertAlmostEqual(p['off'], p['on'])
        self.assertAlmostEqual(sum(p.values()), 1.)
        self.assertAlmostEqual(keep_probability(p, p), .30705984680397597, places=12)
        self.assertEqual(keep_probability({'on': 0, 'same': 1}, {'on': 0, 'same': 1}), 0)

    def test_observational_listener_preserves_choices_and_rng(self):
        collector = {'sessions': []}
        session = TraceSession(100., .3, collector=collector)
        class Player:
            latest = [{'start': 3000, 'end': 7000, 'presentation': Presentation('A', session.setting(), 2.)},
                      {'start': 7000, 'end': 11000, 'presentation': Presentation('B', session.setting(), 2.)}]
        collector['player'] = Player()
        traced = TraceListener(FS, 1., seed=15, collector=collector)
        plain = SimulatedListener(FS, 1., seed=15)
        t = np.arange(4000)/FS
        a = .01*np.sin(2*np.pi*100*t)
        b = .009*np.sin(2*np.pi*100*t)
        for _ in range(5):
            self.assertEqual(traced.compare('phase', 100., a, b), plain.compare('phase', 100., a, b))
            self.assertEqual(traced.rng.bit_generator.state, plain.rng.bit_generator.state)

    def test_parity_rejects_boolean_or_structural_changes(self):
        self.assertEqual(numbers_equal({'x': [True, .3]}, {'x': [True, .3]}), 2)
        with self.assertRaises(AssertionError):
            numbers_equal({'x': [False, .3]}, {'x': [True, .3]})
        with self.assertRaises(AssertionError):
            numbers_equal({'x': [.3]}, {'x': [.3, .4]})

    def test_complete_synthetic_session_parity_and_counterfactuals(self):
        n = 24000
        seen = np.arange(20, n+1, 20)
        phase = 2*np.pi*100*(seen-1)/FS
        arrays = {'seen': seen, 'frequency': np.full((len(seen), 1), 100.),
                  'phasor': (.01*np.exp(1j*phase))[:, None], 'gate': np.ones(len(seen), bool)}
        scene = {'warm': 3000, 'prefix': 14000, 'n': n, 'unreported': 6,
                 'ears': [.01*np.cos(2*np.pi*100*np.arange(n)/FS)],
                 'arrays': arrays, 'earphone': (np.array([1.]), np.array([1.])),
                 'earphone_gain': 1., 'tones': [{'frequency': 100., 'w': np.exp(1j*.6*np.pi),
                                               'mic_amplitude': .01}]}
        a, sa = room.tune_by_ear(scene, .03, 1., 17)
        b, sb, logs = trace_tuning(scene, 17)
        self.assertEqual(sa, sb)
        self.assertEqual([asdict(s) for s in a], [asdict(s) for s in b])
        checks = [c for c in logs[0]['comparisons'] if c['kind'] == 'check']
        self.assertEqual(len(checks), 2)
        for c in checks:
            self.assertEqual(len(c['same_interval']), 2)
            self.assertLessEqual(max(i['end_s'] for i in c['intervals']), 7.)
        json.dumps(logs, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
