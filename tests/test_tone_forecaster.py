"""Checks for the tone-forecaster study: causality, stream alignment, the line finder, the declared split and scoring."""
import json
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np

from anc_lab import forecaster_study as fsd
from anc_lab.antihum import V2_SELECTOR
from anc_lab.tone_forecasters import OnlineRidgeAR, ProminentLines, ToneObserverBank, stream_forecasts
from anc_lab.tone_selection import ToneSelector

FS, BLOCK = 2000, 20
HORIZONS = np.arange(41, 61)


def scene(seconds=6, tones=((83.3, .5), (171.7, .3)), noise=.05, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(seconds*FS)/FS
    x = noise*rng.standard_normal(len(t))
    for f, a in tones:
        x += a*np.sin(2*np.pi*f*t+rng.uniform(-np.pi, np.pi))
    return x


def bank(lines=False, nb_tau=0.):
    return ToneObserverBank(FS, BLOCK, ToneSelector(FS, **V2_SELECTOR), nb_tau=nb_tau,
                            candidates=ProminentLines() if lines else None)


def gain_db(target, forecast):
    return 10*np.log10(np.mean(target**2)/np.mean((target-forecast)**2))


class StreamRecorder:
    """Forecast = the newest sample received. Fed x = arange(n), that is the origin's index."""
    block = BLOCK

    def __init__(self):
        self.last = None

    def push(self, samples):
        self.last = samples[-1]

    def forecast(self, horizons):
        return np.full(len(horizons), self.last)


class ToneForecasterTests(unittest.TestCase):
    def test_stream_forecasts_uses_samples_up_to_each_origin(self):
        x = np.arange(4000.)
        grid = np.arange(1009, 3900, 20)
        out = stream_forecasts(StreamRecorder(), x, grid, HORIZONS)
        np.testing.assert_array_equal(out[:, 0], grid)
        with self.assertRaises(ValueError):
            stream_forecasts(StreamRecorder(), x, np.array([1009, 1019]), HORIZONS)

    def test_bank_is_block_causal(self):
        x = scene()
        changed = x.copy(); changed[7001:] = np.random.default_rng(9).standard_normal(len(x)-7001)
        grid = np.arange(999, len(x)-int(HORIZONS[-1]), BLOCK)
        a = stream_forecasts(bank(lines=True), x, grid, HORIZONS)
        b = stream_forecasts(bank(lines=True), changed, grid, HORIZONS)
        keep = grid <= 7000
        np.testing.assert_array_equal(a[keep], b[keep])
        self.assertFalse(np.array_equal(a[~keep], b[~keep]))

    def test_online_ar_is_causal(self):
        x = scene(seconds=6)
        changed = x.copy(); changed[9001:] = 0.
        origins = np.arange(4999, 11000, 20)
        a = OnlineRidgeAR(FS, HORIZONS).predict(x, origins, HORIZONS)
        b = OnlineRidgeAR(FS, HORIZONS).predict(changed, origins, HORIZONS)
        # Refits use training targets at or before the origin, so nothing after sample 9000 can leak in.
        np.testing.assert_array_equal(a[origins <= 9000], b[origins <= 9000])
        self.assertFalse(np.array_equal(a[origins > 9200], b[origins > 9200]))

    def test_bank_tracks_steady_tones_and_stays_silent_on_noise(self):
        x = scene(seconds=6)
        grid = np.arange(999, len(x)-int(HORIZONS[-1]), BLOCK)
        fc = bank()
        out = stream_forecasts(fc, x, grid, HORIZONS)
        late = grid >= 4*FS
        target = x[grid[late][:, None]+HORIZONS]
        self.assertGreater(gain_db(target, out[late]), 10.)
        freqs = sorted(f for f, _ in fc.components())
        np.testing.assert_allclose(freqs, [83.3, 171.7], atol=.3)
        noise = np.random.default_rng(3).standard_normal(6*FS)
        quiet = stream_forecasts(bank(lines=True), noise, grid, HORIZONS)
        self.assertLess(np.mean(np.any(quiet != 0, axis=1)), .05)

    def test_line_finder_finds_prominent_line_and_median_matches_sliding_median(self):
        lines = ProminentLines()
        x = scene(seconds=5, tones=((123.4, .2),), noise=.3, seed=4)
        found = lines.lines(x)
        self.assertEqual(len(found), 1)
        self.assertAlmostEqual(found[0], 123.4, delta=.2)
        self.assertEqual(lines.lines(np.random.default_rng(5).standard_normal(5*FS)), [])
        self.assertEqual(lines.lines(x[:3*FS]), [])                    # needs a full 4 s window
        # The fast median used by the line finder equals a sliding-window median with edge padding.
        from scipy import ndimage
        level, half = np.random.default_rng(6).standard_normal(500), 40
        slow = np.median(np.lib.stride_tricks.sliding_window_view(np.pad(level, half, mode='edge'), 2*half+1), axis=1)
        np.testing.assert_array_equal(ndimage.median_filter(level, size=2*half+1, mode='nearest'), slow)

    def test_check_width_settings(self):
        self.assertEqual(bank(nb_tau=0.).lp, 0.)
        narrow = bank(nb_tau=.1)
        self.assertAlmostEqual(narrow.lp, np.exp(-BLOCK/(.1*FS)))
        self.assertEqual(narrow.settings()['check_lowpass_seconds'], .1)

    def test_bank_block_time_is_small(self):
        x = scene(seconds=6, tones=tuple((f, .2) for f in (61.1, 97.3, 133.9, 171.7, 213.3, 287.9)))
        grid = np.arange(999, len(x)-int(HORIZONS[-1]), BLOCK)
        fc = bank(lines=True)
        stream_forecasts(fc, x, grid, HORIZONS)
        self.assertLess(1e3*np.mean(fc.block_seconds_own), 5.)

    def test_third_octave_changes(self):
        target = scene(seconds=2, noise=.2)[:3000].reshape(150, 20)
        np.testing.assert_allclose(fsd.third_octave_changes(target, np.zeros_like(target)), 0., atol=1e-9)
        doubled = fsd.third_octave_changes(target, -target)
        np.testing.assert_allclose(doubled, 20*np.log10(2), atol=1e-6)
        self.assertTrue(all(c < -100 for c in fsd.third_octave_changes(target, target)))

    def test_declared_split_is_reproduced_and_disjoint(self):
        split = fsd.load_split()
        dev = {e['file'] for e in split['development_files']}
        test = {e['file'] for e in split['test_files']}
        self.assertFalse(dev & test)
        for group, files in fsd.RECORDING_GROUPS.items():
            self.assertTrue(set(files) <= dev or set(files) <= test, group)   # whole author groups only
        self.assertIn('not independent', split['independence'].lower())

    def test_wander_draws_are_fresh_and_deterministic(self):
        forbidden = [101., 202.5]
        a = fsd.draw_wander(np.random.default_rng(1), 1, forbidden)
        b = fsd.draw_wander(np.random.default_rng(1), 1, forbidden)
        self.assertEqual(a, b)
        for freqs in a.values():
            self.assertTrue(all(abs(f-x) > 2 for f in freqs for x in forbidden))
        spec = fsd.wander_scene_set(a)['wander_fast']
        np.testing.assert_array_equal(fsd.synthesize_wander(spec, 5), fsd.synthesize_wander(spec, 5))

    def test_stages_refuse_to_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'keep.txt').write_text('x')
            with self.assertRaises(ValueError):
                fsd.run_development(folder)
            with self.assertRaises(ValueError):
                fsd.freeze_protocol(folder, output=Path(folder, 'keep.txt'))
            with self.assertRaises(ValueError):
                fsd.run_test(output=folder)


if __name__ == '__main__':
    unittest.main()
