"""Checks for study 03: the capped joint band check (tone_cap) and the study's development plumbing."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from anc_lab import forecaster_study_03 as fs3
from anc_lab.release_study import in_parity
from anc_lab.tone_cap import CappedCheckBank
from anc_lab.tone_floors import JointCheckBank
from anc_lab.tone_forecasters import stream_forecasts

from test_tone_floors import BOTH, make
from test_tone_forecaster import FS, BLOCK, scene


def feed(fc, bands_db, total_db, checks=None):
    """Put band levels straight into the check's history and decide once."""
    for _ in range(checks or fc.min_decide):
        fc.history_db[0].append((np.array(bands_db, float), np.array(total_db, float)))
    fc._decide(0)


def one_band_louder(fc, louder_db, total_db=-6.):
    """Every setting quieter in total but `louder_db` louder than no output in its lowest band."""
    rows = len(fc.settings()['joint_check']['settings'])+1                # no output, then the ten settings
    bands = np.zeros((rows, len(fc.bands)))
    bands[1:, 0] = louder_db
    total = np.r_[0., np.full(rows-1, total_db)]
    return bands, total


class ToneCapTests(unittest.TestCase):
    def test_no_cap_is_the_joint_check(self):
        x = scene(seconds=10, tones=((83.3, .5), (171.7, .3), (233.9, .2)), noise=.6)
        grid = np.arange(999, len(x)-int(BOTH[-1]), BLOCK)
        a = stream_forecasts(make(JointCheckBank), x, grid, BOTH)
        fc = make(CappedCheckBank, cap_db=np.inf)
        b = stream_forecasts(fc, x, grid, BOTH)
        np.testing.assert_array_equal(a, b)
        self.assertGreater(sum(fc.counters['decisions']), 0)
        self.assertEqual(fc.counters['capped_decisions'], [0, 0])

    def test_limit(self):
        fc = make(CappedCheckBank, cap_db=1.)
        self.assertEqual(fc.limit_db(np.array([0., .1, .2])), .5)          # margin when every setting is quiet
        self.assertEqual(fc.limit_db(np.array([0., .6, .9])), .85)         # tie fallback below the cap
        self.assertEqual(fc.limit_db(np.array([0., 3., 4.])), 1.)          # the cap binds
        fc.cap_db = .5
        self.assertEqual(fc.limit_db(np.array([0., 3., 4.])), .5)          # cap at the margin: no fallback
        fc.cap_db = np.inf
        self.assertEqual(fc.limit_db(np.array([0., 3., 4.])), 3.25)        # the joint check's rule

    def test_cap_silences_a_setting_the_joint_check_keeps(self):
        joint = make(CappedCheckBank, cap_db=np.inf)
        bands, total = one_band_louder(joint, 3.)
        feed(joint, bands, total)
        self.assertGreater(joint.active[0], 0)                             # the fallback keeps a setting 3 dB loud
        capped = make(CappedCheckBank, cap_db=1.)
        feed(capped, bands, total)
        self.assertEqual(capped.active[0], 0)                              # the cap leaves only no output
        c = capped.counters
        self.assertEqual((c['decisions'][0], c['fallback_decisions'][0], c['capped_decisions'][0], c['silent_decisions'][0]),
                         (1, 1, 1, 1))
        small = make(CappedCheckBank, cap_db=1.)
        bands, total = one_band_louder(small, .7)
        feed(small, bands, total)
        self.assertGreater(small.active[0], 0)                             # below the cap the fallback still works
        self.assertEqual(small.counters['silent_decisions'][0], 0)

    def test_cap_at_margin_never_keeps_a_loud_setting(self):
        x = scene(seconds=10, tones=((83.3, .5), (171.7, .3), (233.9, .2)), noise=.6)
        grid = np.arange(999, len(x)-int(BOTH[-1]), BLOCK)
        fc = make(CappedCheckBank, cap_db=.5)
        seen = []
        original = fc._decide

        def checked(g):
            original(g)
            louder = np.median([b for b, _ in fc.history_db[g]], axis=0).max(axis=1)
            seen.append(louder[fc.active[g]])
        fc._decide = checked
        stream_forecasts(fc, x, grid, BOTH)
        self.assertGreater(len(seen), 0)
        self.assertLessEqual(max(seen), .5+1e-9)
        self.assertEqual(fc.counters['fallback_decisions'], [0, 0])

    def test_capped_check_is_block_causal(self):
        x = scene(seconds=8)
        changed = x.copy(); changed[9001:] = np.random.default_rng(9).standard_normal(len(x)-9001)
        grid = np.arange(999, len(x)-int(BOTH[-1]), BLOCK)
        a = stream_forecasts(make(CappedCheckBank), x, grid, BOTH)
        b = stream_forecasts(make(CappedCheckBank), changed, grid, BOTH)
        keep = grid <= 9000
        np.testing.assert_array_equal(a[keep], b[keep])

    def test_cap_is_reported(self):
        self.assertEqual(make(CappedCheckBank, cap_db=2.).settings()['joint_check']['cap_db'], 2.)


