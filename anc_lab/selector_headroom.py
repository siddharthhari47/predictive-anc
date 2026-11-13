"""Offline, seen-data selector audit. Never used by the live engine.

Existing predictors stay frozen. Oracles are explicitly noncausal. The simple
causal rules use only completed target blocks and operate after existing gates.
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from scipy import signal
from threadpoolctl import threadpool_limits

from . import forecaster_study as s1
from . import forecaster_study_02 as s2
from . import forecaster_study_03 as s3
from . import forecaster_study_05 as s5
from .generalization import normalized_prefix
from .real_hum_study import (ELECTRICAL, PREFIX_FRACTION, load_any, near_mask,
                             prominent_tones, spectrum, tonal_fraction)
from .selection_study import BLOCK, FS, TRAIN_END, VAL_END, horizon_setup

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "results-selector-headroom-01"
ARMS = ("v2_gated", "fade0.1_linear_gated", "zero")
LOOKBACKS = (2., 4., 8.)
FADE_SECONDS = .1
WINDOW_SECONDS = 2.


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def causal_mix(target, arms, origins, horizon_end, lookback_seconds, fs=FS,
               fade_seconds=FADE_SECONDS, start_seconds=3., margin_db=1.):
    """Choose a gated arm using causal, band-limited matured residual energy.

    target: rows x samples; arms: methods x rows x samples. No hindsight tones.
    All future errors may exist in this offline array, but the cumulative sum
    lookup is capped by each row's target-block maturity time.
    """
    methods, rows, block = arms.shape
    assert target.shape == (rows, block) and len(origins) == rows
    sos = signal.butter(4, (35., 350.), fs=fs, btype="bandpass", output="sos")
    errors = (target[None, :, :] - arms).reshape(methods, -1)
    filtered = signal.sosfilt(sos, errors, axis=1)
    powers = np.sum(filtered.reshape(methods, rows, block)**2, axis=2)
    sums = np.concatenate((np.zeros((methods, 1)), np.cumsum(powers, axis=1)), axis=1)
    mature = np.searchsorted(origins + horizon_end, origins, side="right")
    needed = max(1, round(lookback_seconds * fs / block))
    fade_n = max(1, round(fade_seconds * fs))
    weights = np.eye(methods)[0].copy()
    start_weights, goal = weights.copy(), weights.copy()
    selected, elapsed, switching = 0, fade_n, 0
    out = np.empty((rows, block))
    choices = np.zeros(rows, dtype=np.int16)
    for r, origin in enumerate(origins):
        end = int(mature[r])
        if origin >= start_seconds * fs and end >= needed and elapsed >= fade_n:
            energy = np.maximum(sums[:, end] - sums[:, end-needed], 1e-30)
            best = int(np.argmin(energy))
            if best != selected and energy[selected] >= 10**(margin_db/10) * energy[best]:
                start_weights, goal = weights.copy(), np.eye(methods)[best]
                selected, elapsed = best, 0
                switching += 1
        alpha = np.clip((elapsed + np.arange(1, block+1)) / fade_n, 0., 1.)
        weight_block = start_weights[None, :] + alpha[:, None] * (goal-start_weights)[None, :]
        out[r] = np.sum(weight_block.T * arms[:, r, :], axis=0)
        weights = weight_block[-1]
        elapsed += block
        choices[r] = selected
    return out, {"switches": switching, "selected": choices, "matured_rows": mature,
                 "full_history_rows_required": needed}


def spectral_loss(error, tones, fs=FS):
    """Hindsight objective: tone bins when available, otherwise whole low band."""
    f, power = spectrum(np.ravel(error), fs)
    mask = near_mask(f, tones) if tones else (f >= 35.) & (f <= 350.)
    return float(power[mask].sum())


def transition_block(arms, previous, current, start, stop, fade_samples):
    block = arms[current, start:stop].copy()
    n = min(fade_samples, len(block))
    alpha = np.arange(1, n+1) / fade_samples
    block[:n] = (1-alpha)*arms[previous, start:start+n] + alpha*block[:n]
    return block


def minimum_cost_path(costs, initial=0):
    """Exact DP for additive window costs depending on previous/current arm."""
    windows, methods, _ = costs.shape
    accumulated = np.full(methods, np.inf)
    accumulated[initial] = 0.
    back = np.empty((windows, methods), dtype=np.int16)
    for w in range(windows):
        total = accumulated[:, None] + costs[w]
        back[w] = np.argmin(total, axis=0)
        accumulated = total[back[w], np.arange(methods)]
    now = int(np.argmin(accumulated))
    best_cost = float(accumulated[now])
    choices = np.empty(windows, dtype=np.int16)
    for w in range(windows-1, -1, -1):
        choices[w] = now
        now = int(back[w, now])
    return choices, best_cost


def oracle_mix(target, arms, tones, fs=FS, window_seconds=WINDOW_SECONDS,
               fade_seconds=FADE_SECONDS):
    """Static oracle and 2 s DP oracle with rendered 100 ms transitions.

    The DP is optimal for its additive window spectral loss, not for the full
    file's overlapping Welch statistic. Include the best static arm as a
    predeclared fallback if it scores better on the actual reported metric.
    This is a privileged benchmark, not a universal mathematical upper bound.
    """
    shape = target.shape
    actual = np.ravel(target)
    streams = arms.reshape(len(arms), -1)
    file_losses = [spectral_loss(actual-arm, tones, fs) for arm in streams]
    file_choice = int(np.argmin(file_losses))
    static = streams[file_choice].copy()
    window = max(1, round(window_seconds * fs))
    fade = max(1, round(fade_seconds * fs))
    starts = list(range(0, len(actual), window))
    if len(starts) > 1 and len(actual)-starts[-1] < round(.5*fs):
        starts.pop()  # Avoid a tiny terminal periodogram with no tone-bin support.
    stops = starts[1:] + [len(actual)]
    costs = np.empty((len(starts), len(arms), len(arms)))
    for w, (start, stop) in enumerate(zip(starts, stops)):
        for previous in range(len(arms)):
            for current in range(len(arms)):
                y = transition_block(streams, previous, current, start, stop, fade)
                costs[w, previous, current] = spectral_loss(actual[start:stop]-y, tones, fs)*(stop-start)
    choices, objective = minimum_cost_path(costs)
    output, previous = np.empty_like(actual), 0
    for w, (start, stop) in enumerate(zip(starts, stops)):
        output[start:stop] = transition_block(streams, previous, int(choices[w]), start, stop, fade)
        previous = int(choices[w])
    dp_loss = spectral_loss(actual-output, tones, fs)
    fallback = file_losses[file_choice] <= dp_loss
    if fallback:
        output = static.copy()
    return static.reshape(shape), output.reshape(shape), {
        "file_choice": file_choice, "window_choices": choices.tolist(),
        "static_fallback": bool(fallback), "additive_window_cost": objective,
        "static_loss": file_losses[file_choice], "dp_full_file_loss": dp_loss,
    }


def evaluate_arrays(x, grid, keep, predictions, tones):
    """Score existing gated arms, fixed causal rules and explicit hindsight arms."""
    _, _, groups = horizon_setup()
    extra = {f"causal_L{n:g}": np.zeros_like(predictions["zero"]) for n in LOOKBACKS}
    extra.update({m: predictions["v2_gated"].copy() for m in ("oracle_file", "oracle_window")})
    trace, details = {}, {}
    for columns, horizons in groups:
        label = str(round((horizons[0]-1)*1000/FS))
        target = x[grid[:, None] + horizons]
        arms = np.stack([predictions[m][:, columns] for m in ARMS])
        for lookback in LOOKBACKS:
            name = f"causal_L{lookback:g}"
            mixed, info = causal_mix(target, arms, grid, int(horizons[-1]), lookback)
            extra[name][:, columns] = mixed
            trace[f"{name}_h{label}_selected"] = info.pop("selected")
            trace[f"h{label}_matured_rows"] = info.pop("matured_rows")
            details[f"{name}_h{label}"] = info
        static, window, info = oracle_mix(target[keep], arms[:, keep], tones)
        extra["oracle_file"][np.ix_(keep, columns)] = static
        extra["oracle_window"][np.ix_(keep, columns)] = window
        details[f"oracle_h{label}"] = info
    combined = {**predictions, **extra}
    scored = {name: p[keep] for name, p in combined.items()
              if name in (*ARMS, "joint_gated", "prefix_ar", *extra)}
    return s1.score_forecasts(x, grid[keep], scored, tones), combined, trace, details


def methods_from_protocol(protocol):
    return protocol["methods"]


def case_task(args):
    entry, protocol, output = args
    started = time.perf_counter()
    with threadpool_limits(limits=1):
        if entry["kind"] == "recording":
            path = ROOT / entry["path"]
            assert sha(path) == entry["sha256"]
            if entry.get("known_decode_failure"):
                return {**entry, "skipped": "Previously documented malformed audio; unchanged file excluded in advance."}
            audio, audio_info = load_any(path)
            prefix = int(PREFIX_FRACTION*len(audio))
            x = (audio-float(np.mean(audio[:prefix]))) / max(float(np.std(audio[:prefix])), 1e-12)
            start_score = prefix
            tones = prominent_tones(x[prefix:])
        else:
            name, family, spec, seed, raw = synthetic_tasks()[entry["task_index"]]
            if raw is None:
                raw = s1.synthesize_wander(spec, seed)
                x, _ = normalized_prefix(raw, TRAIN_END)
            else:
                x = raw
            assert array_digest(x) == entry["waveform_sha256"]
            prefix, start_score = TRAIN_END, VAL_END
            tones = [tn["freq"] for tn in spec["tones"] if not tn["drift_hz_per_s"]
                     and tn["start"] == 0 and tn["stop"] >= len(x)/FS] if family == "standard" else [
                         tn["freq"] for tn in spec["tones"] if not tn["linewidth_hz"]]
            audio_info = {"synthetic_family": family, "spec": spec, "seed": seed}
        _, horizons, _ = horizon_setup()
        grid = np.arange(BLOCK*50, len(x)-int(max(horizons)), BLOCK)
        keep = grid >= start_score
        # The existing predictors are evaluated once per case. Their frozen
        # run_methods implementation is unchanged; this is a new development run.
        full_methods = [m for m in methods_from_protocol(protocol) if m["kind"] != "prefix_ar"]
        predictions, info = s2.run_methods(x, grid, np.ones(len(grid), bool), full_methods,
                                           protocol["v2"], prefix)
        ar, ar_info = s2.run_methods(x, grid, grid >= prefix, [{"name": "prefix_ar", "kind": "prefix_ar"}],
                                    protocol["v2"], prefix)
        predictions["prefix_ar"] = np.zeros_like(predictions["zero"])
        predictions["prefix_ar"][grid >= prefix] = ar["prefix_ar"]
        info.update(ar_info)
        scores, combined, trace, details = evaluate_arrays(x, grid, keep, predictions, tones)
        # Store locally for reproducible diagnosis without another predictor run.
        arrays_path = Path(output) / "arrays" / f"{entry['id']}.npz"
        retained = {m: combined[m] for m in (*ARMS, "joint_gated", "prefix_ar")}
        np.savez_compressed(arrays_path, reference=x, origins=grid, keep=keep, horizons=horizons,
                            **retained, **trace)
        result = {**entry, "audio": audio_info, "prefix_seconds": prefix/FS,
                  "score_start_seconds": start_score/FS, "reference_tones_hz": tones,
                  "reference_tone_band_power_fraction": tonal_fraction(x[start_score:], tones),
                  "scores": scores, "selector_details": details, "methods": info,
                  "local_arrays": str(arrays_path.relative_to(ROOT)), "arrays_sha256": sha(arrays_path),
                  "runtime_seconds": time.perf_counter()-started}
        write_new(Path(output) / "cases" / f"{entry['id']}.json", result)
        return result


def synthetic_tasks():
    return s1.development_scenes()[2] + s3.buzz_scenes()[1]


def array_digest(x):
    return hashlib.sha256(np.asarray(x, dtype="<f8").tobytes()).hexdigest()


def inventory():
    entries = []
    original = ROOT / "external-audio/wikimedia-commons-2026-10-16"
    known_bad = {r["file"] for r in read(ROOT / "results-real-hums-01/real_hums.json")["skipped_files"]}
    for source in read(original / "SOURCES.json")["files"]:
        path = original / source["local_file"]
        assert sha(path) == source["sha256"]
        entries.append({"kind": "recording", "cohort": "2026-10-16", "file": path.name,
                        "path": str(path.relative_to(ROOT)), "sha256": sha(path),
                        "author": source["author"], "acoustic": path.name not in ELECTRICAL,
                        "primary_pool": True, "known_decode_failure": path.name in known_bad})
    for n in ("02", "04", "05"):
        old = read(ROOT / f"results-tone-forecaster-{n}/test/test.json")
        lookup = {e["file"]: e for e in old["protocol"]["fresh_recordings"]}
        for name in old["fresh_files"]:
            path = ROOT / f"external-audio/wikimedia-commons-fresh-{n}" / name
            assert sha(path) == old["fresh_sha256"][name]
            entries.append({"kind": "recording", "cohort": f"former-test-{n}", "file": name,
                            "path": str(path.relative_to(ROOT)), "sha256": sha(path),
                            "author": lookup[name]["author"], "acoustic": lookup[name]["acoustic"],
                            "primary_pool": True})
    assert len(entries) == 40
    # Previously captured personal recordings are secondary controls only.
    for rel in ("recordings/goal1_fan_01.wav", "results-goal1-clean/reference.wav",
                "results-source-study-01/fan_on.wav", "results-source-study-01/fan_off.wav"):
        path = ROOT / rel
        entries.append({"kind": "recording", "cohort": "personal-seen-secondary", "file": rel,
                        "path": rel, "sha256": sha(path), "author": "one personal capture setup",
                        "acoustic": True, "primary_pool": False})
    for i, (name, family, spec, seed, raw) in enumerate(synthetic_tasks()):
        if raw is None:
            raw, _ = normalized_prefix(s1.synthesize_wander(spec, seed), TRAIN_END)
        entries.append({"kind": "synthetic", "cohort": f"synthetic-{family}", "file": name,
                        "task_index": i, "waveform_sha256": array_digest(raw), "primary_pool": False})
    for i, entry in enumerate(entries):
        entry["id"] = f"case-{i:03d}"
        entry["data_status"] = "already seen; development diagnostic; never fresh validation"
    return entries


def code_hashes():
    names = set()
    for n in ("04", "05"):
        protocol = read(ROOT / f"results-tone-forecaster-{n}/protocol.json")
        for name, digest in protocol["code_sha256"].items():
            assert sha(ROOT / "anc_lab" / name) == digest, name
            names.add("anc_lab/" + name)
    names.update(("anc_lab/selector_headroom.py", "tests/test_selector_headroom.py"))
    return {name: sha(ROOT / name) for name in sorted(names)}


def prepare(output=STUDY):
    output = Path(output)
    output.mkdir(exist_ok=False)
    protocol05 = read(s5.STUDY / "protocol.json")
    methods = [m for m in protocol05["comparators"] if m["name"] in ("v2", "joint", "prefix_ar")]
    methods.append(protocol05["frozen_candidate"])
    entries = inventory()
    protocol = {
        "kind": "selector_headroom_seen_development_protocol",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "client_date": "2026-10-21", "claude_review_sha256": sha(ROOT / "docs/CLAUDE_REVIEW_20261020.md"),
        "status": "written before new diagnostic scores; settings fixed, not a fresh test",
        "methods": methods, "v2": protocol05["v2"], "arms": list(ARMS),
        "entries": entries, "code_sha256": code_hashes(),
        "causal_rule": {"lookback_seconds": list(LOOKBACKS), "band_hz": [35., 350.],
                        "error_filter": "4th-order Butterworth SOS, causal, separate per arm and horizon",
                        "criterion": "mean squared filtered residual over last L seconds of fully matured target blocks",
                        "minimum_time_seconds": 3., "requires_full_L_seconds": True,
                        "switch_margin_db": 1., "linear_crossfade_seconds": .1,
                        "decision_frequency": "each 10 ms block; hold choice during an active 100 ms transition",
                        "cold_start": "v2; no hindsight tone labels enter any causal rule"},
        "oracles": {"arms": list(ARMS), "file": "best static arm per file and horizon by the primary metric",
                    "window_seconds": 2., "crossfade_seconds": .1,
                    "terminal_window": "merge a final tail shorter than 0.5 s into the preceding window",
                    "window": "dynamic programming minimizes additive window tone-bin residual power (whole low band if no tones), including every rendered transition; best static arm is a predeclared fallback when better on full-file score",
                    "limit": "Privileged hindsight benchmark, not a universal upper bound on arbitrary selectors. Full-file Welch and additive 2 s window losses differ."},
        "score": {"recordings": "unchanged first-40% calibration, score remaining suffix, first channel, causal resampling, max 180 s",
                  "synthetic": "44 existing development scenes plus 8 buzz scenes, score existing final 4 s",
                  "primary": "median of paired tone-bin gain differences versus v2 at 20 ms across decoded acoustic public recordings with reference tones",
                  "aggregation": "one paired value per file; never count its windows as independent sources",
                  "secondary": "120 ms, whole band, strong-source regressions, per-cohort results, source-author clustering, personal files, synthetic controls",
                  "strong_source_rule": "v2 tone gain >=3 dB at the scored horizon",
                  "primary_pool_not_fresh": True},
        "decision": {"window_oracle_headroom_threshold_db": 1.,
                     "below_threshold": "Do not build the tested selector design; diagnose the strong-tone predictor loss. This is a scoped engineering stop, not an impossibility theorem.",
                     "above_threshold": "Assess all fixed causal lookbacks. Do not auto-promote or download a new test in this audit.",
                     "causal_readiness": "paired median >=0.5 dB, >=half oracle paired median, no >1 dB loss on v2>=3 dB sources at 20 ms, no more recording band-boost cases than v2 and no whole-band boosts",
                     "no_hyperparameter_retuning": True},
        "missing_rule": "One known malformed original file is excluded in advance and reported. No substitutions. Other execution failures stop the run.",
        "prior_results": {n: sha(ROOT / f"results-tone-forecaster-{n}/test/test.json") for n in ("02", "04", "05")},
        "scope": "Offline reference prediction only. No downloads, audio streams, engine changes or physical ANC claims.",
    }
    write_new(output / "protocol.json", protocol)
    print(json.dumps({"protocol": str(output / "protocol.json"), "recordings_planned": 44,
                      "public_recordings": 40, "known_decoder_exclusions": 1,
                      "synthetic_scenes": 52, "entries": len(entries)}, indent=2))
    return protocol


def run(output=STUDY, workers=4):
    output = Path(output)
    protocol = read(output / "protocol.json")
    assert protocol["code_sha256"] == code_hashes(), "Code changed after protocol."
    for number, digest in protocol["prior_results"].items():
        assert sha(ROOT / f"results-tone-forecaster-{number}/test/test.json") == digest
    stage = output / "audit"
    stage.mkdir(exist_ok=False)
    (stage / "cases").mkdir()
    (stage / "arrays").mkdir()
    write_new(stage / "execution.json", {"started_utc": datetime.now(timezone.utc).isoformat(),
                                       "workers": workers, "protocol_sha256": sha(output / "protocol.json")})
    started = time.perf_counter()
    results = [None] * len(protocol["entries"])
    with ProcessPoolExecutor(workers) as pool:
        futures = {pool.submit(case_task, (entry, protocol, str(stage))): i
                   for i, entry in enumerate(protocol["entries"])}
        for future in as_completed(futures):
            i = futures[future]
            results[i] = future.result()
            done = sum(r is not None for r in results)
            print(json.dumps({"completed": done, "total": len(results),
                              "id": results[i]["id"], "kind": results[i]["kind"],
                              "skipped": bool(results[i].get("skipped")),
                              "elapsed_minutes": round((time.perf_counter()-started)/60, 2)}), flush=True)
    result = {"kind": "seen_development_headroom_audit", "protocol": protocol, "cases": results,
              "completed_utc": datetime.now(timezone.utc).isoformat(),
              "runtime_seconds": time.perf_counter()-started,
              "claim": "Development diagnostic only, no independent generalization or physical ANC evidence."}
    write_new(stage / "results.json", result)
    write_new(stage / "complete.json", {"results_sha256": sha(stage / "results.json"),
                                       "protocol_sha256": sha(output / "protocol.json"),
                                       "runtime_seconds": result["runtime_seconds"]})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "run"))
    parser.add_argument("--out", type=Path, default=STUDY)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.stage == "prepare":
        prepare(args.out)
    else:
        run(args.out, args.workers)
