"""Verify completed offline evidence and preserve the exact research helpers."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(r"C:\Users\talk2.000\Desktop\Claude\predictive-anc")
WORK = Path(r"C:\Users\talk2.000\Documents\Codex\2026-10-15\referenced-chatgpt-conversation-this-is-an\work")
OUT = WORK.parent / "outputs/selector-headroom-20261021"
TOOLS = ROOT / "research-tools/selector-headroom-01"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write("\n")


prior = {
    "results-tone-forecaster-04/protocol.json": "874e9fd9e25b469d81c4431b4b454069f9404a701afe63b64087ed12ad5073ec",
    "results-tone-forecaster-05/protocol.json": "d02a63720f48f9765747bc48165ddd962c1c1edfbe3e6e7d6e4257acb2734116",
    "results-tone-forecaster-04/test/test.json": "47e9828f6cdf4753b1738e29fdfac72d218f936ce7845daab2531704de287944",
    "results-tone-forecaster-05/test/test.json": "0a098b6a4c9514b1f2247877ad969d9735ac9afec2241cc4c7e4f193e4d4df60",
}
# The test-05 identity is also independently stored in the original audit protocol.
head = ROOT / "results-selector-headroom-01"
protocol = read(head / "protocol.json")
verification = read(OUT / "verification.json")
assert sha(head / "protocol.json") == verification["protocol_sha256"]
assert sha(head / "audit/results.json") == verification["results_sha256"]
for study in ("02", "04", "05"):
    assert sha(ROOT / f"results-tone-forecaster-{study}/test/test.json") == protocol["prior_results"][study]
for name, expected in protocol["code_sha256"].items():
    assert sha(ROOT / name) == expected, name
for name, expected in prior.items():
    assert sha(ROOT / name) == expected, name
for name, expected in verification["artifact_sha256"].items():
    assert sha(OUT / name) == expected, name
assert verification["baseline_checks"]["matching_checks"] == 2426
assert verification["baseline_checks"]["all_pass"]
assert len(verification["baseline_checks"]["synthetic_tone_definition_exceptions"]) == 160

diag = ROOT / "results-joint-setting-diagnosis-01"
d = read(diag / "results.json")
receipt = read(diag / "receipt.json")
assert sha(diag / "plan.json") == receipt["plan_sha256"]
assert sha(diag / "results.json") == receipt["results_sha256"]
assert len(d["consistency_checks"]) == 81 and all(d["consistency_checks"])
assert len(d["cases"]) == 4 and len(d["plan"]["methods"]) == 13
for inp in d["plan"]["inputs"]:
    assert sha(ROOT / inp["local_arrays"]) == inp["arrays_sha256"]
assert sha(WORK / "diagnose_joint_settings_20261021.py") == d["plan"]["hashes"]["runner"]


def score(case, method, horizon=20):
    return next(s for s in case["scores"] if s["method"] == method and s["horizon_start_ms"] == horizon)


line_effects = [
    abs(score(c, f"fixed_{tau:g}_lines_gated")["tone_band_gain_db"]
        - score(c, f"fixed_{tau:g}_selector_gated")["tone_band_gain_db"])
    for c in d["cases"] for tau in (0, .05, .1, .2, .4)
]
assert max(line_effects) < .42

# Clarify historical labeling without altering the recorded results.
instructions = ROOT / "CLAUDE.md"
text = instructions.read_text(encoding="utf-8")
text = text.replace("Latest verified state (20 Oct 2026, Codex):", "Previous verified state (20 Oct 2026, Codex):")
instructions.write_text(text, encoding="utf-8", newline="\n")

TOOLS.mkdir(exist_ok=False)
helpers = (
    "report_selector_headroom_20261021.py",
    "diagnose_joint_settings_20261021.py",
    "finish_headroom_20261021.py",
)
for name in helpers:
    shutil.copyfile(WORK / name, TOOLS / name)
readme = """# Completed 21 October 2026 research helpers

These are exact local copies of the helpers used for the completed selector
audit and four-source joint-setting diagnosis. No audio or forecast arrays are
included here. The project remains in the Claude desktop app's selected folder.

- `anc_lab/selector_headroom.py` is the primary audit runner; the fixed protocol
  and completed evidence are in `results-selector-headroom-01/`.
- `report_selector_headroom_20261021.py` summarizes saved results and checks
  baseline parity without rerunning models.
- `diagnose_joint_settings_20261021.py` ran the ten fixed settings plus three
  controls on four cached, already-seen sources.
- `finish_headroom_20261021.py` verifies receipts and preserves these copies.

The helpers retain their original absolute local paths and write-new guards.
They are execution records, not commands for the user to run. Existing output
directories intentionally prevent accidental repeat or overwrite. Any new
experiment needs a new plan and destination; do not delete completed evidence
to make a runner execute again.

The tests for the diagnostic are `tests/test_selector_headroom.py`. Eight
targeted tests passed before freezing. The earlier full 128-test suite was not
rerun for this audit. The follow-on has 81 baseline/intervention consistency
checks, distinct from unit tests.

Read `docs/SELECTOR_HEADROOM.md` and `docs/JOINT_SETTING_DIAGNOSIS.md` for the
scoped stop decision, scientific limits and next bounded experiment.
"""
(TOOLS / "README.md").write_text(readme, encoding="utf-8", newline="\n")
save(TOOLS / "SHA256.json", {p.name: sha(p) for p in sorted(TOOLS.iterdir()) if p.is_file()})
docs = [
    ROOT / "CLAUDE.md",
    ROOT / "docs/CODEX_HANDOFF.md",
    ROOT / "docs/CONTINUATION_STATUS.md",
    ROOT / "docs/NEXT_OFFLINE_MILESTONE.md",
    ROOT / "docs/SELECTOR_HEADROOM.md",
    ROOT / "docs/JOINT_SETTING_DIAGNOSIS.md",
    OUT / "CONTINUATION.md",
    diag / "REPORT.md",
]
final = {
    "verified_utc": datetime.now(timezone.utc).isoformat(),
    "client_date": "2026-10-21",
    "previous_evidence_unchanged": prior,
    "headroom_protocol_sha256": verification["protocol_sha256"],
    "headroom_results_sha256": verification["results_sha256"],
    "headroom_code_files_verified": len(protocol["code_sha256"]),
    "baseline_metric_comparisons": 2426,
    "synthetic_tone_label_exceptions_disclosed": 160,
    "diagnostic_receipt": receipt,
    "max_matched_line_finder_effect_db_at_20ms": max(line_effects),
    "documents_sha256": {str(p): sha(p) for p in docs},
    "reproducibility_manifest_sha256": sha(TOOLS / "SHA256.json"),
    "no_model_rerun_in_finalization": True,
}
save(OUT / "continuation-verification.json", final)
print(json.dumps({
    "frozen_results_unchanged": True,
    "frozen_audit_code_files": len(protocol["code_sha256"]),
    "baseline_metric_comparisons": 2426,
    "diagnostic_consistency_checks": 81,
    "max_matched_line_finder_effect_db_at_20ms": max(line_effects),
    "report": str(OUT / "CONTINUATION.md"),
}, indent=2))
