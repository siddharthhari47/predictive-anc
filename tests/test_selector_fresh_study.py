"""Fresh-study aggregation, qualification and parity; no new media involved."""
import unittest
import numpy as np
from anc_lab import selector_fresh_study as f


def source(index, difference=0., tonal=True, baseline=4.):
    rows=[]
    for method in f.METHODS:
        for horizon in (20,120):
            rows.append({'method':method,'horizon_start_ms':horizon,
                'tone_band_gain_db':baseline+(difference if method=='causal_L2' else 0.),
                'band_gain_db':0.,'third_octave_boosts_over_1db':0})
    return {'id':str(index),'title':str(index),'status':'scored',
            'reference_tones_hz':[100.] if tonal else [],'scores':rows}


class FreshStudyTests(unittest.TestCase):
    def test_zero_median_can_have_positive_mean_and_interval(self):
        x=[0.]*20+[2.]*10
        r=f.paired_summary(x,resamples=5000)
        self.assertEqual(r['median_db'],0.)
        self.assertAlmostEqual(r['mean_db'],2/3)
        self.assertGreater(r['mean_bootstrap95'][0],0)
        self.assertEqual(r['practical']['ties'],20)

    def test_tolerances_do_not_hide_small_changes(self):
        r=f.paired_summary([0.,.001,-.003,.1,-1.61],resamples=200)
        self.assertEqual(r['numerical']['wins'],2)
        self.assertEqual(r['numerical']['losses'],2)
        self.assertEqual(r['practical']['wins'],1)
        self.assertEqual(r['practical']['losses'],1)

    def test_nonfinite_data_rejected(self):
        with self.assertRaises(ValueError):f.paired_summary([1.,np.nan])

    def test_minimum_count_is_inconclusive_even_with_large_gain(self):
        r=f.evaluate([source(i,5.) for i in range(29)],resamples=100)
        self.assertEqual(r['decision'],'inconclusive_insufficient_eligible_sources')
        r=f.evaluate([source(i,5.,tonal=i<19) for i in range(30)],resamples=100)
        self.assertEqual(r['decision'],'inconclusive_insufficient_eligible_sources')

    def test_strong_loss_vetoes_positive_mean(self):
        c=[source(i,2.) for i in range(30)];c[0]=source(0,-1.1)
        r=f.evaluate(c,resamples=100)
        self.assertTrue(r['criteria']['mean_paired_20ms_ci_lower_above_zero'])
        self.assertFalse(r['criteria']['no_strong_20ms_loss_over_1db'])
        self.assertEqual(r['decision'],'fail_frozen_offline_criteria')

    def test_no_tone_files_and_both_horizons_enter_amplification(self):
        c=[source(i,1.,tonal=i<20) for i in range(30)]
        row=f.score(c[-1],'causal_L2',120)
        row['band_gain_db']=-.6;row['third_octave_boosts_over_1db']=1
        r=f.evaluate(c,resamples=100)
        self.assertFalse(r['criteria']['no_more_band_boost_cases_both_horizons'])
        self.assertFalse(r['criteria']['no_whole_band_boost_cases_both_horizons'])

    def test_duration_is_actual_target_block_duration(self):
        _,_,keep=f.grid_for_length(50*f.FS)
        self.assertLess(keep.sum()*f.BLOCK/f.FS,30)
        _,_,keep=f.grid_for_length(51*f.FS)
        self.assertGreaterEqual(keep.sum()*f.BLOCK/f.FS,30)

    def test_replay_matches_saved_causal_scores_on_seen_sources(self):
        old=f.h.read(f.ROOT/'results-selector-headroom-01/audit/results.json')
        files={'Mobile_lift_stage.ogg','Wiki_Motor_lancha.wav','Microwave_hum.ogg'}
        picked=[c for c in old['cases'] if c.get('file') in files and not c.get('skipped')]
        self.assertGreaterEqual(len(picked),2)
        for case in picked:
            path=f.ROOT/case['local_arrays']
            self.assertEqual(f.h.sha(path),case['arrays_sha256'])
            with np.load(path) as a:
                preds={m:a[m] for m in f.METHODS if m!='causal_L2'}
                rows,_,_,_=f.score_existing(a['reference'],a['origins'],a['keep'],preds,case['reference_tones_hz'])
            for row in rows:
                expected=f.score(case,row['method'],row['horizon_start_ms'])
                for field in ('tone_band_gain_db','band_gain_db','third_octave_change_db'):
                    np.testing.assert_allclose(row[field],expected[field],rtol=1e-10,atol=1e-10)


if __name__=='__main__':unittest.main()
