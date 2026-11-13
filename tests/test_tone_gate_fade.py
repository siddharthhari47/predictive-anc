"""Checks for study 04: the faded realized-error gate, the band check that judges the gated output, and the study's
development plumbing."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from anc_lab import forecaster_study as s1
from anc_lab import forecaster_study_04 as fs4
from anc_lab.release_study import gate_output, in_parity
from anc_lab.selection_study import BLOCK as STUDY_BLOCK, apply_gate, horizon_setup
from anc_lab.tone_floors import JointCheckBank
from anc_lab.tone_forecasters import stream_forecasts
from anc_lab.tone_gate_fade import BlockFade, GatedCheckBank, apply_fade, fade_gains, fade_gate_output
from anc_lab.tone_selection import realized_gate

from test_tone_floors import BOTH, make
from test_tone_forecaster import BLOCK, FS, scene

V2_GATE = {'min_gain_db':-1., 'lookback':5, 'min_matured':3, 'shared_group':0}


def switching(seed=0, rows=300):
    """Gate decisions that switch often, per origin and group."""
    rng = np.random.default_rng(seed)
    return np.repeat(rng.random((rows//6, 2)) > .4, 6, axis=0)


def forecast_with_bad_stretches(seconds=10, seed=0):
    """A scene, the study grid on it and a forecast that is good except in some stretches, so the gate switches."""
    x = scene(seconds=seconds, tones=((83.3, .5), (171.7, .3)), noise=.1, seed=seed)
    _, horizons, groups = horizon_setup()
    grid = np.arange(STUDY_BLOCK*50, len(x)-int(max(horizons)), STUDY_BLOCK)
    rng = np.random.default_rng(seed+1)
    shadow = .9*x[grid[:, None]+horizons]
    bad = (np.arange(len(grid))//40) % 3 == 1
    shadow[bad] += 2.*rng.standard_normal((int(bad.sum()), len(horizons)))
    return x, grid, shadow, groups


class FadeTests(unittest.TestCase):
    def test_one_block_step_fade_is_the_v2_gate(self):
        x, grid, shadow, groups = forecast_with_bad_stretches()
        hard, enabled = gate_output(x, grid, shadow, groups, V2_GATE)
        self.assertTrue(enabled.any() and not enabled.all())
        out, gains, same = fade_gate_output(x, grid, shadow, groups, V2_GATE, {'in_blocks':1, 'out_blocks':1, 'shape':'step'})
        np.testing.assert_array_equal(same, enabled)
        np.testing.assert_array_equal(out, hard)
        out, gains, _ = fade_gate_output(x, grid, shadow, groups, V2_GATE, None)
        np.testing.assert_array_equal(out, hard)
        np.testing.assert_array_equal(gains, enabled.astype(float))

    def test_gains_slew_between_zero_and_one(self):
        enabled = switching()
        g = fade_gains(enabled, 8, 3)
        self.assertTrue(((g >= 0) & (g <= 1)).all())
        step = np.diff(np.vstack([np.zeros((1, 2)), g]), axis=0)
        self.assertLessEqual(step.max(), 1/8+1e-12)
        self.assertGreaterEqual(step.min(), -1/3-1e-12)
        on = np.ones((12, 1), bool)
        np.testing.assert_allclose(fade_gains(on, 8, 3)[:, 0], np.minimum(np.arange(1, 13)/8, 1.))

    def test_faded_output_has_no_steps(self):
        enabled = switching()
        _, _, groups = horizon_setup()
        ones = np.ones((len(enabled), len(BOTH)))
        hard = apply_gate(ones, enabled, groups)[:, groups[0][0]].ravel()
        soft = apply_fade(ones, fade_gains(enabled, 8, 8), groups, 'cosine')[:, groups[0][0]].ravel()
        self.assertEqual(np.abs(np.diff(hard)).max(), 1.)
        # sin^2(pi g / 2) has slope at most pi/2, and g moves 1/8 per 20-sample block.
        self.assertLessEqual(np.abs(np.diff(np.r_[0., soft])).max(), np.pi/2/(8*STUDY_BLOCK)+1e-12)

    def test_block_fade_matches_the_offline_fade(self):
        enabled = switching(3)
        _, _, groups = horizon_setup()
        ones = np.ones((len(enabled), len(BOTH)))
        offline = apply_fade(ones, fade_gains(enabled, 8, 3), groups, 'cosine')
        for g, (columns, _) in enumerate(groups):
            f = BlockFade(len(columns), 8, 3, 'cosine')
            online = np.array([f.step(bool(e)) for e in enabled[:, g]])
            np.testing.assert_allclose(online, offline[:, columns], rtol=0, atol=1e-12)

    def test_fade_timing_has_one_entry_per_origin(self):
        enabled = switching()
        _, _, groups = horizon_setup()
        t = fs4.fade_block_seconds(enabled, fs4.FADE8, groups)
        self.assertEqual(t.shape, (len(enabled),))
        self.assertTrue((t > 0).all())
        self.assertFalse(fs4.fade_block_seconds(enabled, None, groups).any())


class GatedCheckTests(unittest.TestCase):
    def test_a_gate_that_never_shuts_gives_the_joint_check(self):
        x = scene(seconds=10, tones=((83.3, .5), (171.7, .3), (233.9, .2)), noise=.6)
        grid = np.arange(999, len(x)-int(BOTH[-1]), BLOCK)
        a = stream_forecasts(make(JointCheckBank), x, grid, BOTH)
        fc = make(GatedCheckBank, gate={'min_gain_db':-np.inf, 'lookback':5, 'min_matured':0, 'shared_group':0})
        b = stream_forecasts(fc, x, grid, BOTH)
        np.testing.assert_array_equal(a, b)
        self.assertGreater(sum(fc.counters['band_checks']), 0)

    def test_internal_gate_is_the_realized_error_gate(self):
        """Each setting's internal gate decides exactly as realized_gate would on that setting's own forecast."""
        x = scene(seconds=9, tones=((83.3, .5), (171.7, .3), (233.9, .2)), noise=.6, seed=4)
        grid = np.arange(999, len(x)-int(BOTH[-1]), BLOCK)
        fc = make(GatedCheckBank, gate=V2_GATE)
        origins, outputs, opened = [], [], []
        gate_open, choose = fc._gate_open, fc._choose

        def record_gate(g):
            result = gate_open(g)
            if g == 0:
                opened.append(result.copy())
            return result

        def record_choice():
            choose()
            origins.append(fc.seen-1)
            outputs.append(fc.gqueue[0][-1][1].copy())
        fc._gate_open, fc._choose = record_gate, record_choice
        stream_forecasts(fc, x, grid, BOTH)
        origins, outputs, opened = np.array(origins), np.array(outputs), np.array(opened)
        group = horizon_setup()[2][0]
        rows = origins+group[1][-1] < len(x)
        switched = 0
        for s in range(outputs.shape[1]):
            forecast = np.zeros((int(rows.sum()), len(BOTH)))
            forecast[:, group[0]] = outputs[rows, s]
            expected = realized_gate(x, origins[rows], forecast, [group], V2_GATE['min_gain_db'], V2_GATE['lookback'],
                                     V2_GATE['min_matured'], 0)[:, 0]
            np.testing.assert_array_equal(opened[rows, s], expected)
            switched += int(np.sum(expected[1:] != expected[:-1]))
        self.assertGreater(switched, 0)

    def test_gated_check_is_block_causal(self):
        x = scene(seconds=8)
        changed = x.copy(); changed[9001:] = np.random.default_rng(9).standard_normal(len(x)-9001)
        grid = np.arange(999, len(x)-int(BOTH[-1]), BLOCK)
        for fade in (None, fs4.FADE8):
            a = stream_forecasts(make(GatedCheckBank, gate=V2_GATE, fade=fade), x, grid, BOTH)
            b = stream_forecasts(make(GatedCheckBank, gate=V2_GATE, fade=fade), changed, grid, BOTH)
            keep = grid <= 9000
            np.testing.assert_array_equal(a[keep], b[keep])

    def test_settings_report_the_gate(self):
        s = make(GatedCheckBank, gate=V2_GATE, fade=fs4.FADE8).settings()['joint_check']['judged_after_gate']
        self.assertEqual(s, {'gate':V2_GATE, 'fade':fs4.FADE8})


def rule_inputs(cand_boosts=18, cand_buzz=1, cand_tone=5.3, added_ms=.2, joint_buzz=7, no_gate_buzz=2):
    """Development summaries in the shape apply_development_rule reads: joint + gate 25 boosts, v2 + gate tones 3."""
    def rec_row(boosts, tone):
        return {'third_octave_boosts':[{}]*boosts, 'near_boosts':[{}]*boosts, 'whole_band_boosts':[],
                'median_tone_bin_both_horizons_db':tone, 'median_whole_band_both_horizons_db':1.5}
    rec = {'joint_gated':rec_row(25, 5.6), 'joint_ungated':rec_row(21, 5.5), 'v2_gated':rec_row(54, 3.),
           'bank_wide_lines_gated':rec_row(40, 5.), 'v2_fade8_gated':rec_row(48, 3.), 'c_gated':rec_row(cand_boosts, cand_tone)}
    syn = {m:{'late_third_octave_boosts':0, 'late_near_boosts':0, 'mean_objective_db':7., 'windows_below_minus_half_db':6}
           for m in rec}
    late = [{'method':m, 'max_third_octave_change_db':2.} for m, n in
            (('joint_gated', joint_buzz), ('joint_ungated', no_gate_buzz), ('c_gated', cand_buzz)) for _ in range(n)]
    p99 = {'joint':5., 'bank_wide_lines':4., 'c':5.+added_ms}
    runs = [{'methods':{m:{'own_block_ms_p99':v} for m, v in p99.items()}}]
    scenes = [dict(runs[0], family='buzz', late_window_scores=late)]
    return rec, syn, runs, scenes


class Study04Tests(unittest.TestCase):
    CAND = [{'name':'c', 'kind':'gated_check'}]

    def test_method_names_cover_the_candidates(self):
        names = fs4.method_names(fs4.COMPARATORS+fs4.CANDIDATES)
        for n in ('v2_gated', 'joint_gated', 'v2_fade8_gated', 'gcheck_ungated', 'gcheck_fade8_gated',
                  'joint_fade8in3out_gated', 'online_ar', 'prefix_ar'):
            self.assertIn(n, names)

    def test_make_bank_passes_the_output_gate_to_the_check(self):
        v2 = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
        every = {m['name']:m for m in fs4.CANDIDATES}
        bank = fs4.make_bank(every['gcheck_fade8'], v2)
        self.assertIsInstance(bank, GatedCheckBank)
        self.assertEqual((bank.gate, bank.fade), (v2['gate'], fs4.FADE8))
        self.assertIsNone(fs4.make_bank(every['gcheck'], v2).fade)
        self.assertNotIsInstance(fs4.make_bank(every['joint_fade8'], v2), GatedCheckBank)

    def test_run_methods_fades_only_the_output(self):
        v2 = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
        x = scene(seconds=12, tones=((83.3, .5), (171.7, .3), (233.9, .2)), noise=.6)
        _, horizons, _ = horizon_setup()
        grid = np.arange(STUDY_BLOCK*50, len(x)-int(max(horizons)), STUDY_BLOCK)
        keep = grid >= 4000
        every = {m['name']:m for m in fs4.COMPARATORS+fs4.CANDIDATES}
        preds, info = fs4.run_methods(x, grid, keep, [every['joint'], every['joint_fade8']], v2, 4000)
        np.testing.assert_array_equal(preds['joint_ungated'], preds['joint_fade8_ungated'])
        self.assertEqual(preds['joint_gated'].shape, (int(keep.sum()), len(horizons)))
        self.assertIsNone(info['joint']['fade'])
        self.assertEqual(info['joint']['fade_block_ms_max'], 0.)
        self.assertGreater(info['joint_fade8']['fade_block_ms_max'], 0.)
        self.assertGreaterEqual(info['joint_fade8']['own_block_ms_max'], info['joint_fade8']['fade_block_ms_max'])

    def test_rule(self):
        rec, syn, runs, scenes = rule_inputs()
        pick, table, reference = fs4.apply_development_rule(rec, syn, runs, scenes, self.CAND)
        self.assertEqual(pick, 'c')
        self.assertAlmostEqual(table[0]['tone_bin_needed_db'], 4.3)          # v2 + half of the joint check's lead
        self.assertAlmostEqual(table[0]['p99_added_ms'], .2)
        self.assertEqual(reference['joint + gate']['buzz_late_boosts'], 7)
        self.assertEqual(reference['joint, no gate']['buzz_late_boosts'], 2)
        for change, check in (({'cand_boosts':25}, 'a_fewer_boosts'), ({'cand_buzz':3}, 'b_gate_boosts_gone'),
                              ({'cand_tone':4.2}, 'e_tone_gain_kept'), ({'added_ms':1.5}, 'h_time')):
            pick, table, _ = fs4.apply_development_rule(*rule_inputs(**change), self.CAND)
            self.assertIsNone(pick, check)
            self.assertFalse(table[0]['checks'][check])
            self.assertEqual(sum(not ok for ok in table[0]['checks'].values()), 1, check)

    def test_rule_picks_fewest_boosts(self):
        rec, syn, runs, scenes = rule_inputs()
        rec['d_gated'] = dict(rec['c_gated'], third_octave_boosts=[{}]*17, median_tone_bin_both_horizons_db=5.)
        syn['d_gated'] = syn['c_gated']
        runs[0]['methods']['d'] = {'own_block_ms_p99':5.}
        pick, _, _ = fs4.apply_development_rule(rec, syn, runs, scenes, self.CAND+[{'name':'d', 'kind':'joint'}])
        self.assertEqual(pick, 'd')

    def test_fresh_list_must_be_new(self):
        good = {'file':'A_new_machine.ogg', 'title':'File:A new machine.ogg', 'sha1':'0'*40, 'bytes':1, 'seconds':30.,
                'author':'Someone Entirely New 4821', 'licence':'CC0', 'acoustic':True}
        self.assertEqual(fs4.check_fresh_list({'recordings':[good]}), [good])
        for bad in ({'file':'Pump.ogg'}, {'file':'Buzzing_Speakers.ogg'}, {'author':'ezwa'}):
            with self.assertRaises(ValueError):
                fs4.check_fresh_list({'recordings':[dict(good, **bad)]})
        with self.assertRaises(ValueError):
            fs4.check_fresh_list({'recordings':[{k:v for k, v in good.items() if k != 'sha1'}]})
        with self.assertRaises(ValueError):                                    # one author per recording
            fs4.check_fresh_list({'recordings':[good, dict(good, file='Another.ogg')]})

    def test_synthetic_test_draws_are_fresh_and_repeat(self):
        _, wander_dev, _ = s1.development_scenes()
        forbidden = fs4.development_frequencies_04(wander_dev)
        a = fs4.draw_synthetic_test(fs4.SYNTHETIC_TEST, forbidden)
        self.assertEqual(json.dumps(a), json.dumps(fs4.draw_synthetic_test(fs4.SYNTHETIC_TEST, forbidden)))
        standard, wander, buzz = a
        self.assertEqual((len(standard), len(wander), len(buzz)), (3, 3, 3))
        for g in buzz:
            self.assertEqual(g['harmonic'][1], round(2*g['harmonic'][0], 1))
            for f in g['steady']+g['wander']+g['am']+g['harmonic'][:1]:
                self.assertTrue(in_parity(f, 1))
            for f in [f for fs in g.values() for f in fs]:
                self.assertTrue(all(abs(f-b) > 2 for b in forbidden))

    def test_freeze_records_no_candidate_and_runs_once(self):
        with tempfile.TemporaryDirectory() as folder:
            dev = {'code_sha256':fs4._code_hashes(), 'development_pick':None, 'rule':fs4.DEVELOPMENT_RULE, 'rule_table':[],
                   'rule_reference':{}, 'comparators':fs4.COMPARATORS, 'candidates':fs4.CANDIDATES,
                   'v2':{}, 'wander_development_draws':[]}
            Path(folder, 'development.json').write_text(json.dumps(dev), encoding='utf-8')
            out = Path(folder, 'protocol.json')
            p = fs4.freeze_protocol(folder, output=out)
            self.assertIsNone(p['frozen_candidate'])
            self.assertIn('No candidate', p['decision'])
            with self.assertRaises(ValueError):
                fs4.freeze_protocol(folder, output=out)
            with self.assertRaises(ValueError):                                # nothing to test
                fs4.run_test(output=Path(folder, 'test'), protocol_path=out)
            self.assertFalse(Path(folder, 'test').exists())
            out.unlink()
            Path(folder, 'development.json').write_text(json.dumps(dict(dev, code_sha256={})), encoding='utf-8')
            with self.assertRaises(ValueError):                                # code changed since development
                fs4.freeze_protocol(folder, output=out)
            Path(folder, 'development.json').write_text(json.dumps(dict(dev, development_pick='gcheck')), encoding='utf-8')
            fresh = Path(folder, 'fresh.json')
            fresh.write_text(json.dumps({'recordings':[{'file':'Pump.ogg'}]}), encoding='utf-8')
            with self.assertRaises(ValueError):                                # a pick needs a fresh, new list
                fs4.freeze_protocol(folder, output=out, fresh_list=fresh)
            self.assertFalse(out.exists())

    def test_stages_refuse_to_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'keep.txt').write_text('x')
            with self.assertRaises(ValueError):
                fs4.run_development(folder)
            with self.assertRaises(ValueError):
                fs4.run_timing(folder)
            with self.assertRaises(ValueError):                                # the test folder exists
                fs4.run_test(output=folder)

    def test_frozen_code_covers_study_03(self):
        self.assertEqual(fs4.FROZEN_CODE[:len(fs4.fs3.FROZEN_CODE)], fs4.fs3.FROZEN_CODE)
        for name in ('tone_gate_fade.py', 'forecaster_study_04.py', 'forecaster_report_04.py'):
            self.assertIn(name, fs4.FROZEN_CODE)


if __name__ == '__main__':
    unittest.main()
