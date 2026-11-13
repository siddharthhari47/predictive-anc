"""Checks for study 02: the output rules in tone_floors (floors, the joint band check) and the study's frozen plumbing."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from anc_lab import forecaster_study as fsd
from anc_lab import forecaster_study_02 as fs2
from anc_lab.antihum import V2_SELECTOR
from anc_lab.tone_floors import FloorToneBank, JointCheckBank
from anc_lab.tone_forecasters import ProminentLines, ToneObserverBank, stream_forecasts
from anc_lab.tone_selection import ToneSelector

from test_tone_forecaster import BLOCK, FS, HORIZONS, gain_db, scene

BOTH = np.r_[np.arange(41, 61), np.arange(241, 261)]


def make(kind, lines=True, **options):
    return kind(FS, BLOCK, ToneSelector(FS, **V2_SELECTOR), nb_tau=0., candidates=ProminentLines() if lines else None, **options)


class ToneFloorTests(unittest.TestCase):
    def test_floor_bank_without_floors_is_the_plain_bank(self):
        x = scene(seconds=6, tones=((83.3, .5), (171.7, .3), (233.9, .2)))
        grid = np.arange(999, len(x)-int(HORIZONS[-1]), BLOCK)
        a = stream_forecasts(make(ToneObserverBank), x, grid, HORIZONS)
        b = stream_forecasts(make(FloorToneBank), x, grid, HORIZONS)
        np.testing.assert_array_equal(a, b)

    def test_floors_are_respected(self):
        x = scene(seconds=6, tones=((83.3, .5), (171.7, .3), (233.9, .2)), noise=.2)
        fc = make(FloorToneBank, min_tau_seconds=.1, min_tau_lines_seconds=.2)
        grid = np.arange(999, len(x)-int(HORIZONS[-1]), BLOCK)
        seen = []
        original = fc._choose

        def checked():
            original()
            floor = np.where(fc.from_selector, .1, .2)
            on = fc.output_choice >= 0
            seen.append(int(on.sum()))
            self.assertTrue(np.all(fc.taus[fc.output_choice[on]] >= floor[on]-1e-9))
        fc._choose = checked
        stream_forecasts(fc, x, grid, HORIZONS)
        self.assertGreater(sum(seen), 0)                                  # the floors did not just switch everything off

    def test_joint_bank_is_block_causal(self):
        x = scene(seconds=8)
        changed = x.copy(); changed[9001:] = np.random.default_rng(9).standard_normal(len(x)-9001)
        grid = np.arange(999, len(x)-int(BOTH[-1]), BLOCK)
        a = stream_forecasts(make(JointCheckBank), x, grid, BOTH)
        b = stream_forecasts(make(JointCheckBank), changed, grid, BOTH)
        keep = grid <= 9000
        np.testing.assert_array_equal(a[keep], b[keep])
        self.assertFalse(np.array_equal(a[~keep], b[~keep]))

    def test_joint_bank_tracks_steady_tones_and_stays_silent_on_noise(self):
        x = scene(seconds=10)
        grid = np.arange(999, len(x)-int(BOTH[-1]), BLOCK)
        fc = make(JointCheckBank)
        out = stream_forecasts(fc, x, grid, BOTH)
        late = grid >= 8*FS
        for cols in (slice(0, 20), slice(20, 40)):
            target = x[grid[late][:, None]+BOTH[cols]]
            self.assertGreater(gain_db(target, out[late][:, cols]), 10.)
        noise = np.random.default_rng(3).standard_normal(10*FS)
        quiet = stream_forecasts(make(JointCheckBank), noise, grid, BOTH)
        self.assertLess(np.mean(np.any(quiet != 0, axis=1)), .05)

    def test_joint_forecast_uses_the_nearest_horizon_group(self):
        fc = make(JointCheckBank)
        fc.group_components = [[(100., 1+0j)], [(61.3, 2+0j)]]
        out = fc.forecast([50, 250])
        np.testing.assert_allclose(out, [np.cos(2*np.pi*100*50/FS), 2*np.cos(2*np.pi*61.3*250/FS)], atol=1e-12)

    def test_joint_check_drops_output_that_boosts_every_band_and_moves_to_the_best(self):
        fc = make(JointCheckBank)
        noise = np.random.default_rng(4).standard_normal(fc.window)
        start = fc.active[0]
        fc.buffer[0][0] = noise
        fc.buffer[0][1:] = 2*noise                                       # every setting 6 dB louder in every band
        for _ in range(fc.min_decide):
            fc._band_check(0)
        self.assertEqual(fc.active[0], 0)                                 # no output
        fc = make(JointCheckBank)
        fc.buffer[0][0] = noise
        fc.buffer[0][1:] = .5*noise
        fc.buffer[0][4] = .25*noise                                       # setting 3 is clearly best
        for _ in range(fc.min_decide-1):
            fc._band_check(0)
            self.assertEqual(fc.active[0], start)                         # no decision before min_decide checks
        fc._band_check(0)
        self.assertEqual(fc.active[0], 4)

    def test_joint_settings_are_reported(self):
        s = make(JointCheckBank).settings()['joint_check']
        self.assertEqual(len(s['settings']), 10)
        self.assertEqual(s['start_setting'], (.1, False))
        self.assertEqual(s['window_seconds'], 4.)


class Study02Tests(unittest.TestCase):
    def test_fresh_recordings_are_new_files_by_new_authors(self):
        split = fsd.load_split()
        earlier = {e['file'] for e in split['development_files']+split['test_files']}
        fresh = {e['file'] for e in fs2.FRESH_RECORDINGS}
        self.assertFalse(fresh & earlier)
        authors = {e['author'].lower() for e in fs2.FRESH_RECORDINGS}
        self.assertFalse(authors & {a.lower() for a in fsd.RECORDING_GROUPS})
        self.assertEqual(len({e['sha1'] for e in fs2.FRESH_RECORDINGS}), len(fs2.FRESH_RECORDINGS))
        self.assertEqual([e['file'] for e in fs2.FRESH_RECORDINGS if not e['acoustic']], ['60-hz.wav'])

    def test_fresh_path_checks_size_and_sha1(self):
        with tempfile.TemporaryDirectory() as folder:
            data = b'not audio'
            entry = {'file':'a.wav', 'bytes':len(data), 'sha1':hashlib.sha1(data).hexdigest()}
            self.assertIsNone(fs2.fresh_path(entry, folder))              # absent: reported missing, not replaced
            Path(folder, 'a.wav').write_bytes(data)
            self.assertEqual(fs2.fresh_path(entry, folder), Path(folder, 'a.wav'))
            Path(folder, 'a.wav').write_bytes(b'not audio!')
            with self.assertRaises(ValueError):
                fs2.fresh_path(entry, folder)

    def test_synthetic_test_draws_avoid_development_frequencies(self):
        release = json.loads(fsd.RELEASE_PROTOCOL.read_text(encoding='utf-8'))
        _, wander, _ = fsd.development_scenes()
        forbidden = fs2.development_frequencies(release, wander)
        syn = dict(fs2.SYNTHETIC_TEST, forbidden_frequencies=forbidden)
        standard, wdraws = fs2.draw_synthetic_test(syn, forbidden)
        self.assertEqual((standard, wdraws), fs2.draw_synthetic_test(syn, forbidden))
        used = [f for g in standard for fs in g.values() for f in fs]+[f for g in wdraws for fs in g.values() for f in fs]
        self.assertTrue(all(abs(f-b) > 2 for f in used for b in forbidden))
        protocol = fs2.STUDY/'protocol.json'
        if protocol.exists():                                             # the frozen draws are these draws
            frozen = json.loads(protocol.read_text(encoding='utf-8'))['synthetic_test']
            self.assertEqual(json.loads(json.dumps([standard, wdraws])), [frozen['standard_draws'], frozen['wander_draws']])

    def test_method_names_cover_the_new_bank_kinds(self):
        names = fs2.method_names(fs2.COMPARATORS+fs2.CANDIDATES)
        for n in ('v2_gated', 'bank_wide_lines_gated', 'joint_ungated', 'joint_gated', 'floor_lines0.2_gated', 'online_ar'):
            self.assertIn(n, names)

    def test_stages_refuse_to_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'keep.txt').write_text('x')
            with self.assertRaises(ValueError):
                fs2.run_development(folder)
            with self.assertRaises(ValueError):
                fs2.freeze_protocol(folder, output=Path(folder, 'keep.txt'))
            with self.assertRaises(ValueError):
                fs2.run_test(output=folder)


if __name__ == '__main__':
    unittest.main()
