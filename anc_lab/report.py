"""Static scientific figures plus a self-contained, local HTML report."""
from collections import defaultdict
import base64
import html
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

LABELS = {"no_control": "No control", "naive_polarity": "Naive inversion", "ridge_ar": "Linear AR (direct)",
          "mlp": "Causal neural MLP", "tone_tracker": "Tone tracker", "fxnlms_error_mic": "FxNLMS + error mic",
          "oracle_future_reference": "Future oracle (noncausal)"}
COLORS = dict(zip(LABELS, ["#7f8c9d", "#d55e00", "#0072b2", "#cc79a7", "#009e73", "#e6ab02", "#444444"]))


def generate(output, result=None):
    output = Path(output)
    result = result or json.loads((output/"results.json").read_text(encoding="utf-8"))
    rows = result["rows"]
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["scene"], row["profile"], row["method"])].append(row)
    scenes = list(dict.fromkeys(r["scene"] for r in rows))
    profiles = list(dict.fromkeys(r["profile"] for r in rows))
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 140})
    fig, axes = plt.subplots(1, len(scenes), figsize=(6*len(scenes), 5), squeeze=False)
    methods = [m for m in LABELS if m != "no_control"]
    for ax, scene in zip(axes[0], scenes):
        for index, method in enumerate(methods):
            means, low, high = [], [], []
            for profile in profiles:
                values = [r["attenuation_db"] for r in grouped[(scene, profile, method)]]
                means.append(np.mean(values)); low.append(min(values)); high.append(max(values))
            at = np.arange(len(profiles))+(index-2.5)*.12
            ax.errorbar(at, means, yerr=[np.array(means)-low, np.array(high)-means],
                        fmt="o", markersize=4, capsize=2, color=COLORS[method], label=LABELS[method])
        ax.axhline(0, color="#777777", linewidth=.8)
        ax.set_xticks(range(len(profiles)), [p.replace("_", "\n") for p in profiles], fontsize=8)
        ax.set_title(scene.capitalize()); ax.set_ylabel("Simulated attenuation (dB; positive = quieter)")
        ax.grid(axis="y", alpha=.2)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False)
    fig.suptitle("Offline assumed acoustics — means and seed ranges, not hardware measurements")
    fig.tight_layout(rect=(0, .15, 1, .94)); fig.savefig(output/"attenuation.png"); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    for freq in [73, 146, 219]:
        offsets = np.linspace(-2., 2., 601)
        ratio = np.maximum(2*np.abs(np.sin(np.pi*freq*offsets/1000)), 1e-3)
        axes[0].plot(offsets, -20*np.log10(ratio), label=f"{freq} Hz")
    axes[0].set(title="Ideal single-tone limit: exact gain, timing error only", xlabel="Timing error (ms)",
                ylabel="Ideal attenuation (dB)", ylim=(-7, 45))
    axes[0].legend(); axes[0].grid(alpha=.2)
    sweeps = result["timing_sweep"]
    if sweeps:
        offsets = sorted({r["offset_ms"] for r in sweeps})
        values = [[r["attenuation_db"] for r in sweeps if r["offset_ms"] == o] for o in offsets]
        axes[1].plot(offsets, [np.mean(v) for v in values], color=COLORS["tone_tracker"])
        axes[1].fill_between(offsets, [min(v) for v in values], [max(v) for v in values], alpha=.2)
    axes[1].axhline(0, color="#777777", linewidth=.8)
    axes[1].set(title="Simulated steady hum: tracker, wired path", xlabel="Unmodelled output delay (ms)",
                ylabel="Broadband attenuation (dB)")
    axes[1].grid(alpha=.2)
    fig.tight_layout(); fig.savefig(output/"timing.png"); plt.close(fig)

    example = np.load(output/"example_signals.npz")
    fs = int(example["fs"]); start = int(example["score_start"]); end = int(example["score_end"])
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for method in ["no_control", "tone_tracker", "mlp", "fxnlms_error_mic"]:
        values = example[method][start:end]
        f, power = signal.welch(values, fs, nperseg=2048)
        axes[0].plot(f, 10*np.log10(np.maximum(power, 1e-15)), color=COLORS[method], label=LABELS[method])
        axes[1].plot(np.arange(100)*1000/fs, values[:100], color=COLORS[method], label=LABELS[method], alpha=.8)
    axes[0].set(xlim=(30, 350), xlabel="Frequency (Hz)", ylabel="PSD (dB relative to unit²/Hz)", title="Simulated ear residual spectrum")
    axes[1].set(xlabel="Time within test excerpt (ms)", ylabel="Dimensionless ear pressure", title="First 50 ms of the scored interval")
    axes[0].legend(fontsize=8); axes[0].grid(alpha=.2); axes[1].grid(alpha=.2)
    fig.tight_layout(); fig.savefig(output/"residual.png"); plt.close(fig)

    summary = ["# Predictive ANC lab — first offline results", "", result["status"], "",
               f"Seeds: {result['config']['seeds']}. Total runtime: {result['runtime_seconds']:.1f} s.", "",
               "All values use the same held-out physical interval per scene/seed. Positive attenuation means lower residual power; negative means amplification. Ranges below are min/max across seeds, not confidence intervals.", "",
               "| Scene | Transport / calibration | Method | Mean attenuation dB | Seed range dB | Test prediction NRMSE |",
               "|---|---|---|---:|---:|---:|"]
    table = []
    for (scene, profile, method), group in grouped.items():
        vals = [r["attenuation_db"] for r in group]
        forecasts = [r["test_nrmse"] for r in group if "test_nrmse" in r]
        nr = f"{np.mean(forecasts):.3f}" if forecasts else "—"
        cells = [scene, profile, LABELS[method], f"{np.mean(vals):.2f}", f"{min(vals):.2f} to {max(vals):.2f}", nr]
        summary.append("| " + " | ".join(cells) + " |")
        table.append("<tr>"+"".join("<td>"+html.escape(c)+"</td>" for c in cells)+"</tr>")
    summary += ["", "## Interpretation limits", "",
                "- Causal predictors fit only the first training partition; all training target samples precede its boundary. Validation is reported separately; test is chronological and untouched during training.",
                "- Tone frequencies come from training audio, with causal local phase/frequency refits during evaluation. Linear and neural models are frozen. No model is selected using test results.",
                "- Calibrated predictive controllers use exact assumed FIR paths; this is an optimistic calibration condition. The mismatch profile adds 20% actuator gain and 0.5 ms unmodelled delay.",
                "- FxNLMS additionally observes a simulated error microphone and adapts throughout the stream, including test. It uses the same nominal path/delay and transport jitter, but has extra sensing.",
                "- The oracle sees future reference samples and is explicitly noncausal. It is a diagnostic bound for this controller family, not an attainable algorithm or a guaranteed global optimum.",
                "- Prediction NRMSE measures future reference-microphone error; attenuation measures simulated ear residual. They are different quantities.",
                "- Jitter is an illustrative smooth delay process. Delays are chosen stress cases, not measured specifications of wired/Bluetooth products. No codec, AGC, clock drift, dropouts, microphone feedback, music mixing, bilateral fit or head movement is emulated.",
                "- The model has a dimensionless output clamp; no physical SPL or safe playback volume follows from it. No playback occurs.",
                "- The MLP is a small fully trained tanh network, not evidence about the best possible ML architecture. Optimization warnings are preserved in results.json.",
                "", "## Artifacts", "", "- `results.json`: full per-seed metrics, training details, versions, source hashes and timing sweep.",
                "- `metrics.csv`: machine-readable control and prediction comparison, including clipping fractions.",
                "- `example_signals.npz`: reference, simulated ear disturbance and residuals for the first steady/replay seed; no WAV playback assets.",
                "- PNG figures and `report.html`: plots and comparison table."]
    (output/"REPORT.md").write_text("\n".join(summary)+"\n", encoding="utf-8")
    def embedded(name):
        return '<img alt="'+name+'" src="data:image/png;base64,'+base64.b64encode((output/name).read_bytes()).decode()+'">'
    cards = []
    for profile in ["wired_fixed", "wireless_fixed", "wireless_jitter"]:
        values = [r["attenuation_db"] for r in rows if r["scene"] == scenes[0] and r["profile"] == profile and r["method"] == "tone_tracker"]
        cards.append(f'<article><small>{profile.replace("_", " ")} · tone tracker</small><strong>{np.mean(values):.1f} dB</strong><span>simulated attenuation</span></article>')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Predictive ANC · Offline research lab</title><style>
