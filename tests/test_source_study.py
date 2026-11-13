"""Source comparisons must preserve levels and reject misleading spectral peaks."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from scipy.io import wavfile

from anc_lab.source_study import analyze_arrays, pair_quality, read_capture


class SourceStudyTests(unittest.TestCase):
    def setUp(self):
        self.fs = 2000
        self.time = np.arange(30*self.fs)/self.fs
        self.rng = np.random.default_rng(17)
        self.off = .001*self.rng.standard_normal(len(self.time))

    def test_absolute_scale_survives_comparison(self):
        result, _ = analyze_arrays(self.off, 2*self.off, self.fs)
        self.assertAlmostEqual(result['full_recording_rms_ratio_db'], 20*np.log10(2), places=10)
        for partition in result['band_summaries'].values():
            self.assertAlmostEqual(partition['on_off_band_power_db'], 20*np.log10(2), places=10)

    def test_stable_new_tone_passes_but_shared_tone_does_not(self):
        tone = .02*np.sin(2*np.pi*73*self.time)
        result, _ = analyze_arrays(self.off, self.off+tone, self.fs)
        self.assertIn(73., result['spectral_candidates_hz'])
        shared, _ = analyze_arrays(self.off+tone, self.off+tone, self.fs)
        self.assertEqual(shared['spectral_candidates_hz'], [])

    def test_louder_broadband_noise_is_not_a_tone(self):
        on = .01*self.rng.standard_normal(len(self.time))
        result, _ = analyze_arrays(self.off, on, self.fs)
        self.assertGreater(result['band_summaries']['whole_capture']['on_off_band_power_db'], 18)
        self.assertEqual(result['spectral_candidates_hz'], [])

    def test_discovery_only_tone_fails_confirmation(self):
        on = self.off + .02*np.sin(2*np.pi*73*self.time)*(self.time < 12)
        result, _ = analyze_arrays(self.off, on, self.fs)
        row = next(r for r in result['tones'] if r['frequency_hz'] == 73.)
        self.assertTrue(row['discovery_eligible'])
        self.assertFalse(row['passes_spectral_screen'])

    def test_future_changes_cannot_change_discovery_or_eligibility(self):
        tone = .02*np.sin(2*np.pi*73*self.time)
        on = self.off + tone
        changed = on.copy()
        changed[self.time >= 12] = 100*self.rng.standard_normal(int(np.sum(self.time >= 12)))
        original, _ = analyze_arrays(self.off, on, self.fs)
        altered, _ = analyze_arrays(self.off, changed, self.fs)
        keys = ('frequency_hz', 'discovery_prominence_db', 'discovery_on_off_db', 'discovery_eligible')
        self.assertEqual([{k:r[k] for k in keys} for r in original['tones']],
                         [{k:r[k] for k in keys} for r in altered['tones']])

    def test_wav_reader_preserves_scale_and_rejects_tampered_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'capture.wav'
            raw = (.01*np.sin(2*np.pi*73*self.time)).astype(np.float32)
            wavfile.write(path, self.fs, raw)
            meta = {'wav_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                    'provenance':'live_microphone', 'sample_rate':self.fs,
                    'samples':len(raw), 'channels':1, 'device':{'name':'fixture'},
                    'host_api':'test', 'playback':False}
            path.with_suffix('.capture.json').write_text(json.dumps(meta), encoding='utf-8')
            fs, audio, _ = read_capture(path)
            self.assertEqual(fs, self.fs)
            np.testing.assert_array_equal(audio, raw)
            wavfile.write(path, self.fs, 2*raw)
            with self.assertRaisesRegex(ValueError, 'hash does not match'):
                read_capture(path)

    def test_same_device_does_not_prove_fixed_gain_and_mismatch_fails(self):
        quality = {'device_name':'A', 'host_api':'WASAPI', 'sample_rate':48000,
                   'reported_stream_rate':48000., 'samples':1440000,
                   'callback_statuses':[], 'near_full_scale_fraction':0.,
                   'rms_digital':.01, 'playback':False}
        matched = pair_quality(quality, quality)
        self.assertTrue(matched['digital_checks_pass'])
        self.assertFalse(matched['fixed_effective_gain_verified'])
        self.assertFalse(pair_quality(quality, {**quality, 'device_name':'B'})['digital_checks_pass'])


if __name__ == '__main__':
    unittest.main()
