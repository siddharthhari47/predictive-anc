"""How predictable are real hums recorded by other people? (frozen settings, no tuning)

Inputs: freely licensed recordings downloaded from Wikimedia Commons with the
user's approval (see the folder's SOURCES.json). They come from unknown
microphones, rooms and editing chains and were lossy-compressed in most cases,
so they test the detector and forecaster on real sources nobody here chose,
not on the user's room.

Nothing is tuned here. v1 and v2 are the frozen settings from
results-release-study-01/release_protocol.json, applied unchanged. The only
per-file fitting is what each method already does causally: the fixed top-3
tracker and the ridge AR are fitted on each file's first 40% (the "prefix"),
normalization uses that prefix, and every method is scored on the remaining
60%. This is reference-signal prediction only: no acoustic path, no playback,
no ear measurement.
"""
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import csv
import hashlib
import json
from math import gcd
import os
from pathlib import Path
import time

import numpy as np
from scipy import signal
from threadpoolctl import threadpool_limits

from .assessment import forecast_scores
from .predictors import DirectPredictor, ToneTracker, estimate_tones
from .release_study import V1, gate_output
from .selection_study import BLOCK, FS, HORIZONS_MS, horizon_setup
from .tone_selection import SelectedToneForecaster, ToneSelector

PREFIX_FRACTION = .4
MAX_SECONDS = 180.
WORKERS = max(1, min(19, (os.cpu_count() or 2)-2))
PROTOCOL = Path(__file__).resolve().parents[1]/'results-release-study-01'/'release_protocol.json'
# Files whose hum is electrical (a pickup on an amplifier input), not sound in air.
ELECTRICAL = {'MainsBrum50Hz.ogg', 'Mains_hum_60_Hz.ogg'}


def causal_resample(raw, rate, fs):
    """Same causal Kaiser FIR as assessment.load_reference; returns (x, group delay in s)."""
    divisor = gcd(int(rate), fs)
    up, down = fs//divisor, int(rate)//divisor
    if up == down == 1:
        return raw.copy(), 0.
    factor = max(up, down)
    taps = signal.firwin(20*factor+1, 1/factor, window=('kaiser', 5.))*up
    return signal.upfirdn(taps, raw, up=up, down=down), 10*factor/(rate*up)


def ogg_audio_only(data):
    """Drop Ogg Skeleton pages ('fishead'/'fisbone') so libsndfile can decode the audio stream.

    Pages are copied byte for byte; each page carries its own CRC and per-stream
    sequence number, so removing one logical stream leaves the others valid.
    """
    pages, skeleton, i = [], set(), 0
    while i < len(data):
        if data[i:i+4] != b'OggS':
            raise ValueError('Not a well-formed Ogg file')
        segments = data[i+26]
        body = i+27+segments
        end = body+sum(data[i+27:body])
        serial = data[i+14:i+18]
        if data[i+5] & 2 and data[body:body+7] == b'fishead':
            skeleton.add(serial)
        pages.append((serial, data[i:end]))
        i = end
    return b''.join(page for serial, page in pages if serial not in skeleton), len(skeleton) > 0


def load_any(path, fs=FS, max_seconds=MAX_SECONDS):
    """Decode WAV/OGG/MP3, keep channel 0 only (reported, never averaged), resample causally."""
    import io
    import soundfile
    data, stripped = Path(path).read_bytes(), False
    if data[:4] == b'OggS':
        data, stripped = ogg_audio_only(data)
    raw, rate = soundfile.read(io.BytesIO(data), dtype='float64', always_2d=True)
    channels = raw.shape[1]
    stereo_correlation = float(np.corrcoef(raw[:, 0], raw[:, 1])[0, 1]) if channels > 1 and np.std(raw[:, 1]) > 0 else None
    raw = raw[:round(max_seconds*rate), 0]
    if not np.all(np.isfinite(raw)):
        raise ValueError(f'{path.name}: non-finite samples')
    x, delay = causal_resample(raw, rate, fs)
    x = x[:int(len(raw)*fs/rate)]
    info = {'sample_rate':int(rate), 'channels':channels, 'channel_used':0, 'ogg_skeleton_removed':stripped,
            'stereo_channel_correlation':stereo_correlation, 'decoded_seconds':len(raw)/rate,
            'peak_digital':float(np.max(np.abs(raw))), 'rms_digital':float(np.sqrt(np.mean(raw**2))),
            'near_full_scale_fraction':float(np.mean(np.abs(raw) >= .999)), 'resampling_group_delay_seconds':delay}
    return x, info