body{margin:0;background:#f2f4f7;color:#172b3a;font:16px/1.6 system-ui,sans-serif}main{max-width:1280px;margin:auto;padding:40px 28px}h1{font-size:44px;line-height:1.1;margin:12px 0}h2{margin-top:40px}p{max-width:900px}.eyebrow{color:#067661;font-weight:700;letter-spacing:.12em;font-size:13px}.notice{border-left:4px solid #c16b13;padding:16px 20px;background:#fff5df;margin:26px 0}.cards{display:flex;gap:16px;flex-wrap:wrap}article{flex:1;min-width:220px;background:white;border:1px solid #dae0e6;border-radius:12px;padding:22px}article strong{display:block;font-size:38px}article span,small{color:#516575}img{width:100%;background:#fff;border-radius:12px;margin:12px 0}.scroll{overflow:auto;border:1px solid #dae0e6;border-radius:10px}table{border-collapse:collapse;width:100%;font-size:13px;background:white}th,td{text-align:left;padding:10px 12px;border-bottom:1px solid #e6eaef}th{background:#e3ebe9;white-space:nowrap}td:nth-child(n+4){font-variant-numeric:tabular-nums}a{color:#006e68}
</style><main><div class="eyebrow">PREDICTIVE ANC / RESEARCH BUILD 0.1</div><h1>Can prediction buy enough time?</h1>
<p>A reproducible test of steady hum prediction, acoustic paths and delayed anti-noise. Existing microphones and ordinary earphones remain the engineering goal.</p>
<div class="notice"><b>Offline simulation only.</b> These are assumed acoustic paths, not measured ear-level performance. There is no real-time playback, physical ANC claim or validated safe listening level.</div>
<div class="cards">'''+"".join(cards)+'''</div><p>Cards summarize the first scene across seeds. Positive dB means reduced simulated residual power. Negative dB means the controller made it louder.</p>
<h2>Prediction has to survive the whole path</h2><p>Noise → reference microphone → causal predictor → path compensation → output delay and unknown jitter → earphone acoustic path → simulated ear residual. The ear also receives noise the reference microphone cannot observe.</p>
<h2>Control comparison</h2>'''+embedded("attenuation.png")+'''<p>Points show means, whiskers show seed ranges. The oracle uses future data. FxNLMS uses an extra simulated error microphone and adapts online; the other deployable methods do not.</p>
<h2>Timing sensitivity</h2>'''+embedded("timing.png")+'''<p>Constant latency can be anticipated when a tone remains predictable. Unknown timing error rotates the anti-noise phase; improved waveform prediction alone cannot correct an unknown playback time.</p>
<h2>What reaches the simulated ear</h2>'''+embedded("residual.png")+'''<h2>All held-out results</h2><div class="scroll"><table><thead><tr><th>Scene</th><th>Profile</th><th>Method</th><th>Mean dB</th><th>Seed range dB</th><th>Prediction NRMSE</th></tr></thead><tbody>'''+"".join(table)+'''</tbody></table></div>
<h2>Next evidence required</h2><p>Measure a wired device’s end-to-end latency and drift. Identify the earphone-to-ear path on a fixture with a near-ear measurement microphone. Demonstrate repeatable low-volume attenuation against a physical baseline before advancing to wireless.</p>
<p>See <a href="REPORT.md">the experiment notes</a>, <a href="results.json">full results</a> and <a href="../docs/PLAN.md">the project plan</a>. Raw amplitudes and the software clamp do not establish acoustic safety.</p></main></html>'''
    (output/"report.html").write_text(page, encoding="utf-8")
