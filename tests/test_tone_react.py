"""Checks for study 05: the joint band check with tones fading in and out (tone_react, forecaster_study_05)."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

from anc_lab.tone_floors import JointCheckBank
from anc_lab.tone_forecasters import stream_forecasts
from anc_lab.tone_react import FadeCheckBank, association, shaped

from test_tone_floors import BOTH, make
from test_tone_forecaster import FS, BLOCK, scene


def appearing(seconds=8, at=3., stop=None, freq=83.3, amp=.5, noise=.05, seed=4):
    """Noise with one tone that starts at `at` s (and stops at `stop` s)."""
    rng = np.random.default_rng(seed)
    t = np.arange(seconds*FS)/FS
    x = noise*rng.standard_normal(len(t))
    on = (t >= at) & (t < (stop if stop is not None else np.inf))
    return x+on*amp*np.sin(2*np.pi*freq*t+rng.uniform(-np.pi, np.pi))


def push_until(fc, x, seconds):
    end = int(seconds*FS)//BLOCK*BLOCK
    for start in range(0, end, BLOCK):
        fc.push(x[start:start+BLOCK])
    return end


class ToneReactTests(unittest.TestCase):
    def test_step_fades_are_the_joint_check(self):
        x = scene(seconds=10, tones=((83.3, .5), (171.7, .3), (233.9, .2)), noise=.6)
        grid = np.arange(999, len(x)-int(BOTH[-1]), BLOCK)
        a = stream_forecasts(make(JointCheckBank), x, grid, BOTH)
        fc = make(FadeCheckBank, fade_in_seconds=.01, fade_out_seconds=.01, shape='step')
        b = stream_forecasts(fc, x, grid, BOTH)
        np.testing.assert_array_equal(a, b)
        self.assertGreater(sum(fc.counters['band_checks']), 5)

    def test_shapes(self):
        np.testing.assert_allclose(shaped([0., .5, 1., 1.5], 'cosine'), [0., .5, 1., 1.])
        np.testing.assert_allclose(shaped([-.2, .3, 1.], 'linear'), [0., .3, 1.])
        np.testing.assert_array_equal(shaped([0., .1, 1.], 'step'), [0., 1., 1.])
        with self.assertRaises(ValueError):
            shaped(.5, 'square')
        with self.assertRaises(ValueError):
            make(FadeCheckBank, shape='square')

    def test_a_new_tone_fades_in(self):
        x = appearing()
        fc = make(FadeCheckBank, lines=False, fade_in_seconds=.1, fade_out_seconds=.1)
        levels, end = [], 0
        for start in range(0, int(6*FS), BLOCK):
            fc.push(x[start:start+BLOCK])
            s = fc.active[0]-1
            levels.append(float(fc.level[s].max()) if fc.level.shape[1] else 0.)
        levels = np.array(levels)
        first = int(np.flatnonzero(levels > 0)[0])
        self.assertGreater(first*BLOCK/FS, 3.)                                   # nothing before the tone
        np.testing.assert_allclose(levels[first:first+10], np.arange(1, 11)/10)  # 0.1 s: ten blocks up
        self.assertTrue(np.all(levels[first+10:first+30] == 1.))

    def test_a_dropped_tone_fades_out_free_running(self):
        x = scene(seconds=4, tones=((83.3, .5), (171.7, .3)))
        fc = make(FadeCheckBank, lines=False, fade_in_seconds=.05, fade_out_seconds=.1)
        push_until(fc, x, 3.)
        s = fc.active[0]-1
        self.assertTrue(np.all(fc.level[s] == 1.))
        last, omega = fc.last[s].copy(), fc.omega.copy()
        fc.selected, fc.extra = [], []
        fc._reconcile()                                                          # the selector drops both tones
        self.assertEqual(fc.level.shape, (len(fc.options), 0))
        mine = [gh for gh in fc.ghosts if gh[0] == s]
        self.assertEqual(sorted(gh[1] for gh in mine), sorted(omega[last[j], j] for j in range(2)))
        before = mine[0][2]
        fc._choose()
        self.assertAlmostEqual(mine[0][2], before*np.exp(1j*mine[0][1]*BLOCK))  # free-running at its own frequency
        self.assertAlmostEqual(mine[0][3]/fc.full, .9)
        counts = [len(fc.ghosts)]
        for _ in range(10):
            fc._choose()
            counts.append(len(fc.ghosts))
        self.assertGreater(counts[8], 0)
        self.assertEqual(counts[9], 0)                                           # gone after ten blocks (0.1 s)
        self.assertEqual(fc.components(0), [])

    def test_association_matches_the_bank(self):
        test = self
        seen = []

        class Checked(FadeCheckBank):
            def _reconcile(self):
                power, anchor = self.power.copy(), self.anchor.copy()
                order = association(anchor, self.selected, self.extra, self.associate_hz, self.max_tones)
                super()._reconcile()
                test.assertEqual(len(order), len(self.anchor))
                for i, k in enumerate(order):
                    if k is not None:
                        np.testing.assert_array_equal(self.power[:, i], power[:, k])
                        seen.append(k)
                    else:
                        test.assertTrue(np.all(self.power[:, i] == 0))

        x = appearing(seconds=10, at=2., stop=6.)+scene(seconds=10, tones=((171.7, .3), (233.9, .2)), noise=.3, seed=2)
        push_until(make(Checked), x, 10.)
        self.assertGreater(len(seen), 10)

    def test_switch_fade(self):
        x = scene(seconds=4)
        fc = make(FadeCheckBank, fade_in_seconds=.05, fade_out_seconds=.05, switch_fade_seconds=.1)
        push_until(fc, x, 3.)
        old = fc.active[0]
        self.assertEqual(fc.mix[0][old], fc.switch_fade)
        fc.active[0] = 0                                                         # as if the check chose no output
        end = int(3*FS)//BLOCK*BLOCK
        fc.push(x[end:end+BLOCK])
        self.assertEqual((fc.mix[0][old], fc.mix[0][0]), (9, 1))               # a tenth of the way per block
        outputs = sum(abs(ph) for _, ph in fc.components(0))
        self.assertGreater(outputs, 0.)                                          # still mostly the old setting
        for i in range(9):
            fc.push(x[end+(i+1)*BLOCK:end+(i+2)*BLOCK])
        self.assertEqual(fc.components(0), [])

    def test_fade_check_is_block_causal(self):
        x = scene(seconds=8)
        changed = x.copy(); changed[9001:] = np.random.default_rng(9).standard_normal(len(x)-9001)
        grid = np.arange(999, len(x)-int(BOTH[-1]), BLOCK)
        a = stream_forecasts(make(FadeCheckBank, switch_fade_seconds=.2), x, grid, BOTH)
        b = stream_forecasts(make(FadeCheckBank, switch_fade_seconds=.2), changed, grid, BOTH)
        keep = grid <= 9000
        np.testing.assert_array_equal(a[keep], b[keep])

    def test_fades_are_reported(self):
        s = make(FadeCheckBank, fade_in_seconds=.2, fade_out_seconds=.1, switch_fade_seconds=.3,
                 start=(.2, False)).settings()
        self.assertEqual(s['fades'], {'fade_in_seconds':.2, 'fade_out_seconds':.1, 'shape':'cosine',
                                      'switch_fade_seconds':.3})
        self.assertEqual(s['joint_check']['start_setting'], (.2, False))


def _summaries(cand_boosts, cand_change, cand_tone, cand_p99=1.):
    """Development summaries in which the joint check has 3 boosts (2 on change scenes) and the candidate as given."""
    def rec_row(boosts, tone):
        return {'third_octave_boosts':[{}]*boosts, 'near_boosts':[{}]*boosts, 'whole_band_boosts':[],
                'median_tone_bin_both_horizons_db':tone, 'median_whole_band_both_horizons_db':1.}
    rec = {'joint_gated':rec_row(1, 6.), 'v2_gated':rec_row(4, 3.), 'bank_wide_lines_gated':rec_row(3, 5.),
           'fade0.1_gated':rec_row(cand_boosts-cand_change, cand_tone)}
    syn = {m:{'late_third_octave_boosts':0, 'late_near_boosts':0, 'mean_objective_db':7., 'windows_below_minus_half_db':0}
           for m in rec}
    window = {'max_third_octave_change_db':1.5}
    scenes = [{'scene':'tones_stop_9s#dev0', 'late_window_scores':[dict(window, method='joint_gated')]*2
               + [dict(window, method='fade0.1_gated')]*cand_change}]
    for m, n in (('joint_gated', 2), ('fade0.1_gated', cand_change)):
        syn[m]['late_third_octave_boosts'] = n
    runs = [{'methods':{m:{'own_block_ms_p99':p} for m, p in (('joint', 1.), ('bank_wide_lines', 1.), ('fade0.1', cand_p99))}}]
    scenes[0]['methods'] = runs[0]['methods']
    return rec, syn, runs, scenes


class Study05Tests(unittest.TestCase):
    def setUp(self):
        from anc_lab import forecaster_study_05 as fs5
        self.fs5 = fs5

    def test_change_scene_boosts_count_only_the_change_scenes(self):
        w = lambda m, db: {'method':m, 'max_third_octave_change_db':db}
        scenes = [{'scene':'tone_appears_9s#test0', 'late_window_scores':[w('a', 1.2), w('a', .7), w('b', 3.)]},
                  {'scene':'single_tone#test0', 'late_window_scores':[w('a', 4.)]},
                  {'scene':'source_change_9s#dev1', 'late_window_scores':[w('a', 1.)]}]
        self.assertEqual(self.fs5.change_scene_boosts(scenes, 'a'), 2)
        self.assertEqual(self.fs5.change_scene_boosts(scenes, 'a', threshold=.5), 3)

    def test_rule_needs_fewer_boosts_on_the_change_scenes(self):
        cand = [{'name':'fade0.1', 'options':{}}]
        rec, syn, runs, scenes = _summaries(2, 1, 5.)
        pick, table, ref = self.fs5.apply_development_rule(rec, syn, runs, scenes, cand)
        self.assertEqual(pick, 'fade0.1')
        self.assertEqual(table[0]['tone_bin_needed_db'], 4.5)              # v2 + half of the joint check's lead
        self.assertEqual((table[0]['change_scene_boosts'], ref['joint']['change_scene_boosts']), (1, 2))
        rec, syn, runs, scenes = _summaries(2, 2, 5.)                      # fewer boosts, none fewer on the change scenes
        pick, table, _ = self.fs5.apply_development_rule(rec, syn, runs, scenes, cand)
        self.assertIsNone(pick)
        self.assertEqual([k for k, ok in table[0]['checks'].items() if not ok], ['b_fewer_change_boosts'])
        rec, syn, runs, scenes = _summaries(2, 1, 4.)                      # tone gain lost
        self.assertFalse(self.fs5.apply_development_rule(rec, syn, runs, scenes, cand)[1][0]['checks']['e_tone_gain_kept'])
        rec, syn, runs, scenes = _summaries(2, 1, 5., cand_p99=1.6)        # slower than joint by more than 0.5 ms
        self.assertFalse(self.fs5.apply_development_rule(rec, syn, runs, scenes, cand)[1][0]['checks']['h_time'])

    def test_method_names_cover_the_fades(self):
        names = self.fs5.fs2.method_names(self.fs5.COMPARATORS+self.fs5.CANDIDATES)
        for n in ('v2_gated', 'joint_gated', 'fade0.1_gated', 'fade0.1_linear_ungated', 'fade0.1_start0.2_gated'):
            self.assertIn(n, names)
        v2 = json.loads(self.fs5.s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
        bank = self.fs5.fs2.make_bank(self.fs5.CANDIDATES[4], v2)
        self.assertIsInstance(bank, FadeCheckBank)
        self.assertEqual(bank.settings()['fades']['switch_fade_seconds'], .3)

    def test_synthetic_test_draws_avoid_development_and_buzz_frequencies(self):
        from anc_lab import forecaster_study as fsd
        _, wander, _ = fsd.development_scenes()
        forbidden = self.fs5.synthetic_forbidden(wander)
        buzz = [f for g in self.fs5.fs3.buzz_scenes()[0] for fs in g.values() for f in fs]
        self.assertTrue(all(any(abs(f-x) < .01 for x in forbidden) for f in buzz))
        syn = dict(self.fs5.SYNTHETIC_TEST, forbidden_frequencies=forbidden)
        standard, wdraws = self.fs5.fs2.draw_synthetic_test(syn, forbidden)
        self.assertEqual((standard, wdraws), self.fs5.fs2.draw_synthetic_test(syn, forbidden))
        self.assertEqual((len(standard), len(wdraws)), (6, 3))
        protocol = {'synthetic_test':dict(syn, standard_draws=standard, wander_draws=wdraws)}
        tasks = self.fs5.test_scene_tasks(json.loads(json.dumps(protocol)))
        self.assertEqual(sum(t[0].split('#')[0] in self.fs5.CHANGE_SCENES for t in tasks), 18)
        self.assertEqual(len({t[3] for t in tasks}), len(tasks))           # every scene has its own seed

    def test_fresh_list_is_new(self):
        self.assertEqual(self.fs5.fresh_problems(), [])
        seen = dict(self.fs5.fs2.FRESH_RECORDINGS[0])
        self.assertEqual(len(self.fs5.fresh_problems([seen])), 2)          # already local, and an earlier author
        for e in self.fs5.FRESH_RECORDINGS:
            self.assertEqual(set(e) >= {'file', 'title', 'sha1', 'bytes', 'seconds', 'author', 'licence', 'acoustic'}, True)

    def test_freeze_records_no_candidate_and_runs_once(self):
        with tempfile.TemporaryDirectory() as folder:
            dev = {'code_sha256':self.fs5._code_hashes(), 'development_pick':None, 'rule':self.fs5.DEVELOPMENT_RULE,
                   'rule_table':[], 'rule_reference':{}, 'comparators':self.fs5.COMPARATORS,
                   'candidates':self.fs5.CANDIDATES}
            Path(folder, 'development.json').write_text(json.dumps(dev), encoding='utf-8')
            out = Path(folder, 'protocol.json')
            p = self.fs5.freeze_protocol(folder, output=out)
            self.assertIsNone(p['frozen_candidate'])
            self.assertNotIn('synthetic_test', p)
            with self.assertRaises(ValueError):
                self.fs5.freeze_protocol(folder, output=out)
            with self.assertRaises(ValueError):                            # nothing to test
                self.fs5.run_test(output=Path(folder, 'test'), protocol_path=out)
            out.unlink()
            Path(folder, 'development.json').write_text(json.dumps(dict(dev, development_pick='fade0.1')), encoding='utf-8')
            with mock.patch.object(self.fs5, 'FRESH_RECORDINGS', []), self.assertRaises(ValueError):
                self.fs5.freeze_protocol(folder, output=out)               # a pick needs a fresh list
            Path(folder, 'development.json').write_text(json.dumps(dict(dev, code_sha256={})), encoding='utf-8')
            with self.assertRaises(ValueError):                            # code changed since development
                self.fs5.freeze_protocol(folder, output=out)
            self.assertFalse(out.exists())

    def test_test_stage_runs_once(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'test').mkdir()
            with self.assertRaises(ValueError):
                self.fs5.run_test(output=Path(folder, 'test'), protocol_path=Path(folder, 'missing.json'))

    def test_development_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'keep.txt').write_text('x')
            with self.assertRaises(ValueError):
                self.fs5.run_development(folder)

    def test_frozen_code_covers_study_03(self):
        self.assertEqual(self.fs5.FROZEN_CODE[:len(self.fs5.fs3.FROZEN_CODE)], self.fs5.fs3.FROZEN_CODE)
        self.assertIn('tone_react.py', self.fs5.FROZEN_CODE)
        self.assertEqual(self.fs5.fs2.BANK_KINDS['react'], FadeCheckBank)


if __name__ == '__main__':
    unittest.main()
