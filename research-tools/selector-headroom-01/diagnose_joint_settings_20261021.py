"""Seen-source diagnostic: hold each existing joint-check setting fixed."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(r"C:\Users\talk2.000\Desktop\Claude\predictive-anc")
DEST = ROOT / "results-joint-setting-diagnosis-01"
sys.path.insert(0, str(ROOT))
from anc_lab import forecaster_study as s1
from anc_lab import forecaster_study_02 as s2
from anc_lab import forecaster_study_05 as s5

FILES = ("Mobile_lift_stage.ogg", "Wiki_Motor_lancha.wav",
         "Mil_Mi-8MTV-1_helicopter_starting_up.ogg", "Photocopie.ogg")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write("\n")


def task(args):
    entry, plan = args
    started = time.perf_counter()
    with threadpool_limits(limits=1):
        path = ROOT / entry["local_arrays"]
        assert sha(path) == entry["arrays_sha256"]
        with np.load(path) as arrays:
            x, grid, keep = arrays["reference"], arrays["origins"], arrays["keep"]
        forecasts, info = s2.run_methods(x, grid, keep, plan["methods"], plan["v2"],
                                         round(entry["prefix_seconds"]*2000))
        scores = s1.score_forecasts(x, grid[keep], forecasts, entry["reference_tones_hz"])
        result = {"file": entry["file"], "scores": scores, "methods": info,
                  "runtime_seconds": time.perf_counter()-started}
        save(DEST / f"{entry['id']}.json", result)
        return result


def metric(result, method, horizon=20, field="tone_band_gain_db"):
    return next(s[field] for s in result["scores"] if s["method"] == method
                and s["horizon_start_ms"] == horizon)


def main():
    headroom = read(ROOT / "results-selector-headroom-01/audit/results.json")
    previous = read(ROOT / "results-tone-forecaster-04/test/test.json")
    sources = [c for name in FILES for c in headroom["cases"] if c["file"] == name]
    p5 = read(s5.STUDY / "protocol.json")
    methods = [
        {"name": f"fixed_{level:g}_{'lines' if lines else 'selector'}", "kind": "joint", "nb_tau": 0.,
         "lines": True, "options": {"start": [level, lines], "min_checks_to_decide": 1_000_000_000}}
        for lines in (True, False) for level in (0., .05, .1, .2, .4)
    ]
    # Controls are re-evaluated for parity; existing model implementations stay unchanged.
    methods += [m for m in p5["comparators"] if m["name"] in ("v2", "joint", "bank_wide_lines")]
    assert len(methods) == 13
    plan = {
        "kind": "post_hoc_seen_strong_source_setting_diagnostic",
        "created_utc": datetime.now(timezone.utc).isoformat(), "client_date": "2026-10-21",
        "purpose": "After the selector stop, localize the source loss to static output restrictions or adaptive setting choices.",
        "hypothesis": "The unrestricted bank retains strong-tone accuracy, while the joint check's output restrictions sacrifice it.",
        "design": "Full existing 2x5 setting menu: line-finder tones on/off by minimum memory 0/.05/.1/.2/.4 s. Hold each setting fixed by preventing the band check from changing its initial choice. The bank's own internal tracking/choice, existing output gate and all other parameters are unchanged.",
        "controls": ["v2", "joint", "bank_wide_lines"],
        "methods": methods, "v2": p5["v2"],
        "inputs": [{k: c[k] for k in ("id","file","local_arrays","arrays_sha256","prefix_seconds","reference_tones_hz")}
                   for c in sources],
        "metrics": "20/120 ms tone and whole-band gain; every third-octave band change. Report all settings, not only a winner.",
        "limits": "Already-seen, outcome-selected four-source diagnosis. Holding the joint setting fixed changes its adaptation, not just transition smoothing. Static winners are hindsight, not deployable replacements.",
        "guard_tradeoff": "Never call disabling a protective check an improvement based only on tone gain; retain all amplification results.",
        "hashes": {"runner": sha(Path(__file__)),
                   "study04_test": sha(ROOT / "results-tone-forecaster-04/test/test.json"),
                   "headroom_results": sha(ROOT / "results-selector-headroom-01/audit/results.json"),
                   "code": p5["code_sha256"]},
        "scope": "Offline only, no playback, capture, downloads, engine changes or fresh validation.",
    }
    for name, expected in plan["hashes"]["code"].items():
        assert sha(ROOT / "anc_lab" / name) == expected
    DEST.mkdir(exist_ok=False)
    save(DEST / "plan.json", plan)
    started = time.perf_counter()
    results = []
    with ProcessPoolExecutor(4) as pool:
        for future in as_completed([pool.submit(task, (c, plan)) for c in sources]):
            result = future.result()
            results.append(result)
            print(f"Completed strong source {len(results)}/4", flush=True)
    results.sort(key=lambda r: FILES.index(r["file"]))
    checks = []
    for result in results:
        old = next(c for c in previous["fresh_recordings"] if c["file"] == result["file"])
        for method in ("v2_gated","joint_gated","bank_wide_lines_gated"):
            for horizon in (20,120):
                for field in ("tone_band_gain_db","band_gain_db","third_octave_change_db"):
                    checks.append(bool(np.allclose(metric(result,method,horizon,field),
                                                   metric(old,method,horizon,field), atol=1e-8, rtol=1e-8)))
        for horizon in (20,120):
            checks.append(bool(np.isclose(metric(result,"fixed_0_lines_gated",horizon),
                                          metric(result,"bank_wide_lines_gated",horizon), atol=1e-8,rtol=1e-8)))
        if result["file"] == "Photocopie.ogg":
            checks.append(bool(np.isclose(metric(result,"fixed_0.1_selector_gated"),
                                          metric(result,"joint_gated"), atol=1e-8,rtol=1e-8)))
    save(DEST / "results.json", {"plan":plan, "cases":results, "consistency_checks":checks,
                                "runtime_seconds":time.perf_counter()-started})
    assert all(checks), "Baseline or fixed-setting consistency check failed."
    lines = ["# Why the joint check loses on strong hums", "", "21 October 2026 · Post-hoc diagnosis on four already-seen sources", "",
             "All figures are reference prediction, not measured ANC. These sources were selected because earlier results showed losses. "
             "The experiment is diagnostic and cannot establish generalization.", "",
             "Each existing output setting was held fixed. This separates the available settings from the joint check's past-error decisions. "
             "The bank's own tracking and existing output gate were unchanged.", "",
             "## Tone accuracy at 20 ms", "",
             "| Method | Lift | Motorboat | Helicopter | Copier |", "|---|---:|---:|---:|---:|"]
    names = ["v2_gated","bank_wide_lines_gated","joint_gated"]+[m["name"]+"_gated" for m in methods[:10]]
    for method in names:
        lines.append("| "+method+" | "+" | ".join(f"{metric(r,method):.2f}" for r in results)+" |")
    lines += ["", "## Largest third-octave amplification at 20 ms", "",
              "Positive values are increased residual energy in a band; 1 dB or more is a boost case. "
              "Some bands have very little reference power. This is not ear-level SPL.", "",
              "| Method | Lift | Motorboat | Helicopter | Copier |", "|---|---:|---:|---:|---:|"]
    for method in names:
        lines.append("| "+method+" | "+" | ".join(f"{metric(r,method,field='max_third_octave_change_db'):.2f}" for r in results)+" |")
    lines += ["", "## Interpretation limits", "",
              "- `fixed_0_lines` is the unrestricted setting. Its score matches the original bank, verifying the intervention.",
              "- `selector` excludes extra line-finder tones; `lines` permits them. The number is the minimum allowed tracker memory in seconds.",
              "- Fixing a setting removes the joint check's adaptation and its setting transitions together. It does not isolate transition transients alone.",
              "- All static settings and both horizons are retained in the JSON. Choosing a winning static setting here would be hindsight tuning.",
              "- The protective check cannot simply be removed: compare the amplification table as well as tone accuracy.",
              f"- All {len(checks)} baseline/intervention consistency checks pass. No frozen model code changed.", "",
              f"[Plan]({(DEST/'plan.json').as_posix()}) · [All scores]({(DEST/'results.json').as_posix()})"]
    with (DEST/"REPORT.md").open("x",encoding="utf-8",newline="\n") as f:
        f.write("\n".join(lines)+"\n")
    save(DEST/"receipt.json", {"plan_sha256":sha(DEST/"plan.json"),"results_sha256":sha(DEST/"results.json"),
                             "consistency_checks_passed":len(checks)})
    print(json.dumps({r["file"]:{m:metric(r,m) for m in names} for r in results},indent=2))


if __name__ == "__main__":
    main()
