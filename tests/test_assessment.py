"""Real-reference assessment must not manufacture success or future access."""
import tempfile
import unittest
from unittest import mock
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from anc_lab.assessment import choose_method, cycle_forecast, forecast_scores, gate, load_reference


class AssessmentTests(unittest.TestCase):
    def test_zero_forecast_is_zero_gain(self):
        x = np.sin(2*np.pi*73*np.arange(12000)/2000)
        scores = forecast_scores(x, np.zeros_like(x), 2000)
        self.assertAlmostEqual(scores["prediction_gain_db"], 0)
        self.assertAlmostEqual(scores["band_prediction_gain_db"], 0)
        self.assertAlmostEqual(scores["nrmse"], 1)
        self.assertFalse(gate(scores, True))

    def test_known_scaling_has_correct_error_gain(self):
        x = np.sin(2*np.pi*73*np.arange(12000)/2000)
        scores = forecast_scores(x, .5*x, 2000)
        self.assertAlmostEqual(scores["band_prediction_gain_db"], 20*np.log10(2), places=9)
        self.assertTrue(gate(scores, True))
        self.assertFalse(gate(scores, False))
        self.assertFalse(gate({**scores, "nrmse": 1.1}, True))

    def test_cycle_never_uses_future_at_long_horizons(self):
        x = np.arange(1000.)
        changed = x.copy(); changed[501:] = 1e8
        horizons = np.array([1, 20, 40, 240, 260])
        np.testing.assert_array_equal(cycle_forecast(x, [500], horizons, 27),
                                      cycle_forecast(changed, [500], horizons, 27))
        self.assertTrue(np.all(cycle_forecast(x, [500], horizons, 27) <= 500))

    def test_validation_selection_includes_zero_as_a_real_option(self):
        scores = {"zero": {"band_prediction_gain_db": 0.}, "mlp": {"band_prediction_gain_db": -1.}}
        self.assertEqual(choose_method(scores), "zero")
        scores["tone_tracker"] = {"band_prediction_gain_db": 7.}
        self.assertEqual(choose_method(scores), "tone_tracker")

    def test_reference_normalization_and_resampling_are_causal(self):
        rng = np.random.default_rng(21)
        raw = (.1*rng.standard_normal(64000)).astype(np.float32)
        altered = raw.copy(); altered[48000:] = .8
        with tempfile.TemporaryDirectory() as directory:
            p, q = Path(directory)/"p.wav", Path(directory)/"q.wav"
            wavfile.write(p, 16000, raw); wavfile.write(q, 16000, altered)
            a, am = load_reference(p, 2000, 4, 2)
            b, bm = load_reference(q, 2000, 4, 2)
            np.testing.assert_array_equal(a[:6000], b[:6000])
            self.assertEqual(am["normalization_scale"], bm["normalization_scale"])
            self.assertEqual(am["resampling_group_delay_seconds"], .005)

    def test_clipping_is_visible_before_normalization(self):
        x = np.sin(2*np.pi*73*np.arange(8000)/2000).astype(np.float32)
        x[0] = 1.
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/"clipped.wav"
            wavfile.write(p, 2000, x)
            _, quality = load_reference(p, 2000, 4, 2)
            self.assertGreater(quality["near_full_scale_fraction"], 0)

    def test_rerunning_trial_fails_before_opening_microphone(self):
        from anc_lab.cli import main
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/"existing-trial"
            output.mkdir()
            marker = output/"assessment.json"
            marker.write_text('{"preserve": true}', encoding="utf-8")
            with mock.patch("sys.argv", ["anc-lab", "trial", "--out", str(output)]), \
                    mock.patch("anc_lab.capture.capture") as capture:
                with self.assertRaisesRegex(ValueError, "capture was not started"):
                    main()
                capture.assert_not_called()
            self.assertEqual(marker.read_text(encoding="utf-8"), '{"preserve": true}')


if __name__ == "__main__":
    unittest.main()