def spectrum(x, fs=FS):
    """Welch power spectrum with 0.25 Hz bins (coarser only when the segment is shorter than 4 s)."""
    return signal.welch(x, fs, nperseg=min(len(x), 4*fs))


def prominent_tones(x, fs=FS, band=(35., 350.), prominence_db=10., limit=6):
    """Non-causal reference analysis of a segment: spectral peaks at least `prominence_db`
    above the median of the surrounding +-10 Hz. Independent of every forecaster."""
    f, p = spectrum(x, fs)
    df = f[1]-f[0]
    level = 10*np.log10(np.maximum(p, 1e-30))
    half = max(1, round(10/df))
    local = np.array([np.median(level[max(0, i-half):i+half+1]) for i in range(len(level))])
    peaks, _ = signal.find_peaks(level)
    keep = [i for i in peaks if band[0] <= f[i] <= band[1] and level[i]-local[i] >= prominence_db]
    keep = sorted(keep, key=lambda i: -p[i])
    chosen = []
    for i in keep:
        if all(abs(f[i]-c) > 3. for c in chosen):
            chosen.append(float(f[i]))
        if len(chosen) == limit:
            break
    return sorted(chosen)


def near_mask(f, frequencies, halfwidth=1.5):
    near = np.zeros(len(f), bool)
    for tone in frequencies:
        near |= np.abs(f-tone) <= halfwidth
    return near


def tonal_fraction(x, frequencies, fs=FS, band=(35., 350.), halfwidth=1.5):
    """Share of band power within +-halfwidth Hz of the given tones.

    -10*log10(1 - fraction) is the most any tone-only canceller could remove from
    this band, if it cancelled those tones perfectly and touched nothing else.
    """
    f, p = spectrum(x, fs)
    inband = (f >= band[0]) & (f <= band[1])
    total = float(p[inband].sum())
    return float(p[inband & near_mask(f, frequencies, halfwidth)].sum())/total if total > 0 else 0.


def tone_band_gain(target, forecast, frequencies, fs=FS, halfwidth=1.5):
    """Prediction gain measured only within +-halfwidth Hz of the given tones (dB).

    Rows of target/forecast tile the timeline (origins every BLOCK, BLOCK horizons),
    so the flattened arrays are continuous waveforms.
    """
    if not frequencies:
        return None
    a, e = np.ravel(target), np.ravel(target-forecast)
    f, pa = spectrum(a, fs)
    _, pe = spectrum(e, fs)
    near = near_mask(f, frequencies, halfwidth)
    return float(10*np.log10(max(pa[near].sum(), 1e-30)/max(pe[near].sum(), 1e-30)))


