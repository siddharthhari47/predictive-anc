import unittest
import numpy as np
from anc_lab import engine_smoothing as es
from anc_lab.antihum import FS, BLOCK

DT = BLOCK/FS


def tone_arrays(n=400, f=100., wobble_hz=None, depth=0.):
    k = np.arange(n)
    amp = 1+depth*np.sin(2*np.pi*(wobble_hz or 0)*k*DT)
    phasor = (amp*np.exp(2j*np.pi*f*k*DT))[:, None]
    return {'seen': (k+1)*BLOCK, 'frequency': np.full((n, 1), f), 'phasor': phasor, 'gate': np.ones(n, bool)}


class EngineSmoothingChecks(unittest.TestCase):
    def test_steady_tone_passes_unchanged(self):
        a = tone_arrays()
        out = es.smooth_arrays(a, .1)['phasor']
        self.assertTrue(np.allclose(out, a['phasor']))

    def test_off_tone_wobble_is_attenuated_more_by_narrower_smoother(self):
        a = tone_arrays(wobble_hz=10., depth=.2)
        base = np.exp(2j*np.pi*100.*np.arange(400)*DT)[:, None]
        wobble = lambda p: np.std(np.abs(p[100:]/base[100:]))
        raw, wide, narrow = wobble(a['phasor']), wobble(es.smooth_arrays(a, .3)['phasor']), wobble(es.smooth_arrays(a, .1)['phasor'])
        self.assertLess(wide, .6*raw)  # one pole, 5.7 Hz half-width: about -6 dB at 10 Hz
        self.assertLess(narrow, wide)

    def test_causal(self):
        a = tone_arrays(wobble_hz=7., depth=.3)
        b = {**a, 'phasor': a['phasor'].copy()}
        b['phasor'][250:] *= 3
        x, y = es.smooth_arrays(a, .3)['phasor'], es.smooth_arrays(b, .3)['phasor']
        self.assertTrue(np.array_equal(x[:250], y[:250]))
        self.assertFalse(np.allclose(x[250:], y[250:]))

    def test_state_cleared_after_gate_off_and_long_gaps(self):
        a = tone_arrays(wobble_hz=7., depth=.3)
        a['gate'][99] = False
        out = es.smooth_arrays(a, .3)['phasor']
        self.assertEqual(out[100, 0], a['phasor'][100, 0])
        b = tone_arrays(wobble_hz=7., depth=.3)
        b['frequency'][200:200+es.MAX_GAP+1] = np.nan
        out = es.smooth_arrays(b, .3)['phasor']
        self.assertEqual(out[200+es.MAX_GAP+1, 0], b['phasor'][200+es.MAX_GAP+1, 0])

    def test_unmatched_component_is_not_smoothed_into_another(self):
        a = tone_arrays()
        a['frequency'][200:] = 103.
        out = es.smooth_arrays(a, .3)['phasor']
        self.assertEqual(out[200, 0], a['phasor'][200, 0])

    def test_bandwidths_follow_the_lead(self):
        self.assertAlmostEqual(es.bandwidth_hz(.3), 5.68, places=2)
        self.assertLess(es.bandwidth_hz(.1), 1/(6*es.LEAD))
        self.assertLess(es.bandwidth_hz(.3), 1.05/(6*es.LEAD))

    def test_engine_scene_keeps_tuning_and_scoring_on_one_engine(self):
        scene = {'arrays': tone_arrays(), 'trace': {}}
        scene['trace']['v2'] = scene['arrays']
        s = es.engine_scene(scene, .3)
        self.assertIs(s['arrays'], s['trace']['v2'])
        self.assertIs(scene['trace']['v2'], scene['arrays'])


if __name__ == '__main__':
    unittest.main()
