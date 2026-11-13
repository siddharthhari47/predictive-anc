import unittest

import numpy as np

from anc_lab import engine_smoothing as es
from anc_lab import smoother_timing as st
from anc_lab.antihum import BLOCK, FS


def stream(arrays, alpha=st.ALPHA):
    s = st.PhasorSmoother(alpha)
    out = np.zeros_like(arrays['phasor'])
    for k in range(len(arrays['frequency'])):
        columns = [j for j in range(arrays['frequency'].shape[1]) if not np.isnan(arrays['frequency'][k, j])]
        got = s.step([(float(arrays['frequency'][k, j]), complex(arrays['phasor'][k, j])) for j in columns], arrays['gate'][k])
        for j, (_, p) in zip(columns, got):
            out[k, j] = p
    return out


def messy(seed, rows=800, width=3):
    rng = np.random.default_rng(seed)
    f = 100.+200.*np.arange(width)+np.cumsum(rng.normal(0, .15, (rows, width)), axis=0)
    p = (1+rng.normal(0, .2, (rows, width)))*np.exp(2j*np.pi*f*np.arange(rows)[:, None]*BLOCK/FS+1j*rng.normal(0, .4, (rows, width)))
    missing = rng.random((rows, width)) < .15
    f[missing], p[missing] = np.nan, 0
    p[rng.random((rows, width)) < .02] = 0
    return {'frequency': f, 'phasor': p, 'gate': rng.random(rows) > .05}


class StreamingSmoother(unittest.TestCase):
    def test_matches_the_offline_smoother(self):
        for seed in range(5):
            a = messy(seed)
            np.testing.assert_allclose(stream(a), es.smooth_arrays(a, st.ALPHA)['phasor'], rtol=1e-10, atol=1e-12)

    def test_crossing_tones_and_long_gaps(self):
        a = messy(9, width=2)
        a['frequency'][:, 1] = a['frequency'][:, 0]+1.
        a['frequency'][300:330] = np.nan
        a['phasor'][np.isnan(a['frequency'])] = 0
        np.testing.assert_allclose(stream(a), es.smooth_arrays(a, st.ALPHA)['phasor'], rtol=1e-10, atol=1e-12)

    def test_state_is_bounded(self):
        s = st.PhasorSmoother()
        for k in range(2000):
            s.step([(100.+k, 1+0j), (900.-k/2, 1j), (1500., 2+0j)], True)
            self.assertLessEqual(len(s.states), 3*(st.es.MAX_GAP+1))

    def test_rule(self):
        def run(step, path, quiet):
            return {'smoother_step_ms': {'p99': step, 'max': step}, 'path_ms': {'p99': path, 'max': path, 'count': 1, 'over_5ms': 0, 'over_10ms': 0},
                    'backlog_ms': 0., 'quiet_qualified': quiet}
        self.assertEqual(st.decide([run(.1, 3., True)])['path'], 'pass')
        self.assertEqual(st.decide([run(.1, 6., True)])['path'], 'fail')
        loaded = st.decide([run(.1, 3., False)])
        self.assertEqual((loaded['smoother'], loaded['path']), ('pass', 'inconclusive_contended'))
        self.assertEqual(st.decide([run(.9, 3., False)])['smoother'], 'inconclusive_contended')
        self.assertEqual(st.decide([run(.9, 3., True)])['smoother'], 'fail')


if __name__ == '__main__':
    unittest.main()
