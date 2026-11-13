"""Scientific invariants for a diagnostic component adapter, without audio."""
import unittest
import numpy as np

from anc_lab.antihum import ToneSetting
from anc_lab.selection_study import FS, BLOCK, horizon_setup
from anc_lab.selector_components import ComponentFrame, selected_components, wave
from anc_lab.tone_selection import SelectedToneForecaster


def frame(v2, fade, dc=0., gates=(True, True), previous=(True, True), weights=None):
    groups = tuple(h for _, h in horizon_setup()[2])
    if weights is None:
        weights = np.tile([1., 0., 0.], (BLOCK, 1))
    return ComponentFrame(4000, groups, tuple(v2), dc, (tuple(fade), tuple(fade)),
                          np.array(gates), np.array(previous), (weights, weights.copy()), (0, 0), 0)


class ComponentTests(unittest.TestCase):
    def test_local_fit_with_dc_and_fast_release_matches_existing_forecast(self):
        t = np.arange(1400)/FS
        config = {'window_seconds': .3, 'release_ratio': .25, 'release_window_seconds': .1}
        h = horizon_setup()[1]
        for x in (0.8*np.sin(2*np.pi*137.4*t+.7)+.19,
                  np.r_[.8*np.sin(2*np.pi*137.4*t[:-240]+.7), np.zeros(240)]):
            components, dc = selected_components(x, [(137., 1.)], config)
            expected = SelectedToneForecaster(FS, None, **config).predict(
                x, [len(x)-1], h, decisions=[(len(x)-1, [(137., 1.)])])[0]
            np.testing.assert_allclose(wave(components, h, dc), expected, atol=1e-10, rtol=1e-10)
        self.assertEqual(components, ())

    def test_dc_never_enters_tuned_tone_drive_and_gate_modes_are_explicit(self):
        f = frame([(100., 1.+0j)], [], dc=.8, gates=(True, False), previous=(False, False))
        tone = np.cos(2*np.pi*100*f.horizons[0]/FS)
        settings = [ToneSetting(100., 1.)]
        np.testing.assert_allclose(f.reconstruct()['v2_gated'][:BLOCK], tone+.8)
        np.testing.assert_allclose(f.anti_noise(settings, 0), -tone, atol=1e-12)
        np.testing.assert_allclose(f.anti_noise(settings, 0, gate_rendering='block_ramp'),
                                   -tone*np.arange(1, BLOCK+1)/BLOCK, atol=1e-12)
        with self.assertRaises(ValueError):
            f.anti_noise(settings, 2)

    def test_crossfade_preserves_distinct_tones_and_phase_settings(self):
        alpha = np.arange(1, BLOCK+1)/BLOCK
        weights = np.column_stack([1-alpha, alpha, np.zeros(BLOCK)])
        f = frame([(100., 1.)], [(200., 2.)], weights=weights)
        h = f.horizons[1]
        settings = [ToneSetting(100., .5, 90.), ToneSetting(200., .25, -90.)]
        expected = .5*(1-alpha)*np.sin(2*np.pi*100*h/FS)-.5*alpha*np.sin(2*np.pi*200*h/FS)
        np.testing.assert_allclose(f.anti_noise(settings, 1), expected, atol=1e-12)
        f.mix_weights = (np.tile([0., 0., 1.], (BLOCK, 1)),)*2
        np.testing.assert_array_equal(f.anti_noise(settings, 0), np.zeros(BLOCK))

    def test_switch_to_phase_biased_predictor_can_invalidate_fixed_tuning(self):
        # A deliberately wrong predictor, not a statement about observed L2.
        f = frame([(100., 1.)], [(100., -1.)])
        settings = [ToneSetting(100., 1.)]
        pressure = np.cos(2*np.pi*100*f.horizons[0]/FS)
        before = pressure+f.anti_noise(settings, 0)
        f.mix_weights = (np.tile([0., 1., 0.], (BLOCK, 1)),)*2
        after = pressure+f.anti_noise(settings, 0)
        self.assertLess(float(np.max(np.abs(before))), 1e-12)
        amplification = 10*np.log10(np.mean(after**2)/np.mean(pressure**2))
        self.assertAlmostEqual(amplification, 20*np.log10(2.), places=10)


if __name__ == '__main__':
    unittest.main()
