"""Matched input-only source characterization in absolute digital units.

This is an exploratory source screen, not prediction validation or ANC.
Tone locations are fixed using the discovery prefix before confirmation.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile


@dataclass(frozen=True)
class SourceConfig:
    seconds: int = 30
    discovery_seconds: int = 12
    window_seconds: int = 2
    low_hz: float = 35.
    high_hz: float = 350.
    tone_half_width_hz: float = 1.
    background_inner_hz: float = 3.
    background_outer_hz: float = 10.
    min_peak_separation_hz: float = 6.
    min_local_prominence_db: float = 6.
    min_on_off_increase_db: float = 6.
    min_confirmation_fraction: float = .8


def db_ratio(numerator, denominator):
    """Finite display floor only; quantities are power, not amplitude."""
    return 10*np.log10(np.maximum(numerator, 1e-30)/np.maximum(denominator, 1e-30))


def read_capture(path):
    """Preserve digital scale and require a matching local capture sidecar."""
    path = Path(path)
    metadata = json.loads(path.with_suffix('.capture.json').read_text(encoding='utf-8'))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if metadata.get('wav_sha256') != digest:
        raise ValueError(f'Capture hash does not match the WAV: {path.name}')
    fs, raw = wavfile.read(path)
    if raw.ndim != 1 or len(raw) == 0 or not np.all(np.isfinite(raw)):
        raise ValueError('Source study requires finite, nonempty, mono audio.')
    if metadata.get('provenance') != 'live_microphone':
        raise ValueError('Source study requires live_microphone capture provenance.')
    if (metadata.get('sample_rate') != fs or metadata.get('samples') != len(raw)
            or metadata.get('channels') != 1):
        raise ValueError('Capture metadata rate, length or channel count does not match the WAV.')
    if raw.dtype == np.uint8:
        audio = (raw.astype(float)-128)/128
    elif np.issubdtype(raw.dtype, np.signedinteger):
        audio = raw.astype(float)/(2.**(np.iinfo(raw.dtype).bits-1))
    elif np.issubdtype(raw.dtype, np.floating):
        audio = raw.astype(float)
    else:
        raise ValueError('Unsupported WAV encoding.')
    quality = {
        'filename': path.name, 'sha256': digest, 'sample_rate': fs, 'samples': len(audio),
        'duration_seconds': len(audio)/fs, 'peak_digital': float(np.max(np.abs(audio))),
        'rms_digital': float(np.sqrt(np.mean(audio**2))),
        'near_full_scale_fraction': float(np.mean(np.abs(audio) >= .999)),
        'device_name': metadata['device']['name'], 'host_api': metadata['host_api'],
        'reported_stream_rate': metadata.get('reported_stream_rate'),
        'reported_input_latency_seconds': metadata.get('reported_input_latency_seconds'),
        'callback_statuses': metadata.get('callback_statuses', []),
        'started_utc': metadata.get('started_utc'),
        'os_processing': metadata.get('os_processing', 'Unknown'),
        'playback': metadata.get('playback'),
    }
    return fs, audio, quality


def pair_quality(off, on):
    """Digital/provenance checks do not establish fixed physical gain."""
    reasons = []
    for key in ('device_name', 'host_api', 'sample_rate', 'reported_stream_rate', 'samples'):
        if off[key] != on[key]:
            reasons.append(f'Mismatched {key}.')
    for name, quality in (('off', off), ('on', on)):
        if quality['callback_statuses']:
            reasons.append(f'{name}: reported stream errors.')
        if quality['near_full_scale_fraction'] > 0:
            reasons.append(f'{name}: near-full-scale samples.')
        if quality['rms_digital'] <= 1e-8:
            reasons.append(f'{name}: near-silent input.')
        if quality['playback'] is not False:
            reasons.append(f'{name}: input-only provenance not confirmed.')
    return {'digital_checks_pass': not reasons, 'reasons': reasons,
            'fixed_effective_gain_verified': False, 'spl_calibrated': False,
            'note': 'Same named input and format; OS gain, AGC, beamforming and suppression are unverified. Device names are not hardware serial IDs.'}


def _window_psd(audio, fs, cfg):
    size = cfg.window_seconds*fs
    frames = np.asarray(audio, dtype=float).reshape(-1, size)
    freq, power = signal.periodogram(frames, fs=fs, window='hann', detrend='constant',
                                     scaling='density', axis=-1)
    return freq, power, np.sqrt(np.mean(frames**2, axis=1))


def _tone_measures(freq, psd, center, cfg):
    distance = np.abs(freq-center)
    tone = distance <= cfg.tone_half_width_hz
    background = ((distance >= cfg.background_inner_hz)
                  & (distance <= cfg.background_outer_hz))
    density = np.mean(psd[..., tone], axis=-1)
    floor = np.median(psd[..., background], axis=-1)
    return density, db_ratio(density, floor)


def analyze_arrays(off, on, fs, cfg=SourceConfig()):
    """Return a fixed-band source screen and plotting arrays; no RMS normalization."""
    if (fs < 2*cfg.high_hz or len(off) != cfg.seconds*fs or len(on) != len(off)
            or cfg.seconds % cfg.window_seconds or cfg.discovery_seconds % cfg.window_seconds
            or not 0 < cfg.discovery_seconds < cfg.seconds
            or not np.all(np.isfinite(off)) or not np.all(np.isfinite(on))):
        raise ValueError('Require matched finite 30-second arrays, suitable rate and whole analysis windows.')
    freq, off_psd, off_rms = _window_psd(off, fs, cfg)
    _, on_psd, on_rms = _window_psd(on, fs, cfg)
    cut = cfg.discovery_seconds//cfg.window_seconds
    discovery_off, discovery_on = off_psd[:cut].mean(axis=0), on_psd[:cut].mean(axis=0)
    band = (freq >= cfg.low_hz) & (freq <= cfg.high_hz)
    df = freq[1]-freq[0]

    # Select frequencies and discovery eligibility exclusively on the first 12 s.
    peaks, _ = signal.find_peaks(discovery_on,
                                distance=max(1, round(cfg.min_peak_separation_hz/df)))
    discovery = []
    for index in peaks:
        if not band[index]:
            continue
        center = float(freq[index])
        on_density, prominence = _tone_measures(freq, discovery_on, center, cfg)
        off_density, _ = _tone_measures(freq, discovery_off, center, cfg)
        contrast = float(db_ratio(on_density, off_density))
        discovery.append({
            'frequency_hz': center, 'band_hz': [center-cfg.tone_half_width_hz,
                                                center+cfg.tone_half_width_hz],
            'discovery_prominence_db': float(prominence), 'discovery_on_off_db': contrast,
            'discovery_eligible': bool(prominence >= cfg.min_local_prominence_db
                                       and contrast >= cfg.min_on_off_increase_db),
        })

    # Fixed bands now face a separate 18 s confirmation partition. Each on
    # window is compared with the *mean off confirmation* PSD; recordings are
    # not simultaneous and are never aligned, subtracted or treated as pairs.
    confirmation_off = off_psd[cut:].mean(axis=0)
    for row in discovery:
        center = row['frequency_hz']
        on_density, prominence = _tone_measures(freq, on_psd[cut:], center, cfg)
        off_density, _ = _tone_measures(freq, confirmation_off, center, cfg)
        contrast = db_ratio(on_density, off_density)
        passed = ((prominence >= cfg.min_local_prominence_db)
                  & (contrast >= cfg.min_on_off_increase_db))
        count = int(passed.sum())
        fraction = count/len(passed)
        row.update({
            'confirmation_on_off_db': float(db_ratio(on_density.mean(), off_density)),
            'confirmation_median_prominence_db': float(np.median(prominence)),
            'confirmation_windows_passing': count,
            'confirmation_windows_total': len(passed),
            'confirmation_fraction': fraction,
            'passes_spectral_screen': bool(row['discovery_eligible']
                                            and fraction >= cfg.min_confirmation_fraction),
        })
    discovery.sort(key=lambda row: row['frequency_hz'])
    summaries = {}
    for name, selection in [('discovery', slice(0, cut)), ('confirmation', slice(cut, None)),
                            ('whole_capture', slice(None))]:
        p_off = float(off_psd[selection, :][:, band].mean(axis=0).sum()*df)
        p_on = float(on_psd[selection, :][:, band].mean(axis=0).sum()*df)
        summaries[name] = {'off_band_power_digital': p_off, 'on_band_power_digital': p_on,
                           'on_off_band_power_db': float(db_ratio(p_on, p_off))}
    result = {'config': asdict(cfg), 'band_summaries': summaries, 'tones': discovery,
              'spectral_candidates_hz': [r['frequency_hz'] for r in discovery if r['passes_spectral_screen']],
              'full_recording_rms_ratio_db': float(db_ratio(np.mean(np.asarray(on)**2),
                                                            np.mean(np.asarray(off)**2))),
              'psd_method': 'Mean of nonoverlapping 2 s Hann periodograms, constant detrend, 0.5 Hz bins; density in digital FS^2/Hz.',
              'interpretation': 'A persistent spectral line is only a candidate for a fresh held-out prediction trial. It does not establish phase coherence, causality margin or physical ear attenuation.'}
    arrays = {'frequency_hz': freq, 'off_psd': off_psd, 'on_psd': on_psd,
              'off_window_rms': off_rms, 'on_window_rms': on_rms}
    return result, arrays


def run_study(off_path, on_path, output):
    output = Path(output)
    if (output/'source_study.json').exists():
        raise ValueError('Study result already exists; choose a new result directory.')
    cfg = SourceConfig()
    protocol_path = output/'protocol.json'
    protocol = json.loads(protocol_path.read_text(encoding='utf-8')) if protocol_path.exists() else None
    if protocol:
        expected = {'duration_each_seconds':cfg.seconds, 'selection_band_hz':[cfg.low_hz, cfg.high_hz],
                    'discovery_seconds':cfg.discovery_seconds,
                    'confirmation_seconds':cfg.seconds-cfg.discovery_seconds,
                    'welch_window_seconds':cfg.window_seconds,
                    'candidate_min_local_prominence_db':cfg.min_local_prominence_db,
                    'candidate_min_on_off_increase_db':cfg.min_on_off_increase_db,
                    'candidate_min_confirmation_fraction':cfg.min_confirmation_fraction}
        for key, value in expected.items():
            if protocol.get(key) != value:
                raise ValueError(f'Analysis disagrees with recorded protocol: {key}')
    fs, off, off_quality = read_capture(off_path)
    on_fs, on, on_quality = read_capture(on_path)
    if fs != on_fs:
        raise ValueError('Capture sample rates differ.')
    result, arrays = analyze_arrays(off, on, fs, cfg)
    result.update({'created_utc': datetime.now(timezone.utc).isoformat(),
                   'off': off_quality, 'on': on_quality,
                   'quality': pair_quality(off_quality, on_quality),
                   'analysis_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   'protocol_sha256': hashlib.sha256(protocol_path.read_bytes()).hexdigest() if protocol else None,
                   'protocol': protocol,
                   'no_playback': True, 'physical_anc_validated': False})
    output.mkdir(parents=True, exist_ok=True)
    with (output/'source_study.json').open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    # Spectral aggregates only: no raw microphone samples in this NPZ.
    np.savez_compressed(output/'spectra.npz', **arrays)
    return result
