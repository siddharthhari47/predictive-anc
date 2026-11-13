"""Check frequency-group separation and pooled source boundaries."""
import unittest
import numpy as np

from anc_lab.generalization import DEVELOPMENT, HELD_OUT, normalized_prefix, pooled_training


class GeneralizationTests(unittest.TestCase):
    def test_held_out_frequencies_are_distinct_from_development(self):
        development = [f for group in DEVELOPMENT for f in group]
        held_out = [f for group in HELD_OUT.values() for f in group]
        self.assertTrue(all(abs(a-b)>1 for a in development for b in held_out))

    def test_pooled_examples_never_span_source_boundaries(self):
        sources = [np.arange(100.)**2, np.arange(120.)**3+1e6]
        horizons = np.array([1, 7])
        inputs, targets, counts = pooled_training(sources, horizons, lags=4)
        cursor = 0
        for raw, count in zip(sources, counts):
            source, _ = normalized_prefix(raw, len(raw))
            origins = np.arange(3, len(source)-7, 5)
            expected_x = source[origins[:,None]-np.arange(4)]
            expected_y = source[origins[:,None]+horizons]
            np.testing.assert_array_equal(inputs[cursor:cursor+len(origins)], expected_x)
            np.testing.assert_array_equal(targets[cursor:cursor+len(origins)], expected_y)
            self.assertLess(count['last_target'], len(raw))
            cursor += len(origins)
        self.assertEqual(cursor, len(inputs))

    def test_new_source_scaling_never_uses_future_values(self):
        raw = np.arange(100.)
        changed = raw.copy(); changed[40:] = 1e9
        a, am = normalized_prefix(raw, 40)
        b, bm = normalized_prefix(changed, 40)
        self.assertEqual(am, bm)
        np.testing.assert_array_equal(a[:40], b[:40])


if __name__ == '__main__':
    unittest.main()
