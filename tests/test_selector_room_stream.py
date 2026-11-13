"""Alignment/causal-decision tests for the live-convention offline bridge."""
import unittest
import numpy as np
from anc_lab.antihum import ToneSetting, replay as live_replay
from anc_lab.selector_room_stream import render, hard_reference, lead_group
from anc_lab.selector_headroom import causal_mix
from anc_lab.selector_stream_profile import MaturedMixer
from anc_lab.selection_study import FS, BLOCK, horizon_setup


class RoomStreamTests(unittest.TestCase):
    def test_future_samples_cannot_change_prefix_trace(self):
        from anc_lab.selector_room_stream import stream
        from anc_lab.selector_stream_profile import cached_dpss
        from anc_lab import selector_headroom as h
        from threadpoolctl import threadpool_limits
        p = h.read(h.ROOT/'results-selector-fresh-01/protocol.json')
        rng = np.random.default_rng(221)
        t = np.arange(5*FS)/FS
        x = .01*np.cos(2*np.pi*137.4*t)+rng.normal(0, .001, len(t))
        y = x.copy()
        y[6400:] = rng.normal(0, .1, len(y)-6400)
        with threadpool_limits(limits=1), cached_dpss(True):
            first = stream(x, p)
            second = stream(y, p)
        for key in ('weights', 'selected', 'dc', 'gated_reference'):
            np.testing.assert_array_equal(first[key][:320], second[key][:320])

    def test_render_live_origin_gate_and_offsets_at_exact_room_leads(self):
        # Known phasors at seen-1, with an origin at a non-integral cycle.
        seen = np.array([20, 40, 60])
        freq = 299.3
        ph = np.exp(2j*np.pi*freq*(seen-1)/FS+.4j)
        a = {'seen': seen, 'frequency': np.full((3, 1), freq), 'phasor': ph[:, None],
             'gate': np.array([False, True, True])}
        trace = {'v2': a, 'bank': [a, a], 'dc': np.full(3, .2),
                 'weights': np.tile([.4, .6, 0.], (3, 2, BLOCK, 1))}
        settings = [ToneSetting(freq, .7, 23., offset_hz=.25, offset_origin_s=.03)]
        for lead in (.03, .2):
            expected = live_replay(a, settings, lead)
            np.testing.assert_allclose(render(trace, settings, lead), expected, atol=1e-14)
            np.testing.assert_array_equal(render(trace, settings, lead, 'v2'), expected)
            v2, chooser = hard_reference(trace, lead)
            time = ((seen-1)[:, None]+round(lead*FS)+np.arange(BLOCK))/FS
            truth = (np.cos(2*np.pi*freq*time+.4)+.2)*a['gate'][:, None]
            np.testing.assert_allclose(v2, truth, atol=1e-12)
            np.testing.assert_allclose(chooser, v2-.6*.2*a['gate'][:, None], atol=1e-12)
        with self.assertRaises(ValueError):
            lead_group(.02)

    def test_mixer_matches_original_rule_on_live_sample_grid(self):
        rng = np.random.default_rng(220)
        x = rng.normal(size=10*FS)
        origins = np.arange(999, len(x)-300, BLOCK)
        for _, hz in horizon_setup()[2]:
            target = x[origins[:, None]+hz]
            arms = np.stack([target*.55, target*.95, np.zeros_like(target)])
            arms[1, 500:] *= -3
            expected, details = causal_mix(target, arms, origins, int(hz[-1]), 2.)
            mixer = MaturedMixer(hz)
            actual, choices = [], []
            for i, origin in enumerate(origins):
                actual.append(mixer.step(x[max(0, origin-2400):origin+1], origin, arms[:, i]))
                choices.append(mixer.selected)
            np.testing.assert_allclose(actual, expected, atol=1e-10, rtol=1e-10)
            np.testing.assert_array_equal(choices, details['selected'])
            self.assertGreater(mixer.switches, 1)


if __name__ == '__main__':
    unittest.main()
