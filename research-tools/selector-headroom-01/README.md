# Completed 21 October 2026 research helpers

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
