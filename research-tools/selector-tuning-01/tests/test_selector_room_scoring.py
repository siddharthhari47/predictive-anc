import unittest
import numpy as np
from anc_lab.antihum import ToneSetting, FS, BLOCK
from anc_lab.selector_room_scoring import evaluate, relaxed_retune_bound, summarize


class RoomScoringTests(unittest.TestCase):
    def test_biased_switch_is_harmful_and_relaxed_retuning_is_only_an_oracle(self):
        n = 8*FS
        seen = np.arange(BLOCK, n+1, BLOCK)
        t = np.arange(n)/FS
        phase = np.exp(2j*np.pi*100*(seen-1)/FS)
        a = {'seen': seen, 'frequency': np.full((len(seen), 1), 100.),
             'phasor': .01*phase[:, None], 'gate': np.ones(len(seen), bool)}
        b = {**a, 'phasor': -a['phasor']}
        weights = np.tile([1., 0., 0.], (len(seen), 2, BLOCK, 1))
        weights[500:] = [0., 1., 0.]
        trace = {'v2': a, 'bank': [b, b], 'weights': weights}
        off = .01*np.cos(2*np.pi*100*t)+1e-4*np.cos(2*np.pi*127*t)
        scene = {'trace': trace, 'ears': [off], 'prefix': 2*FS, 'n': n, 'unreported': 0,
                 'earphone': (np.array([1.]), np.array([1.])), 'earphone_gain': 1.,
                 'tones': [{'frequency': 100.}]}
        baseline, _ = evaluate(scene, [ToneSetting(100., 1.)], .03, 'v2', [100.])
        harmful, _ = evaluate(scene, [ToneSetting(100., 1.)], .03, 'chooser', [100.])
        self.assertGreater(baseline['band_db'], 35.)
        self.assertLess(harmful['band_db'], -3.)
        arrival = int(seen[500])-1+60
        bound = relaxed_retune_bound(scene, .03, [{'arrival_sample': arrival}])
        self.assertTrue(bound['relaxed_noncausal'])
        self.assertEqual(bound['segments'], 2)
        self.assertGreater(bound['band_db'], 35.)

    def test_sources_not_rooms_are_bootstrapped_and_new_harm_vetoes_gain(self):
        cases = []
        for source, losses in [('a', [-2., 0., 0.]), ('b', [1.])]:
            for k, gain in enumerate(losses):
                rows = []
                for lead in (30, 200):
                    rows.extend([{'lead_ms': lead, 'arm': arm, 'tone_db': 5.+difference,
                                  'band_db': .1, 'clipped_fraction': 0.,
                                  'bands': [{'centre_hz': 100., 'amplification_db': boost}]}
                                 for arm, difference, boost in [('v2_tuned', 0., 0.),
                                     ('chooser_reuse_v2', gain, 2. if source == 'b' else 0.),
                                     ('chooser_tuned', gain, 0.)]])
                cases.append({'source_id': source, 'case_id': source+str(k), 'rows': rows, 'switch_windows': []})
        result = summarize(cases, {str(lead): {'exposed_complete_sources': 6} for lead in (30, 200)})
        out = result['30']['chooser_reuse_v2']
        self.assertAlmostEqual(out['mean_paired_db'], (1.-2./3)/2)
        self.assertEqual(len(out['new_boosts']), 1)
        self.assertFalse(out['point_criteria_passed'])


if __name__ == '__main__':
    unittest.main()
