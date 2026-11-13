"""Scientific checks for the new offline selector diagnostic; no audio devices."""
import itertools
import unittest

import numpy as np

from anc_lab.selector_headroom import causal_mix, minimum_cost_path, oracle_mix, spectral_loss, transition_block


class SelectorHeadroomTests(unittest.TestCase):
    FS, BLOCK = 2000, 20

    def example(self, horizon=260):
        origins = np.arange(1000, 20000, self.BLOCK)
        at = origins[:, None] + horizon-self.BLOCK + np.arange(1, self.BLOCK+1)
        target = np.sin(2*np.pi*83.3*at/self.FS)
        arms = np.stack((.5*target, target, np.zeros_like(target)))
        return origins, target, arms

    def test_future_target_errors_cannot_change_present_decisions(self):
        origins, target, arms = self.example()
        cutoff = 10000
        before, trace = causal_mix(target, arms, origins, 260, 2.)
        changed = target.copy()
        # Even a partially arrived block is forbidden until its final sample.
        changed[origins+260 > cutoff] += np.random.default_rng(8).normal(0, 100,
            changed[origins+260 > cutoff].shape)
        after, trace_after = causal_mix(changed, arms, origins, 260, 2.)
        eligible = origins <= cutoff
        np.testing.assert_array_equal(before[eligible], after[eligible])
        np.testing.assert_array_equal(trace["selected"][eligible], trace_after["selected"][eligible])

    def test_future_arm_changes_cannot_change_past_output(self):
        origins, target, arms = self.example()
        cutoff = 10000
        before, _ = causal_mix(target, arms, origins, 260, 2.)
        changed = arms.copy()
        changed[:, origins > cutoff, :] *= -100
        after, _ = causal_mix(target, changed, origins, 260, 2.)
        np.testing.assert_array_equal(before[origins <= cutoff], after[origins <= cutoff])

    def test_maturity_boundary_includes_only_complete_targets(self):
        origins, target, arms = self.example()
        _, trace = causal_mix(target, arms, origins, 260, 2.)
        for now, count in zip(origins, trace["matured_rows"]):
            if count:
                self.assertLessEqual(origins[count-1]+260, now)
            if count < len(origins):
                self.assertGreater(origins[count]+260, now)

    def test_cold_start_and_full_history_requirements(self):
        origins, target, arms = self.example()
        out, trace = causal_mix(target, arms, origins, 260, 8.)
        not_ready = (origins < 3*self.FS) | (trace["matured_rows"] < 800)
        np.testing.assert_array_equal(out[not_ready], arms[0, not_ready])
        self.assertTrue(np.any(trace["selected"][~not_ready] == 1))

    def test_one_db_margin_and_ties_do_not_cause_switching(self):
        origins, target, _ = self.example()
        # Only a 0.4 dB residual-power advantage: below the fixed 1 dB margin.
        arms = np.stack((.5*target, (1-.5*10**(-.4/20))*target, np.zeros_like(target)))
        out, trace = causal_mix(target, arms, origins, 260, 2.)
        self.assertEqual(trace["switches"], 0)
        np.testing.assert_array_equal(out, arms[0])
        identical = np.repeat(arms[:1], 3, axis=0)
        _, trace = causal_mix(target, identical, origins, 260, 2.)
        self.assertEqual(trace["switches"], 0)

    def test_transition_renders_sample_ramp_and_reaches_destination(self):
        arms = np.stack((np.zeros(400), np.ones(400)))
        output = transition_block(arms, 0, 1, 0, 400, 200)
        np.testing.assert_allclose(output[:200], np.arange(1, 201)/200)
        np.testing.assert_array_equal(output[200:], 1.)
        self.assertLessEqual(np.max(np.abs(np.diff(output))), .00500000001)

    def test_dynamic_program_matches_exhaustive_paths(self):
        costs = np.random.default_rng(12).uniform(0, 5, (5, 3, 3))
        path, cost = minimum_cost_path(costs)
        def value(states):
            previous = 0
            total = 0.
            for i, state in enumerate(states):
                total += costs[i, previous, state]
                previous = state
            return total
        exhaustive = min(value(states) for states in itertools.product(range(3), repeat=5))
        self.assertAlmostEqual(cost, exhaustive)
        self.assertAlmostEqual(value(path), exhaustive)

    def test_oracle_includes_static_baseline_and_all_costs_are_scored(self):
        n = 12520  # Deliberately short final tail, merged into preceding window.
        t = np.arange(n)/self.FS
        target = np.sin(2*np.pi*83.3*t).reshape(-1, self.BLOCK)
        first = target.copy()
        second = target.copy()
        first[len(first)//2:] *= .2
        second[:len(second)//2] *= .2
        arms = np.stack((first, second, np.zeros_like(target)))
        static, window, details = oracle_mix(target, arms, [83.3])
        self.assertLessEqual(spectral_loss(target-window, [83.3]),
                             spectral_loss(target-static, [83.3])+1e-14)
        self.assertLessEqual(spectral_loss(target-static, [83.3]),
                             spectral_loss(target-first, [83.3])+1e-14)
        self.assertEqual(len(details["window_choices"]), 3)
        self.assertTrue(np.all(np.isfinite(window)))
        self.assertTrue(np.all(window <= np.max(arms, axis=0)+1e-12))
        self.assertTrue(np.all(window >= np.min(arms, axis=0)-1e-12))


if __name__ == "__main__":
    unittest.main()
