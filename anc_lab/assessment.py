"""Goal 1: held-out reference-microphone forecasting, without simulated ear pressure."""
from dataclasses import asdict, dataclass
import hashlib
import json
from math import gcd
from pathlib import Path
import time

import numpy as np
from scipy import signal
from scipy.io import wavfile
from threadpoolctl import threadpool_limits

from .predictors import DirectPredictor, ToneTracker, estimate_tones


@dataclass
class AssessmentConfig:
    fs: int = 2000
    train_seconds: float = 12.
    validation_seconds: float = 6.
    test_seconds: float = 12.
    block: int = 20
    horizons_ms: tuple = (20., 120.)
    seed: int = 7
    required_band_gain_db: float = 6.


def load_reference(path, fs, seconds, train_seconds):
    """Causal resampling; original full-scale quality retained before normalization."""
    rate, raw = wavfile.read(path)
    if raw.ndim != 1:
        raise ValueError("Provide a mono reference WAV; do not silently average microphone channels.")
    if np.issubdtype(raw.dtype, np.integer):
        info = np.iinfo(raw.dtype)
        offset = (info.max+1)/2 if np.issubdtype(raw.dtype, np.unsignedinteger) else 0.
        scale = (info.max+1)/2 if offset else max(abs(info.min), info.max)
        raw = (raw.astype(float)-offset)/scale
    raw = np.asarray(raw, float)
    if len(raw)/rate < seconds:
        raise ValueError(f"Need {seconds:g} seconds without looping or padding the source.")
    raw = raw[:round(seconds*rate)]
    if not np.all(np.isfinite(raw)):
        raise ValueError("Non-finite input samples.")
    quality = {"sample_rate": int(rate), "duration_seconds": len(raw)/rate,
               "peak_digital": float(np.max(np.abs(raw))),
               "rms_digital": float(np.sqrt(np.mean(raw**2))),
               "near_full_scale_fraction": float(np.mean(np.abs(raw) >= .999))}
    divisor = gcd(int(rate), fs)
    up, down = fs//divisor, int(rate)//divisor
    if up == down == 1:
        x, group_delay = raw.copy(), 0.
    else:
        factor = max(up, down)
        taps = signal.firwin(20*factor+1, 1/factor, window=("kaiser", 5.))*up
        x = signal.upfirdn(taps, raw, up=up, down=down)
        group_delay = 10*factor/(rate*up)
    x = x[:round(seconds*fs)]
    train = round(train_seconds*fs)
    center = float(np.mean(x[:train]))
    scale = float(np.std(x[:train]))
    if scale < 1e-8:
        raise ValueError("Training reference is silent or effectively constant.")
    quality.update(normalization_mean=center, normalization_scale=scale,
                   resampling_group_delay_seconds=group_delay)
    return (x-center)/scale, quality


def forecast_scores(actual, forecast, fs, discard_seconds=.5):
    """Chronological waveform and band-error powers. This is not acoustic attenuation."""
    actual, forecast = np.asarray(actual).ravel(), np.asarray(forecast).ravel()
    if actual.shape != forecast.shape or len(actual) < fs:
        raise ValueError("Scoring requires aligned waveforms of at least one second.")
    error = actual-forecast
    sos = signal.butter(4, [35, 350], btype="bandpass", fs=fs, output="sos")
    desired_band = signal.sosfilt(sos, actual)
    error_band = signal.sosfilt(sos, error)
    start = round(discard_seconds*fs)
    desired_power = max(float(np.mean(actual[start:]**2)), 1e-30)
    mse = float(np.mean(error[start:]**2))
    band_power = max(float(np.mean(desired_band[start:]**2)), 1e-30)
    band_mse = float(np.mean(error_band[start:]**2))
    return {"nrmse": float(np.sqrt(mse/desired_power)), "mse": mse,
            "prediction_gain_db": float(10*np.log10(desired_power/max(mse, 1e-30))),
            "band_prediction_gain_db": float(10*np.log10(band_power/max(band_mse, 1e-30))),
            "band_nrmse": float(np.sqrt(band_mse/band_power)),
            "band_power_fraction": band_power/desired_power,
            "scored_samples": len(actual)-start}


def persistence_forecast(x, origins, horizons):
    return np.repeat(x[np.asarray(origins), None], len(horizons), axis=1)


def cycle_forecast(x, origins, horizons, period_samples):
    """Repeat the last observed cycle, wrapping long horizons into known history."""
    lag = np.mod(-np.asarray(horizons), period_samples)
    indices = np.asarray(origins)[:, None]-lag[None, :]
    if np.min(indices) < 0:
        raise ValueError("Not enough history for repeating-cycle baseline.")
    return x[indices]


def choose_method(validation_scores):
    """Selection is a pure function of validation results, never test scores."""
    return max(validation_scores, key=lambda method: validation_scores[method]["band_prediction_gain_db"])


def gate(scores, quality_ok, required_db=6.):
    return bool(quality_ok and scores["band_prediction_gain_db"] >= required_db and scores["nrmse"] <= 1.)


