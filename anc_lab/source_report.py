"""Self-contained, local HTML and figures for a matched source study."""
import base64
import csv
import html
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import numpy as np


def generate_source_report(output, result=None):
    output = Path(output)
    result = result or json.loads((output/'source_study.json').read_text(encoding='utf-8'))
    arrays = np.load(output/'spectra.npz')
    frequency = arrays['frequency_hz']
    off, on = arrays['off_psd'], arrays['on_psd']
    cfg = result['config']
    cut = cfg['discovery_seconds']//cfg['window_seconds']
    times = (np.arange(len(off))+.5)*cfg['window_seconds']
    colors = ['#64748b', '#0b887c']
    plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':10, 'figure.dpi':150,
                         'axes.spines.top':False, 'axes.spines.right':False})
    log = lambda values: 10*np.log10(np.maximum(values, 1e-30))
    visible = frequency <= 1000

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    for axis, limit in zip(axes, [(35, 350), (0, 1000)]):
        for name, power, color in zip(['Fan off', 'Fan on'], [off, on], colors):
            axis.plot(frequency[visible], log(power.mean(axis=0)[visible]), color=color, label=name, linewidth=1)
        axis.set(xlim=limit, xlabel='Frequency (Hz)', ylabel='PSD (dB re 1 FS²/Hz)')
        axis.legend(); axis.grid(alpha=.2)
    axes[0].set_title('Target band · original digital levels')
    axes[1].set_title('Wider context · same vertical scale')
    limits = [axis.get_ylim() for axis in axes]
    for axis in axes:
        axis.set_ylim(min(v[0] for v in limits), max(v[1] for v in limits))
    fig.tight_layout(); fig.savefig(output/'spectra.png'); plt.close(fig)

    keep = (frequency >= cfg['low_hz']) & (frequency <= cfg['high_hz'])
    combined = np.concatenate([log(off[:, keep]).ravel(), log(on[:, keep]).ravel()])
    norm = Normalize(vmin=float(np.percentile(combined, 2)), vmax=float(np.percentile(combined, 99)))
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), layout='constrained')
    for axis, name, power in zip(axes, ['Fan off', 'Fan on'], [off, on]):
        mesh = axis.pcolormesh(times, frequency[keep], log(power[:, keep]).T,
                               shading='nearest', cmap='magma', norm=norm)
        axis.axvline(cfg['discovery_seconds'], color='#7ce3df', linestyle='--', linewidth=1)
        axis.set(title=name, xlabel='Time within each separate recording (s)', ylabel='Frequency (Hz)')
    fig.colorbar(mesh, ax=axes, label='PSD (dB re 1 FS²/Hz) · shared scale')
    fig.savefig(output/'persistence.png'); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 3.8))
    for name, power, color, key in zip(['Fan off', 'Fan on'], [off, on], colors,
                                      ['off_window_rms', 'on_window_rms']):
        axes[0].plot(times, 20*np.log10(np.maximum(arrays[key], 1e-30)), '-o',
                     markersize=3, label=name, color=color)
        for label, selection, style in [('Discovery', slice(0, cut), '-'),
                                         ('Confirmation', slice(cut, None), '--')]:
            axes[1].plot(frequency[visible], log(power[selection].mean(axis=0)[visible]), style,
                         color=color, linewidth=1, label=f'{name}: {label}')
    axes[0].set(xlabel='Time within each separate recording (s)', ylabel='RMS (dB re digital amplitude 1)',
                title='Recorded level over time')
    axes[0].axvline(cfg['discovery_seconds'], color='#999', linestyle='--')
    axes[1].set(xlim=(35, 350), xlabel='Frequency (Hz)', ylabel='PSD (dB re 1 FS²/Hz)',
                title='Discovery and confirmation spectra')
    for axis in axes:
        axis.grid(alpha=.2); axis.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(output/'levels.png'); plt.close(fig)

    candidates = result['spectral_candidates_hz']
    digital_ok = result['quality']['digital_checks_pass']
    if not digital_ok:
        headline = 'Recording checks failed: repeat the matched comparison.'
        finding = 'The spectral numbers are diagnostic only because the pair failed digital/provenance checks.'
        next_step = 'Resolve the listed recording problems before selecting a control band.'
    elif candidates:
        candidate_text = ', '.join(f'{f:g} Hz' for f in candidates)
        headline = f'Spectral candidates found: {candidate_text}.'
        finding = ('These bands are stronger with the fan running and persist in the confirmation portion. '
                   'This is a source-screening result; phase predictability and fan attribution remain unproven.')
        next_step = ('Predeclare these bands, then run the existing causal predictors on a fresh independent '
                     'recording. Keep the earlier failed broad-band prediction result unchanged.')
    else:
        headline = 'No persistent low-frequency tone passed the source screen.'
        finding = ('The fan-on/off level difference alone does not provide a stable narrowband target. '
                   'This microphone and setup have not yet demonstrated the tonal reference needed for the prototype.')
        next_step = ('Document or disable input enhancements where possible, then characterize a more tonal '
                     'steady source or a better microphone position. Retain this pair as a negative source-screening result.')

    rows = result['tones']
    with (output/'tones.csv').open('w', newline='', encoding='utf-8') as handle:
        fields = list(rows[0]) if rows else ['frequency_hz', 'passes_spectral_screen']
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    # Display the strongest discovery peaks, irrespective of pass/fail, without
    # selecting favorable frequencies from confirmation.
    shown = sorted(rows, key=lambda row: row['discovery_prominence_db'], reverse=True)[:10]
    table = ''.join(
        f'<tr><td>{r["frequency_hz"]:g}</td><td>{r["discovery_prominence_db"]:.2f}</td>'
        f'<td>{r["discovery_on_off_db"]:+.2f}</td><td>{r["confirmation_on_off_db"]:+.2f}</td>'
        f'<td>{r["confirmation_windows_passing"]}/{r["confirmation_windows_total"]}</td>'
        f'<td>{"PASS" if r["passes_spectral_screen"] else "Does not pass"}</td></tr>' for r in shown)
    if not table:
        table = '<tr><td colspan="6">No discovery peaks.</td></tr>'
    summary = result['band_summaries']['whole_capture']
    confirmations = result['band_summaries']['confirmation']
    quality_text = 'PASS' if digital_ok else '; '.join(result['quality']['reasons'])
    images = {}
    for filename in ('spectra.png', 'persistence.png', 'levels.png'):
        images[filename] = 'data:image/png;base64,'+base64.b64encode((output/filename).read_bytes()).decode('ascii')
    capture_rows = ''.join(
        f'<tr><td>{label}</td><td>{r["rms_digital"]:.6g}</td><td>{r["peak_digital"]:.6g}</td>'
        f'<td>{r["duration_seconds"]:g} s</td><td>{html.escape(r["started_utc"] or "unknown")}</td></tr>'
        for label, r in [('Fan off', result['off']), ('Fan on', result['on'])])
    protocol_path = output/'protocol.json'
    conditions = result.get('protocol') or {}
    user_confirmed = bool(conditions.get('off_conditions', {}).get('confirmation')
                          and conditions.get('on_conditions', {}).get('confirmation'))
    conditions_sentence = ('The user confirmed the requested quiet fan-off and steady fan-on conditions.'
                           if user_confirmed else 'Source isolation and room conditions are not independently verified.')
    study_date = result['created_utc'].split('T')[0]
    content = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Fan source study · Predictive ANC lab</title>
