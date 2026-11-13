import json
import unittest

import numpy as np

from anc_lab import engine_smoothing as es
from anc_lab import selector_headroom as h
from anc_lab import selector_room_study as rooms
from anc_lab import tuning_decision as td
from anc_lab import tuning_fresh as tf
from anc_lab.antihum import FS

CASE = 'fresh-018-r0'


class ParityWithDevelopmentRooms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        c = next(c for c in h.read(td.STUDY/'protocol.json')['cases'] if c['case_id'] == CASE)
        cls.case = c
        cls.saved, cls.meta = rooms.load_case(c)
        with np.load(tf.ROOT/cls.meta['source_path']) as a:
            dry = a['reference'].copy()
        _, cls.scene = tf.build_room(dry, cls.meta['seed'])

    def test_rebuilt_room_matches_saved_room(self):
        np.testing.assert_array_equal(self.scene['mic'], self.saved['mic'])
        np.testing.assert_array_equal(self.scene['ears'][0], self.saved['ears'][0])
        self.assertEqual([t['frequency'] for t in self.scene['tones']], [t['frequency'] for t in self.saved['tones']])
        for key in ('prefix', 'n', 'warm', 'unreported'):
            self.assertEqual(self.scene[key], self.saved[key])

    def test_both_arms_reproduce_saved_development_runs(self):
        reference = self.meta['reference_tones_hz']
        old = {(r['sigma'], r['seed_index'], r['arm']): r
               for r in h.read(es.STUDY/'cases'/(CASE+'.json'))['runs']}
        seed = self.case['seeds'][0]
        o = tf.tuned_run(self.scene, reference, 1., 0, seed, 'O')
        s = tf.tuned_run(es.engine_scene(self.scene, tf.ALPHA), reference, 1., 0, seed, 'SD-s30')
        self.assertEqual(o['settings'], old[(1., 0, 'O')]['settings'])
        self.assertEqual(o['room'], old[(1., 0, 'O')]['room'])
        self.assertEqual(s['settings'], old[(1., 0, 'SD-s30')]['settings'])
        self.assertEqual(s['room'], old[(1., 0, 'SD-s30')]['room'])


class Rule(unittest.TestCase):
    good = {'harmful_keeps_prefix': 1, 'room_harms': 1}
    base = {'harmful_keeps_prefix': 2, 'room_harms': 2}

    def test_pass_needs_all_conditions(self):
        self.assertEqual(tf.decide(.01, 0., self.good, self.base, 12, 25)[1], 'pass')
        self.assertEqual(tf.decide(-.01, 0., self.good, self.base, 12, 25)[1], 'fail')
        self.assertEqual(tf.decide(.01, -.06, self.good, self.base, 12, 25)[1], 'fail')
        self.assertEqual(tf.decide(.01, 0., self.base, self.good, 12, 25)[1], 'fail')

    def test_too_few_rooms_is_inconclusive_even_when_scores_pass(self):
        self.assertEqual(tf.decide(.5, 0., self.good, self.base, 11, 25)[1], 'inconclusive_too_few_rooms')
        self.assertEqual(tf.decide(.5, 0., self.good, self.base, 12, 24)[1], 'inconclusive_too_few_rooms')

    def test_room_seeds_are_stable_and_distinct(self):
        self.assertEqual(tf.room_seed('tf-001', 0), tf.room_seed('tf-001', 0))
        self.assertNotEqual(tf.room_seed('tf-001', 0), tf.room_seed('tf-001', 1))


if __name__ == '__main__':
    unittest.main()
