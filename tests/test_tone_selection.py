"""Checks for the causal tone-count selector and the realized-error mute gate."""
import tempfile
import unittest

import numpy as np
from scipy import signal

from anc_lab.selection_study import (DEV_GROUPS, TEST_GROUPS, frequency_extent, run_selection_study)
from anc_lab.generalization import DEVELOPMENT, HELD_OUT
from anc_lab.tone_selection import SelectedToneForecaster, ToneSelector, line_test, realized_gate

FS = 2000


def tones(freqs, amps, seconds=6, noise=.01, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(seconds*FS)/FS
    x = noise*rng.standard_normal(len(t))
    for f, a in zip(freqs, amps):
        x += a*np.sin(2*np.pi*f*t+rng.uniform(-np.pi, np.pi))
    return x


class ToneSelectionTests(unittest.TestCase):
    def test_future_samples_cannot_change_decisions_or_forecasts(self):
        x = tones([88.], [.5])
        changed = x.copy(); changed[7001:] = 5*np.random.default_rng(3).standard_normal(len(x)-7001)
        selector = ToneSelector(FS)
        a = [d for d in selector.timeline(x) if d[0] <= 7000]
        b = [d for d in selector.timeline(changed) if d[0] <= 7000]
        self.assertEqual(a, b)
        origins, horizons = np.arange(3000, 6800, 20), np.arange(1, 41)
        pa = SelectedToneForecaster(FS, selector).predict(x, origins, horizons)
        pb = SelectedToneForecaster(FS, selector).predict(changed, origins, horizons)
        np.testing.assert_allclose(pa[origins <= 7000-40], pb[origins <= 7000-40])

    def test_noise_without_tones_stays_inactive(self):
        selector = ToneSelector(FS, alpha=1e-3, acquire=2, history=3)
        for seed in range(6):
            rng = np.random.default_rng(100+seed)
            white = rng.standard_normal(6*FS)
            rumble = signal.lfilter([1.], [1., -.98], rng.standard_normal(6*FS))
            for x in (white, rumble):
                self.assertTrue(all(not active for _, active in selector.timeline(x)))

    def test_counts_and_locates_tones_without_labels(self):
        for freqs in ([133.9], [62.8, 171.3, 288.4]):
            final = ToneSelector(FS).timeline(tones(freqs, [.45, .25, .13][:len(freqs)]))[-1][1]
            self.assertEqual(len(final), len(freqs))
            for f, (found, _) in zip(freqs, final):
                self.assertLess(abs(found-f), .3)

    def test_constant_or_tiny_input_is_handled(self):
        self.assertEqual(line_test(np.zeros(2000), FS), [])
        self.assertEqual(line_test(np.full(2000, .3), FS), [])

    def test_gate_uses_only_matured_forecasts(self):
        rng = np.random.default_rng(5)
        x = rng.standard_normal(4000)
        origins = np.arange(500, 3500, 20)
        horizons = np.arange(1, 21)
        forecast = rng.standard_normal((len(origins), 20))
        groups = [(np.arange(20), horizons)]
        a = realized_gate(x, origins, forecast, groups)
        changed = x.copy(); changed[2001:] = 0
        b = realized_gate(changed, origins, forecast, groups)
        np.testing.assert_array_equal(a[origins <= 2000], b[origins <= 2000])
        self.assertFalse(a.any())  # random forecasts never beat zero

    def test_test_groups_are_fresh(self):
        old = frequency_extent(DEV_GROUPS)+[f for g in DEVELOPMENT for f in g]+[f for g in HELD_OUT.values() for f in g]
        self.assertTrue(all(abs(a-b) > 2 for a in frequency_extent(TEST_GROUPS) for b in old))

    def test_study_refuses_existing_results(self):
        with tempfile.TemporaryDirectory() as folder:
            open(f'{folder}/keep.txt', 'w').close()
            with self.assertRaises(ValueError):
                run_selection_study(folder)


if __name__ == '__main__':
    unittest.main()
