import unittest
import numpy as np
from anc_lab.selector_compatibility import fit_fixed,matched_ratios,ratio_summary


class CompatibilityChecks(unittest.TestCase):
    def test_prefix_oracle_recovers_coefficients_without_suffix_leakage(self):
        t=np.arange(2000)/2000;x=np.column_stack([np.cos(2*np.pi*107*t),np.sin(2*np.pi*107*t)])
        coef=np.array([-.6,.8]);y=-x@coef
        fit=fit_fixed(y,x,100,1000)
        np.testing.assert_allclose(fit['coefficients'],coef,atol=1e-12)
        y[1000:]=100.;x[1000:]=23.
        self.assertEqual(fit,fit_fixed(y,x,100,1000))
        self.assertFalse(fit_fixed(y,np.zeros_like(x),100,1000)['identifiable'])

    def test_ratio_known_phase_and_missing_matches(self):
        v={'frequency':np.array([[100.],[100.],[100.]]),'phasor':np.ones((3,1),complex)}
        b={'frequency':np.array([[100.],[100.],[130.]]),'phasor':np.array([[1.],[-1.],[1.]],complex)}
        a,counts=matched_ratios(v,b,np.ones(3,bool),np.ones(3,bool),np.array([3020,3040,3060]),np.zeros(3,int))
        np.testing.assert_allclose(a['ratio'],np.array([np.ones(20),-np.ones(20)]),atol=1e-12)
        self.assertEqual(counts['v2_without_bank_match'],1)
        s=ratio_summary(a,np.array([False,True]))
        self.assertAlmostEqual(s['idealized_retained_attenuation_db']['p50'],-20*np.log10(2))

    def test_ambiguous_associations_are_not_silently_counted(self):
        v={'frequency':np.array([[100.,102.]]),'phasor':np.ones((1,2),complex)}
        b={'frequency':np.array([[101.]]),'phasor':np.ones((1,1),complex)}
        a,c=matched_ratios(v,b,np.ones(1,bool),np.ones(1,bool),np.array([3020]),np.zeros(1,int))
        self.assertEqual(len(a['ratio']),0);self.assertEqual(c['ambiguous_matches'],2)

    def test_unique_components_sum_and_ramp_is_explicit(self):
        v={'frequency':np.array([[100.],[100.]]),'phasor':np.ones((2,1),complex)}
        b={'frequency':np.array([[100.,100.],[100.,100.]]),'phasor':np.full((2,2),.5,complex)}
        a,c=matched_ratios(v,b,np.ones(2,bool),np.array([False,True]),np.array([3020,3040]),np.zeros(2,int))
        np.testing.assert_allclose(a['ratio'],1.,atol=1e-12)
        np.testing.assert_allclose(a['ramped_ratio'][0],np.arange(1,21)/20,atol=1e-12)


if __name__=='__main__':unittest.main()
