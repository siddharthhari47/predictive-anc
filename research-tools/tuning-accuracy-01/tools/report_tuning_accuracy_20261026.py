from pathlib import Path
import sys, csv, json, math, shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
sys.path.insert(0, str(ROOT))
from anc_lab import tuning_accuracy_diagnostic as d
from anc_lab import selector_headroom as h

OUT = d.STUDY
EXPORT = Path(r'C:\Users\talk2.000\Documents\Codex\2026-10-15\referenced-chatgpt-conversation-this-is-an\outputs\tuning-accuracy-20261026')


def p_stable(mu):
    # Positive small-tail differences avoid subtracting two rounded numbers near one.
    return {'on': .5*math.erfc((1+mu)/2),
            'off': .5*math.erfc((1-mu)/2),
            'same': .5*(math.erfc((abs(mu)-1)/2)-math.erfc((abs(mu)+1)/2))}


def main():
    d.verified()
    summary = h.read(OUT/'summary.json')
    verification = h.read(OUT/'verification.json')
    logs = h.read(OUT/'acceptance-results.json')['cases']
    tones = [r for c in h.read(OUT/'oracle-results.json')['cases'] for r in c['tones']]
    table = list(csv.DictReader((OUT/'tone-diagnostics.csv').open(encoding='utf-8')))
    trial_table = list(csv.DictReader((OUT/'check-trials.csv').open(encoding='utf-8')))
    assert len(table) == len(tones) == 78 and len(trial_table) == 156
    stable, negative, max_delta, max_keep_delta = [], 0, 0., 0.
    for c in logs:
        for k, session in enumerate(c['sessions']):
            rows = [r for r in session['comparisons'] if r['kind'] == 'check']
            ps = []
            for i, r in enumerate(rows):
                p = p_stable(r['on_minus_off_db'])
                assert all(0 <= x <= 1 for x in p.values())
                assert abs(sum(p.values())-1) < 5e-16
                negative += int(r['choice_probabilities']['same'] < 0)
                max_delta = max(max_delta, *[abs(p[j]-r['choice_probabilities'][j]) for j in p])
                stable.append({'case_id': c['case_id'], 'tone_index': k, 'frequency_hz': session['frequency'],
                               'check_number': i+1, **p})
                ps.append(p)
            value = sum(pa*pb for a, pa in ps[0].items() for b, pb in ps[1].items()
                        if 'off' not in (a, b) and 'on' in (a, b))
            max_keep_delta = max(max_keep_delta, abs(value-session['conditional_keep_probability']))
    # Symmetry and null-case checks of the reporting repair.
    for mu in [0., .5, 1., 5., 10., 20., 50.]:
        p, q = p_stable(mu), p_stable(-mu)
        assert p['on'] == q['off'] and p['same'] == q['same']
        assert all(x >= 0 for x in p.values())
    with (OUT/'check-probabilities-stable.csv').open('x', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, list(stable[0])); w.writeheader(); w.writerows(stable)
    h.write_new(OUT/'probability-roundoff-correction.json', {
        'created_utc': d.now(), 'kind': 'post-run reporting-only numerical correction',
        'reason': 'Computing same probability as 1-p_on-p_off can produce a tiny negative tail when p_on rounds to one. Use symmetric erfc tail differences.',
        'negative_raw_rows': negative,
        'largest_negative_raw_magnitude': max(-float(r['same_probability']) for r in trial_table),
        'maximum_any_probability_change': max_delta, 'maximum_keep_probability_change': max_keep_delta,
        'original_files_modified': [], 'corrected_file': 'check-probabilities-stable.csv',
        'decisions_changed': 0, 'settings_or_signal_scores_changed': 0,
        'validation': 'All 156 probability vectors nonnegative and sum to one within 5e-16; seven null/tail symmetry cases pass.'})

    kept = [r for r in tones if r['kept']]
    muted = [r for r in tones if not r['kept']]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4), constrained_layout=True)
    fig.set_facecolor('#fafbf9')
    colors = ['#25766c', '#b46435']
    for ax in axes:
        ax.set_facecolor('#fafbf9')
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(axis='y', alpha=.15)
        ax.set_axisbelow(True)
    for i, (group, color) in enumerate(zip([kept, muted], colors)):
        values = sorted(abs(r['phase_error_deg']) for r in group)
        # Deterministic spreading, not another experimental random draw.
        dx = .16*np.sin(np.arange(len(values))*2.39996)
        axes[0].scatter(i+dx, values, color=color, alpha=.65, s=19)
        med = np.median(values)
        axes[0].plot([i-.25, i+.25], [med, med], color='black', lw=2)
        axes[0].text(i+.29, med, f'{med:.1f}°', va='center', fontsize=9)
    axes[0].set_xticks([0, 1], ['Kept (40)', 'Muted (38)'])
    axes[0].set_xlim(-.5, 1.8); axes[0].set_ylim(0, 190)
    axes[0].set_ylabel('Absolute phase error (degrees)')
    axes[0].set_title('Settings found vs prefix optimum', fontsize=11)
    axes[0].text(.02, -.20, 'Black bars: median. All 78 eligible tones.', transform=axes[0].transAxes, fontsize=9)
    a = next(r for r in summary['mute_opportunity_counts'] if r['benefit_db'] == 1.)
    x = np.arange(2)
    b1 = [a['bounded_candidate_muted_prefix']['tones'], a['precheck_muted_prefix']['tones']]
    b2 = [a['bounded_candidate_muted_prefix_and_suffix']['tones'], a['precheck_muted_prefix_and_suffix']['tones']]
    bars1 = axes[1].bar(x-.17, b1, width=.32, color='#536f9c', label='Tuning portion')
    bars2 = axes[1].bar(x+.17, b2, width=.32, color='#94b8b0', label='Also later portion')
    axes[1].bar_label(bars1, padding=3); axes[1].bar_label(bars2, padding=3)
    axes[1].set_xticks(x, ['Best-setting\ncandidate', 'Setting\nalready found'])
    axes[1].set_ylim(0, 13); axes[1].set_ylabel('Number of muted tones')
    axes[1].set_title('Missed opportunities of ≥1 dB', fontsize=11)
    axes[1].legend(frameon=False, fontsize=8)
    axes[1].text(.02, -.20, 'Single-tone simulated auditory band.', transform=axes[1].transAxes, fontsize=9)
    vals = [-2.2063769461, 6.8950292694, 4.6886523233]
    bars = axes[2].bar(np.arange(3), vals, color=['#25766c', '#bd7547', '#9b493d'], width=.64)
    axes[2].bar_label(bars, labels=[f'{v:+.2f}' for v in vals], padding=3)
    axes[2].axhline(0, color='#888', lw=.8)
    axes[2].set_xticks(np.arange(3), ['Anti-hum\neffect', 'Background\nchange', 'Compared\non − off'])
    axes[2].set_ylim(-4, 9); axes[2].set_ylabel('Level difference (dB); lower is quieter')
    axes[2].set_title('Why a useful microwave tone failed', fontsize=11)
    axes[2].text(.02, -.20, 'One final check; different recording times.', transform=axes[2].transAxes, fontsize=9)
    fig.suptitle('Tuning diagnosis • simulated ears only • 26 October 2026', fontsize=14)
    fig.savefig(OUT/'tuning-diagnosis.png', dpi=180, bbox_inches='tight')
    plt.close(fig)

    harm_rows = '\n'.join(f"| {r['case_id']} / {r['frequency_hz'] and float(r['frequency_hz']):.1f} Hz | {float(r['absolute_phase_error_deg']):.1f}° | {float(r['precheck_prefix_erb_db']):+.3f} | {float(r['precheck_suffix_erb_db']):+.3f} |" for r in table if r['kept'] == 'True' and float(r['precheck_prefix_erb_db']) < 0)
    mute_rows = '\n'.join(f"| {r['benefit_db']:g} | {r['bounded_candidate_muted_prefix']['tones']} | {r['bounded_candidate_muted_prefix_and_suffix']['tones']} | {r['precheck_muted_prefix']['tones']} | {r['precheck_muted_prefix_and_suffix']['tones']} |" for r in summary['mute_opportunity_counts'])
    report = f'''# Tuning accuracy and final-check diagnosis

26 October 2026 · Completed response to Claude review #55

**The simulation identifies two problems: finding a useful setting, and judging it against changing sound.** Six of 40 kept tones made their own auditory band louder during the tuning portion. Ten of 38 muted tones had at least 1 dB of potential band reduction at a better setting; only three had already reached that benefit before the final check. This supports improving tuning, but does not establish that extra button presses alone will solve it.

All results are **simulated-ear diagnostics on already-seen recordings**. The live app remains on v2. No new candidate, physical noise cancellation or measured human judgement accuracy is claimed.

![Tuning diagnosis]({(OUT/'tuning-diagnosis.png').as_posix()})

## What was evaluated

Every eligible tone from the original primary 30 ms v2 runs: **78 tones in 37 simulated rooms, representing 14 source recordings**. The remaining 35 of 72 rooms had no eligible menu and remain in the inventory. The existing 1 dB listener model, settings, random draws and time intervals were preserved. All 37 original tuning runs reproduce: **1,681 saved summary/setting fields agree**.

The best-setting reference fits two native phase bases to known simulated-ear pressure in each tone's auditory band, using only the tuning prefix after the 1.5-second warm-up. It is a signal-aware linear oracle, not information available from the laptop microphone. Performance after the prefix is evaluated without refitting; that later audio is already development data from earlier studies, not an untouched test.

## Search accuracy

| Quantity | All 78 | Kept 40 | Muted 38 |
|---|---:|---:|---:|
| Median absolute phase error | 26.7° | 9.5° | 46.0° |
| Median absolute gain error | 4.43 dB | 2.12 dB | 9.80 dB |
| Phase error above 60° | 21 | 6 | 15 |
| Median single-tone band reduction before final check | +0.20 dB | +1.41 dB | +0.001 dB |

The compressor is a bad tail case; the typical kept setting is substantially closer than its phase error suggests. Short prefixes allow one sweep turn each way for 21 tones; 57 allow three turns each way. Their median phase errors are 31.6° and 24.9° respectively. These different source groups do **not** establish a causal benefit from extra presses. Presses are also missed by the model; the observed count ranges from one to six.

A phase error above 60° is not a universal harm rule. An ideal sinusoid's residual power factor is `1 + a² − 2a cos(θ)`, where `a` is the relative amplitude. Here a 73.4° setting still improves its band by 0.14 dB, while a 59.4° setting makes its band louder. The actual rendered result determines harm.

## Kept settings that made their band louder

Each row evaluates that one tone through the native output cap and simulated path; positive means attenuation, negative means amplification. These effects cannot be summed into a whole-room result.

| Room / tone | Phase error | Tuning portion, dB | Later portion, dB |
|---|---:|---:|---:|
{harm_rows}

All six worsen their tuning band by more than 0.1 dB; two exceed 0.5 dB and one exceeds 1 dB. Five remain harmful later, three by more than 0.1 dB. A different kept tone becomes slightly harmful only later: six later harms overall, none above 0.5 dB. The original whole-band compressor crossing remains unchanged; it uses a different outcome than this per-tone auditory-band diagnostic.

## Muted tones: missed search opportunities versus rejected good settings

The grid was written down before this diagnostic ran. A "best-setting candidate" applies the original gain bounds and digital cap to the prefix oracle. It is a feasible benchmark, not a claim that a listener can find it.

| Band reduction threshold, dB | Muted: best candidate reaches it in prefix | Also reaches it later | Muted: setting already found reaches it in prefix | Also reaches it later |
|---|---:|---:|---:|---:|
{mute_rows}

At 1 dB, the ten potential opportunities span nine rooms and five sources; six persist into later audio across six rooms and four sources. Seven of those ten never reached a 1 dB setting during search. Three did reach it but were rejected, and two of those still provide at least 1 dB later. Calling all ten final-check errors would conflate search with acceptance.

All 78 linear fits are identifiable, with condition numbers 1.0000–1.0088. One unconstrained oracle lies outside the original gain range. Five oracle commands and three pre-check commands clip somewhere in the retained recording; the reported band scores include the native digital cap. The gain-bounded benchmark is not claimed to be the exact optimum of the nonlinear capped problem. All ≥1 dB muted-opportunity counts are unchanged by imposing the gain bounds.

## What the final checks actually compared

The observer logged all 156 final A/B pairs, including their actual noise draws, without changing choices. It also compared on/off at each identical recording interval with earlier kept tones present. This distinguishes the anti-hum's local effect from differences between successive recording segments.

- **Compressor false keep:** `old-013-r2`, 193.9 Hz. In the first check the noiseless sequential on-minus-off difference was **+1.481 dB** (on louder), but judgement noise changed it to **−0.266 dB**, recorded as "same". In the second check there was no modeled on/off level difference in either interval; background change produced +0.343 dB and noise changed that to **−1.052 dB**, recorded as "on". "Same" plus "on" passed. With these fixed settings and presentations, the existing noise model gives an **8.30%** keep probability.
- **Microwave false mute:** `old-004-r1`, 300 Hz. The setting already reduces the full-prefix auditory band by **3.71 dB**, and the later band by **4.88 dB**. One check wraps from 13.5–15.5 s back to 1.5–3.5 s. Anti-hum reduces the second interval by **2.21 dB**, but its background is **6.90 dB** louder than the earlier off interval. The comparison therefore says on is **4.69 dB louder**, before any judgement noise. The next check strongly prefers on, but one off answer vetoes it.
- **Locomotive false mute:** `old-014-r0`, 91.3 Hz. A setting providing +1.31/+1.54 dB prefix/later benefit is rejected when a **4.33 dB background rise** overwhelms its 1.86 dB local reduction. This pair does not wrap the recording, so wrapping is not the only issue.

Across all final pairs the median absolute background difference is **0.69 dB**, the 90th percentile **3.87 dB**, and the maximum **11.93 dB**. Eleven pairs wrap the tuning prefix. Nine pairs have no modeled on/off level difference in either interval; four belong to ultimately kept tones. These are hearing-metric nulls, not proof of zero physical output.

Seventeen of 40 kept settings average less than 1 dB of same-interval benefit in their final checks. With settings and intervals held fixed, removing only the final comparison noise would reject four actual keeps and retain three actual mutes. That is a conditional counterfactual, not a rerun of a noise-free tuner. Three of the six prefix-harmful keeps would still be kept by their noiseless sequential checks because background variation favors them.

The 1 dB noise is **per presentation**. Difference noise has a standard deviation of √2 dB; the "same" zone is ±1 dB. Even a true null has a **30.7%** probability of passing two checks under this model. These are consequences of assumed listener behavior, not measured human error rates. Sweep presses use a different reaction-delay/miss/window model.

## Verification and next work

Ten targeted unit checks passed, including complete synthetic-session parity, prefix isolation and RNG preservation. **{verification['numeric_checks']:,} numerical audit checks** reproduced normal-equation fits, direct native rendering, all capped scores and the nine earlier compressor fits; maximum difference **{verification['maximum_absolute_difference']:.2e}**. The observer reproduces all saved tuning settings and summaries. Cached traces, native rendering and filter primitives are shared; this is not an independent physical model.

Eight raw Gaussian "same" tail probabilities had tiny negative roundoff (at most 8.31e-24). A separate, saved reporting correction computes nonnegative tail differences; maximum change in any keep probability is {max_keep_delta:.2e}. No raw result, decision, setting or audio score was changed. See [stable probabilities]({(OUT/'check-probabilities-stable.csv').as_posix()}) and [correction receipt]({(OUT/'probability-roundoff-correction.json').as_posix()}).

**Next: isolate search accuracy and comparison validity in a bounded development experiment.** Use these logs to design an ablation of extra/clearer phase evidence versus checks that require active, sufficiently comparable tone evidence. A same-recording-segment oracle is a diagnostic control only; a real listener cannot replay the environment at will. A deployable check must use causal activity/stability evidence and repeated or shorter comparisons. Do not relax acceptance or widen the tone menu from these results alone. Intermittent detections and predictor-switch compatibility remain later work.

Quiet-machine timing and user-started physical validation remain separate open requirements. No audio was played or recorded, and the live engine and all previous frozen studies are unchanged.

Files: [protocol]({(OUT/'protocol.json').as_posix()}) · [tone table]({(OUT/'tone-diagnostics.csv').as_posix()}) · [all check trials]({(OUT/'check-trials.csv').as_posix()}) · [verification]({(OUT/'verification.json').as_posix()}) · [full logged tuning]({(OUT/'acceptance-results.json').as_posix()})
'''
    (OUT/'REPORT.md').write_text(report, encoding='utf-8')
    EXPORT.mkdir(exist_ok=False)
    (EXPORT/'RESULTS.md').write_text(report, encoding='utf-8')
    for name in ['tuning-diagnosis.png', 'tone-diagnostics.csv', 'check-trials.csv',
                 'check-probabilities-stable.csv', 'verification.json', 'summary.json',
                 'probability-roundoff-correction.json', 'protocol.json']:
        shutil.copy2(OUT/name, EXPORT/name)
    h.write_new(OUT/'report-receipt.json', {'created_utc': d.now(), 'report_sha256': h.sha(OUT/'REPORT.md'),
        'export': str(EXPORT), 'export_sha256': {x.name: h.sha(x) for x in EXPORT.iterdir() if x.is_file()},
        'raw_audio_or_waveforms_exported': False})
    print(json.dumps({'report': str(OUT/'REPORT.md'), 'export': str(EXPORT),
                      'stable_probability_rows': len(stable), 'keep_probability_max_change': max_keep_delta}))


if __name__ == '__main__':
    main()