class Study03Tests(unittest.TestCase):
    def test_buzz_draws_avoid_every_test_frequency_and_repeat(self):
        forbidden = fs3.buzz_forbidden()
        a, tasks = fs3.buzz_scenes()
        b, _ = fs3.buzz_scenes()
        self.assertEqual(a, b)
        self.assertEqual(len(tasks), 8)
        self.assertEqual({t[1] for t in tasks}, {'buzz'})
        for g in a:
            self.assertEqual(g['harmonic'][1], round(2*g['harmonic'][0], 1))
            for f in [f for fs in g.values() for f in fs]:
                self.assertTrue(in_parity(f, 0))
                self.assertTrue(all(abs(f-x) > 2 for x in forbidden))
                self.assertGreaterEqual(f, 102.)

    def test_method_names_cover_the_caps(self):
        names = fs3.fs2.method_names(fs3.COMPARATORS+fs3.CANDIDATES)
        for n in ('v2_gated', 'joint_gated', 'bank_wide_lines_gated', 'cap0.5_gated', 'cap3_ungated', 'online_ar'):
            self.assertIn(n, names)

    def test_rule_needs_fewer_boosts_than_the_joint_check(self):
        def summaries(cap_boosts, cap_tone):
            def rec_row(boosts, tone):
                return {'third_octave_boosts':[{}]*boosts, 'near_boosts':[{}]*boosts, 'whole_band_boosts':[],
                        'median_tone_bin_both_horizons_db':tone, 'median_whole_band_both_horizons_db':1.}
            def syn_row():
                return {'late_third_octave_boosts':0, 'late_near_boosts':0, 'mean_objective_db':7.,
                        'windows_below_minus_half_db':0}
            rec = {'joint_gated':rec_row(2, 6.), 'v2_gated':rec_row(5, 3.), 'bank_wide_lines_gated':rec_row(4, 5.),
                   'cap1_gated':rec_row(cap_boosts, cap_tone)}
            syn = {m:syn_row() for m in rec}
            runs = [{'methods':{m:{'own_block_ms_p99':1.} for m in ('joint', 'bank_wide_lines', 'cap1')}}]
            return rec, syn, runs
        cand = [{'name':'cap1', 'options':{'cap_db':1.}}]
        rec, syn, runs = summaries(1, 5.)
        pick, table, _ = fs3.apply_development_rule(rec, syn, runs, [], cand)
        self.assertEqual(pick, 'cap1')
        self.assertEqual(table[0]['tone_bin_needed_db'], 4.5)              # v2 + half of the joint check's lead
        rec, syn, runs = summaries(2, 5.)                                  # as many boosts as the joint check
        self.assertIsNone(fs3.apply_development_rule(rec, syn, runs, [], cand)[0])
        rec, syn, runs = summaries(1, 4.)                                  # fewer boosts, tone gain lost
        pick, table, _ = fs3.apply_development_rule(rec, syn, runs, [], cand)
        self.assertIsNone(pick)
        self.assertFalse(table[0]['checks']['d_tone_gain_kept'])

    def test_freeze_records_no_candidate_and_runs_once(self):
        with tempfile.TemporaryDirectory() as folder:
            dev = {'code_sha256':fs3._code_hashes(), 'development_pick':None, 'rule':fs3.DEVELOPMENT_RULE, 'rule_table':[],
                   'rule_reference':{}, 'comparators':fs3.COMPARATORS, 'candidates':fs3.CANDIDATES}
            Path(folder, 'development.json').write_text(json.dumps(dev), encoding='utf-8')
            out = Path(folder, 'protocol.json')
            p = fs3.freeze_protocol(folder, output=out)
            self.assertIsNone(p['frozen_candidate'])
            with self.assertRaises(ValueError):
                fs3.freeze_protocol(folder, output=out)
            out.unlink()
            Path(folder, 'development.json').write_text(json.dumps(dict(dev, development_pick='cap1')), encoding='utf-8')
            with self.assertRaises(ValueError):                            # a pick needs a written test stage first
                fs3.freeze_protocol(folder, output=out)
            Path(folder, 'development.json').write_text(json.dumps(dict(dev, code_sha256={})), encoding='utf-8')
            with self.assertRaises(ValueError):                            # code changed since development
                fs3.freeze_protocol(folder, output=out)

    def test_development_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'keep.txt').write_text('x')
            with self.assertRaises(ValueError):
                fs3.run_development(folder)

    def test_frozen_code_covers_study_02(self):
        self.assertEqual(fs3.FROZEN_CODE[:len(fs3.fs2.FROZEN_CODE)], fs3.fs2.FROZEN_CODE)
        self.assertIn('tone_cap.py', fs3.FROZEN_CODE)


if __name__ == '__main__':
    unittest.main()
