import unittest
from dataclasses import asdict
import numpy as np
from anc_lab import tuning_decision as td
from anc_lab import tuning_ablation as ab
from anc_lab import tuning_accuracy_diagnostic as diag
from anc_lab import selector_headroom as h
from anc_lab.tuning import SimulatedListener
from anc_lab.antihum import FS


def to_check(session):
    while session.stage != 'check':
        step = session.next_step()
        if step.kind == 'sweep':
            session.presses([1., 5., 9.])
        else:
            session.answer('same')


def checked(answers, seed=5):
    """answers: list of (heard, background_db). Returns the finished session."""
    s = td.DecisionSession(80., .2, sequential=True, seed=seed)
    to_check(s)
    for heard, background in answers:
        step = s.next_step()
        on_first = step.presentations[0].setting.gain > 0
        choice = 'same' if heard == 'same' else 'A' if (heard == 'on') == on_first else 'B'
        s.answer(choice, background_db=background)
    return s


class TuningDecisionChecks(unittest.TestCase):
    def test_evidence_signs_and_background_correction(self):
        self.assertGreater(td.pair_llr('on', 0.), 0)
        self.assertLess(td.pair_llr('off', 0.), 0)
        self.assertLess(td.pair_llr('same', 0.), 0)
        # "On quieter" is weaker evidence when the background itself fell in the on interval.
        self.assertLess(td.pair_llr('on', -3.), td.pair_llr('on', 0.))
        # "Same" while the background rose in the on interval suggests the anti-hum cancelled the rise.
        self.assertGreater(td.pair_llr('same', 3.), td.pair_llr('same', 0.))

    def test_sequential_stops(self):
        s = checked([('on', 0.)]*3)
        self.assertTrue(s.done and s.summary()['kept'])
        self.assertEqual(s.summary()['check_pairs'], 3)
        s = checked([('off', 0.)])
        self.assertFalse(s.done)  # one "louder" answer (-1.91) is just short of the mute bound (-2.20)
        s = checked([('off', 0.), ('same', 0.)])
        self.assertTrue(s.done)
        self.assertFalse(s.summary()['kept'])
        s = checked([('on', 0.), ('same', 0.)]*3)
        self.assertTrue(s.done)
        self.assertEqual(s.summary()['check_pairs'], 6)
        self.assertEqual(s.summary()['kept'], s.evidence > 0)

    def test_null_and_useful_operating_points(self):
        rng = np.random.default_rng(0)
        def keep_rate(effect, n=3000):
            kept = 0
            for _ in range(n):
                evidence, pairs = 0., 0
                while td.LOWER < evidence < td.UPPER and pairs < td.MAX_PAIRS:
                    b = rng.normal(0, 1.5)
                    d = effect+b+rng.normal(0, np.sqrt(2))
                    heard = 'same' if abs(d) < 1 else 'on' if d < 0 else 'off'
                    evidence += td.pair_llr(heard, b+rng.normal(0, 1.))
                    pairs += 1
                kept += evidence >= td.UPPER or (evidence > td.LOWER and evidence > 0)
            return kept/n
        self.assertLess(keep_rate(0.), .2)
        self.assertLess(keep_rate(1.), .05)
        self.assertGreater(keep_rate(-2.), .85)

    def test_background_sign_follows_presentation_order(self):
        listener = SimulatedListener(FS, 1., seed=0)
        t = np.arange(8000)/FS
        mic = .01*np.sin(2*np.pi*90*t)
        mic[4000:] *= 10**(3/20)
        on_first = td.background_change(listener, mic, [(0, 4000), (4000, 8000)], True, 90.)
        off_first = td.background_change(listener, mic, [(0, 4000), (4000, 8000)], False, 90.)
        self.assertAlmostEqual(on_first, -3., places=1)
        self.assertAlmostEqual(on_first, -off_first)

    def test_seeds_extend_the_ablation_seeds(self):
        self.assertEqual(td.seeds_for('x', 7)[:ab.EXTRA_SEEDS+1], ab.seeds_for('x', 7))
        self.assertEqual(len(set(td.seeds_for('x', 7))), td.SEEDS)

    def test_original_and_search_arms_reproduce_ablation_runs(self):
        p = h.read(ab.STUDY/'protocol.json')
        c = next(c for c in p['cases'] if c['menu_tones'] == 1)
        scene, _, _ = diag.load(c)
        old = {(r['sigma'], r['seed_index'], r['arm']): r for r in h.read(ab.STUDY/'cases'/(c['case_id']+'.json'))['runs']}
        for k in (0, 3):
            for arm, search in (('O', False), ('S', True)):
                settings, _ = td.tune(scene, c['seeds'][k], 2., search, False)
                self.assertEqual([asdict(s) for s in settings], old[(2., k, arm)]['settings'])


if __name__ == '__main__':
    unittest.main()
