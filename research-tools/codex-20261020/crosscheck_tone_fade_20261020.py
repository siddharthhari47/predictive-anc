"""Post-hoc diagnostic only: unchanged study-05 candidate on already-seen study-04 audio."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(r"C:\Users\talk2.000\Desktop\Claude\predictive-anc")
DEST = ROOT / "results-tone-crosscheck-20261020"
PUBLIC = Path(r"C:\Users\talk2.000\Documents\Codex\2026-10-15\referenced-chatgpt-conversation-this-is-an\outputs\anc-studies-20261020")
sys.path.insert(0, str(ROOT))
from anc_lab import forecaster_study_02 as fs2
from anc_lab import forecaster_study_04 as s4
from anc_lab import forecaster_study_05 as s5
from anc_lab.forecaster_report import paired, sign_test_p


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def match(a, b):
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(match(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(match(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-9)
    return a == b


def main():
    started = time.perf_counter()
    p4path, p5path = (ROOT / f"results-tone-forecaster-{n}/protocol.json" for n in ("04", "05"))
    p4, p5 = (json.loads(p.read_text(encoding="utf-8")) for p in (p4path, p5path))
    previous_path = ROOT / "results-tone-forecaster-04/test/test.json"
    previous = json.loads(previous_path.read_text(encoding="utf-8"))
    for protocol in (p4, p5):
        for name, sha in protocol["code_sha256"].items():
            assert digest(ROOT / "anc_lab" / name) == sha, name
    assert p4["v2"] == p5["v2"]
    methods = [m for m in p5["comparators"] if m["name"] in ("v2", "joint")]
    assert len(methods) == 2
    for method in methods:
        assert method == next(m for m in p4["comparators"] if m["name"] == method["name"])
    methods.append(p5["frozen_candidate"])
    candidate = p5["frozen_candidate"]["name"] + "_gated"
    inputs = [(e, fs2.fresh_path(e, s4.FRESH_AUDIO)) for e in p4["fresh_recordings"]
              if e["file"] in previous["fresh_files"]]
    assert len(inputs) == len(previous["fresh_files"]) == 6
    assert all(p is not None for _, p in inputs)
    assert {p.name: digest(p) for _, p in inputs} == previous["fresh_sha256"]
    plan = {
        "kind": "post_hoc_cross_source_diagnostic",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "planned_before_this_diagnostic_run",
        "purpose": "Check the unchanged study-05 per-tone fade on the already-scored study-04 cohort.",
        "data_status": "All six recordings were seen in study 04. This is not a new held-out test.",
        "no_selection_or_retuning": True,
        "primary_study_results_unchanged": True,
        "methods": methods,
        "v2": p5["v2"],
        "workers": 6,
        "source_protocol_sha256": {"04": digest(p4path), "05": digest(p5path)},
        "source_study04_test_sha256": digest(previous_path),
        "input_sha256": {p.name: digest(p) for _, p in inputs},
        "metrics": ["20/120 ms tone-bin prediction gain", "20/120 ms whole-band prediction gain",
                    "recording-horizon cases with >=1 dB third-octave amplification",
                    "recording-horizon cases with >0.5 dB whole-band amplification"],
        "baseline_consistency": "Recomputed v2/joint score rows must match original study-04 scores.",
        "scope": "Reference-waveform prediction only; no audio stream, acoustic path or near-ear measurement.",
        "timing": "Multiprocessing compute measurements do not qualify real-time performance.",
        "runner_sha256": digest(Path(__file__)),
    }
    DEST.mkdir(exist_ok=False)
    dump(DEST / "plan.json", plan)
    print("Post-hoc plan saved. Six already-seen recordings; no tuning or primary-test rerun.", flush=True)
    records = [None] * len(inputs)
    with ProcessPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(s5._recording_task, (str(path), methods, p5["v2"], entry["acoustic"])): i
                   for i, (entry, path) in enumerate(inputs)}
        for future in as_completed(futures):
            i = futures[future]
            records[i] = future.result()
            print(f"Completed recording {i + 1}/{len(inputs)}", flush=True)
    names = fs2.method_names(methods)
    rec, _, _ = fs2.summarize(records, [], names)
    comparators = ("zero", "v2_ungated", "v2_gated", "joint_ungated", "joint_gated")
    baseline_checks = []
    for record in records:
        old = next(r for r in previous["fresh_recordings"] if r["file"] == record["file"])
        for method in comparators:
            a = [s for s in record["scores"] if s["method"] == method]
            b = [s for s in old["scores"] if s["method"] == method]
            baseline_checks.append({"file": record["file"], "method": method, "matches": match(a, b)})
    comparisons = {}
    for other in ("v2_gated", "joint_gated"):
        differences = paired(records, candidate, other, 20., "tone_band_gain_db")
        wins, losses = sum(v > 0 for _, v in differences), sum(v < 0 for _, v in differences)
        comparisons[other] = {
            "wins": wins, "losses": losses, "ties": len(differences) - wins - losses,
            "two_sided_sign_test_p": sign_test_p(wins, losses), "file_differences_db": differences,
        }
    metrics = {m: {
        "tone_median_20ms_db": rec[m]["median_tone_bin_db"]["20"],
        "tone_median_120ms_db": rec[m]["median_tone_bin_db"]["120"],
        "whole_band_median_20ms_db": rec[m]["median_whole_band_db"]["20"],
        "whole_band_median_120ms_db": rec[m]["median_whole_band_db"]["120"],
        "recording_band_boost_cases": len(rec[m]["third_octave_boosts"]),
        "recording_whole_band_boost_cases": len(rec[m]["whole_band_boosts"]),
        "tone_files": rec[m]["tone_files"],
    } for m in ("v2_gated", "joint_gated", candidate)}
    result = {
        "kind": "post_hoc_cross_source_diagnostic", "completed_utc": datetime.now(timezone.utc).isoformat(),
        "plan": plan, "candidate": candidate, "records": records, "summary": rec, "metrics": metrics,
        "paired_comparisons_20ms": comparisons, "baseline_consistency_checks": baseline_checks,
        "all_baselines_match_study04": all(c["matches"] for c in baseline_checks),
        "runtime_seconds": time.perf_counter() - started,
        "claim": "Descriptive check on already-seen sources. Not an independent test or measured ANC.",
    }
    dump(DEST / "diagnostic.json", result)
    assert result["all_baselines_match_study04"], "Comparator score mismatch: inspect before interpreting."
    dump(PUBLIC / "cross-source-review.json", {k: v for k, v in result.items() if k not in ("records", "summary")})
    lines = [
        "# Per-tone fade across the earlier source cohort", "",
        "**Post-hoc diagnostic, not a new held-out test.** All six files were already scored in study 04. "
        "The study-05 candidate and settings were unchanged; no parameter search or new model selection occurred. "
        "Both frozen primary studies retain their original results.", "",
        "All figures describe reference-microphone waveform prediction, not ear-level sound reduction.", "",
        "| Method | Tone gain, 20 / 120 ms (dB) | Whole-band gain, 20 / 120 ms (dB) | Band boosts | Whole-band boosts |",
        "|---|---:|---:|---:|---:|",
    ]
    labels = {"v2_gated": "v2", "joint_gated": "Joint check", candidate: "100 ms per-tone fade"}
    for m, v in metrics.items():
        lines.append(f"| {labels[m]} | {v['tone_median_20ms_db']:.2f} / {v['tone_median_120ms_db']:.2f} | "
                     f"{v['whole_band_median_20ms_db']:.2f} / {v['whole_band_median_120ms_db']:.2f} | "
                     f"{v['recording_band_boost_cases']} | {v['recording_whole_band_boost_cases']} |")
    lines += ["", "Boost counts use 12 recording-by-horizon cases: two horizons for each of six files. "
              "The band threshold is at least 1 dB amplification in any third-octave band; "
              "the whole-band threshold is greater than 0.5 dB amplification.", "", "## Paired source results", ""]
    for other, comp in comparisons.items():
        lines.append(f"- Against {labels[other]}, tone gain at 20 ms: {comp['wins']} wins, "
                     f"{comp['losses']} losses, {comp['ties']} ties. Descriptive sign-test p={comp['two_sided_sign_test_p']:.3f}.")
    lines += ["", "| File | v2 tone gain | Joint tone gain | Per-tone fade tone gain |",
              "|---|---:|---:|---:|"]
    for record in records:
        scores = {s["method"]: s["tone_band_gain_db"] for s in record["scores"] if s["horizon_start_ms"] == 20}
        lines.append(f"| {record['file']} | {scores['v2_gated']:.2f} | {scores['joint_gated']:.2f} | {scores[candidate]:.2f} |")
    lines += ["", "## Integrity and limits", "",
              "- All 30 comparator checks match the original study-04 score rows within numerical tolerance.",
              "- The diagnostic was planned after seeing both primary outcomes. Its findings cannot be counted "
              "as independent confirmation or used to tune a method and then call this cohort fresh.",
              "- Source code, both protocols, input hashes and candidate settings matched the frozen records.",
              "- CPU timing from this parallel run does not qualify the live system.",
              "- The live engine remains v2 pending stronger source-general evidence, timing and physical-path validation.", "",
              f"[Plan]({(DEST/'plan.json').as_posix()}) · [Full diagnostic]({(DEST/'diagnostic.json').as_posix()})"]
    content = "\n".join(lines) + "\n"
    for path in (DEST / "REPORT.md", PUBLIC / "cross-source-review.md"):
        with path.open("x", encoding="utf-8", newline="\n") as f:
            f.write(content)
    dump(DEST / "receipt.json", {"diagnostic_sha256": digest(DEST / "diagnostic.json"),
                                "plan_sha256": digest(DEST / "plan.json"),
                                "report_sha256": digest(DEST / "REPORT.md"),
                                "baseline_checks_passed": 30, "engine_changed": False})
    print(json.dumps({"metrics": metrics, "paired": comparisons,
                      "all_baselines_match_study04": True}, indent=2), flush=True)


if __name__ == "__main__":
    main()
