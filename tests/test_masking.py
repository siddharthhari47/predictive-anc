"""Hum masking, offline only: nothing here opens an audio device."""
import unittest

import numpy as np
from scipy import signal

from anc_lab.live_engine import FaintEngine
from anc_lab.mask_app import MaskRunner
from anc_lab.masking import CREST, HOLD_SECONDS, MaskGenerator, erb

RATE, CAP = 48000, .05


def band_share(x, lo, hi):
    f, p = signal.welch(x, RATE, nperseg=8192)
    return p[(f >= lo) & (f <= hi)].sum()/p.sum()


class MaskGeneratorTest(unittest.TestCase):
    def test_silent_without_hum(self):
        g = MaskGenerator(RATE, CAP, seed=1)
        g.update([], 0.)
        self.assertFalse(np.any(g.render(4800)))

    def test_noise_sits_in_the_hum_band_at_the_set_level(self):
        g = MaskGenerator(RATE, CAP, level=1., seed=2)
        g.update([(200., .01)], 0.)
        g.render(RATE)                                   # past the fade-in
        x = np.concatenate([g.render(480) for _ in range(400)])
        self.assertGreater(band_share(x[:, 0], 200-erb(200), 200+erb(200)), .9)
        rms = np.sqrt(np.mean(x**2))
        self.assertAlmostEqual(rms/(CAP/CREST), 1., delta=.15)
        self.assertLess(np.corrcoef(x[:, 0], x[:, 1])[0, 1], .1)      # independent noise per ear

    def test_wandering_hum_keeps_one_band(self):
        g = MaskGenerator(RATE, CAP, seed=3)
        for k, f in enumerate((200., 201.5, 198.7, 200.8)):
            g.update([(f, .01)], k*.25)
        self.assertEqual(len(g.bands), 1)

    def test_band_holds_then_fades_out(self):
        g = MaskGenerator(RATE, CAP, level=1., seed=4)
        g.update([(150., .01)], 0.)
        g.render(RATE)
        g.update([], HOLD_SECONDS-.5)
        self.assertTrue(np.any(g.render(480)))
        g.update([], HOLD_SECONDS+.5)
        g.render(RATE)                                   # fade-out finishes
        g.update([], HOLD_SECONDS+1.5)
        self.assertEqual(g.bands, [])
        self.assertFalse(np.any(g.render(480)))

    def test_level_glides_without_jumps(self):
        g = MaskGenerator(RATE, CAP, level=0., seed=5)
        g.update([(200., .01)], 0.)
        g.render(RATE)
        g.set_level(1.)
        x = g.render(4800)[:, 0]
        self.assertLess(np.sqrt(np.mean(x[:480]**2)), .2*np.sqrt(np.mean(x[-480:]**2)))


class MaskRunnerTest(unittest.TestCase):
    def test_masks_a_faint_wobbly_hum_end_to_end(self):
        rng = np.random.default_rng(6)
        n = 12*RATE
        wobble = np.convolve(rng.standard_normal(n), np.ones(RATE//2)/np.sqrt(RATE//2), 'same')
        hum = .05*np.sin(2*np.pi*np.cumsum(200+wobble/np.std(wobble))/RATE)
        mic = hum+.02*rng.standard_normal(n)
        runner = MaskRunner(RATE, CAP, 60, FaintEngine(), level=1., seed=7)
        runner.limiter.start()
        out = []
        for k in range(n//480):
            runner.on_input(mic[k*480:(k+1)*480], k*.01)
            runner.pump()
            out.append(runner.on_output(480, k*.01+.05))
        out = np.concatenate(out)
        self.assertFalse(np.any(out[:RATE]))              # nothing before the first 1 s window
        self.assertTrue(any(abs(f-200) < 5 for f in runner.masked()))
        self.assertLessEqual(np.max(np.abs(out)), CAP)
        self.assertGreater(band_share(out[-3*RATE:, 0], 170, 230), .8)
        self.assertEqual(runner.state()['stopped'], False)


if __name__ == '__main__':
    unittest.main()
