"""Local visual report for the real reference forecast experiment."""
import base64
import csv
import html
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal


LABELS = {"zero": "Zero forecast", "persistence": "Hold last sample", "repeat_cycle": "Repeat last cycle",
          "tone_tracker": "Tone tracker", "ridge_ar": "Linear AR", "mlp": "Neural MLP"}


def generate_assessment_report(output, result=None):
    output = Path(output)
    result = result or json.loads((output/"assessment.json").read_text(encoding="utf-8"))
    notes_path = output/"trial_notes.json"
    notes = json.loads(notes_path.read_text(encoding="utf-8")) if notes_path.exists() else {}
    conditions = notes.get("conditions", "No additional conditions reported.")
    interpretation = notes.get("interpretation", "")
    arrays = np.load(output/"forecast_arrays.npz")
    fs = int(arrays["fs"])
    x = arrays["reference"]
    train_end, validation_end = int(arrays["train_end"]), int(arrays["validation_end"])
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 140})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    f, t, power = signal.spectrogram(x, fs, nperseg=2048, noverlap=1536)
    mesh = axes[0].pcolormesh(t, f, 10*np.log10(np.maximum(power, 1e-20)), shading="auto", cmap="magma")
    axes[0].axvline(train_end/fs, color="cyan", linestyle="--", linewidth=1)
    axes[0].axvline(validation_end/fs, color="cyan", linestyle="--", linewidth=1)
    axes[0].set(xlabel="Recording time (s)", ylabel="Frequency (Hz)", ylim=(35, 350), title="Real microphone: tone stability over time")
    fig.colorbar(mesh, ax=axes[0], label="PSD (dB, normalized reference units)")
    for name, segment in [("Training", x[:train_end]), ("Validation", x[train_end:validation_end]), ("Test", x[validation_end:])]:
        freq, psd = signal.welch(segment, fs, nperseg=4096)
        axes[1].plot(freq, 10*np.log10(np.maximum(psd, 1e-20)), label=name)
    axes[1].set(xlim=(35, 350), xlabel="Frequency (Hz)", ylabel="PSD (dB, normalized reference units)", title="Spectrum by chronological partition")
    axes[1].legend(); axes[1].grid(alpha=.2)
    fig.tight_layout(); fig.savefig(output/"source.png"); plt.close(fig)

    ms_values = result["config"]["horizons_ms"]
    methods = list(LABELS)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.7))
    for j, ms in enumerate(ms_values):
        rows = {r["method"]: r for r in result["rows"] if r["horizon_start_ms"] == ms}
        for ax, metric in zip(axes, ["band_prediction_gain_db", "prediction_gain_db"]):
            at = np.arange(len(methods))+(j-.5)*.34
            values = [rows[m]["test"][metric] for m in methods]
            bars = ax.bar(at, values, width=.32, label=f"{ms:g} ms", color=["#0072b2", "#009e73"][j])
            for m, bar in zip(methods, bars):
                if rows[m]["selected"]:
                    bar.set_edgecolor("#172b3a"); bar.set_linewidth(2)
    for ax in axes:
        ax.axhline(0, color="#777", linewidth=.7)
        ax.set_xticks(range(len(methods)), [LABELS[m].replace(" ", "\n", 1) for m in methods], fontsize=8)
        ax.grid(axis="y", alpha=.2); ax.legend()
        ax.set_ylabel("Prediction-error power improvement vs zero (dB)")
    axes[0].axhline(6, color="#ab5117", linestyle="--", label="6 dB target")
    axes[0].set_title("Held-out 35–350 Hz prediction"); axes[1].set_title("Held-out full analysis-band waveform")
    fig.tight_layout(); fig.savefig(output/"prediction.png"); plt.close(fig)

    fig, axes = plt.subplots(1, len(ms_values), figsize=(12, 3.8), squeeze=False)
    for ax, ms in zip(axes[0], ms_values):
        key = str(ms)
        actual, pred = arrays[f"actual_{key}"], arrays[f"forecast_{key}"]
        # Fixed test location; no search for a favorable illustration.
        start, count = fs, int(.1*fs)
        at = np.arange(count)*1000/fs
        ax.plot(at, actual[start:start+count], color="#8897aa", label="Actual reference")
        ax.plot(at, pred[start:start+count], color="#007c68", label="Chosen forecast")
        ax.set(title=f"{ms:g} ms: {LABELS[result['evaluation'][key]['method']]}",
               xlabel="Time within fixed test excerpt (ms)", ylabel="Normalized microphone amplitude")
        ax.legend(); ax.grid(alpha=.2)
    fig.tight_layout(); fig.savefig(output/"waveforms.png"); plt.close(fig)

    cards, findings = [], []
    for ms in ms_values:
        entry = result["evaluation"][str(ms)]
        score = entry["test"]
        decision = "TARGET MET" if entry["prediction_target_met"] else "TARGET NOT MET"
        findings.append(f"At {ms:g} ms, validation selected {LABELS[entry['method']]}. Held-out low-band prediction gain: {score['band_prediction_gain_db']:.2f} dB; full-reference NRMSE: {score['nrmse']:.3f}. {decision}.")
        cards.append(f'<article><small>{ms:g} ms forecast · {LABELS[entry["method"]]}</small><strong>{score["band_prediction_gain_db"]:.2f} dB</strong><span>low-band prediction gain</span><b>{decision}</b></article>')
    warning_count = sum(bool(v.get("warnings")) for v in result["models"].values())
    quality = "PASS" if result["quality_ok"] else "FAIL: "+"; ".join(result["quality_reasons"])
    future = ("Repeat with an independent fan recording and a fixed model choice, then measure reference-to-ear coherence and the wired acoustic path."
              if result["evaluation"][str(ms_values[0])]["prediction_target_met"] else
              "The current recording does not meet the forecast target. Inspect whether stable tonal energy is present and whether laptop input processing changes it. Test a more stationary or more tonal source, or adjust source/microphone placement; preserve this failed trial. Do not enable anti-noise output from this result.")
    lines = ["# Goal 1 — first real microphone trial", "", result["status"], "",
             f"Source: {result['source_label']}. Input: `{result['input_file']}`. Duration: {result['quality']['duration_seconds']:.1f} s.",
             f"Capture quality: {quality}.", "", f"Reported conditions: {conditions}. {interpretation}",
             "", "## Held-out finding", ""]+findings+[
             "", "The stated horizon is the start of the next 10 ms forecast block. Models use reference history only. Selection uses validation data; the test partition is evaluated afterward.",
             "", "| Method | Horizon ms | Selected | Validation low-band gain dB | Test low-band gain dB | Test full gain dB | Test NRMSE |",
             "|---|---:|---|---:|---:|---:|---:|"]
    table = []
    csv_rows = []
    for row in result["rows"]:
        cells = [LABELS[row["method"]], f"{row['horizon_start_ms']:g}", "yes" if row["selected"] else "",
                 f"{row['validation']['band_prediction_gain_db']:.2f}", f"{row['test']['band_prediction_gain_db']:.2f}",
                 f"{row['test']['prediction_gain_db']:.2f}", f"{row['test']['nrmse']:.3f}"]
        lines.append("| "+" | ".join(cells)+" |")
        table.append("<tr>"+"".join("<td>"+html.escape(c)+"</td>" for c in cells)+"</tr>")
        csv_rows.append({"method": row["method"], "horizon_ms": row["horizon_start_ms"], "selected": row["selected"],
                         **{"validation_"+k:v for k,v in row["validation"].items()},
                         **{"test_"+k:v for k,v in row["test"].items()}})
    lines += ["", "## Interpretation and next step", "", future, "",
              "- Prediction gain compares future reference waveform error with zero prediction. It is not measured cancellation at an ear.",
              "- Low-band scoring uses the same causal 35–350 Hz Butterworth filter on actual and error signals, with 0.5 s discarded for startup. This is a predefined weighting of prediction error, not a new input supplied to the predictors.",
              "- Full-reference scoring is at the 2 kHz analysis rate after causal anti-alias resampling; it does not cover noise above 1 kHz.",
              "- The laptop's AGC, suppression and echo-processing state is unknown. Device-reported input latency is not an acoustic round-trip measurement.",
              f"- {warning_count} neural fit(s) reported optimization warnings; details are preserved in assessment.json.",
              "- One capture is one session. There is no independent-session generalization or near-ear calibration evidence yet."]
    (output/"FINDINGS.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    with (output/"metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader(); writer.writerows(csv_rows)
    def embed(name):
        return '<img alt="'+name+'" src="data:image/png;base64,'+base64.b64encode((output/name).read_bytes()).decode()+'">'
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Goal 1 · Real fan prediction</title>
<style>body{background:#f1f5f4;color:#173532;font:16px/1.6 system-ui,sans-serif;margin:0}main{max-width:1180px;margin:auto;padding:42px 28px}h1{font-size:42px;line-height:1.15}h2{margin-top:36px}.kicker{color:#007c68;font-weight:700;letter-spacing:.12em;font-size:13px}.cards{display:flex;gap:20px;flex-wrap:wrap}article{background:white;border:1px solid #d5e0dc;border-radius:12px;padding:22px;flex:1;min-width:230px}strong{display:block;font-size:38px}article b{display:block;font-size:13px;margin-top:14px;color:#a04b18}small,article span{color:#526963}.note{padding:18px 22px;background:#fff5e3;border-left:4px solid #c77c2b;margin:24px 0}img{width:100%;border-radius:10px;margin:10px 0}.scroll{overflow:auto}table{border-collapse:collapse;background:white;width:100%;font-size:13px}th,td{padding:10px;border-bottom:1px solid #dde6e1;text-align:left}th{background:#dcebe6}p{max-width:950px}a{color:#007360}</style>
<main><div class="kicker">PREDICTIVE ANC / GOAL 1 / REAL MICROPHONE</div><h1>Can we predict this fan?</h1><p>Thirty seconds recorded through the laptop microphone. Train on the first 12 seconds, choose on the next 6, then evaluate the final 12.</p>
<div class="note"><b>Reference prediction only.</b> No anti-noise was played and no ear-level cancellation was measured. The 6 dB target concerns prediction-error power in the 35–350 Hz band.<br><b>Reported conditions:</b> '''+html.escape(conditions)+". "+html.escape(interpretation)+'''</div><div class="cards">'''+"".join(cards)+f'''</div><p>Capture quality: <b>{html.escape(quality)}</b>. Model choices were frozen using validation scores. {warning_count} neural fit(s) reported optimization warnings.</p>
<h2>What the microphone recorded</h2>'''+embed("source.png")+'''<h2>Held-out prediction performance</h2>'''+embed("prediction.png")+'''<p>Outlined bars are the models selected using validation. Positive gain means less forecast-error power than zero prediction. Higher is better; 0 dB means no improvement.</p><h2>A fixed test excerpt</h2>'''+embed("waveforms.png")+'''<h2>Complete comparison</h2><div class="scroll"><table><thead><tr><th>Method</th><th>Horizon ms</th><th>Selected</th><th>Validation band dB</th><th>Test band dB</th><th>Test full dB</th><th>Test NRMSE</th></tr></thead><tbody>'''+"".join(table)+'''</tbody></table></div><h2>Next experiment</h2><p>'''+html.escape(future)+'''</p><p>See <a href="FINDINGS.md">findings and limitations</a>, <a href="assessment.json">complete measurements</a>, and <a href="../docs/GOAL_1.md">the predeclared first goal</a>.</p></main></html>'''
    (output/"report.html").write_text(page, encoding="utf-8")
