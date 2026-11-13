"""Checks for the fast tone-release path and the fresh random frequency draws."""
import tempfile
import unittest

import numpy as np

from anc_lab.generalization import DEVELOPMENT, HELD_OUT
from anc_lab.release_study import draw_groups, in_parity, make_dev_scenes, objective_windows, run_release_study
from anc_lab.selection_study import TEST_GROUPS, frequency_extent, scene_set
from anc_lab.tone_selection import SelectedToneForecaster, ToneSelector

FS = 2000


def tone(freq, amp, seconds=8, stop=None, noise=.01, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(seconds*FS)/FS
    x = noise*rng.standard_normal(len(t)) + amp*np.sin(2*np.pi*freq*t+.3)*(t < (stop or seconds))
    return x


class ReleaseStudyTests(unittest.TestCase):
    def test_fast_release_is_causal(self):
        x = tone(88., .5)
        changed = x.copy(); changed[9001:] = 0.
        origins, horizons = np.arange(3000, 8800, 20), np.arange(1, 41)
        fc = lambda: SelectedToneForecaster(FS, ToneSelector(FS, alpha=1e-2), release_ratio=.5)
        a, b = fc().predict(x, origins, horizons), fc().predict(changed, origins, horizons)
        keep = origins <= 9000
        np.testing.assert_allclose(a[keep], b[keep])

    def test_fast_release_drops_stopped_tone_but_keeps_steady_one(self):
        horizons = np.arange(1, 41)
        selector = ToneSelector(FS, alpha=1e-2, release=4)
        stopped = tone(88., .5, stop=5.)
        origins = np.arange(5*FS+200, 5*FS+600, 20)            # 0.1-0.3 s after the stop
        slow = SelectedToneForecaster(FS, selector).predict(stopped, origins, horizons)
        fast_fc = SelectedToneForecaster(FS, selector, release_ratio=.5, release_window_seconds=.1)
        fast = fast_fc.predict(stopped, origins, horizons)
        self.assertGreater(np.sqrt(np.mean(slow**2)), .05)      # the old path is still forecasting
        self.assertLess(np.sqrt(np.mean(fast**2)), 1e-12)       # the fast path has dropped it
        steady = tone(88., .5)
        steady_fc = SelectedToneForecaster(FS, selector, release_ratio=.5, release_window_seconds=.1)
        steady_fc.predict(steady, np.arange(3*FS, 7*FS, 20), horizons)
        self.assertEqual(steady_fc.fast_drops, 0)

    def test_random_draws_are_fresh_and_band_separated(self):
        rng = np.random.default_rng(5)
        forbidden = frequency_extent(TEST_GROUPS)+[f for g in DEVELOPMENT for f in g]+[f for g in HELD_OUT.values() for f in g]
        for parity in (0, 1):
            for _ in range(4):
                g = draw_groups(rng, parity, forbidden)
                self.assertEqual({k:len(v) for k, v in g.items()}, {k:len(v) for k, v in TEST_GROUPS.items()})
                for key, freqs in g.items():
                    for f in freqs:
                        self.assertTrue(all(abs(f-b) > 2 for b in forbidden))
                        if key == 'drift':
                            self.assertEqual(int(f//10) % 2, parity)
                            self.assertEqual(int((f+6)//10), int(f//10))
                        elif key == 'harmonic':
                            self.assertTrue(in_parity(f, parity, 1., 9.))
                        else:
                            self.assertTrue(in_parity(f, parity))
                for spec in scene_set(g).values():
                    fs = sorted(t['freq'] for t in spec['tones'])
                    self.assertTrue(all(b-a >= 15 for a, b in zip(fs, fs[1:])))
        # Even-band (development) and odd-band (test) draws can never be within 5 Hz of each other.
        self.assertFalse(any(in_parity(f, 0) and in_parity(f, 1) for f in np.arange(40, 330, .1)))

    def test_development_scenes_are_deterministic_and_windows_cover_events(self):
        draws_a, scenes_a = make_dev_scenes()
        draws_b, scenes_b = make_dev_scenes()
        self.assertEqual(draws_a, draws_b)
        self.assertEqual(len(scenes_a), 36)
        np.testing.assert_array_equal(scenes_a['tones_stop_9s#dev1'][1], scenes_b['tones_stop_9s#dev1'][1])
        self.assertIn((9., 10.5), objective_windows(scenes_a['tones_stop_9s#dev0'][0]))

    def test_refuses_existing_results_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            open(f'{folder}/keep.txt', 'w').close()
            with self.assertRaises(ValueError):
                run_release_study(folder)


if __name__ == '__main__':
    unittest.main()