def assess(path, output, config=None):
    config = config or AssessmentConfig()
    path, output = Path(path), Path(output)
    if (output/"assessment.json").exists():
        raise ValueError("Assessment already exists; use a new output folder to preserve prior findings.")
    if min(config.train_seconds, config.validation_seconds, config.test_seconds) < 2:
        raise ValueError("Each partition needs at least two seconds.")
    seconds = config.train_seconds+config.validation_seconds+config.test_seconds
    x, quality = load_reference(path, config.fs, seconds, config.train_seconds)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    sidecar = path.with_suffix(".capture.json")
    metadata = json.loads(sidecar.read_text(encoding="utf-8")) if sidecar.exists() else {}
    authenticated_capture = metadata.get("provenance") == "live_microphone" and metadata.get("wav_sha256") == digest
    reasons = []
    if not authenticated_capture:
        reasons.append("No matching live-microphone capture sidecar; physical provenance is unverified.")
    if metadata.get("callback_statuses"):
        reasons.append("Capture reported audio-stream status errors.")
    if quality["near_full_scale_fraction"] > 0:
        reasons.append("Near-full-scale samples present; clipping margin not established.")
    if quality["rms_digital"] < 1e-8:
        reasons.append("Reference is effectively silent.")
    quality_ok = not reasons
    train_end = round(config.train_seconds*config.fs)
    validation_end = train_end+round(config.validation_seconds*config.fs)
    delays = [round(ms*config.fs/1000) for ms in config.horizons_ms]
    horizons = np.unique(np.concatenate([d+np.arange(1, config.block+1) for d in delays]))
    max_horizon = int(max(horizons))
    # Common origin ranges ensure every horizon stays inside its own partition.
    validation_origins = np.arange(train_end, validation_end-max_horizon, config.block)
    test_origins = np.arange(validation_end, len(x)-max_horizon, config.block)
    frequencies = estimate_tones(x[:train_end], config.fs)
    f, power = signal.periodogram(x[:train_end], fs=config.fs, nfft=8*train_end, window="hann")
    strongest = max(frequencies, key=lambda freq: power[np.argmin(abs(f-freq))])
    period = max(2, round(config.fs/strongest))
    models, model_info = {}, {}
    validation_predictions = {"zero": np.zeros((len(validation_origins), len(horizons))),
                              "persistence": persistence_forecast(x, validation_origins, horizons),
                              "repeat_cycle": cycle_forecast(x, validation_origins, horizons, period)}
    started = time.perf_counter()
    with threadpool_limits(limits=1):
        for method in ["tone_tracker", "ridge_ar", "mlp"]:
            print(f"Fitting and validating {method} on microphone reference", flush=True)
            if method == "tone_tracker":
                model = ToneTracker(config.fs, frequencies)
                model_info[method] = {"training_frequencies_hz": frequencies, "window_seconds": .6}
            else:
                model = DirectPredictor(method, horizons, seed=config.seed).fit(x, train_end)
                model_info[method] = model.metadata
            models[method] = model
            validation_predictions[method] = model.predict(x, validation_origins, horizons)
        validation_scores, selected = {}, {}
        for delay, ms in zip(delays, config.horizons_ms):
            key = str(ms)
            cols = np.searchsorted(horizons, delay+np.arange(1, config.block+1))
            target = x[validation_origins[:, None]+horizons[cols]]
            validation_scores[key] = {name: forecast_scores(target, pred[:, cols], config.fs)
                                      for name, pred in validation_predictions.items()}
            selected[key] = choose_method(validation_scores[key])
        # Freeze choices before any held-out prediction or test metric is computed.
        selection = {"selected_by_horizon_ms": selected.copy(), "criterion": "maximum validation band prediction gain",
                     "no_test_data_used": True}
        print(f"Validation choices frozen: {selected}", flush=True)
        test_predictions = {"zero": np.zeros((len(test_origins), len(horizons))),
                            "persistence": persistence_forecast(x, test_origins, horizons),
                            "repeat_cycle": cycle_forecast(x, test_origins, horizons, period)}
        for method, model in models.items():
            test_predictions[method] = model.predict(x, test_origins, horizons)
    rows, evaluation = [], {}
    example = {"reference": x, "fs": np.array(config.fs), "validation_end": np.array(validation_end),
               "train_end": np.array(train_end), "test_origins": test_origins, "horizons": horizons}
    for delay, ms in zip(delays, config.horizons_ms):
        key = str(ms)
        cols = np.searchsorted(horizons, delay+np.arange(1, config.block+1))
        target = x[test_origins[:, None]+horizons[cols]]
        for method, pred in test_predictions.items():
            score = forecast_scores(target, pred[:, cols], config.fs)
            rows.append({"method": method, "horizon_start_ms": ms, "horizon_end_ms": ms+config.block/config.fs*1000,
                         "selected": method == selected[key], "validation": validation_scores[key][method], "test": score})
            if method == selected[key]:
                evaluation[key] = {"method": method, "test": score, "quality_ok": quality_ok,
                                   "prediction_target_met": gate(score, quality_ok, config.required_band_gain_db)}
                example[f"actual_{key}"] = target.ravel()
                example[f"forecast_{key}"] = pred[:, cols].ravel()
                example[f"target_start_{key}"] = np.array(int(test_origins[0]+delay+1))
    output.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output/"forecast_arrays.npz", **example)
    result = {"schema_version": 1, "kind": "real_reference_forecast_assessment",
              "status": "Reference prediction only; no output playback or ear-level cancellation measured.",
              "config": asdict(config), "input_file": path.name, "input_sha256": digest,
              "source_label": metadata.get("source_label", "unverified input file"),
              "capture": {k: v for k, v in metadata.items() if k != "callback_timestamps"},
              "quality": quality, "quality_ok": quality_ok, "quality_reasons": reasons,
              "models": model_info, "training_frequencies_hz": frequencies,
              "repeat_cycle_period_samples": period, "repeat_cycle_frequency_hz": config.fs/period,
              "selection": selection, "evaluation": evaluation, "rows": rows,
              "runtime_seconds": time.perf_counter()-started,
              "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in Path(__file__).parent.glob("*.py")}}
    (output/"assessment.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    return result
