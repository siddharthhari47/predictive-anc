"""Plain-language report for the real-recording predictability check."""
from pathlib import Path

import numpy as np

METHODS = ['fixed_top3_tracker', 'auto_v1_gated', 'auto_v2_ungated', 'auto_v2_gated', 'adapted_ridge_ar']
LABELS = ['Old: fixed top-3', 'v1 + gate', 'v2, no gate', 'v2 + gate', 'AR adapted on prefix']
COLORS = ['#b34c66', '#6aa6b0', '#2f8f6f', '#0b5d4b', '#6567a5']


def short(name, width=34):
    stem = Path(name).stem.replace('_', ' ')
    return stem if len(stem) <= width else stem[:width-1]+'…'


def write_real_hum_report(output, result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    output = Path(output)
    files = sorted(result['files'], key=lambda r: -next(s['band_gain_db'] for s in r['scores']
                                                         if s['method'] == 'auto_v2_gated' and s['horizon_start_ms'] == 20.))
    gain = lambda r, m, ms: next(s['band_gain_db'] for s in r['scores'] if s['method'] == m and s['horizon_start_ms'] == ms)
    fig, axes = plt.subplots(2, 1, figsize=(15, 9), sharex=True)
    for axis, ms in zip(axes, (20., 120.)):
        for j, (m, label, color) in enumerate(zip(METHODS, LABELS, COLORS)):
            vals = np.array([gain(r, m, ms) for r in files])
            axis.bar(np.arange(len(files))+(j-2)*.16, np.clip(vals, -15, 40), width=.16, color=color, label=label)
        ceiling = [r['tone_only_ceiling_db'] for r in files]
        axis.scatter(np.arange(len(files)), np.clip(ceiling, -15, 40), marker='_', s=300, color='#222', zorder=3,
                     label='Ceiling if the steady tones were cancelled perfectly')
        axis.axhline(0, color='#555', linewidth=.7)
        axis.set_ylabel('Test gain (dB)'); axis.set_title(f'Forecast starting {ms:g} ms ahead')
        axis.grid(axis='y', alpha=.2)
    axes[-1].set_xticks(range(len(files)), [short(r['file'], 26)+(' (electrical)' if r['electrical_not_acoustic'] else '') for r in files],
                        rotation=55, ha='right', fontsize=8)
    fig.legend(*axes[0].get_legend_handles_labels(), loc='upper center', ncol=6, frameon=False, fontsize=9)
    fig.suptitle('Real recordings from Wikimedia Commons: reference prediction only (35–350 Hz, clipped to [-15, 40] dB)', y=.995)
    fig.tight_layout(rect=(0, 0, 1, .95)); fig.savefig(output/'real_hums.png', dpi=140); plt.close(fig)

    acoustic = [r for r in files if not r['electrical_not_acoustic']]
    tonebins = lambda r, m, ms: next(s['tone_band_gain_db'] for s in r['scores'] if s['method'] == m and s['horizon_start_ms'] == ms)
    useful = [r for r in acoustic if gain(r, 'auto_v2_gated', 20.) >= 3.]
    harmed = {r['file'] for r in files for ms in (20., 120.) if gain(r, 'auto_v2_gated', ms) < -.5}
    ar_harmed = {r['file'] for r in files for ms in (20., 120.) if gain(r, 'adapted_ridge_ar', ms) < -.5}
    with_tones = [r for r in acoustic if r['reference_tones_hz']]
    ar_better = [r for r in with_tones if tonebins(r, 'adapted_ridge_ar', 20.) > tonebins(r, 'auto_v2_gated', 20.)+3]
    v2_better = [r for r in with_tones if tonebins(r, 'auto_v2_gated', 20.) > tonebins(r, 'adapted_ridge_ar', 20.)+3]
    median = lambda v: float(np.median(v)) if len(v) else float('nan')
    lines = ['# Real hums recorded by other people: how predictable are they?', '',
             '**Reference-signal prediction on independent real recordings.** No acoustic path, no playback, no ear measurement. '
             'A forecast gain here says how well the hum *at the recording microphone* could be predicted ahead of time. It is not noise cancellation.', '',
             f"Settings: v1 and v2 frozen from `{result['settings_source']}`, unchanged. Nothing was tuned on these files. "
             f"Split: {result['split']}. Recordings longer than {result['max_seconds_per_file']:g} s were cut there.", '',
             '![Real recordings](real_hums.png)', '',
             '## Summary (computed from the tables below)', '',
             f"- Analysed: {len(acoustic)} acoustic recordings and {len(files)-len(acoustic)} electrical mains-hum clips"
             + (f"; {len(result.get('skipped_files', []))} file(s) could not be decoded (listed below)." if result.get('skipped_files') else '.'),
             f"- Whole 35–350 Hz band, 20 ms ahead, acoustic recordings: v2 + gate median {median([gain(r, 'auto_v2_gated', 20.) for r in acoustic]):.1f} dB; "
             f"at least 3 dB on {len(useful)} of {len(acoustic)}. Median ceiling for a perfect tones-only canceller: {median([r['tone_only_ceiling_db'] for r in acoustic]):.1f} dB.",
             f"- Below −0.5 dB (worse than predicting nothing) at either horizon: v2 + gate on {len(harmed)} file(s); AR adapted on prefix on {len(ar_harmed)}.",
             f"- Tone bins alone (±1.5 Hz around the reference tones), 20 ms ahead, on the {len(with_tones)} acoustic recordings that have tones: "
             f"v2 + gate median {median([tonebins(r, 'auto_v2_gated', 20.) for r in with_tones]):.1f} dB, AR median {median([tonebins(r, 'adapted_ridge_ar', 20.) for r in with_tones]):.1f} dB. "
             f"AR was more than 3 dB better on {len(ar_better)}, v2 more than 3 dB better on {len(v2_better)}.", '',
             '"Reference tones" come from a separate, after-the-fact spectral analysis of each test part (peaks at least 10 dB above the surrounding ±10 Hz). '
             "No forecaster sees them; they only say where to measure. \"Tone share\" = share of the test part's 35–350 Hz power within ±1.5 Hz of them. "
             '"Ceiling" = −10·log10(1 − share): what perfect cancellation of only those tones would remove from the band.', '',
             '## Whole band, 35–350 Hz (test part; dB, 20 / 120 ms ahead)', '',
             '| Recording | Kind | Test s | Reference tones (Hz) | Tone share | Ceiling | ' + ' | '.join(LABELS) + ' |',
             '|---|---|---:|---|---:|---:|' + '---:|'*len(LABELS)]
    for r in files:
        kind = 'electrical' if r['electrical_not_acoustic'] else 'acoustic'
        tones = ', '.join(f'{t:.0f}' for t in r['reference_tones_hz']) or 'none'
        cells = [f"{gain(r, m, 20.):.1f} / {gain(r, m, 120.):.1f}" for m in METHODS]
        lines.append(f"| [{short(r['file'])}]({r['source']['source_page']}) | {kind} | {r['test_seconds']:.0f} | {tones} | "
                     f"{100*r['reference_tone_band_power_fraction']:.0f}% | {r['tone_only_ceiling_db']:.1f} | " + ' | '.join(cells) + ' |')
    lines += ['', '## Tone bins only (±1.5 Hz around the reference tones; dB, 20 / 120 ms ahead)', '',
              'How much quieter the tones themselves would be if the forecast were subtracted perfectly at the microphone. This is the part people hear as "hum".', '',
              '| Recording | Steady tones v2 held (Hz) | ' + ' | '.join(LABELS) + ' |', '|---|---|' + '---:|'*len(LABELS)]
    for r in files:
        if not r['reference_tones_hz']:
            continue
        cells = [f"{tonebins(r, m, 20.):.1f} / {tonebins(r, m, 120.):.1f}" for m in METHODS]
        lines.append(f"| {short(r['file'])} | {', '.join(str(t) for t in r['v2_steady_tones_hz']) or 'none'} | " + ' | '.join(cells) + ' |')
    lines += ['', '"Steady tones v2 held" = tones the v2 detector kept active in at least half of its test-part updates.']
    lines += ['', '## Detector behaviour (test part)', '',
              '| Recording | v2 mean active tones | v2 updates with any tone | v2 gate open (20 / 120 ms) | v1 mean active tones | Channels (used) |', '|---|---:|---:|---:|---:|---|']
    for r in files:
        d2, d1 = r['detection']['v2'], r['detection']['v1']
        a = r['audio']
        ch = f"{a['channels']} (ch 0" + (f", L/R corr {a['stereo_channel_correlation']:.2f})" if a['stereo_channel_correlation'] is not None else ')')
        lines.append(f"| {short(r['file'])} | {d2['mean_active_tones_test']:.2f} | {100*d2['fraction_updates_with_any_tone_test']:.0f}% | "
                     f"{100*d2['gate_enabled_fraction_test'][0]:.0f}% / {100*d2['gate_enabled_fraction_test'][1]:.0f}% | {d1['mean_active_tones_test']:.2f} | {ch} |")
    t = [r['timing']['v2'] for r in files]
    if result.get('skipped_files'):
        lines += ['', '## Not analysed', '']
        lines += [f"- {short(r['file'], 60)}: the local decoder (libsndfile) could not read it ({r['skipped']}). It is kept unchanged on disk." for r in result['skipped_files']]
    lines += ['', '## Sources and licences', '',
              'All files are from Wikimedia Commons and were downloaded with the user\'s approval for local analysis only. They are not redistributed. '
              'SHA-256 for each file is in `real_hums.json`. Full records: `external-audio/wikimedia-commons-2026-10-16/SOURCES.md`.', '',
              '| Recording | Licence | Author |', '|---|---|---|']
    for r in sorted(files+result.get('skipped_files', []), key=lambda r: r['file']):
        lines.append(f"| {short(r['file'], 60)} | {r['source']['licence']} | {r['source']['author'][:70] or '—'} |")
    lines += ['', '## Honest limits', '',
              '- Unknown microphones, rooms, gain and editing. Most files are lossy-compressed (Ogg Vorbis, MP3). Some may have been trimmed, filtered or noise-reduced before upload.',
              '- Stereo files: channel 0 only, never averaged (the correlation between channels is listed above).',
              '- One recording per source and no repeats. The 60% test part is late in each file, so a source that changes later (switching on or off, speed steps) is in the test part.',
              '- The two mains-hum clips are electrical pickups of 5–6 s, not sound in air. They show the detector on an almost perfectly periodic signal and are reported separately.',
              '- A high forecast gain at the microphone is necessary for cancellation at the ear but not sufficient. The ear hears the hum through a different path, and the earphone adds its own.',
              '', '## Compute', '',
              f"- v2 selector update {np.mean([x['selector_update_ms_mean'] for x in t]):.1f} ms mean; forecast {np.mean([x['forecast_ms_per_origin'] for x in t]):.2f} ms per 10 ms block (offline Python, one thread).",
              f"- Whole check: {result['runtime_seconds']/60:.1f} minutes."]
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
