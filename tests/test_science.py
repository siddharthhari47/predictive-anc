"""Checks for causality, delay sign, physical paths, and meaningful controls."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile
from threadpoolctl import threadpool_limits

from anc_lab.control import fxlms, inverse_path, predicted_command, render, transport
from anc_lab.metrics import attenuation
from anc_lab.predictors import DirectPredictor, ToneTracker
from anc_lab.signals import jitter_trace, make_scene, paths


class ScienceTests(unittest.TestCase):
    def test_future_samples_cannot_change_causal_forecasts(self):
        rng = np.random.default_rng(7)
        x = np.sin(2*np.pi*73*np.arange(5000)/2000)+.01*rng.standard_normal(5000)
        changed = x.copy(); changed[3501:] = rng.standard_normal(len(changed)-3501)*10
        with threadpool_limits(limits=1):
            predictors = [ToneTracker(2000, [73.]),
                          DirectPredictor("ridge_ar", np.arange(1, 50)).fit(x, 2500),
                          DirectPredictor("mlp", np.arange(1, 50)).fit(x, 2500)]
            for model in predictors:
                np.testing.assert_allclose(model.predict(x, [3500], np.arange(1, 50)),
                                           model.predict(changed, [3500], np.arange(1, 50)))

    def test_training_future_does_not_change_fit(self):
        rng = np.random.default_rng(1)
        x = rng.standard_normal(3000); altered = x.copy(); altered[2000:] = 1e6
        with threadpool_limits(limits=1):
            for kind in ["ridge_ar", "mlp"]:
                a = DirectPredictor(kind, np.arange(1, 60)).fit(x, 2000)
                b = DirectPredictor(kind, np.arange(1, 60)).fit(altered, 2000)
                np.testing.assert_allclose(a.model.coefs_[0] if kind == "mlp" else a.model.coef_,
                                           b.model.coefs_[0] if kind == "mlp" else b.model.coef_)
                self.assertLess(a.metadata["last_training_target"], 2000)

    def test_delay_is_positive_and_fractional(self):
        u = np.zeros(100); u[10] = 1
        v = transport(u, 20.5, np.zeros(100))
        self.assertEqual(v[30], .5); self.assertEqual(v[31], .5)
        self.assertEqual(np.sum(v[:30]), 0)

    def test_tone_timing_formula_matches_rendered_signal(self):
        fs, f, delta = 2000, 73, .001
        t = np.arange(20000)/fs; d = np.sin(2*np.pi*f*t)
        anti = -np.sin(2*np.pi*f*(t-delta))
        expected = -20*np.log10(2*abs(np.sin(np.pi*f*delta)))
        self.assertAlmostEqual(attenuation(d, d+anti), expected, places=5)

    def test_path_compensated_future_reference_cancels(self):
        fs, n, block, delay, advance = 2000, 10000, 20, 40, 16
        p, s = paths(fs); q, error = inverse_path(p, s)
        self.assertLess(error, .001)
        x = np.sin(2*np.pi*73*np.arange(n)/fs)
        origins = np.arange(1000, 9500, block)
        h = np.arange(1, delay+advance+block+1)
        prediction = x[origins[:, None]+h]
        u, clips = predicted_command(prediction, h, origins, delay, advance, q, n, block, 2.)
        d = signal.lfilter(p, [1.], x)
        e = d+render(u, s, delay, np.zeros(n))
        self.assertGreater(attenuation(d[2000:9000], e[2000:9000]), 50)
        self.assertEqual(clips, 0)
        # Deliberately wrong timing must destroy the near-perfect result.
        bad = d+render(u, s, delay+2, np.zeros(n))
        self.assertLess(attenuation(d[2000:9000], bad[2000:9000]), 10)

    def test_fxlms_adapts_with_delayed_error_sensor(self):
        fs = 2000
        scene = make_scene("steady", fs, 8, 7)
        jitter = jitter_trace(len(scene.reference), fs, .25, 8)
        u, e, _ = fxlms(scene.reference, scene.disturbance, scene.secondary,
                         scene.secondary, 40, 40, jitter)
        np.testing.assert_allclose(e, scene.disturbance+render(u, scene.secondary, 40, jitter), atol=1e-10)
        self.assertGreater(attenuation(scene.disturbance[-4000:], e[-4000:]), 5)

    def test_reference_and_ear_are_distinct_and_reproducible(self):
        a = make_scene("steady", 2000, 2, 7); b = make_scene("steady", 2000, 2, 7)
        np.testing.assert_array_equal(a.reference, b.reference)
        self.assertFalse(np.allclose(a.reference, a.disturbance))

    def test_replay_rejects_short_or_stereo_recording(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"clip.wav"
            wavfile.write(path, 2000, np.zeros(100, dtype=np.float32))
            with self.assertRaisesRegex(ValueError, "never looped"):
                make_scene("replay", 2000, 12, 7, path)
            wavfile.write(path, 2000, np.zeros((24000, 2), dtype=np.float32))
            with self.assertRaisesRegex(ValueError, "mono"):
                make_scene("replay", 2000, 12, 7, path)

    def test_replay_resampling_and_normalization_do_not_read_future(self):
        rng = np.random.default_rng(7)
        original = (.1*rng.standard_normal(32000)).astype(np.float32)
        changed = original.copy(); changed[24000:] = 5
        with tempfile.TemporaryDirectory() as folder:
            a, b = Path(folder)/"a.wav", Path(folder)/"b.wav"
            wavfile.write(a, 16000, original); wavfile.write(b, 16000, changed)
            first = make_scene("replay", 2000, 2, 7, a, normalization_seconds=1.)
            second = make_scene("replay", 2000, 2, 7, b, normalization_seconds=1.)
            np.testing.assert_allclose(first.reference[:3000], second.reference[:3000], atol=1e-12)


if __name__ == "__main__":
    unittest.main()
