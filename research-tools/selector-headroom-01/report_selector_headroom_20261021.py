"""Summarize the completed, frozen seen-data audit without rerunning predictors."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np

ROOT = Path(r"C:\Users\talk2.000\Desktop\Claude\predictive-anc")
STUDY = ROOT / "results-selector-headroom-01"
OUT = Path(r"C:\Users\talk2.000\Documents\Codex\2026-10-15\referenced-chatgpt-conversation-this-is-an\outputs\selector-headroom-20261021")
sys.path.insert(0, str(ROOT))
from anc_lab.selector_headroom import code_hashes

LABELS = {
    "zero": "Zero output", "v2_gated": "v2", "joint_gated": "Joint check",
    "fade0.1_linear_gated": "Per-tone fade", "prefix_ar": "Prefix AR",
    "causal_L2": "Past errors: 2 s", "causal_L4": "Past errors: 4 s", "causal_L8": "Past errors: 8 s",
    "oracle_file": "Hindsight: static", "oracle_window": "Hindsight: windows",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write("\n")


def score(case, method, ms=20, metric="tone_band_gain_db"):
    return next(s[metric] for s in case["scores"] if s["method"] == method and s["horizon_start_ms"] == ms)


def median(values):
    return float(statistics.median(values)) if values else None


def bootstrap(values, groups=None):
    """Descriptive bootstrap only: these sources are already seen and purposive."""
    if not values:
        return None
    rng = np.random.default_rng(20261021)
    x = np.array(values)
    if groups is None:
        boot = np.median(x[rng.integers(0, len(x), (5000, len(x)))], axis=1)
    else:
        unique = sorted(set(groups))
        blocks = [x[np.array(groups) == g] for g in unique]
        boot = np.array([np.median(np.concatenate([blocks[i] for i in rng.integers(0, len(blocks), len(blocks))]))
                         for _ in range(5000)])
    return [float(v) for v in np.quantile(boot, [.025, .975])]


def primary(cases):
    return [c for c in cases if c.get("primary_pool") and c.get("acoustic") and c["reference_tones_hz"]]


def overview(cases, method):
    tonal = primary(cases)
    public = [c for c in cases if c.get("primary_pool")]
    acoustic = [c for c in public if c["acoustic"]]
    values = [score(c, method)-score(c, "v2_gated") for c in tonal]
    long = [score(c, method, 120)-score(c, "v2_gated", 120) for c in tonal]
    strong = [c for c in tonal if score(c, "v2_gated") >= 3.]
    rows = [s for c in public for s in c["scores"] if s["method"] == method]
    return {
        "tone_median_20_db": median([score(c, method) for c in tonal]),
        "paired_median_20_db": median(values),
        "paired_median_120_db": median(long),
        "paired_source_bootstrap95": bootstrap(values),
        "paired_author_cluster_bootstrap95": bootstrap(values, [c["author"] for c in tonal]),
        "paired_wins": sum(v > 1e-9 for v in values), "paired_losses": sum(v < -1e-9 for v in values),
        "paired_ties": sum(abs(v) <= 1e-9 for v in values),
        "whole_band_median_20_db": median([score(c, method, metric="band_gain_db") for c in acoustic]),
        "recording_band_boost_cases": sum(s["third_octave_boosts_over_1db"] > 0 for s in rows),
        "recording_whole_band_boost_cases": sum(s["band_gain_db"] < -.5 for s in rows),
        "strong_source_count": len(strong),
        "strong_losses_over_1db": [c["file"] for c in strong if score(c, method)-score(c, "v2_gated") < -1.],
        "worst_strong_paired_gain_db": min([score(c, method)-score(c, "v2_gated") for c in strong], default=None),
    }


def audit_baselines(cases):
    """Compare wrapper outputs with existing scores; preserve deliberate no-tone synthetic labels."""
    old_records, old_scenes = {}, {}
    development = read(ROOT / "results-tone-forecaster-05/development/dev-01/development.json")
    for record in development["recordings"]:
        old_records[record["file"]] = record
    for scene in development["scenes"]:
        old_scenes[scene["scene"]] = scene
    for n in ("04", "05"):
        previous = read(ROOT / f"results-tone-forecaster-{n}/test/test.json")
        for record in previous.get("seen_recordings", []) + previous["fresh_recordings"]:
            old_records[record["file"]] = record
    checks, omitted_tone_comparisons = [], []
    for case in cases:
        old = (old_records if case["kind"] == "recording" else old_scenes).get(case["file"])
        if old is None:
            continue
        old_scores = old.get("scores", old.get("late_window_scores"))
        for row in case["scores"]:
            if row["method"] not in ("zero", "v2_gated", "joint_gated", "prefix_ar", "fade0.1_linear_gated"):
                continue
            previous = next((s for s in old_scores if s["method"] == row["method"]
                             and s["horizon_start_ms"] == row["horizon_start_ms"]), None)
            if previous is None:
                continue
            for field in ("band_gain_db", "tone_band_gain_db", "third_octave_change_db"):
                a, b = row[field], previous[field]
                if field == "tone_band_gain_db" and case["kind"] == "synthetic" and (a is None) != (b is None):
                    omitted_tone_comparisons.append({"id": case["id"], "field": field,
                        "reason": "New diagnostic labels stochastic wandering tones as no static tone bins; whole-band scores remain comparable."})
                    continue
                same = a is b if a is None or b is None else bool(np.allclose(a, b, rtol=1e-8, atol=1e-8))
                checks.append({"id": case["id"], "method": row["method"], "horizon": row["horizon_start_ms"],
                               "field": field, "matches": same})
    assert checks and all(c["matches"] for c in checks), [c for c in checks if not c["matches"]][:8]
    return {"matching_checks": len(checks), "all_pass": True,
            "synthetic_tone_definition_exceptions": omitted_tone_comparisons}


def fmt(v):
    return "n/a" if v is None else f"{v:.2f}"


def main():
    raw = read(STUDY / "audit/results.json")
    protocol = read(STUDY / "protocol.json")
    receipt = read(STUDY / "audit/complete.json")
    assert raw["protocol"] == protocol
    assert protocol["code_sha256"] == code_hashes()
    assert sha(STUDY / "audit/results.json") == receipt["results_sha256"]
    assert sha(STUDY / "protocol.json") == receipt["protocol_sha256"]
    cases = [c for c in raw["cases"] if not c.get("skipped")]
    recordings = [c for c in cases if c["kind"] == "recording"]
    scenes = [c for c in cases if c["kind"] == "synthetic"]
    public = [c for c in recordings if c["primary_pool"]]
    tonal = primary(recordings)
    integrity = audit_baselines(cases)
    for case in cases:
        assert sha(ROOT / case["local_arrays"]) == case["arrays_sha256"]
        if case["kind"] == "recording":
            assert sha(ROOT / case["path"]) == case["sha256"]
    metrics = {m: overview(recordings, m) for m in LABELS}
    headroom = metrics["oracle_window"]["paired_median_20_db"]
    enough = headroom is not None and headroom >= 1.
    readiness = {}
    for m in ("causal_L2", "causal_L4", "causal_L8"):
        v = metrics[m]
        readiness[m] = {
            "paired_median_at_least_half_db": v["paired_median_20_db"] >= .5,
            "half_oracle_headroom_kept": v["paired_median_20_db"] >= .5*headroom,
            "no_strong_source_loss_over_1db": not v["strong_losses_over_1db"],
            "no_more_band_boosts": v["recording_band_boost_cases"] <= metrics["v2_gated"]["recording_band_boost_cases"],
            "no_whole_band_boosts": v["recording_whole_band_boost_cases"] == 0,
        }
    eligible = [m for m, checks in readiness.items() if enough and all(checks.values())]
    if not enough:
        decision = "Stop this selector design; diagnose the bank predictors' loss on strong hums."
    elif not eligible:
        decision = "Headroom exists, but none of the fixed causal rules meets all readiness checks. Keep v2; investigate the selection errors on seen data before a new test."
    else:
        decision = "Headroom and a plausible fixed causal candidate exist. Keep v2 in the engine; design an independent, frozen source test before promotion."
    cohort_metrics = {cohort: {m: overview([c for c in recordings if c["cohort"] == cohort], m)
                               for m in LABELS}
                      for cohort in sorted({c["cohort"] for c in public})}
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "client_date": "2026-10-21",
        "stage": "seen/development diagnostic", "decoded_public_recordings": len(public),
        "primary_acoustic_tonal_recordings": len(tonal), "primary_author_groups": len({c["author"] for c in tonal}),
        "secondary_personal_recordings": len(recordings)-len(public), "synthetic_scenes": len(scenes),
        "skipped": [c for c in raw["cases"] if c.get("skipped")],
        "metrics": metrics, "cohort_metrics": cohort_metrics,
        "oracle_headroom_at_least_1db": enough, "causal_readiness": readiness,
        "eligible_fixed_rules": eligible, "decision": decision,
        "integrity": integrity, "protocol_sha256": receipt["protocol_sha256"],
        "results_sha256": receipt["results_sha256"], "runtime_seconds": raw["runtime_seconds"],
        "unit_checks_passed_before_freeze": 8,
        "engine_changed": False, "audio_device_streams_opened": False,
        "independent_validation": False,
    }
    OUT.mkdir(exist_ok=False)
    dump(STUDY / "SUMMARY.json", summary)
    dump(OUT / "summary.json", summary)
    lines = [
        "# Is choosing between predictors worth building?", "",
        "21 October 2026 · Seen-data development audit", "",
        f"**{decision}**", "",
        f"The hindsight window benchmark offers **{headroom:.2f} dB** median paired tone improvement over v2 "
        f"at 20 ms. The prespecified threshold was **1.00 dB**. "
        f"The three causal rules offer **{fmt(metrics['causal_L2']['paired_median_20_db'])}, "
        f"{fmt(metrics['causal_L4']['paired_median_20_db'])}, and {fmt(metrics['causal_L8']['paired_median_20_db'])} dB** "
        "for 2, 4 and 8 second histories respectively.", "",
        f"Scored {len(public)} public recordings, four personal recordings separately, and {len(scenes)} existing synthetic scenes. "
        f"The primary statistic uses {len(tonal)} acoustic public recordings with tones "
        f"({len({c['author'] for c in tonal})} credited-author groups). One known malformed public file remains disclosed below. "
        "All data were already seen. This is neither fresh generalization evidence nor measured ANC.", "",
        f"![Audit comparison]({(OUT/'selector-headroom.png').as_posix()})", "",
        "## Source-level evidence", "",
        "| Method | Tone median at 20 ms | Paired gain vs v2 | Paired gain at 120 ms | Band boosts | Whole-band boosts | Strong-source losses >1 dB |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for m, v in metrics.items():
        lines.append(f"| {LABELS[m]} | {fmt(v['tone_median_20_db'])} | {fmt(v['paired_median_20_db'])} | "
                     f"{fmt(v['paired_median_120_db'])} | {v['recording_band_boost_cases']} | "
                     f"{v['recording_whole_band_boost_cases']} | {len(v['strong_losses_over_1db'])} |")
    lines += ["", "All gain columns are dB of reference-waveform prediction. The paired metric subtracts v2's score "
              "on each recording before taking the median. Boosts count public recording-by-horizon cases "
              f"({2*len(public)} total), including electrical/unknown-acoustic captures. Band boosts mean at least "
              "1 dB amplification in any third-octave band; whole-band boosts mean more than 0.5 dB amplification. "
              "Strong sources have v2 tone gain at least 3 dB at 20 ms.", "",
              "## Fixed causal rules", ""]
    for m, checks in readiness.items():
        failed = [k.replace("_", " ") for k, ok in checks.items() if not ok]
        lines.append(f"- **{LABELS[m]}:** " + ("all readiness checks pass." if not failed else "Fails: "+", ".join(failed)+"."))
    lines += ["", "No hyperparameter was tuned after this protocol was written. AR and joint check are reported "
              "as comparisons and were never options in the selector. The practical rules use only fully arrived "
              "target errors, and all crossfades are scored.", "", "## The strong sources Claude highlighted", "",
              "| Source | v2 | Per-tone fade | Hindsight window | Causal 2 / 4 / 8 s |",
              "|---|---:|---:|---:|---:|"]
    strong_names = ("Mobile_lift_stage.ogg", "Wiki_Motor_lancha.wav",
                    "Mil_Mi-8MTV-1_helicopter_starting_up.ogg", "Photocopie.ogg")
    for name in strong_names:
        c = next(c for c in public if c["file"] == name)
        lines.append(f"| {name} | {score(c,'v2_gated'):.2f} | {score(c,'fade0.1_linear_gated'):.2f} | "
                     f"{score(c,'oracle_window'):.2f} | "
                     + " / ".join(f"{score(c,m):.2f}" for m in ("causal_L2","causal_L4","causal_L8"))+" |")
    lines += ["", "## Cohorts and uncertainty", "",
              "| Cohort | Tonal files | Window-oracle paired median | Causal 2 / 4 / 8 s paired median |",
              "|---|---:|---:|---:|"]
    for cohort, v in cohort_metrics.items():
        n = len(primary([c for c in recordings if c["cohort"] == cohort]))
        lines.append(f"| {cohort} | {n} | {fmt(v['oracle_window']['paired_median_20_db'])} | "
                     + " / ".join(fmt(v[m]["paired_median_20_db"]) for m in ("causal_L2","causal_L4","causal_L8"))+" |")
    lines += ["", "The JSON includes both per-recording and credited-author-cluster bootstrap intervals. "
              "They describe this purposively collected, already-seen pool; they do not certify generalization. "
              "Author metadata also cannot establish independent acoustic capture conditions.", "",
              "## Secondary controls", "",
              "| Synthetic method | Late band-boost cases | Late whole-band boosts |",
              "|---|---:|---:|"]
    for m in LABELS:
        rows = [s for c in scenes for s in c["scores"] if s["method"] == m]
        lines.append(f"| {LABELS[m]} | {sum(s['third_octave_boosts_over_1db']>0 for s in rows)} | "
                     f"{sum(s['band_gain_db']<-.5 for s in rows)} |")
    lines += ["", "Synthetic counts are scene-by-horizon cases in the existing final-four-second windows. "
              "For the stochastic wandering/buzz scenes this diagnostic uses whole-band oracle loss and does not "
              "assign fixed reference tone bins. Earlier reports scored their nominal center frequencies; those "
              "tone-bin values are intentionally not compared as identical. Whole-band and third-octave baseline "
              "comparisons remain available.", "", "Personal recordings (secondary, not pooled into the primary statistic):", ""]
    for c in recordings:
        if not c["primary_pool"]:
            lines.append(f"- {c['file']}: whole-band gains at 20 ms, v2 / causal 2 / 4 / 8 s = "
                         + " / ".join(f"{score(c,m,metric='band_gain_db'):.2f}" for m in ("v2_gated","causal_L2","causal_L4","causal_L8"))+" dB.")
    lines += ["", "## Limits of the oracle", "",
              "The static oracle sees the whole scored recording. The window oracle sees future errors, optimizes "
              "an additive two-second spectral objective, and includes actual 100 ms transitions. Its static fallback "
              "prevents a worse whole-file score than the best fixed arm. It is deliberately privileged, but "
              "is not a proof that no other architecture could exceed it. The 1 dB stop is a scoped development "
              "decision for this family, not an impossibility claim.", "",
              "The practical rules minimize causal low-band energy; the hindsight benchmarks can also use the "
              "hindsight tone labels defining the primary metric. That information advantage is explicit.", "",
              "## Integrity and next action", "",
              f"- {integrity['matching_checks']} available frozen-baseline metric comparisons match within numerical tolerance.",
              "- Eight targeted checks passed before freezing: future-data invariance, complete-target accounting, "
              "cold start, hysteresis, sample ramps, oracle optimization and static fallback.",
              "- All input, forecast-array, diagnostic-code, protocol and prior-result hashes were verified.",
              "- Excluded in advance: Resident_air-conditioned_out_door_unit.ogg, already documented as malformed.",
              f"- Run time: {raw['runtime_seconds']/60:.2f} minutes. Parallel offline timing is not real-time qualification.",
              f"- **Next action:** {decision}",
              "- Keep v2. No downloads, recording, playback or engine changes occurred.",
              "- Physical continuation still requires measured paths, timing and low calibrated fixture output.",
              "", f"[Protocol]({(STUDY/'protocol.json').as_posix()}) · "
              f"[Full local evidence]({(STUDY/'audit/results.json').as_posix()}) · "
              f"[Summary and uncertainty]({(OUT/'summary.json').as_posix()}) · "
              f"[Claude's review]({(ROOT/'docs/CLAUDE_REVIEW_20261020.md').as_posix()})"]
    content = "\n".join(lines)+"\n"
    for path in (STUDY / "REPORT.md", OUT / "RESULTS.md"):
        with path.open("x", encoding="utf-8", newline="\n") as f:
            f.write(content)
    plot(summary, tonal)
    dump(OUT / "verification.json", {
        "verified_utc": datetime.now(timezone.utc).isoformat(), "baseline_checks": integrity,
        "protocol_sha256": sha(STUDY / "protocol.json"), "results_sha256": sha(STUDY / "audit/results.json"),
        "artifact_sha256": {p.name: sha(p) for p in OUT.iterdir() if p.is_file()},
        "arrays_verified": len(cases), "predictors_rerun_by_report": False,
    })
    print(json.dumps({k: summary[k] for k in ("decoded_public_recordings", "primary_acoustic_tonal_recordings",
        "oracle_headroom_at_least_1db", "eligible_fixed_rules", "decision")}, indent=2))
    print(json.dumps({m: {k: v[k] for k in ("paired_median_20_db","recording_band_boost_cases",
        "recording_whole_band_boost_cases","strong_losses_over_1db")} for m,v in metrics.items()}, indent=2))


def plot(summary, tonal):
    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":10,
                         "axes.spines.top":False, "axes.spines.right":False})
    fig, axes = plt.subplots(1, 3, figsize=(15, 6.2), gridspec_kw={"width_ratios": [1.2, 1.3, 1.]})
    fig.patch.set_facecolor("#f8fafc")
    methods = ["fade0.1_linear_gated", "causal_L2", "causal_L4", "causal_L8", "oracle_file", "oracle_window"]
    vals = [summary["metrics"][m]["paired_median_20_db"] for m in methods]
    colors = ["#64748b"] + ["#007f78"]*3 + ["#bc8426"]*2
    axes[0].barh([LABELS[m] for m in methods], vals, color=colors, height=.6)
    axes[0].invert_yaxis()
    axes[0].axvline(0, color="#64748b", lw=.8)
    axes[0].axvline(1., color="#bc8426", lw=1., ls="--")
    axes[0].set_xlabel("Median paired tone gain over v2 (dB)")
    axes[0].set_title("Does the chooser have room to help?", loc="left", pad=18, fontsize=12)
    for i, v in enumerate(vals):
        axes[0].text(v + (.025 if v >= 0 else -.025), i, f"{v:.2f}",
                     va="center", ha="left" if v>=0 else "right", weight="bold")
    span = max(max(vals)-min(vals), 1)
    axes[0].set_xlim(min(0,min(vals))-.2*span, max(1.,max(vals))+.25*span)
    xs = [score(c, "v2_gated") for c in tonal]
    ys = [score(c, "fade0.1_linear_gated")-score(c, "v2_gated") for c in tonal]
    axes[1].scatter(xs, ys, color="#476a8e", s=35, alpha=.85)
    axes[1].axhline(0, color="#64748b", lw=.8)
    axes[1].axhline(-1., color="#b4544b", lw=.8, ls="--")
    axes[1].set_xlabel("v2 tone prediction gain (dB)")
    axes[1].set_ylabel("Per-tone fade minus v2 (dB)")
    axes[1].set_title("Where does the fade lose accuracy?", loc="left", pad=18, fontsize=12)
    labels = {"Mobile_lift_stage.ogg":"Lift", "Wiki_Motor_lancha.wav":"Motorboat",
              "Mil_Mi-8MTV-1_helicopter_starting_up.ogg":"Helicopter", "Photocopie.ogg":"Copier"}
    for c,x,y in zip(tonal,xs,ys):
        if c["file"] in labels:
            axes[1].annotate(labels[c["file"]], (x,y), xytext=(5,5), textcoords="offset points", fontsize=9)
    boost_methods = ["v2_gated","fade0.1_linear_gated","causal_L2","causal_L4","causal_L8"]
    boosts = [summary["metrics"][m]["recording_band_boost_cases"] for m in boost_methods]
    bars = axes[2].barh([LABELS[m] for m in boost_methods], boosts,
                       color=["#34465d","#64748b"]+["#007f78"]*3, height=.6)
    axes[2].invert_yaxis()
    axes[2].set_xlabel("Recording × horizon cases")
    axes[2].set_title("Amplification: lower is better", loc="left", pad=18, fontsize=12)
    axes[2].xaxis.set_major_locator(MaxNLocator(integer=True))
    axes[2].set_xlim(0, max(boosts+[1])*1.2)
    for bar,v in zip(bars,boosts):
        axes[2].text(v+.2, bar.get_y()+bar.get_height()/2,str(v),va="center",weight="bold")
    for ax in axes:
        ax.set_facecolor("#f8fafc")
        ax.grid(axis="x",alpha=.12)
        ax.set_axisbelow(True)
    fig.suptitle("Should we build a predictor chooser?", x=.04, ha="left", y=.98, fontsize=22, weight="bold")
    fig.text(.04,.90,f"Seen-data diagnostic · {len(tonal)} acoustic tonal recordings · Reference prediction, not measured ANC.",
             fontsize=11,color="#475569")
    fig.text(.04,.035,"Dashed 1 dB line: predeclared headroom threshold. Gold methods use future information. Band-boost threshold: ≥1 dB.",
             fontsize=10,color="#475569")
    fig.subplots_adjust(left=.12,right=.97,top=.75,bottom=.16,wspace=.65)
    fig.savefig(OUT/"selector-headroom.png",dpi=170,facecolor=fig.get_facecolor())
    fig.savefig(OUT/"selector-headroom.svg",facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == "__main__":
    main()
