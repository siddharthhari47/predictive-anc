"""Chronological benchmark. No audio output or hardware access."""
from dataclasses import asdict, dataclass
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import time

import numpy as np
from threadpoolctl import threadpool_limits

from .control import fxlms, inverse_path, predicted_command, render
from .metrics import forecast_metrics, residual_metrics
from .predictors import DirectPredictor, ToneTracker, estimate_tones
from .signals import jitter_trace, make_scene


@dataclass
class Config:
    fs: int = 2000
    train_seconds: float = 6.
    validation_seconds: float = 2.
    test_seconds: float = 4.
    block: int = 20
    lags: int = 128
    advance: int = 16
    inverse_taps: int = 40
    output_limit: float = 1.2  # Dimensionless simulation saturation, NOT safe SPL.
    seeds: tuple = (7, 19, 43)
    scenes: tuple = ("steady", "drifting", "unpredictable")


PROFILES = [
    {"name": "wired_fixed", "delay_ms": 20., "jitter_ms": 0., "bias_ms": 0., "gain": 1.},
    {"name": "wired_jitter", "delay_ms": 20., "jitter_ms": .25, "bias_ms": 0., "gain": 1.},
    {"name": "wireless_fixed", "delay_ms": 120., "jitter_ms": 0., "bias_ms": 0., "gain": 1.},
    {"name": "wireless_jitter", "delay_ms": 120., "jitter_ms": 2., "bias_ms": 0., "gain": 1.},
    {"name": "wired_miscalibrated", "delay_ms": 20., "jitter_ms": 0., "bias_ms": .5, "gain": 1.2},
]


