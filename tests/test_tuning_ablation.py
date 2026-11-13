import unittest
from dataclasses import asdict
from itertools import product
import numpy as np
from anc_lab import tuning_ablation as ab
from anc_lab import tuning_accuracy_diagnostic as diag
from anc_lab import antihum_study as room
from anc_lab.tuning import SimulatedListener, TuningSession
from anc_lab.antihum import FS


def to_stage(session, stage):
    """Drive a session with fixed answers until it reaches `stage`."""
    while session.stage != stage:
        step = session.next_step()
        if step.kind == 'sweep':
            session.presses([1., 5., 9.])
        else:
            session.answer('same')


class TuningAblationChecks(unittest.TestCase):
    def test_plain_session_matches_original_answer_for_answer(self):
        rng = np.random.default_rng(3)
        a, b = TuningSession(80., .2, seed=11), ab.AblationSession(80., .2, seed=11)
        self.assertEqual(a.check_on_first, b.check_on_first)
        while not a.done:
            sa, sb = a.next_step(), b.next_step()
            self.assertEqual([asdict(p.setting) for p in sa.presentations], [asdict(p.setting) for p in sb.presentations])
            if sa.kind == 'sweep':
                times = list(rng.uniform(0, 12, 3))
                a.presses(times), b.presses(times)
            else:
                choice = ['A', 'B', 'same'][rng.integers(3)]
                a.answer(choice), b.answer(choice)
        self.assertTrue(b.done)
        self.assertEqual(a.summary(), b.summary())

    def test_search_sweeps_alternate_four_times(self):
        s = ab.AblationSession(80., .2, search=True)
        to_stage(s, 'sweep')
        directions = []
        while s.stage == 'sweep':
            step = s.next_step()
            directions.append(np.sign(step.presentations[0].setting.offset_hz))
            s.presses([1., 5., 9.])
        self.assertEqual(directions, [1, -1, 1, -1])
        self.assertEqual(s.stage, 'phase')

    def test_majority_vote_moves_half_a_step(self):
        for answers, move, asked in [(['A', 'A'], -30., 2), (['B', 'same', 'B'], 30., 3),
                                     (['same', 'same'], 0., 2), (['A', 'B', 'same'], 0., 3)]:
            s = ab.AblationSession(80., .2, search=True)
            to_stage(s, 'phase')
            phase = s.phase
            for i, choice in enumerate(answers):
                self.assertEqual((s.stage, s.fine_index), ('phase', 0))
                d = s.next_step().presentations[1].setting.phase_deg-phase
                self.assertAlmostEqual(d % 360, 60.)
                s.answer(choice)
            self.assertEqual(len(answers), asked)
            self.assertEqual(s.fine_index, 1)
            self.assertAlmostEqual((s.phase-phase+180) % 360-180, move)

    def check_session(self, answers):
        """answers: list of (on/off/same, valid). Returns the finished session."""
        s = ab.AblationSession(80., .2, check=True, seed=5)
        to_stage(s, 'check')
        gain = s.gain
        for heard, valid in answers:
            step = s.next_step()
            on_first = step.presentations[0].setting.gain > 0
            choice = 'same' if heard == 'same' else 'A' if (heard == 'on') == on_first else 'B'
            s.answer(choice, valid=valid)
        self.assertTrue(s.done)
        self.assertEqual(s.gain_before_check, gain)
        return s

    def test_validated_check_rules(self):
        self.assertTrue(self.check_session([('on', True), ('same', True), ('on', True)]).summary()['kept'])
        self.assertTrue(self.check_session([('off', False), ('on', True), ('on', False), ('on', True), ('same', True)]).summary()['kept'])
        self.assertFalse(self.check_session([('on', True), ('same', True), ('same', True)]).summary()['kept'])
        s = self.check_session([('on', True), ('off', True)])
        self.assertFalse(s.summary()['kept'])
        self.assertIn('louder with anti-hum: switched off', s.flags)
        s = self.check_session([('on', False)]*4+[('on', True)]*2)
        self.assertFalse(s.summary()['kept'])
        self.assertTrue(s.flags[-1].startswith('inconclusive'))
        self.assertEqual((s.summary()['check_pairs'], s.summary()['valid_check_pairs']), (6, 2))

    def test_validated_check_null_keep_probability(self):
        p = diag.check_probabilities(0.)
        keep = sum(np.prod([p[x] for x in xs]) for xs in product(['on', 'same', 'off'], repeat=3)
                   if 'off' not in xs and xs.count('on') >= 2)
        self.assertAlmostEqual(keep, 3*p['on']**2*p['same']+p['on']**3)
        self.assertLess(keep, .11)
        self.assertLess(keep, diag.keep_probability(p, p)/2.5)

    def test_validity_reads_only_the_microphone(self):
        listener = SimulatedListener(FS, 1., seed=0)
        t = np.arange(8000)/FS
        mic = .01*np.sin(2*np.pi*90*t)
        state = listener.rng.bit_generator.state
        self.assertTrue(ab.mic_stable(listener, mic, [(0, 4000), (4000, 8000)], 90.)[0])
        mic[4000:] *= 10**(3/20)
        valid, change = ab.mic_stable(listener, mic, [(0, 4000), (4000, 8000)], 90.)
        self.assertFalse(valid)
        self.assertAlmostEqual(change, -3., places=1)
        self.assertEqual(listener.rng.bit_generator.state, state)

    def test_seeds_are_fixed_and_start_with_the_recorded_one(self):
        seeds = ab.seeds_for('old-000-r0', 123)
        self.assertEqual(seeds[0], 123)
        self.assertEqual(seeds, ab.seeds_for('old-000-r0', 123))
        self.assertEqual(len(set(seeds)), ab.EXTRA_SEEDS+1)
        self.assertNotEqual(seeds[1:], ab.seeds_for('old-001-r0', 123)[1:])

    def test_original_arm_reproduces_saved_room_tuning(self):
        p = h_read_accuracy()
        c = next(c for c in p['cases'] if c['menu_tones'] == 1)
        scene, meta, saved = diag.load(c)
        seed = meta['tuning_seeds']['30']['1.0']
        settings, _ = ab.tune(scene, seed)
        self.assertGreater(diag.numbers_equal([asdict(s) for s in settings], saved['v2_settings']), 0)
        reference, _ = room.tune_by_ear(scene, ab.LEAD, 1., seed)
        self.assertEqual([asdict(s) for s in settings], [asdict(s) for s in reference])


def h_read_accuracy():
    from anc_lab import selector_headroom as h
    return h.read(diag.STUDY/'protocol.json')


if __name__ == '__main__':
    unittest.main()