def _file_task(args):
    path, v2 = args
    path = Path(path)
    with threadpool_limits(limits=1):
        try:
            audio, info = load_any(path)
        except Exception as error:      # decoder limits are reported, never hidden
            return {'file':path.name, 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                    'skipped':f'{type(error).__name__}: {str(error).split(": ")[-1]}'}
        prefix = int(PREFIX_FRACTION*len(audio))
        mean, scale = float(np.mean(audio[:prefix])), max(float(np.std(audio[:prefix])), 1e-12)
        x = (audio-mean)/scale
        _, horizons, groups = horizon_setup()
        grid = np.arange(BLOCK*50, len(x)-int(max(horizons)), BLOCK)
        test_rows = grid >= prefix
        outputs, detect, timing = {}, {}, {}
        for label, cfg in (('v1', V1), ('v2', v2)):
            selector = ToneSelector(FS, **cfg['selector'])
            fc = SelectedToneForecaster(FS, selector, **cfg['forecaster'])
            shadow = fc.predict(x, grid, horizons)
            out, enabled = gate_output(x, grid, shadow, groups, cfg['gate'])
            outputs[f'auto_{label}_ungated'], outputs[f'auto_{label}_gated'] = shadow, out
            test_decisions = [a for t, a in fc.decisions if t >= prefix]
            counts = [len(a) for a in test_decisions]
            hist = {}
            for a in test_decisions:
                for f, _ in a:
                    hist[round(f)] = hist.get(round(f), 0)+1
            common = sorted(hist.items(), key=lambda kv: -kv[1])
            detect[label] = {'mean_active_tones_test':float(np.mean(counts)) if counts else 0.,
                             'fraction_updates_with_any_tone_test':float(np.mean([c > 0 for c in counts])) if counts else 0.,
                             'most_frequent_active_hz':[{'hz':int(k), 'fraction_of_updates':v/max(len(counts), 1)} for k, v in common[:6]],
                             'gate_enabled_fraction_test':[float(np.mean(enabled[test_rows, g])) for g in range(len(groups))],
                             'fast_drops':fc.fast_drops}
            timing[label] = {'selector_update_ms_mean':1e3*float(np.mean(selector.update_seconds_measured)),
                             'forecast_ms_per_origin':1e3*fc.predict_seconds_per_origin}
        fixed = estimate_tones(x[:prefix], FS)
        models = {'fixed_top3_tracker':ToneTracker(FS, fixed),
                  'adapted_ridge_ar':DirectPredictor('ridge_ar', horizons, seed=7).fit(x, prefix)}
        origins = grid[test_rows]
        preds = {'zero':np.zeros((len(origins), len(horizons)))}
        preds.update({m:p[test_rows] for m, p in outputs.items()})
        preds.update({m:model.predict(x, origins, horizons) for m, model in models.items()})
        reference_tones = prominent_tones(x[prefix:])
        scores = []
        for (cols, hz), ms in zip(groups, HORIZONS_MS):
            target = x[origins[:, None]+hz]
            for m, p in preds.items():
                s = forecast_scores(target, p[:, cols], FS)
                scores.append({'method':m, 'horizon_start_ms':ms, 'band_gain_db':s['band_prediction_gain_db'],
                               'tone_band_gain_db':tone_band_gain(target, p[:, cols], reference_tones),
                               'band_nrmse':s['band_nrmse'], 'band_power_fraction':s['band_power_fraction']})
        steady = [d['hz'] for d in detect['v2']['most_frequent_active_hz'] if d['fraction_of_updates'] >= .5]
        fraction = tonal_fraction(x[prefix:], reference_tones)
        return {'file':path.name, 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'electrical_not_acoustic':path.name in ELECTRICAL, 'audio':info,
                'analysed_seconds':len(x)/FS, 'prefix_seconds':prefix/FS, 'test_seconds':(len(x)-prefix)/FS,
                'normalization':{'mean':mean, 'scale':scale, 'fit_on':'prefix only'},
                'fixed_top3_hz':[float(v) for v in fixed], 'detection':detect, 'timing':timing,
                'v2_steady_tones_hz':steady, 'reference_tones_hz':reference_tones,
                'reference_tone_band_power_fraction':fraction,
                'tone_only_ceiling_db':float(-10*np.log10(max(1-fraction, 1e-6))), 'scores':scores}


def run_real_hum_study(audio_folder, output, protocol_path=PROTOCOL):
    output, audio_folder = Path(output), Path(audio_folder)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output folder must be new or empty; earlier results are preserved.')
    sources = json.loads((audio_folder/'SOURCES.json').read_text(encoding='utf-8'))
    protocol = json.loads(Path(protocol_path).read_text(encoding='utf-8'))
    v2 = protocol['v2']
    files = [audio_folder/r['local_file'] for r in sources['files']]
    missing = [f.name for f in files if not f.exists()]
    if missing:
        raise FileNotFoundError(f'Missing downloaded files: {missing}')
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with ProcessPoolExecutor(WORKERS) as pool:
        results = list(pool.map(_file_task, [(str(f), v2) for f in files]))
    by_file = {r['local_file']:r for r in sources['files']}
    skipped = [r for r in results if 'skipped' in r]
    results = [r for r in results if 'skipped' not in r]
    for r in results+skipped:
        src = by_file[r['file']]
        r['source'] = {k:src[k] for k in ('commons_title', 'source_page', 'licence', 'author')}
    result = {'kind':'real_hum_predictability', 'created_utc':datetime.now(timezone.utc).isoformat(),
              'settings_source':str(Path(protocol_path).name), 'v1':V1, 'v2':v2,
              'split':f'normalize and fit prefix-trained comparators on the first {PREFIX_FRACTION:.0%}; score the remaining {1-PREFIX_FRACTION:.0%}',
              'max_seconds_per_file':MAX_SECONDS, 'files':results, 'skipped_files':skipped, 'runtime_seconds':time.perf_counter()-started,
              'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'labels':'Reference-signal prediction on independent real recordings. Not acoustic attenuation.'}
    (output/'real_hums.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    with open(output/'metrics.csv', 'w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['file', 'method', 'horizon_start_ms', 'test_band_gain_db', 'electrical_not_acoustic'])
        for r in results:
            for s in r['scores']:
                writer.writerow([r['file'], s['method'], s['horizon_start_ms'], s['band_gain_db'], r['electrical_not_acoustic']])
    from .real_hum_report import write_real_hum_report
    write_real_hum_report(output, result)
    return result
