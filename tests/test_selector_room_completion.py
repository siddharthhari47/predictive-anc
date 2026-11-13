import unittest
import numpy as np
from anc_lab.antihum import ToneSetting, FS, BLOCK
from anc_lab import antihum_study as room
from anc_lab.selector_room_completion import muted_parity_evaluate, ORIGINAL_EVALUATE


class MutedParityTests(unittest.TestCase):
    def setUp(self):
        n = 8*FS
        seen = np.arange(BLOCK, n+1, BLOCK)
        phase = np.exp(2j*np.pi*100*(seen-1)/FS)
        a = {'seen': seen, 'frequency': np.full((len(seen), 1), 100.),
             'phasor': .01*phase[:, None], 'gate': np.ones(len(seen), bool)}
        trace = {'v2': a, 'bank': [a, a],
                 'weights': np.tile([1., 0., 0.], (len(seen), 2, BLOCK, 1))}
        self.scene = {'trace': trace, 'arrays': a,
            'ears': [.01*np.cos(2*np.pi*100*np.arange(n)/FS)],
            'prefix': 2*FS, 'n': n, 'unreported': 0,
            'earphone': (np.array([1.]), np.array([1.])), 'earphone_gain': 1.}

    def test_empty_and_muted_commands_match_historical_zero_convention(self):
        for settings in ([], [ToneSetting(100., 0.)]):
            for tones in ([], [100.]):
                for method in ('v2', 'chooser'):
                    actual, on = muted_parity_evaluate(self.scene, settings, .03, method, tones)
                    expected = room.evaluate(self.scene, settings, .03, tones)[0]
                    for key, value in expected.items():
                        if key not in ('move_cm', 'drift_ms'):
                            self.assertEqual(actual[key], value)
                    np.testing.assert_array_equal(on, self.scene['ears'][0])
                    self.assertTrue(all(b['amplification_db'] == 0 for b in actual['bands']))

    def test_active_metrics_and_signal_are_unchanged(self):
        for method in ('v2', 'chooser'):
            args = (self.scene, [ToneSetting(100., .7, 13.)], .03, method, [100.])
            actual, a = muted_parity_evaluate(*args)
            expected, b = ORIGINAL_EVALUATE(*args)
            self.assertEqual(actual, expected)
            np.testing.assert_array_equal(a, b)


if __name__ == '__main__':
    unittest.main()
