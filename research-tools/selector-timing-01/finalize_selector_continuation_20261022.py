"""Publish local project reports after the timing and component checks finish."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shutil
import numpy as np

ROOT = Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
WORK = Path(r'C:\Users\talk2.000\Documents\Codex\2026-10-15\referenced-chatgpt-conversation-this-is-an\work')
DELIVERY = WORK.parent/'outputs/selector-timing-20261022'
COMPONENTS = ROOT/'results-selector-components-01'
TIMING = ROOT/'results-selector-timing-01'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        stream.write(value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False)+'\n')


def insert_after_heading(path, text):
    current = path.read_text(encoding='utf-8')
    first, rest = current.split('\n', 1)
    path.write_text(first+'\n\n'+text+'\n'+rest, encoding='utf-8')


def main():
    p = read(COMPONENTS/'protocol.json')
    r = read(COMPONENTS/'results.json')
    checks = []

    def check(label, ok):
        assert ok, label
        checks.append(label)

    check('component protocol hash', sha(COMPONENTS/'protocol.json') == read(COMPONENTS/'frozen.json')['sha256'])
    for name, digest in p['code_sha256'].items():
        check('frozen component dependency '+name, sha(ROOT/name) == digest)
    check('all fixed cases', [c['id'] for c in r['cases']] == [c['id'] for c in p['cases']])
    check('numerical outcome', r['passed_numerical_parity'] and all(c['passed'] for c in r['cases']))
    check('comparisons', r['sources'] == 12 and r['forecast_method_comparisons'] == 36 and r['exact_decision_arrays'] == 12)
    check('maximum saved error', r['maximum_forecast_error'] == max(max(c['max_error_to_saved'].values()) for c in r['cases']))
    check('unity drive error', r['maximum_unity_drive_error'] == max(c['unity_tuned_drive_max_error'] for c in r['cases']))
    check('switch totals', r['switches_by_horizon'] == np.sum([c['chooser_transitions_by_horizon'] for c in r['cases']], axis=0).tolist())
    check('ghost totals', r['ghost_frames'] == sum(c['ghost_frames'] for c in r['cases']))
    check('coverage rule', r['coverage_sufficient_for_exercised_switches'] ==
          (all(n > 0 for n in r['switches_by_horizon']) and r['ghost_frames'] > 0))
    for c in r['cases']:
        check(c['id']+' receipt', c == read(COMPONENTS/'parity'/(c['id']+'.json')))
        check(c['id']+' origin/decision counts', c['origins'] == 2950 and c['exact_choices'])
    # These older scientific outputs must not change during engineering work.
    preserved = {
        'results-tone-forecaster-04/protocol.json': '874e9fd9e25b469d81c4431b4b454069f9404a701afe63b64087ed12ad5073ec',
        'results-tone-forecaster-05/protocol.json': 'd02a63720f48f9765747bc48165ddd962c1c1edfbe3e6e7d6e4257acb2734116',
        'results-tone-forecaster-04/test/test.json': '47e9828f6cdf4753b1738e29fdfac72d218f936ce7845daab2531704de287944',
        'results-tone-forecaster-05/test/test.json': '0a098b6a4c9514b1f2247877ad969d9735ac9afec2241cc4c7e4f193e4d4df60',
        'results-selector-headroom-01/audit/results.json': '6dff4b3b07c553b389a808f3c9af37ae02ea0862da697f8594b4ffc8f9071c6f',
        'results-selector-fresh-01/REPORT.md': 'd9c03201811636e16a218e745d8dafcedb147f4d85b7823f87089a8bfb51c28e',
        'anc_lab/antihum.py': '599bd571cf75c3c18719540e7c32dd0a1f67f3fca6c761273bce2ce955d01c23',
    }
    for name, digest in preserved.items():
        check('preserved '+name, sha(ROOT/name) == digest)
    write_new(COMPONENTS/'VERIFICATION.json', {'passed': True, 'checks': len(checks), 'check_names': checks,
        'protocol_sha256': sha(COMPONENTS/'protocol.json'), 'results_sha256': sha(COMPONENTS/'results.json'),
        'preserved_sha256': preserved, 'created_utc': datetime.now(timezone.utc).isoformat()})

    sw = r['switches_by_horizon']
    mix = r['mixed_blocks_by_horizon']
    coverage = 'met' if r['coverage_sufficient_for_exercised_switches'] else 'not met'
    lines = ['# Chooser components: reconstruction check complete', '',
        '22 October 2026. Offline reference-waveform reconstruction only. No new simulated-ear or physical ANC result.', '',
        f"The component adapter passed all **36 method/source comparisons** on 12 fixed, already-seen recordings and reproduced all 12 decision arrays exactly. Largest waveform difference: **{r['maximum_forecast_error']:.3g}** in normalized reference units, below the frozen 1e-9 absolute / 1e-8 relative tolerance. The unity-gain tone renderer, with DC explicitly removed, differed by at most {r['maximum_unity_drive_error']:.3g}.", '',
        f'The fixed first-30-second inputs contain **{sw[0]} / {sw[1]} chooser transitions** at the 20/120 ms groups, **{mix[0]} / {mix[1]} mixed blocks**, and **{r["ghost_frames"]} bank ghost-tone frames**. The minimum exercised-state coverage rule was **{coverage}**. Ghost counts describe bank state, including times its output may be muted; they do not assert audible ghost tones.', '',
        '## What the adapter preserves', '',
        '- Original causal v2 local frequency/phase/amplitude fits, fast release and DC term; original faded-bank per-horizon components, including fading-out ghosts.',
        '- Independent matured-error gates and the exact sample-level three-arm chooser fade. No new fit to the mixed waveform and no changed chooser decisions.',
        '- Component phasors are referenced to the newest input sample. Tested horizon indices are 41–60 and 241–260: first samples 20.5 and 120.5 ms after the origin. Arbitrary leads are rejected.',
        '- A separate negative tone renderer applies each matched tone setting before summing predictor contributions. It excludes DC, retains separate frequencies, and explicitly selects hard gates or per-block ramps.', '',
        '## Checks and their limits', '',
        'Four targeted unit checks passed. They cover v2 fit/DC/release, deliberate gate differences and DC removal, distinct-frequency crossfades plus the zero arm, and a deliberately phase-reversed predictor switch. In that artificial last check, a setting that cancels the first predictor gives +6.02 dB amplification after switching to an opposite-phase predictor. This demonstrates that fixed tuning can be invalidated in principle and that the test detects it; it is not an observed L2 failure.', '',
        'The adapter intentionally repeats a least-squares fit to expose v2 components. It is a diagnostic, not the measured timing implementation or a proposed production engine. The comparison uses already-seen clips and supports representation fidelity only. It does not establish tuning robustness, new-source accuracy, room generalization or real-time performance.', '',
        '| Source | 20 ms transitions | 120 ms transitions | Ghost frames | Maximum reference error |',
        '|---|---:|---:|---:|---:|']
    for c in r['cases']:
        lines.append(f"| {c['id']} | {c['chooser_transitions_by_horizon'][0]} | {c['chooser_transitions_by_horizon'][1]} | {c['ghost_frames']} | {max(c['max_error_to_saved'].values()):.3g} |")
    lines += ['', '## Remaining integration experiment', '',
        '1. Reproduce the stored original v2 results for the 48 existing room/source draws, with their original 30/200 ms leads, seeds and prefix/suffix split. Keep this as a baseline reproduction, separate from the new 20.5/120.5 ms component mapping.',
        '2. Freeze the new room runner, exact rendering convention and lead comparison before any candidate ear scores. Make hard-gated reference-preserving tone output and block-ramped integration output explicit separate conditions; neither silently inherits the fresh waveform pass.',
        '3. Tune each method using only the calibration prefix, keep settings fixed for the scored suffix, and include v2 settings reused on the chooser as a diagnostic. Freeze source-group aggregation, switch-coverage requirements and harm limits first. Preserve no-tone/muted rooms and include deliberately biased/no-switch controls.',
        '4. Report simulated-ear tone and whole-band attenuation, every amplification/clipping case and windows around switches. No retuning per switch. The study must disclose inadequate switching coverage rather than claiming safety from ties.', '',
        'The new room experiment has **not run**. The original room simulator and live v2 engine are unchanged. The quiet-machine timing gate also remains unresolved; no engine promotion is proposed.', '',
        '## Receipts', '',
        f"- Protocol SHA256: `{sha(COMPONENTS/'protocol.json')}`.",
        f"- Results SHA256: `{sha(COMPONENTS/'results.json')}`.",
        f'- {len(checks)} saved-result/frozen-dependency checks passed. No full test-suite rerun is claimed.',
        '- Reports contain only summaries; original media and waveform arrays remain local.', '']
    write_new(COMPONENTS/'REPORT.md', '\n'.join(lines))

    short = ('**22 October continuation:** The 72-run timing profile is complete, but all runs were contended, so the quiet-machine gate is **inconclusive**. '
             'Caching deterministic tapers preserves the forecasts and lowers observed p99, but only 1/24 cached runs is below 5 ms. '
             f'The tone-component adapter also passes its 12-source reconstruction check ({sw[0]}/{sw[1]} real chooser transitions across the two horizons). '
             'It does not yet establish fixed-tuning performance. Keep the live engine on v2; next reproduce the old room baseline and freeze/run the fixed-tuning comparison. '
             'The fresh +0.536 dB mean reference-prediction gain remains the leading accuracy result, with its existing scope limits.')
    status = '# Chooser timing and tuning integration status\n\n'+short+'\n\n'
    status += ('[Timing report](../results-selector-timing-01/REPORT.md) · '
               '[Component report](../results-selector-components-01/REPORT.md) · '
               '[Fresh accuracy result](../results-selector-fresh-01/REPORT.md)\n\n'
               'The 5 ms threshold is a reserve for the 2 kHz forecast core, not a measurement of a complete live app. '
               'Original p99 ranged 14.15–27.53 ms; cached 4.52–15.41 ms; uncached v2 comparison core 5.94–13.04 ms. '
               'The cache lowered p99 in every paired source/repetition, but did not lower the total >5 ms count. '
               'Preserve the contended diagnostic and repeat the frozen schedule in a new output location only when the machine qualifies as quiet. '
               'Do not terminate unrelated work. A smaller tracker bank would be a new accuracy candidate.\n\n'
               'The component adapter preserves the original tone frequencies, phasors, ghosts and sample-level fades. '
               'Its extra diagnostic fit is outside the measured timing core. It supports only the tested sample horizons; '
               'the old room leads of 30/200 ms are not silently treated as 20/120 ms. '
               'The existing live renderer excludes DC and ramps its output gate; the reference forecasts use hard gates and include DC. '
               'Both conventions must remain explicit in the room comparison.\n\n'
               'Four new component unit checks and the earlier three timing-adapter checks passed. '
               'The timing report independently recomputed 1,093 sample/receipt checks; the component receipt report records its own count. '
               'No full-suite claim, downloads, capture, playback, live-engine changes or physical ANC result.\n')
    write_new(ROOT/'docs/SELECTOR_TIMING_STATUS.md', status)
    for name, target in [('CLAUDE.md', 'docs/SELECTOR_TIMING_STATUS.md'),
                         ('docs/CONTINUATION_STATUS.md', 'SELECTOR_TIMING_STATUS.md'),
                         ('docs/CODEX_HANDOFF.md', 'SELECTOR_TIMING_STATUS.md')]:
        insert_after_heading(ROOT/name, '> '+short+f' Read [current timing/integration status]({target}). Earlier next-step statements below are historical.\n')
    # Update the explicitly current sections, retaining earlier dated history.
    path = ROOT/'CLAUDE.md'
    text = path.read_text(encoding='utf-8')
    marker = '## Immediate next milestone'
    before, _ = text.split(marker, 1)
    path.write_text(before+marker+'\n\n'+short+'\n\nRead `docs/SELECTOR_TIMING_STATUS.md`, `results-selector-timing-01/REPORT.md` and `results-selector-components-01/REPORT.md`. Preserve all frozen protocols, older failures and raw results.\n', encoding='utf-8')
    path = ROOT/'docs/CONTINUATION_STATUS.md'
    text = path.read_text(encoding='utf-8').replace('Updated 21 October 2026, India time.', 'Updated 22 October 2026, India time.', 1)
    lines = text.splitlines()
    lines = [('Current direction (22 Oct): '+short) if line.startswith('Current direction (21 Oct):') else line for line in lines]
    path.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    insert_after_heading(ROOT/'README.md', short+' See [the timing and integration checkpoint](docs/SELECTOR_TIMING_STATUS.md).\n')
    insert_after_heading(ROOT/'docs/SELECTOR_FRESH_STATUS.md', '> The fresh accuracy result below is unchanged. Its timing follow-on and component reconstruction are now complete; quiet-machine timing remains inconclusive and room tuning remains untested. Read [the current integration checkpoint](SELECTOR_TIMING_STATUS.md).\n')

    # Add a dated follow-on to the timing report rather than changing its earlier
    # description of what remained to be built at timing completion.
    with (TIMING/'REPORT.md').open('a', encoding='utf-8') as stream:
        stream.write('\n## Follow-on, 22 October: component reconstruction completed\n\n'+
            f'The component adapter now exists and passed all 36 method/source comparisons, including {sw[0]}/{sw[1]} actual chooser transitions. '
            'See [its report](../results-selector-components-01/REPORT.md). The room test and old-room baseline reproduction are still pending. '
            'This does not alter the timing measurements or promote the engine.\n')
    text = (TIMING/'REPORT.md').read_text(encoding='utf-8').replace('The v2 comparison also misses', 'The uncached v2 comparison also misses', 1)
    (TIMING/'REPORT.md').write_text(text, encoding='utf-8')
    path = DELIVERY/'RESULTS.md'
    text = path.read_text(encoding='utf-8')
    text = text.replace('The next independent step is to preserve each tone\'s timing and level through a predictor switch, then test fixed tuning in the existing simulated rooms.',
        f'The new tone bridge now passes reconstruction checks on all 12 recordings, including {sw[0]}/{sw[1]} predictor switches at the two tested horizons. The next step is to test fixed tuning in the existing simulated rooms.')
    text += f'\n[Component reconstruction report](<{COMPONENTS / "REPORT.md"}>)\n'
    path.write_text(text, encoding='utf-8')
    vault = Path(r'C:\Users\talk2.000\Documents\Obsidian Vault\Predictive ANC\Progress log.md')
    with vault.open('a', encoding='utf-8') as stream:
        stream.write('\n\n## 2026-10-22 — timing diagnostic and component reconstruction\n\n'+short+'\n\n'
            'The cache reduced per-run p99 by a paired median 57.2% under load, but no quiet-machine pass/failure can be assigned. '
            f'Component maximum reference discrepancy {r["maximum_forecast_error"]:.3g}; '
            f'{r["ghost_frames"]} bank ghost frames exercised. Four targeted component checks pass; 1,093 timing receipt checks pass. '
            'No audio opened; historical frozen studies and engine hashes verified unchanged. '
            'Reports: `results-selector-timing-01/REPORT.md`, `results-selector-components-01/REPORT.md`, `docs/SELECTOR_TIMING_STATUS.md`.\n')

    # Copy only research helper source, never media or reference forecast arrays.
    for name, files in [
        ('selector-timing-01', [WORK/'report_selector_timing_20261022.py', WORK/'finalize_selector_continuation_20261022.py']),
        ('selector-components-01', [ROOT/'anc_lab/selector_components.py', ROOT/'anc_lab/selector_component_study.py', ROOT/'tests/test_selector_components.py']),
    ]:
        target = ROOT/'research-tools'/name
        target.mkdir(exist_ok=False)
        hashes = {}
        for source in files:
            shutil.copy2(source, target/source.name)
            hashes[source.name] = sha(target/source.name)
        write_new(target/'SHA256.json', hashes)
    delivery = read(DELIVERY/'delivery.json')
    delivery.update(report_sha256=sha(TIMING/'REPORT.md'), results_sha256=sha(DELIVERY/'RESULTS.md'),
        component_protocol_sha256=sha(COMPONENTS/'protocol.json'),
        component_results_sha256=sha(COMPONENTS/'results.json'), component_report_sha256=sha(COMPONENTS/'REPORT.md'))
    (DELIVERY/'delivery.json').write_text(json.dumps(delivery, indent=2)+'\n', encoding='utf-8')
    bridge = {
        'dated': '2026-10-22', 'reply_to': 47,
        'timing': {'quiet_gate': 'inconclusive: all 72 runs contended',
                   'protocol_sha256': sha(TIMING/'protocol.json'),
                   'uncached_p99_ms': [14.150761, 27.533648], 'cached_p99_ms': [4.520834, 15.405946],
                   'cached_runs_under_5ms': '1/24', 'paired_median_p99_reduction_percent': 57.2274144,
                   'over_5ms_uncached_cached': [9410, 9466], 'over_10ms_uncached_cached': [2970, 661],
                   'qualification': 'No definitive quiet pass/fail. One logical CPU / BLAS one thread. Forecast core only. Windows CPU samples quantized; wall time used. v2 comparison is uncached.',
                   'parity': '72 standalone method/source/variant comparisons bit-identical; exact decisions; all timed runs also passed.',
                   'report': str(TIMING/'REPORT.md'), 'verification_checks': 1093},
        'components': {k: v for k, v in r.items() if k != 'cases'},
        'component_report': str(COMPONENTS/'REPORT.md'),
        'next': 'Component reconstruction passed. Next reproduce original 48-room v2 baseline and freeze room runner, rendering/horizon mapping, switch coverage and harm rules before comparing fixed tuning. Quiet-machine timing separately unresolved. No live engine change.',
        'review_request': 'Challenge the next room comparison: new component horizons start 20.5/120.5 ms after the newest sample, old room simulation uses 30/200 ms. Fresh forecasts include DC and hard gates; live renderer omits DC and block-ramps gates. Keep reference-preserving and ramped output conditions explicit. Any flaw in this mapping or minimum switch coverage before implementation?',
        'safety': 'No audio devices, uploads of media/forecast arrays, or engine changes. Summaries only. Fresh accuracy pass unchanged.'}
    write_new(DELIVERY/'claude-summary.json', bridge)
    print(json.dumps({'component_checks': len(checks), 'component_summary': {k:v for k,v in r.items() if k != 'cases'},
                      'delivery': str(DELIVERY), 'hashes': delivery}, indent=2))


if __name__ == '__main__':
    main()
