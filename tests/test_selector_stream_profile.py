"""Causality and numerical parity for the offline timing adapter."""
import unittest
import numpy as np
from scipy import signal
from anc_lab import selector_headroom as h
from anc_lab.selector_stream_profile import MaturedMixer,MaturedGate,cached_dpss
from anc_lab.selection_study import FS,BLOCK,horizon_setup


class StreamProfileTests(unittest.TestCase):
    def test_mixer_matches_batch_with_switches_and_maturity(self):
        rng=np.random.default_rng(51)
        x=rng.normal(size=9*FS)
        origins=np.arange(1000,len(x)-300,BLOCK)
        for _,hz in horizon_setup()[2]:
            target=x[origins[:,None]+hz]
            arms=np.stack([target*.6,target*.95,np.zeros_like(target)])
            arms[1,450:]*=-2
            expected,info=h.causal_mix(target,arms,origins,int(hz[-1]),2.)
            stream=MaturedMixer(hz);out=[];choices=[]
            for row,t in enumerate(origins):
                out.append(stream.step(x[max(0,t-2300):t+1],t,arms[:,row]))
                choices.append(stream.selected)
            np.testing.assert_allclose(out,expected,rtol=1e-10,atol=1e-10)
            np.testing.assert_array_equal(choices,info['selected'])
            self.assertGreater(stream.switches,0)
            self.assertLessEqual(len(stream.pending),14)
            self.assertLessEqual(len(stream.cumulative),201)

    def test_gate_matches_batch_with_matured_targets_only(self):
        rng=np.random.default_rng(53);x=rng.normal(size=5000)
        _,hz,groups=horizon_setup();grid=np.arange(1000,4700,BLOCK)
        target=x[grid[:,None]+hz]
        shadows=np.stack([.5*target,2.8*target]);config={'min_gain_db':-1.,'lookback':5,'min_matured':3,'shared_group':0}
        expected=[h.s2.gate_output(x,grid,s,groups,config)[0] for s in shadows]
        gate=MaturedGate(groups,config);out=[]
        for row,t in enumerate(grid):out.append(gate.step(x[:t+1],t,shadows[:,row])[0])
        np.testing.assert_array_equal(np.asarray(out).transpose(1,0,2),expected)

    def test_dpss_cache_restores_function_and_preserves_values(self):
        original=signal.windows.dpss;expected=original(64,4.,Kmax=7)
        with cached_dpss(True) as cache:
            a=signal.windows.dpss(64,4.,Kmax=7);b=signal.windows.dpss(64,4.,Kmax=7)
            self.assertIs(a,b);self.assertFalse(a.flags.writeable)
            np.testing.assert_array_equal(a,expected);self.assertEqual(len(cache),1)
        self.assertIs(signal.windows.dpss,original)


if __name__=='__main__':unittest.main()
