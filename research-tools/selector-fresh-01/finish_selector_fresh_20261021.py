"""Publish local reports and project handoff after the frozen run and verification."""
from pathlib import Path
from datetime import datetime, timezone
import json, re, shutil, sys
ROOT=Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
WORK=Path(__file__).parent
OUT=WORK.parent/'outputs/selector-fresh-20261021'
sys.path.insert(0,str(ROOT))
from anc_lab import selector_headroom as h
S=ROOT/'results-selector-fresh-01'

def write(path,text):path.write_text(text+'\n',encoding='utf-8')
def replace_top_note(path,note):
    text=path.read_text(encoding='utf-8')
    text=re.sub(r'(?m)^> .*?(?:\n\n)',note+'\n\n',text,count=1)
    write(path,text.rstrip())

def main():
    s=h.read(S/'SUMMARY.json');v=h.read(S/'VERIFICATION.json');assert v['all_passed']
    c=s['methods']['causal_L2'];b=s['methods']['v2_gated']
    result=h.read(S/'test/results.json');manifest=h.read(S/'download/manifest.json')
    ci=c['20']['mean_bootstrap95']
    ci_text='unavailable' if ci is None else f'{ci[0]:+.3f} to {ci[1]:+.3f} dB'
    mean='unavailable' if c['20']['mean_db'] is None else f'{c["20"]["mean_db"]:+.3f} dB'
    decision=s['decision'].replace('_',' ')
    if s['decision']=='pass_frozen_offline_criteria':
        action='Retain unchanged L2 as the leading offline chooser candidate. Next, measure its compute deadlines and tail latency without audio, with output parity first. Engine integration still requires timing and acoustic-path validation.'
    elif s['decision']=='inconclusive_insufficient_eligible_sources':
        action='Keep L2 as an unconfirmed development candidate and keep v2 in the engine. Diagnose the cohort shortfall and any harms from these now-seen records; a later confirmation needs a separately frozen, better-targeted fresh cohort. Do not top up or reinterpret this run as a pass.'
    else:
        action='Keep v2 in the engine. Use the saved fresh-test arrays as development data to diagnose the unmet criteria, beginning with any strong-hum regressions or extra band amplification. Do not retune against this set and call it confirmation.'
    outcome=f'The fresh L2 test is complete: **{decision}**. {s["usable_sources"]}/40 sources were scored, {s["tonal_sources"]} with reference tones. Mean paired gain over v2 at 20 ms: **{mean}**, 95% source-bootstrap interval **{ci_text}**.'
    current=f'> **Latest completed result, 21 Oct:** {outcome} {action} Read [fresh-test status](SELECTOR_FRESH_STATUS.md). Earlier pending-test and median-stop statements below are historical.'
    for name in ('CONTINUATION_STATUS.md','CODEX_HANDOFF.md','SELECTOR_HEADROOM.md','NEXT_OFFLINE_MILESTONE.md','JOINT_SETTING_DIAGNOSIS.md'):
        replace_top_note(ROOT/'docs'/name,current)
    path=ROOT/'CLAUDE.md'
    replace_top_note(path,current.replace('(SELECTOR_FRESH_STATUS.md)','(docs/SELECTOR_FRESH_STATUS.md)'))
    text=path.read_text(encoding='utf-8')
    text=text.replace('Latest verified state (21 Oct 2026, Codex): the selector-headroom audit',
                      'Historical median-based audit state (21 Oct 2026, Codex; superseded for forward decisions above): the selector-headroom audit')
    text=re.sub(r'## Immediate next milestone\n.*',
        '## Immediate next milestone\n\n'+outcome+'\n\n'+action+'\n\nRead `docs/SELECTOR_FRESH_STATUS.md` and `results-selector-fresh-01/REPORT.md`. Preserve both operational amendments, original protocols and all failed results. Necessary downloads remain authorized. No live audio or engine promotion occurred.\n',text,flags=re.S)
    write(path,text.rstrip())
    path=ROOT/'docs/CONTINUATION_STATUS.md'
    text=path.read_text(encoding='utf-8')
    text=re.sub(r'Current direction \(21 Oct\):.*?\n\n','Current direction (21 Oct): '+outcome+' '+action+'\n\n',text,count=1,flags=re.S)
    write(path,text.rstrip())
    status=ROOT/'docs/SELECTOR_FRESH_STATUS.md'
    old=status.read_text(encoding='utf-8')
    if '## Acquisition preparation history' not in old:
        write(status,'# Fresh selector test status\n\n'+outcome+'\n\n'+action+
          '\n\n[Completed report](../results-selector-fresh-01/REPORT.md) · [Saved numerical summary](../results-selector-fresh-01/SUMMARY.json) · [Verification](../results-selector-fresh-01/VERIFICATION.json).\n\n'
          'The original protocol and two operational amendments preceded scoring. The unchanged chooser was tested once. All raw media and arrays remain local; no physical ANC claim.\n\n## Acquisition preparation history\n\n'+old.split('\n',1)[1].lstrip())
    readme=ROOT/'README.md';text=readme.read_text(encoding='utf-8')
    text=text.replace('# Predictive ANC lab\n','# Predictive ANC lab\n\n**Latest research, 21 October 2026:** '+outcome+' See [fresh-test report](results-selector-fresh-01/REPORT.md).\n',1)
    text=text.replace('Read CLAUDE.md, docs/CLAUDE_HANDOFF.md and CLAUDE_START_PROMPT.md. Continue the existing project from those files, beginning with verification and the proposed automatic tone-count/confidence milestone. Keep the first continuation offline.',
        'Read CLAUDE.md, docs/SELECTOR_FRESH_STATUS.md and docs/CONTINUATION_STATUS.md. Continue the existing project from the latest completed result and its stated next step. Keep the continuation offline.')
    write(readme,text.rstrip())
    archive=ROOT/'research-tools/selector-fresh-01';archive.mkdir(exist_ok=False)
    names=['discover_selector_sources_20261021.py','freeze_selector_fresh_20261021.py',
       'download_selector_fresh_20261021.py','prepare_selector_acquisition_amendment.py',
       'download_selector_derivatives_20261021.py','freeze_selector_decoder_amendment.py',
       'reassess_selector_20261021.py','report_selector_fresh_20261021.py','finish_selector_fresh_20261021.py']
    for name in names:shutil.copy2(WORK/name,archive/name)
    h.write_new(archive/'SHA256.json',{name:h.sha(archive/name) for name in names})
    write(archive/'README.md','# Fresh selector test execution records\n\nExact copies of helpers used on 21 October 2026. The scientific runner is `anc_lab/selector_fresh_study.py`; `results-selector-fresh-01/` holds the original protocol, two pre-scoring operational amendments, download receipts, one completed test and reports.\n\nThe original download was stopped when Commons requested smaller representations. That history is retained. The source list, candidate and analysis endpoints were not changed. The metadata-routing fix is documented separately with the original runner preserved. Eighteen targeted checks passed; no full-suite claim.\n\nThese helpers retain absolute local paths and write-new safeguards. They are execution records, not user terminal instructions. Do not remove output folders to rerun them. A new experiment needs a new protocol and destination. Raw media, decoded audio and forecast arrays stay local and are not included here.')
    OUT.mkdir(exist_ok=False)
    for name in ('SUMMARY.json','VERIFICATION.json','paired-gains.png'):
        if (S/name).exists():shutil.copy2(S/name,OUT/name)
    combined=sum(c[str(t)]['band_boost_cases'] for t in (20,120));basecombined=sum(b[str(t)]['band_boost_cases'] for t in (20,120))
    prose=['# Fresh chooser test — 21 October 2026','',outcome,'',
        'Claude’s correction was right: the old audit’s paired median hid gains on a minority of recordings. Its +0.750 dB mean was promising development evidence, so this test used new sources and a mean-based rule written before scoring.',
        '',f'- Strong-hum losses greater than 1 dB at 20 ms: {len(c["20"]["strong_losses_over_1db"])}.',
        f'- Source-by-horizon band-amplification cases: {combined} for the chooser versus {basecombined} for v2.',
        f'- At 120 ms, mean paired gain: {c["120"]["mean_db"]:+.3f} dB; worst paired loss/gain: {c["120"]["minimum_db"]:+.3f} dB.' if s['tonal_sources'] else '- No tonal sources qualified.',
        '',action,'',
        'The download policy changed before scoring because Wikimedia rejected large originals and requested smaller copies. Official representations were selected uniformly, leaving two sources unavailable. A separate pre-scoring fix correctly routed Ogg videos through the specified decoder. These deviations are preserved alongside the original freeze. No candidate or statistical threshold was changed.',
        '',f'Validation: 18 targeted checks passed; {len(v["checks"])} saved-result/receipt checks passed. No full-suite rerun is claimed.',
        '',f'[Full source-by-source report]({(S/"REPORT.md").as_posix()}) · [Project status]({(ROOT/"docs/SELECTOR_FRESH_STATUS.md").as_posix()})',
        '', '**All results measure prediction at a recording microphone. They do not establish quieter sound at an ear. The live engine remains v2.**']
    write(OUT/'RESULTS.md','\n'.join(prose))
    obsidian=Path(r'C:\Users\talk2.000\Documents\Obsidian Vault\Predictive ANC\Progress log.md')
    with obsidian.open('a',encoding='utf-8') as stream:
        stream.write('\n\n## 2026-10-21 — corrected selector interpretation and completed fresh test\n\n'+outcome+'\n\n'+action+
            '\n\nClaude #43 correctly identified the median endpoint’s insensitivity to ties. That reinterpretation was post-hoc; the original audit is preserved. This new run used a prewritten mean endpoint, unchanged L2, fixed source identities, and two pre-scoring acquisition/decoder amendments. Two media representations unavailable, no replacement. Eighteen targeted checks passed; no full-suite rerun. Reference prediction only; no physical audio or engine change.\n\nReport: `'+str(S/'REPORT.md')+'`. User-facing copy: `'+str(OUT/'RESULTS.md')+'`.\n')
    h.write_new(S/'delivery.json',{'completed_utc':datetime.now(timezone.utc).isoformat(),
        'output_directory':str(OUT),'research_helpers':str(archive),'report_sha256':h.sha(S/'REPORT.md'),
        'user_report_sha256':h.sha(OUT/'RESULTS.md'),'next_step':action})
    print(json.dumps({'output':str(OUT/'RESULTS.md'),'decision':decision,'next':action},indent=2))

if __name__=='__main__':main()
