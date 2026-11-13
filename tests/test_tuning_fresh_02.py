import unittest

from anc_lab import tuning_fresh as tf
from anc_lab import tuning_fresh_02  # noqa: F401  (applies the second study's paths and seed)


class SecondFreshTest(unittest.TestCase):
    def test_only_paths_and_seed_differ(self):
        self.assertEqual(tf.STUDY.name, 'results-tuning-fresh-02')
        self.assertEqual(tf.AUDIO.name, 'wikimedia-commons-tuning-fresh-02')
        self.assertEqual(tf.ROOM_SEED, 20261031)
        self.assertEqual((tf.MIN_SOURCES, tf.MIN_ROOMS, tf.ROOMS_PER_SOURCE), (12, 25, 3))
        self.assertEqual(tf.ARMS, ('O', 'SD-s30'))

    def test_rule_is_unchanged(self):
        base = {'harmful_keeps_prefix': 5, 'room_harms': 5}
        good = {'harmful_keeps_prefix': 5, 'room_harms': 5}
        self.assertEqual(tf.decide(.01, -.05, good, base, 12, 25)[1], 'pass')
        self.assertEqual(tf.decide(.01, -.05, good, base, 11, 25)[1], 'inconclusive_too_few_rooms')
        self.assertEqual(tf.decide(0., 0., good, base, 12, 25)[1], 'fail')


if __name__ == '__main__':
    unittest.main()
