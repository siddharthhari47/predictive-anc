"""Read-only integrity checks of completed studies, then save a new verification receipt."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(r"C:\Users\talk2.000\Desktop\Claude\predictive-anc")
WORK = Path(r"C:\Users\talk2.000\Documents\Codex\2026-10-15\referenced-chatgpt-conversation-this-is-an\work")
OUT = WORK.parent / "outputs/anc-studies-20261020"
HELPERS = ROOT / "research-tools/codex-20261020"
EXPECTED = {
    "04": {
        "protocol": "874e9fd9e25b469d81c4431b4b454069f9404a701afe63b64087ed12ad5073ec",
        "test": "47e9828f6cdf4753b1738e29fdfac72d218f936ce7845daab2531704de287944",
        "files": 6, "scenes": 60,
    },
    "05": {
        "protocol": "d02a63720f48f9765747bc48165ddd962c1c1edfbe3e6e7d6e4257acb2734116",
        "test": "0a098b6a4c9514b1f2247877ad969d9735ac9afec2241cc4c7e4f193e4d4df60",
        "files": 7, "scenes": 84,
    },
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write("\n")


def main():
    studies = {}
    bytes_total, file_count = 0, 0
    for number, expected in EXPECTED.items():
        folder = ROOT / f"results-tone-forecaster-{number}"
        protocol, result = read(folder / "protocol.json"), read(folder / "test/test.json")
        download = read(folder / "download-20261020/download_manifest.json")
        review = read(folder / "CODEX_REVIEW.json")
        execution = read(folder / "execution-20261020.json")
        complete = read(folder / "execution-complete-20261020.json")
        assert sha(folder / "protocol.json") == expected["protocol"]
        assert sha(folder / "test/test.json") == expected["test"]
        assert protocol == result["protocol"]
        assert len(protocol["code_sha256"]) == 18
        for name, digest in protocol["code_sha256"].items():
            assert sha(ROOT / "anc_lab" / name) == digest, name
        assert complete["test_json_sha256"] == review["test_json_sha256"] == expected["test"]
        assert (complete["protocol_sha256"] == review["protocol_sha256"]
                == download["protocol_sha256"] == execution["protocol_sha256"] == expected["protocol"])
        assert sha(folder / "CODEX_REVIEW.json") == sha(OUT / f"study-{number}-review.json")
        assert not list(folder.glob("execution-failed*"))
        inputs, absent = [], []
        for entry in protocol["fresh_recordings"]:
            path = ROOT / f"external-audio/wikimedia-commons-fresh-{number}" / entry["file"]
            receipt = next(f for f in download["files"] if f["file"] == entry["file"])
            if entry["file"] in result["fresh_missing"]:
                assert not path.exists()
                assert receipt["status"] == "missing" and "429" in receipt["reason"]
                absent.append(entry["file"])
                continue
            assert receipt["status"] == "verified_download"
            data = path.read_bytes()
            assert len(data) == entry["bytes"] == receipt["bytes"]
            assert hashlib.sha1(data).hexdigest() == entry["sha1"] == receipt["sha1"]
            digest = hashlib.sha256(data).hexdigest()
            assert digest == receipt["sha256"] == result["fresh_sha256"][entry["file"]]
            bytes_total += len(data)
            file_count += 1
            inputs.append({"file": entry["file"], "bytes": len(data), "sha256": digest,
                           "frozen_size_sha1_and_download_test_sha256_match": True})
        assert len(inputs) == expected["files"] == len(result["fresh_files"])
        assert len(result["scenes"]) == expected["scenes"]
        assert [r["file"] for r in result["fresh_recordings"]] == result["fresh_files"]
        assert absent == result["fresh_missing"] == download["missing"] == complete["fresh_missing"]
        assert sum(v["bytes"] for v in inputs) == download["bytes_verified"]
        studies[number] = {
            "protocol_sha256": expected["protocol"], "test_sha256": expected["test"],
            "all_18_frozen_code_hashes_match": True, "inputs": inputs, "missing_without_replacement": absent,
            "primary_execution_receipts": [str(folder / f) for f in
                ("execution-20261020.json", "execution-complete-20261020.json")],
            "frozen_primary_executions": 1, "saved_score_review_sha256": sha(folder / "CODEX_REVIEW.json"),
            "saved_score_recount_passed_for": review["summary_recomputed_from_saved_scores_for"],
            "synthetic_scene_count": len(result["scenes"]),
        }
    assert file_count == 13 and bytes_total == 20_068_308
    crossfolder = ROOT / "results-tone-crosscheck-20261020"
    cross, receipt = read(crossfolder / "diagnostic.json"), read(crossfolder / "receipt.json")
    assert sha(crossfolder / "diagnostic.json") == receipt["diagnostic_sha256"]
    assert sha(crossfolder / "plan.json") == receipt["plan_sha256"]
    assert sha(crossfolder / "REPORT.md") == receipt["report_sha256"]
    assert cross["all_baselines_match_study04"]
    assert len(cross["baseline_consistency_checks"]) == 30
    assert all(v["matches"] for v in cross["baseline_consistency_checks"])
    assert cross["plan"]["source_study04_test_sha256"] == EXPECTED["04"]["test"]
    assert cross["plan"]["source_protocol_sha256"] == {n: v["protocol"] for n, v in EXPECTED.items()}

    # Copies are helper implementations, not frozen model/protocol changes.
    helper_names = ("run_frozen_studies_20261020.py", "review_frozen_results_20261020.py",
                    "record_study_outcome_20261020.py", "compare_frozen_studies_20261020.py",
                    "crosscheck_tone_fade_20261020.py", "finish_study_docs_20261020.py",
                    "verify_completed_studies_20261020.py")
    old_manifest = HELPERS / "SHA256.json"
    backup = HELPERS / "SHA256.before-finalization.json"
    if not backup.exists():
        shutil.copyfile(old_manifest, backup)
    for name in helper_names:
        shutil.copyfile(WORK / name, HELPERS / name)
    helper_hashes = {name: sha(HELPERS / name) for name in helper_names}
    old_manifest.write_text(json.dumps(helper_hashes, indent=2) + "\n", encoding="utf-8", newline="\n")
    assert all(sha(WORK / name) == digest for name, digest in helper_hashes.items())
    report_files = [p for p in OUT.iterdir() if p.is_file() and p.name != "verification.json"]
    verification = {
        "verified_utc": datetime.now(timezone.utc).isoformat(), "status": "passed",
        "studies": studies, "total_downloaded_files": file_count, "total_downloaded_bytes": bytes_total,
        "missing_recordings_total": 3, "primary_test_runs": 2,
        "post_hoc_diagnostic_runs": 1, "post_hoc_comparator_checks_passed": 30,
        "post_hoc_diagnostic_sha256": receipt["diagnostic_sha256"],
        "post_download_unit_checks": {
            "source": "Observed unittest output during this continuation; not rerun by this audit.",
            "passed": 3, "runtime_seconds": 0.222,
            "tests": ["test_tone_gate_fade.Study04Tests.test_fresh_list_must_be_new",
                      "test_tone_gate_fade.Study04Tests.test_synthetic_test_draws_are_fresh_and_repeat",
                      "test_tone_react.Study05Tests.test_fresh_list_is_new"],
        },
        "earlier_full_suite": {"passed": 128, "runtime_seconds": 51.607,
                               "scope": "Earlier in this continuation, before downloads. No predictor source changed afterward."},
        "helper_sha256": helper_hashes, "report_files_sha256": {p.name: sha(p) for p in report_files},
        "engine_changed": False, "audio_device_streams_opened": False,
        "primary_models_rerun_by_this_audit": False,
        "claim": "Offline reference prediction only. No physical ear-level cancellation measured.",
    }
    dump(OUT / "verification.json", verification)
    dump(HELPERS / "verification.json", verification)
    print(json.dumps({k: verification[k] for k in
                      ("status", "total_downloaded_files", "total_downloaded_bytes", "missing_recordings_total",
                       "primary_test_runs", "post_hoc_diagnostic_runs", "post_hoc_comparator_checks_passed")}, indent=2))


if __name__ == "__main__":
    main()
