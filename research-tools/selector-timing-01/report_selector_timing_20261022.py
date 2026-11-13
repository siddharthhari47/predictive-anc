"""Verify and report the completed frozen timing study; never replay forecasts."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil

import numpy as np

ROOT = Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
STUDY = ROOT / 'results-selector-timing-01'
DELIVERY = Path(r'C:\Users\talk2.000\Documents\Codex\2026-10-15\referenced-chatgpt-conversation-this-is-an\outputs\selector-timing-20261022')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        if isinstance(value, str):
            stream.write(value)
        else:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write('\n')


def stats(x):
    return dict(count=len(x), mean=float(np.mean(x)), p50=float(np.percentile(x, 50)),
                p95=float(np.percentile(x, 95)), p99=float(np.percentile(x, 99)),
                max=float(np.max(x)), over_5ms=int(np.sum(x > 5)),
                over_10ms=int(np.sum(x > 10)))


def main():
    result = read(STUDY / 'timing/results.json')
    protocol = read(STUDY / 'protocol.json')
    summary = read(STUDY / 'SUMMARY.json')
    checks = []

    def check(label, condition):
        assert condition, label
        checks.append(label)

    check('protocol hash', sha(STUDY / 'protocol.json') == read(STUDY / 'frozen.json')['sha256'])
    for name, digest in protocol['code_sha256'].items():
        check('frozen code ' + name, sha(ROOT / name) == digest)
    check('unchanged fresh scores', sha(ROOT / 'results-selector-fresh-01/test/results.json') == protocol['fresh_results_sha256'])
    check('unchanged fresh protocol', sha(ROOT / 'results-selector-fresh-01/protocol.json') == protocol['fresh_protocol_sha256'])
    check('summary duplicate', summary == result['summary'])
    rows = result['runs']
    variants = ('original', 'cached_dpss', 'v2_only')
    expected_keys = {(e['id'], v, r) for e in protocol['cases'] for v in variants for r in (1, 2)}
    check('exact 72 unique scheduled runs', len(rows) == len(expected_keys) == 72 and
          {(r['id'], r['variant'], r['repetition']) for r in rows} == expected_keys)
    samples, receipts, cpu_samples = {}, {}, []
    for row in rows:
        name = f"{row['id']}-r{row['repetition']}-{row['variant']}"
        check(name + ' parity receipt', row['parity_passed'])
        path = ROOT / row['sample_path']
        check(name + ' sample hash', sha(path) == row['sample_sha256'])
        check(name + ' row receipt', read(path.with_suffix('.json')) == row)
        receipts[str(path.relative_to(ROOT))] = sha(path)
        receipts[str(path.with_suffix('.json').relative_to(ROOT))] = sha(path.with_suffix('.json'))
        with np.load(path) as a:
            check(name + ' origins', np.array_equal(a['origins'], np.arange(1000, 60000, 20)))
            check(name + ' finite samples', all(np.isfinite(a[k]).all() for k in ('wall_ms', 'thread_cpu_ms', 'parts_ms')))
            for field in ('wall_ms', 'thread_cpu_ms'):
                check(name + ' recomputed ' + field, stats(a[field]) == row[field])
            check(name + ' late stats', stats(a['wall_ms'][a['origins'] >= 30000]) == row['late_wall_ms'])
            for j, part in enumerate(('bank', 'v2_selector', 'forecast', 'gate', 'mix')):
                check(name + ' part ' + part, stats(a['parts_ms'][:, j]) == row['parts_ms'][part])
            samples[(row['id'], row['variant'], row['repetition'])] = a['wall_ms'].copy()
            cpu_samples.extend(a['thread_cpu_ms'].tolist())
        env = result['environment']
        check(name + ' quiet rule', row['quiet_qualified'] ==
              bool(env['quiet_preflight'] and row['estimated_background_cpu_percent'] <= 5))
    parity = read(STUDY / 'parity/complete.json')
    check('parity totals', parity['passed'] and parity['sources'] == 12 and
          parity['source_variant_method_comparisons'] == 72 and parity['exact_decision_arrays'] == 24)
    max_abs = 0.0
    for entry in protocol['cases']:
        row = read(STUDY / 'parity' / (entry['id'] + '.json'))
        check(entry['id'] + ' standalone parity', row['passed'] and row['origins'] == 2950)
        for c in row['checks']:
            check(entry['id'] + ' exact choices ' + str(c['cache']), c['exact_choices'])
            max_abs = max(max_abs, *c['max_abs_error'].values())
    comparisons = []
    for sid in [e['id'] for e in protocol['cases']]:
        for rep in (1, 2):
            original = next(r for r in rows if (r['id'], r['variant'], r['repetition']) == (sid, 'original', rep))
            cache = next(r for r in rows if (r['id'], r['variant'], r['repetition']) == (sid, 'cached_dpss', rep))
            comparisons.append({'id': sid, 'repetition': rep, 'original_p99_ms': original['wall_ms']['p99'],
                                'cached_p99_ms': cache['wall_ms']['p99'],
                                'reduction_percent': 100 * (1 - cache['wall_ms']['p99'] / original['wall_ms']['p99'])})
    aggregate = {}
    for v in variants:
        rr = [r for r in rows if r['variant'] == v]
        quiet = all(r['quiet_qualified'] for r in rr)
        budget = all(r['wall_ms']['p99'] < 5 for r in rr)
        decision = ('pass_forecast_core_budget' if budget else 'fail_forecast_core_budget') if quiet else 'inconclusive_quiet_machine_gate_contended_diagnostic'
        check(v + ' aggregate decision', summary[v]['decision'] == decision)
        check(v + ' counts', summary[v]['total_blocks'] == sum(r['wall_ms']['count'] for r in rr) == 70800)
        check(v + ' worst p99', summary[v]['worst_p99_ms'] == max(r['wall_ms']['p99'] for r in rr))
        check(v + ' misses', summary[v]['over_10ms_blocks'] == sum(r['wall_ms']['over_10ms'] for r in rr))
        aggregate[v] = {
            'runs': len(rr), 'p99_range_ms': [min(r['wall_ms']['p99'] for r in rr), max(r['wall_ms']['p99'] for r in rr)],
            'median_run_p99_ms': float(np.median([r['wall_ms']['p99'] for r in rr])),
            'runs_under_5ms': sum(r['wall_ms']['p99'] < 5 for r in rr),
            'maximum_block_ms': max(r['wall_ms']['max'] for r in rr),
            'over_5ms_blocks': sum(r['wall_ms']['over_5ms'] for r in rr),
            'over_10ms_blocks': sum(r['wall_ms']['over_10ms'] for r in rr),
            'late_p99_range_ms': [min(r['late_wall_ms']['p99'] for r in rr), max(r['late_wall_ms']['p99'] for r in rr)],
            'all_quiet': quiet, 'decision': decision,
        }
    engine_digest = sha(ROOT / 'anc_lab/antihum.py')
    check('live engine unchanged', engine_digest == '599bd571cf75c3c18719540e7c32dd0a1f67f3fca6c761273bce2ce955d01c23')
    cpu = np.array(cpu_samples)
    env = result['environment']
    verification = {
        'created_utc': datetime.now(timezone.utc).isoformat(), 'passed': True, 'checks': len(checks),
        'check_names': checks, 'protocol_sha256': sha(STUDY / 'protocol.json'),
        'timing_results_sha256': sha(STUDY / 'timing/results.json'),
        'maximum_standalone_parity_absolute_error': max_abs,
        'source_repetition_cache_comparisons': comparisons, 'aggregate': aggregate,
        'estimated_background_cpu_range_percent': [min(r['estimated_background_cpu_percent'] for r in rows), max(r['estimated_background_cpu_percent'] for r in rows)],
        'thread_cpu_zero_fraction': float(np.mean(cpu == 0)),
        'thread_cpu_nonzero_values_ms': sorted(set(cpu[cpu > 0].tolist())),
        'live_engine_sha256': engine_digest, 'sample_receipts_sha256': receipts,
    }
    write_new(STUDY / 'VERIFICATION.json', verification)
    names = {'original': 'Uncached chooser', 'cached_dpss': 'Equivalent cached chooser', 'v2_only': 'v2 comparison core'}
    lines = ['# Chooser timing: useful speedup, quiet-machine gate unresolved', '',
             '22 October 2026. Offline engineering profile on saved, already-seen reference signals. No audio device was opened. The live engine remains v2.', '',
             '**Decision: inconclusive under the frozen quiet-machine rule.** All three preflight windows were busy, so none of the 72 runs qualifies for a quiet-machine verdict. Both chooser versions miss the observed 5 ms p99 budget on this loaded machine. This is evidence of a deployment risk under load, not a definitive quiet-machine failure.', '',
             f'The bounded streaming implementation and the DPSS cache reproduce all saved forecasts on the 12 specified recordings (largest absolute difference {max_abs:g}); all 24 standalone chooser-decision arrays match exactly. Every timed run also passed forecast parity. The cache changes repeated mathematical work, not the prediction rule.', '',
             '## Observed processing times', '',
             'Each row covers 24 runs (12 sources × two repetitions), 70,800 measured 10 ms blocks. A p99 means 99% of measured blocks completed within that time; it is not the maximum or a deadline guarantee. The criterion requires **every** run p99 below 5 ms and quiet qualification.', '',
             '| Forecast core | Per-run p99 range (ms) | Median run p99 (ms) | Runs below 5 ms | Blocks above 5 ms | Blocks above 10 ms | Slowest block (ms) |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for v in variants:
        a = aggregate[v]
        lines.append(f"| {names[v]} | {a['p99_range_ms'][0]:.2f}–{a['p99_range_ms'][1]:.2f} | {a['median_run_p99_ms']:.2f} | {a['runs_under_5ms']}/24 | {a['over_5ms_blocks']:,}/70,800 | {a['over_10ms_blocks']:,}/70,800 | {a['maximum_block_ms']:.2f} |")
    reduction = np.array([r['reduction_percent'] for r in comparisons])
    lines += ['', f'The cache lowered p99 in {int(np.sum(reduction > 0))}/24 source/repetition comparisons, with a median relative reduction of {np.median(reduction):.1f}%. These are sequential measurements under changing contention, not an isolated causal estimate of the optimization. The v2 comparison also misses the observed budget; it uses this adapter and is not a measurement of the complete current app.', '',
              'The cache did **not** reduce the number of blocks above the stricter 5 ms reserve threshold in this run (9,466 versus 9,410). The improved p99 and >10 ms count therefore do not imply fewer misses at every threshold.', '',
              '![Per-source timing under load](timing-p99.png)', '',
              'The plot and table below retain the worse repetition for each source; no favorable interval was selected.', '',
              '| Source | Uncached p99 (ms) | Cached p99 (ms) | v2 core p99 (ms) |', '|---|---:|---:|---:|']
    for entry in protocol['cases']:
        vals = [max(r['wall_ms']['p99'] for r in rows if r['id'] == entry['id'] and r['variant'] == v) for v in variants]
        lines.append(f"| {entry['id']}: {entry['title'].replace('|', '/')} | " + ' | '.join(f'{x:.2f}' for x in vals) + ' |')
    preflight = ', '.join(f"{w['system_mean_percent']:.2f}%" for w in env['preflight_windows'])
    bg = verification['estimated_background_cpu_range_percent']
    lines += ['', '## Measurement scope and limits', '',
              f"- Windows, Python {env['python']}, {env['physical_cores']} physical cores / {env['logical_cpus']} logical processors. Timed process restricted to logical processor {env['selected_logical_cpu']}; numerical-library threads limited to one. Affinity restored by the benchmark's finally block.",
              f'- Preflight whole-machine CPU: {preflight}, each above the 5% limit. During-run estimated background CPU ranged {bg[0]:.2f}–{bg[1]:.2f}%. The Windows aggregate estimate is conservative/approximate; the preflight alone makes every run unqualified.',
              '- Includes both independent detectors, both 20/120 ms forecast horizons, matured-error gates, filtering/error history, chooser decisions and sample crossfades. Includes startup and detector-update blocks; late-suffix summaries remain in the raw report.',
              '- Excludes decoding, normalization, resampling, UI, device-rate synthesis, audio callbacks, hardware transport, and ear acoustics. The reserved half-block does not measure these costs. No claim of complete app scheduling performance.',
              f"- Windows thread CPU accounting is coarse: {100 * verification['thread_cpu_zero_fraction']:.1f}% of block samples are zero; nonzero values occur in 15.625 ms increments. Use high-resolution wall time for the gate. CPU-time p99 is not a valid per-block execution-cost estimate here.",
              '- Timing instrumentation has overhead. Part-wise p99 values are not additive. Sequential source repetitions share a changing CPU environment; this is one machine, one schedule, a bounded selection of seen recordings.',
              '- The scoped DPSS cache is a research implementation that temporarily replaces the SciPy function and restores it afterward. A thread-safe production cache/integration would require separate checks.', '',
              '## Tuning integration: specific missing check', '',
              'The existing tuning simulator uses per-tone complex amplitudes; the fresh chooser emits mixed waveform blocks. A faithful adapter must carry the original tone frequencies and amplitudes, per-tone release/ghost components, gates and sample-level chooser fades. It must reconstruct the tested 20/120 ms forecasts before any room result is interpreted. The older room simulator uses 30/200 ms leads, so that mapping must be explicit.', '',
              'There is also a renderer mismatch to resolve explicitly: the live v2 renderer excludes the fitted DC term and ramps its gate across a block, while the fresh reference forecast gates the entire block (including DC). Reusing the fresh prediction score as proof of equivalent tuned output would be incorrect. No tuning-switch result is claimed yet.', '',
              'The prepared room plan preserves 48 existing room/source draws, prefix-only tuning and fixed suffix settings. It includes simulated-ear amplification, clipping and switch-window checks plus a deliberately biased switching control. Its adapter, mapping, coverage and harm rules still need to be frozen before execution.', '',
              '## Next action', '',
              'Retain the fresh accuracy pass and current live v2 engine. Keep this contended diagnostic intact. A separate, newly recorded repetition under an actually quiet CPU environment is needed for the quiet-machine decision; do not stop unrelated work. The equivalent cache is the first optimization to retain. Any smaller/rotating tracker bank changes the candidate and needs new accuracy validation.', '',
              'The independent work available now is the component/renderer parity adapter and the fixed-tuning simulation. Even passing both engineering checks would support a proposal for an engine change, not physical ANC. Real ear-level evidence still needs measured paths, timing and a calibrated low-output near-ear fixture.', '',
              '## Reproducibility', '',
              f"- Frozen protocol SHA256: `{sha(STUDY / 'protocol.json')}`.",
              f"- Saved timing results SHA256: `{sha(STUDY / 'timing/results.json')}`.",
              f'- {len(checks)} report/receipt checks passed, including recomputation from every timing array and verification of all frozen code. Three targeted streaming/cache unit checks passed before freezing; no new full-suite claim.',
              '- `protocol.json`, `frozen.json`, `parity/`, `timing/`, `SUMMARY.json` and `VERIFICATION.json` preserve the schedule, samples, outcomes and receipts. Reference audio/forecast arrays remain local.', '']
    write_new(STUDY / 'REPORT.md', '\n'.join(lines))

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 6), layout='constrained')
    styles = [('original', '#ae614b', 'o', -.18), ('cached_dpss', '#007e78', 's', 0), ('v2_only', '#66758a', '^', .18)]
    ids = [e['id'] for e in protocol['cases']]
    for v, color, marker, offset in styles:
        ys = [max(r['wall_ms']['p99'] for r in rows if r['id'] == sid and r['variant'] == v) for sid in ids]
        ax.scatter(np.arange(len(ids)) + offset, ys, c=color, marker=marker, s=50, label=names[v])
    ax.axhline(5, color='#a42940', linestyle='--', linewidth=1.4, label='Frozen 5 ms budget')
    ax.set_xticks(np.arange(len(ids)), [x.replace('fresh-', '') for x in ids])
    ax.set(xlabel='Fixed recording ID (fresh-)', ylabel='Worse repetition p99, milliseconds', ylim=(0, None))
    ax.grid(axis='y', alpha=.2)
    ax.legend(loc='upper right', frameon=False)
    ax.set_title('Caching reduces observed time; quiet-machine decision remains unresolved\nSingle logical CPU, busy computer; 10 ms input blocks', loc='left', fontsize=13)
    fig.savefig(STUDY / 'timing-p99.png', dpi=160)
    plt.close(fig)

    DELIVERY.mkdir(parents=True, exist_ok=False)
    a, b = aggregate['original'], aggregate['cached_dpss']
    short = f'''# Chooser speed check

The caching change preserves the forecasts and makes processing faster. **The quiet-computer test remains unresolved:** every measurement was taken while other work kept the computer busy.

Across 24 runs per version, the 99th-percentile block time was **{a['p99_range_ms'][0]:.1f}–{a['p99_range_ms'][1]:.1f} ms** before caching and **{b['p99_range_ms'][0]:.1f}–{b['p99_range_ms'][1]:.1f} ms** after. The written target is below **5 ms in every run**. Only {b['runs_under_5ms']}/24 cached runs were under that target, and none qualified as a quiet-computer measurement.

Both implementations matched the saved predictions on all 12 selected recordings; every chooser decision matched too. The original fresh-recording accuracy result remains valid. This speed check measures the prediction core, not the whole live app.

![Processing times under load](timing-p99.png)

The next independent step is to preserve each tone's timing and level through a predictor switch, then test fixed tuning in the existing simulated rooms. The current app and the offline forecasts use slightly different gate rendering, which must be accounted for before those results can be compared.

The live app still uses v2. No recording or playback was started, and no physical noise cancellation is claimed.

[Full technical report](<{STUDY / 'REPORT.md'}>) · [Verification](<{STUDY / 'VERIFICATION.json'}>)
'''
    write_new(DELIVERY / 'RESULTS.md', short)
    shutil.copy2(STUDY / 'timing-p99.png', DELIVERY / 'timing-p99.png')
    write_new(DELIVERY / 'delivery.json', {'protocol_sha256': sha(STUDY / 'protocol.json'),
              'report_sha256': sha(STUDY / 'REPORT.md'), 'results_sha256': sha(DELIVERY / 'RESULTS.md'),
              'verification_sha256': sha(STUDY / 'VERIFICATION.json'), 'checks': len(checks)})
    print(json.dumps({'passed': True, 'checks': len(checks), 'aggregate': aggregate,
                     'max_parity_error': max_abs, 'cache_median_reduction_percent': float(np.median(reduction)),
                     'delivery': str(DELIVERY)}, indent=2))


if __name__ == '__main__':
    main()
