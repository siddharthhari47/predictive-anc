from pathlib import Path
import sys, shutil, json, re, csv

ROOT = Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
WORK = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from anc_lab import tuning_accuracy_diagnostic as d
from anc_lab import selector_headroom as h

summary = ('**26 October tuning diagnosis:** Claude review #55 is completed on all 78 eligible v2 tones. '
           'Six of 40 kept tones make their individual auditory band louder during tuning. Ten of 38 muted tones '
           'have at least 1 dB of potential prefix benefit, but only three had already found such a setting. '
           'Final checks can also mistake changing background sound for an anti-hum effect. Original tuning reproduces '
           'in all 37 eligible rooms. Keep v2 live; next isolate better search from better comparison evidence, '
           'before widening the menu. These are seen-data simulated-ear diagnostics; quiet-machine timing and physical ANC remain unvalidated.')

d.verified()
updated = []
for name in ['CLAUDE.md', 'README.md', 'docs/CONTINUATION_STATUS.md', 'docs/CODEX_HANDOFF.md',
             'docs/SELECTOR_TIMING_STATUS.md', 'docs/SELECTOR_COMPATIBILITY_STATUS.md']:
    path = ROOT/name
    text = path.read_text(encoding='utf-8')
    assert '**26 October tuning diagnosis:**' not in text
    target = 'docs/TUNING_ACCURACY_STATUS.md' if '/' not in name else 'TUNING_ACCURACY_STATUS.md'
    first, rest = text.split('\n', 1)
    text = first+'\n\n> '+summary+f' Read [current tuning diagnosis]({target}). Earlier next-step statements below are historical.\n'+rest
    if name == 'CLAUDE.md':
        index = text.index('## Immediate next milestone')
        text = text[:index] + ('## Immediate next milestone\n\n'+summary+
            '\n\nRead `docs/TUNING_ACCURACY_STATUS.md`, `results-tuning-accuracy-01/REPORT.md` '
            'and `docs/TUNING_DIAGNOSTIC_NEXT.md`. The preceding compatibility and room reports remain unchanged. '
            'Preserve all frozen protocols, older failures and raw results.\n')
    path.write_text(text, encoding='utf-8')
    updated.append(name)

log = Path(r'C:\Users\talk2.000\Documents\Obsidian Vault\Predictive ANC\Progress log.md')
assert '2026-10-26 — tuning accuracy and acceptance diagnosis' not in log.read_text(encoding='utf-8')
with log.open('a', encoding='utf-8') as f:
    f.write('\n\n## 2026-10-26 — tuning accuracy and acceptance diagnosis\n\n'+summary+'\n\n'
            'Median phase error: 26.7 degrees overall, 9.5 kept, 46.0 muted. At 1 dB, six of ten muted oracle opportunities '
            'also persist later; two of three rejected useful settings persist. The compressor false keep is traced to the exact noise draws; '
            'a microwave false mute is traced to a 6.90 dB background rise, and a locomotive example shows the issue without looping. '
            'Ten targeted tests, 1,681 original tuning parity fields and 2,803 numerical audit checks pass (max 5.68e-14). '
            'A separate tiny-tail probability repair changes no decisions or audio scores. No audio device, new model or previous frozen result changed. '
            'Report: `results-tuning-accuracy-01/REPORT.md`; next proposal: `docs/TUNING_DIAGNOSTIC_NEXT.md`.\n')

snapshot = ROOT/'research-tools/tuning-accuracy-01'
snapshot.mkdir(exist_ok=False)
files = ['anc_lab/tuning_accuracy_diagnostic.py', 'tests/test_tuning_accuracy_diagnostic.py',
         'docs/TUNING_ACCURACY_DIAGNOSTIC.md', 'docs/TUNING_ACCURACY_STATUS.md', 'docs/TUNING_DIAGNOSTIC_NEXT.md']
for name in files:
    dest = snapshot/name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT/name, dest)
for name in ['analyze_tuning_accuracy_20261026.py', 'report_tuning_accuracy_20261026.py', 'finalize_tuning_accuracy_20261026.py']:
    dest = snapshot/'tools'/name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(WORK/name, dest)
(snapshot/'README.md').write_text('''# Tuning diagnosis source snapshot

26 October 2026. Research helpers and protocol/status documents for `results-tuning-accuracy-01`.
The main project supplies frozen native imports and cached room inputs; this is a source snapshot, not a standalone new ANC app.
No raw audio, reference arrays, simulated-ear waveforms or complex ratio arrays are included.
The diagnostic output directory already exists and must not be overwritten or rerun in place.
The reporting-only probability correction preserves original raw results.
''', encoding='utf-8')
h.write_new(snapshot/'manifest.json', {str(x.relative_to(snapshot)): h.sha(x) for x in snapshot.rglob('*') if x.is_file()})

out = d.STUDY
report_receipt = h.read(out/'report-receipt.json')
export = Path(report_receipt['export'])
for name, digest in report_receipt['export_sha256'].items():
    assert h.sha(export/name) == digest
for name, expected in [('tone-diagnostics.csv', 78), ('check-trials.csv', 156), ('check-probabilities-stable.csv', 156)]:
    with (out/name).open(encoding='utf-8', newline='') as f:
        assert len(list(csv.DictReader(f))) == expected
for target in re.findall(r'\]\(([^)]+)\)', (out/'REPORT.md').read_text(encoding='utf-8')):
    assert Path(target).exists(), target
manifest = h.read(snapshot/'manifest.json')
for name, digest in manifest.items():
    assert h.sha(snapshot/name) == digest
d.verified()
h.write_new(out/'finalization.json', {'created_utc': d.now(), 'status': 'complete',
    'current_docs_updated': updated+['docs/TUNING_ACCURACY_STATUS.md', 'docs/TUNING_DIAGNOSTIC_NEXT.md'],
    'project_log_updated': str(log), 'assistant_memory_modified': False,
    'research_snapshot': str(snapshot), 'snapshot_files': len(manifest),
    'export_hashes_verified': True, 'report_local_links_verified': True,
    'csv_counts': {'tones': 78, 'check_pairs': 156, 'stable_probabilities': 156},
    'targeted_tests': {'count': 10, 'result': 'passed', 'observed_runtime_seconds': .108,
                       'command': 'python -m unittest tests.test_tuning_accuracy_diagnostic tests.test_selector_compatibility -v'},
    'frozen_protocol_and_live_sources_unchanged': True,
    'live_engine_sha256': h.sha(ROOT/'anc_lab/antihum.py'),
    'previous_room_results_sha256': h.sha(ROOT/'results-selector-tuning-01/results.json')})
print(json.dumps({'status': 'complete', 'snapshot_files': len(manifest), 'export': str(export),
                  'live_engine_sha256': h.sha(ROOT/'anc_lab/antihum.py')}))