def run(output, config=None, replay=None):
    config = config or Config()
    if config.fs != 2000 or config.block != 20:
        raise ValueError("v0.1 benchmark is specified at 2 kHz and 20-sample blocks.")
    if min(config.train_seconds, config.validation_seconds, config.test_seconds) < 1:
        raise ValueError("Each chronological partition must be at least one second.")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    delays = sorted({round(p["delay_ms"]*config.fs/1000) for p in PROFILES})
    horizons = np.unique(np.concatenate([np.arange(d+config.advance-config.inverse_taps+2,
                                                  d+config.advance+config.block+1) for d in delays]))
    train_end = round(config.train_seconds*config.fs)
    val_end = train_end+round(config.validation_seconds*config.fs)
    seconds = config.train_seconds+config.validation_seconds+config.test_seconds
    rows, model_info, sweeps = [], [], []
    examples = {}
    with threadpool_limits(limits=1):
        for scene_name in (("replay",) if replay else config.scenes):
            for seed in config.seeds:
                print(f"Building {scene_name}, seed {seed}", flush=True)
                scene = make_scene(scene_name, config.fs, seconds, seed, replay,
                                   normalization_seconds=config.train_seconds)
                x, d, n = scene.reference, scene.disturbance, len(scene.reference)
                origins = np.arange(train_end, n-int(max(horizons))-config.block, config.block)
                frequencies = estimate_tones(x[:train_end], config.fs)
                q, inverse_error = inverse_path(scene.primary, scene.secondary, config.advance, config.inverse_taps)
                # Common valid physical interval for every controller/delay/profile.
                score_start = val_end+max(delays)+config.advance+config.inverse_taps+config.block
                score_end = int(origins[-1])
                score = slice(score_start, score_end)
                if score_end-score_start < config.fs:
                    raise ValueError("Not enough test audio after delay and warmup margins.")
                predictions = {}
                for method in ["ridge_ar", "mlp", "tone_tracker"]:
                    fit_start = time.perf_counter()
                    if method == "tone_tracker":
                        predictor = ToneTracker(config.fs, frequencies)
                        metadata = {"detected_frequencies_hz": frequencies, "window_seconds": .6}
                    else:
                        predictor = DirectPredictor(method, horizons, config.lags, seed).fit(x, train_end)
                        metadata = predictor.metadata
                    pred_start = time.perf_counter()
                    predictions[method] = predictor.predict(x, origins, horizons)
                    metadata = {**metadata, "method": method, "scene": scene_name, "seed": seed,
                                "prediction_seconds": time.perf_counter()-pred_start,
                                "origin_count": len(origins), "total_seconds": time.perf_counter()-fit_start}
                    model_info.append(metadata)
                # Noncausal future-reference bound; includes sensor noise and inverse/transport imperfections.
                predictions["oracle_future_reference"] = x[origins[:, None]+horizons]
                for profile in PROFILES:
                    delay = round(profile["delay_ms"]*config.fs/1000)
                    actual_delay = delay+profile["bias_ms"]*config.fs/1000
                    jitter = jitter_trace(n, config.fs, profile["jitter_ms"], seed+100, config.block)
                    if np.min(actual_delay+jitter) <= 1:
                        raise ValueError("Noncausal delay trace; reduce jitter or increase nominal delay.")
                    actual_s = scene.secondary*profile["gain"]
                    commands = {"no_control": (np.zeros(n), 0.),
                                "naive_polarity": (-np.clip(x, -config.output_limit, config.output_limit),
                                                   float(np.mean(np.abs(x) > config.output_limit)))}
                    for method, pred in predictions.items():
                        commands[method] = predicted_command(pred, horizons, origins, delay, config.advance,
                                                             q, n, config.block, config.output_limit)
                    # Tune the adaptive baseline using validation ear-error only;
                    # delayed gradients can require a much smaller adaptation step.
                    candidates = []
                    for step in [.001, .005, .015]:
                        cu, ce, cc = fxlms(x, d, actual_s, scene.secondary, delay,
                                           actual_delay, jitter, mu=step, limit=config.output_limit)
                        val_power = float(np.mean(ce[train_end:val_end]**2))
                        candidates.append((val_power, step, cu, ce, cc))
                    _, fxstep, fxcommand, fxerror, fxclips = min(candidates, key=lambda item: item[0])
                    commands["fxnlms_error_mic"] = (fxcommand, fxclips)
                    for method, (command, clips) in commands.items():
                        residual = d+render(command, actual_s, actual_delay, jitter)
                        if method == "fxnlms_error_mic" and not np.allclose(residual, fxerror, atol=1e-10):
                            raise AssertionError("Online FxNLMS and offline acoustic renderer disagree.")
                        row = {"scene": scene_name, "seed": seed, "profile": profile["name"], "method": method,
                               **profile, "jitter_actual_rms_ms": float(np.std(jitter)*1000/config.fs),
                               "score_start_seconds": score_start/config.fs, "score_end_seconds": score_end/config.fs,
                               "clip_fraction": clips, "inverse_relative_error": inverse_error,
                               **residual_metrics(d[score], residual[score], config.fs, frequencies)}
                        row.pop("name")
                        if method == "fxnlms_error_mic":
                            row["adaptation_step"] = fxstep
                            row["step_selection"] = "minimum validation ear residual power; grid .001,.005,.015"
                        if method in predictions:
                            cols = np.searchsorted(horizons, delay+np.arange(1, config.block+1))
                            # These horizons are included by the contiguous compensation horizon sets.
                            target_indices = origins[:, None]+horizons[cols]
                            for partition, mask in [("validation", (target_indices[:, 0] >= train_end) &
                                                                   (target_indices[:, -1] < val_end)),
                                                    ("test", (origins >= val_end) &
                                                             (target_indices[:, -1] < n))]:
                                measures = forecast_metrics(x[target_indices[mask]], predictions[method][mask][:, cols])
                                row.update({f"{partition}_{k}": v for k, v in measures.items()})
                        rows.append(row)
                        if seed == config.seeds[0] and scene_name in ("steady", "replay") and profile["name"] == "wired_fixed":
                            examples[method] = residual
                    if seed == config.seeds[0] and scene_name in ("steady", "replay") and profile["name"] == "wired_fixed":
                        examples.update(reference=x, disturbance=d, score_start=np.array(score_start),
                                        score_end=np.array(score_end), fs=np.array(config.fs))
                        # Replayable dimensionless arrays, deliberately not earphone playback files.
                        np.savez_compressed(output/"example_signals.npz", **examples)
                    if scene_name == "steady":
                        if profile["name"] == "wired_fixed":
                            command = commands["tone_tracker"][0]
                            for offset in np.arange(-2., 2.001, .1):
                                res = d+render(command, actual_s, delay+offset*config.fs/1000, jitter)
                                sweeps.append({"seed": seed, "offset_ms": round(float(offset), 4),
                                               **residual_metrics(d[score], res[score], config.fs, frequencies)})
                print(f"  finished {scene_name}, seed {seed}", flush=True)
    package_versions = {name: importlib.metadata.version(name) for name in
                        ["numpy", "scipy", "matplotlib", "scikit-learn", "threadpoolctl"]}
    code_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob("*.py")}
    result = {"schema_version": 1, "status": "OFFLINE SIMULATION ONLY; no physical ANC or safe SPL validated",
              "config": asdict(config), "profiles": PROFILES, "environment": {"python": platform.python_version(),
              "platform": platform.platform(), "packages": package_versions}, "source_sha256": code_hashes,
              "input_sha256": hashlib.sha256(Path(replay).read_bytes()).hexdigest() if replay else None,
              "rows": rows, "models": model_info, "timing_sweep": sweeps,
              "runtime_seconds": time.perf_counter()-start}
    (output/"results.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    columns = [k for k in rows[0] if k != "tone_attenuation_db"]
    columns += [k for k in rows[1] if k not in columns and k != "tone_attenuation_db"]
    # Oracle/predictive fields may first appear after no_control and naive rows.
    columns = list(dict.fromkeys(k for row in rows for k in row if k != "tone_attenuation_db"))
    with (output/"metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows({k: v for k, v in row.items() if k in columns} for row in rows)
    return result