<style>
:root{{color-scheme:light}}*{{box-sizing:border-box}}body{{margin:0;background:#edf2f4;color:#142b35;font:16px/1.6 system-ui,sans-serif}}main{{max-width:1120px;margin:auto;padding:44px 24px 72px}}header p{{max-width:900px}}h1{{font-size:clamp(28px,4vw,44px);line-height:1.15;letter-spacing:-.03em}}h2{{font-size:23px}}.eyebrow{{text-transform:uppercase;font-size:12px;letter-spacing:.14em;color:#08796e;font-weight:700}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:28px 0}}article,section{{background:white;border:1px solid #d5e0e5;border-radius:13px;padding:22px;margin-top:20px}}article{{margin:0}}article strong{{display:block;font-size:30px}}article span,small{{color:#516572}}.callout{{border-left:4px solid #0b887c;padding:12px 18px;background:#e1f2ef}}img{{display:block;width:100%;height:auto;margin:14px 0}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{text-align:left;padding:10px 9px;border-bottom:1px solid #dce5e9}}.scroll{{overflow-x:auto}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}}code{{overflow-wrap:anywhere}}footer{{margin-top:24px;color:#516572;font-size:13px}}@media(max-width:700px){{.cards{{grid-template-columns:1fr}}main{{padding:24px 14px}}section{{padding:15px}}}}
</style></head><body><main><header><div class="eyebrow">Predictive ANC lab · source characterization · {study_date}</div>
<h1>{headline}</h1><p>{finding}</p><p class="callout">Recorded microphone sound only. No anti-noise was played, no ear pressure was measured, and no physical ANC claim is made.</p></header>
<div class="cards"><article><small>Fan on / fan off · 35–350 Hz</small><strong>{summary['on_off_band_power_db']:+.2f} dB</strong><span>Recorded band-power difference, not attenuation</span></article>
<article><small>Whole-recording RMS ratio</small><strong>{result['full_recording_rms_ratio_db']:+.2f} dB</strong><span>Original digital levels; no independent normalization</span></article>
<article><small>Persistent spectral candidates</small><strong>{len(candidates)}</strong><span>Fixed discovery bands checked on the later 18 seconds</span></article></div>
<section><h2>What the microphone received</h2><p>Each capture lasts 30 seconds. The fan-off capture uses {result['off']['sample_rate']:,} Hz. Digital checks, including matching input name and format: <b>{html.escape(quality_text)}</b>. {conditions_sentence}</p>
<img src="{images['spectra.png']}" alt="Fan-off and fan-on power spectra on the original digital scale">
<p>The band-power difference in the confirmation portion is {confirmations['on_off_band_power_db']:+.2f} dB. These sequential captures cannot identify the source of every component. A gain change or microphone enhancement could also change the recorded spectrum.</p></section>
<section><h2>Does a tone persist?</h2><img src="{images['persistence.png']}" alt="Spectrograms with a shared color scale and a 12-second discovery boundary">
<p>The dashed line separates the first 12 seconds used to locate peaks from the last 18 seconds used for confirmation. Heatmaps share one color scale; each column is a nonoverlapping 2-second window.</p>
<div class="scroll"><table><thead><tr><th>Peak Hz</th><th>Discovery prominence dB</th><th>Discovery on/off dB</th><th>Confirmation on/off dB</th><th>Passing windows</th><th>Spectral screen</th></tr></thead><tbody>{table}</tbody></table></div>
<p><small>Up to 10 strongest discovery peaks shown; all peaks are saved in tones.csv. A candidate needs ≥6 dB local prominence and ≥6 dB on/off band increase during discovery, then both conditions in at least 80% of confirmation windows (8 of 9). Persistent spectral energy does not prove a predictable phase waveform.</small></p></section>
<section><h2>Recording stability and next step</h2><img src="{images['levels.png']}" alt="Two-second RMS levels and discovery versus confirmation spectra">
<p><b>{next_step}</b></p><p>The original 6 dB held-out prediction target remains unmet. Any new target band requires a new forecast experiment. Near-ear measurements, acoustic-path calibration and output timing measurements remain later gates.</p></section>
<section><h2>Evidence and limits</h2><div class="scroll"><table><thead><tr><th>Capture</th><th>Digital RMS</th><th>Digital peak</th><th>Length</th><th>Started UTC</th></tr></thead><tbody>{capture_rows}</tbody></table></div>
<p>Input: {html.escape(result['off']['device_name'])}, {html.escape(result['off']['host_api'])}. No near-full-scale samples or stream errors are required for the digital quality check. Neither capture is SPL-calibrated. The same endpoint and format do not establish fixed effective gain: AGC, beamforming, suppression and OS enhancements remain unverified.</p>
<details><summary>Analysis definition and provenance</summary><p>Hann periodograms: 2-second windows, no overlap, constant detrend, 0.5 Hz spacing. Power density is in digital full-scale squared per hertz. Candidate power is the mean density within ±1 Hz; local background is the median density 3–10 Hz from the peak. Each confirmation window is compared with the mean fan-off confirmation spectrum, not an arbitrarily aligned off window. Reported band power sums PSD bins over 35–350 Hz.</p>
<p>No per-recording scaling, waveform subtraction, model fitting, threshold retuning, or simulated ear transfer is applied. Criteria are an engineering screen, not a statistical significance test; there is only one sequential pair.</p>
<p>Off WAV SHA-256: <code>{result['off']['sha256']}</code><br>On WAV SHA-256: <code>{result['on']['sha256']}</code><br>Analysis code SHA-256: <code>{result['analysis_sha256']}</code></p>
<pre>{html.escape(json.dumps(conditions, indent=2))}</pre></details></section>
<footer>Local analysis · Raw recordings remain local · Shared-scale spectral aggregates and machine-readable results are saved beside this report.</footer></main></body></html>'''
    (output/'report.html').write_text(content, encoding='utf-8')
    markdown = f'''# Matched fan source study

{headline}

{finding}

- 35–350 Hz recorded power, fan on versus off: {summary['on_off_band_power_db']:+.2f} dB.
- Whole-recording digital RMS ratio: {result['full_recording_rms_ratio_db']:+.2f} dB.
- Spectral candidates passing discovery and confirmation: {candidates}.
- Digital/provenance checks: {quality_text}; effective gain and input enhancements unverified.

Next: {next_step}

This is a single sequential pair on an uncalibrated reference microphone. It provides no measured ANC attenuation, ear-level pressure, or successful future-waveform prediction. Earlier prediction failures remain unchanged. See report.html for figures and source_study.json for full metrics and provenance.
'''
    (output/'REPORT.md').write_text(markdown, encoding='utf-8')
    return output/'report.html'
