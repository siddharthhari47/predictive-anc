"""Record the completed review-53 diagnostics and narrow the next work."""
from pathlib import Path
from datetime import datetime,timezone
import sys,re,json,shutil

ROOT=Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
WORK=Path(r'C:\Users\talk2.000\Documents\Codex\2026-10-15\referenced-chatgpt-conversation-this-is-an')
sys.path.insert(0,str(ROOT))
from anc_lab import selector_headroom as h
from anc_lab import selector_compatibility as study
OUT=study.STUDY

SUMMARY='**24 October follow-up diagnostics:** Claude review #53 is tested. The compressor supports a bad accepted tuning setting: best v2/bank phases differ by 4.37 degrees, while accepted v2 is 152.58 degrees from its own prefix optimum. Of 72 primary rooms, 34 had intermittent detections below the menu rule, one had no detection, 11 were fully muted by the final listening check, and 26 kept active settings. Direct comparison of all 78 available recordings finds substantial predictor disagreement on real audio; fixed tuning cannot be assumed interchangeable. Prior room/fresh results remain unchanged. Keep v2 live; next diagnose menu eligibility and tuning acceptance, not a larger switch cohort. Quiet-machine timing and physical ANC remain unvalidated.'


def new(path,text):
    with path.open('x',encoding='utf-8',newline='\n') as f:f.write(text.rstrip()+'\n')


def main():
    study.verified();assert h.read(OUT/'verification.json')['passed']
    before={}
    for name in ['CLAUDE.md','README.md','docs/CONTINUATION_STATUS.md','docs/CODEX_HANDOFF.md','docs/SELECTOR_TIMING_STATUS.md']:
        path=ROOT/name;before[name]=h.sha(path);text=path.read_text(encoding='utf-8')
        text,n=re.subn(r'\*\*24 October continuation:\*\* All 72 fixed-tuning rooms[^\n]*?not an ear-attenuation claim\.',SUMMARY,text,
                       count=2 if name in ('CLAUDE.md','docs/CONTINUATION_STATUS.md') else 1)
        assert n>=1,(name,n)
        text=text.replace('current room-test status](docs/SELECTOR_ROOM_STATUS.md)','current compatibility status](docs/SELECTOR_COMPATIBILITY_STATUS.md)')
        text=text.replace('current room-test status](SELECTOR_ROOM_STATUS.md)','current compatibility status](SELECTOR_COMPATIBILITY_STATUS.md)')
        text=text.replace('the room-test checkpoint](docs/SELECTOR_ROOM_STATUS.md)','the compatibility checkpoint](docs/SELECTOR_COMPATIBILITY_STATUS.md)')
        if name=='CLAUDE.md':
            text=text.replace('Read `docs/SELECTOR_ROOM_STATUS.md`, `results-selector-tuning-01/REPORT.md` and `docs/SELECTOR_ROOM_NEXT.md`.',
                'Read `docs/SELECTOR_COMPATIBILITY_STATUS.md`, `results-selector-compatibility-01/REPORT.md` and `docs/TUNING_DIAGNOSTIC_NEXT.md`. The completed room test remains in `results-selector-tuning-01/REPORT.md`.')
        if name=='README.md':text=text.replace('Read CLAUDE.md, docs/SELECTOR_ROOM_STATUS.md and docs/CONTINUATION_STATUS.md.',
                                              'Read CLAUDE.md, docs/SELECTOR_COMPATIBILITY_STATUS.md and docs/CONTINUATION_STATUS.md.')
        if name=='docs/CONTINUATION_STATUS.md':
            text+='\n\n### 24 Oct: review-53 diagnostics completed\n\n'+SUMMARY+'\n\nNine compressor tones in three rooms: optimal v2/bank phase differences at most 8.20 degrees, with no clipping of the fitted outputs. The main case supports tuning acceptance error; its cause is still unmeasured. The 35 empty menus contain 34 intermittent-detection cases, correcting the wording “no tone at all”. The 78 references include 71 public acoustic, three electrical and four personal controls. Sixty-five public sources have matched active components: median source median mismatch 0.428; equal-source mean fraction above 0.1 is 89.7%. The ratio is an idealized single-tone reference diagnostic, not measured ear attenuation or a general ANC ceiling. Four targeted checks and 5,056 numerical audit comparisons pass; max difference 2.84e-13. All earlier frozen files and live v2 are unchanged. See [report](../results-selector-compatibility-01/REPORT.md) and [next bounded diagnostic](TUNING_DIAGNOSTIC_NEXT.md).\n'
        path.write_text(text,encoding='utf-8',newline='\n')
    for name in ['docs/SELECTOR_ROOM_STATUS.md','docs/SELECTOR_ROOM_NEXT.md']:
        path=ROOT/name;before[name]=h.sha(path);text=path.read_text(encoding='utf-8')
        heading,rest=text.split('\n',1)
        notice='\n\n> **24 October follow-up:** The three review-53 diagnostics are complete. Read [current compatibility findings](SELECTOR_COMPATIBILITY_STATUS.md) and [the revised next step](TUNING_DIAGNOSTIC_NEXT.md). The large natural-switch synthetic cohort below is superseded; the completed room experiment and its frozen result are preserved.\n'
        path.write_text(heading+notice+rest,encoding='utf-8',newline='\n')
    new(ROOT/'docs/SELECTOR_COMPATIBILITY_STATUS.md',f'''# Compatibility and tuning diagnosis — 24 October 2026

{SUMMARY}

[Full report](../results-selector-compatibility-01/REPORT.md) · [Verification](../results-selector-compatibility-01/verification.json) · [Next bounded diagnostic](TUNING_DIAGNOSTIC_NEXT.md)

The three compressor rooms have nine tone comparisons. The harmful 193.914 Hz tone's best prefix phases are 204.27 degrees for v2 and 199.90 for the bank; actual accepted v2 was 51.68, chooser 200.09. This supports a bad accepted setting, but the cause of acceptance has not been isolated. The earlier harm crossing is retained.

The empty-menu count is not equivalent to no detection: 34 of 35 had intermittent detections below 50% prefix presence. The strongest cluster's median presence is 18.8%. The other 11 silent primary rooms were muted by the final on/off check. Gain-limit flags do not explain muting. The same aggregate split holds for chooser-own tuning; individual settings differ.

All 78 decoded references were compared at the native common origin and actual 30 ms output lead. Sixty-five of 71 public acoustic sources have matched active tone pairs; six have none. Median source median RMS |1-r| is 0.428, median source p95 is 1.230. Equal-source mean fraction above 0.1 is 89.7%; near selector changes it is 86.6% across 23 sources. Electrical and personal controls are separate. Missing and ambiguous matches are counted, never replaced by a benign ratio.

The -20log10|1-r| expression assumes perfect pre-switch single-tone cancellation and a common path. With initial residual e, the new residual is r e + (1-r)s. It is not a universal cancellation ceiling or a bound on loss from existing tuning. Large disagreement does not establish which predictor is more accurate. No new switch guard is selected.

The earlier 0.02–0.05 dB results were incremental gains over v2, not total cancellation in every room. The current saved v2 results include 15.27 dB at tone bins / 9.81 dB across 35–350 Hz in one ventilation room, but a zero median across tonal rooms. These are simulated-ear results only.

Four targeted tests pass, and 5,056 numerical audit checks reproduce saved distributions and 18 prefix-oracle fits, maximum discrepancy 2.84e-13. Source/array/code receipts match. No full-suite rerun, new audio download, playback, microphone capture, engine change or physical ANC validation. The research helper snapshot excludes waveform and ratio arrays.
''')
    new(ROOT/'docs/TUNING_DIAGNOSTIC_NEXT.md','''# Next bounded diagnostic: eligibility and acceptance

24 October 2026. Proposed development work after the completed compatibility diagnosis. No new candidate or acceptance benchmark is frozen here.

The direct recorded-waveform comparison replaces the earlier large synthetic switch-cohort proposal. Existing forced-switch null/bias controls remain useful. The compressor's best fixed settings are close, so there is no reason to begin with a broad predictor phase-calibration redesign.

## First question: what do the intermittent detections represent?

Use the 34 already-seen rooms with detections but no eligible prefix tone. Keep the existing detector, tracker, gate and menu rules. Log contiguous stable episodes, frequency movement, amplitude and completed forecast error using only past samples. Distinguish a short repeatable tone from frequency clustering effects, tracking instability or detections that do not predict usefully. Keep all 34 cases and report unsuccessful/no-evidence outcomes. Known simulated-ear information can diagnose possible benefit, but must not enter a deployable decision feature.

This should decide whether a causal acquisition rule deserves a new development experiment. Do not lower the 50% persistence threshold just to produce output. Tone eligibility and microphone predictability do not establish useful pressure reduction at the ear.

## Second question: why did the final check accept a harmful setting?

Instrument the existing primary 30 ms tuning runs for rooms with an eligible menu. Reuse their exact scene, random stream and simulated listener settings. First require full parity with each saved tuning summary; logging must not consume random draws or change presentations. Then retain the final check's on/off order, compared time intervals, noiseless auditory-band levels and noisy answers. Determine whether changing background sound, judgement noise, or another interaction explains false acceptance.

This is diagnosis of the existing procedure, not permission to train on its scored suffix. Keep noise-free comparisons and matched-segment counterfactuals explicitly post-hoc. If a narrower acceptance intervention is proposed, freeze its development comparison separately and reserve fresh validation for later.

## What remains unchanged

No selector threshold, tuning-aware switch guard, live model or physical trial is chosen by this proposal. Own-prefix tuning and a compatibility-aware guard remain possible later candidates; the observed ratio distribution alone does not evaluate either. Keep original failed/inconclusive results, raw data local, and v2 live. Quiet-machine timing and near-ear physical measurement are independent outstanding requirements.
''')
    log=Path(r'C:\Users\talk2.000\Documents\Obsidian Vault\Predictive ANC\Progress log.md')
    with log.open('a',encoding='utf-8',newline='\n') as f:
        f.write('\n\n## 2026-10-24 — compressor oracle, muting causes and reference compatibility\n\n'+SUMMARY+'\n\nFour targeted checks and the saved-result audit pass. The 35 empty menus are 34 intermittent-detection cases plus one no-detection case; 11 further rooms are fully muted by the final check. The real-source forecast comparison rejects a general near-identical-predictor assumption. The ratio formula is conditional, not a physical ANC guarantee. The tiny earlier average increments are over v2, not all absolute ear gains. Next: bounded eligibility/acceptance instrumentation, no large new switch cohort. Report: `results-selector-compatibility-01/REPORT.md`.\n')
    bundle=ROOT/'research-tools/selector-compatibility-01';bundle.mkdir(exist_ok=False);files=[]
    for name in ['anc_lab/selector_compatibility.py','tests/test_selector_compatibility.py','docs/SELECTOR_COMPATIBILITY_STATUS.md','docs/TUNING_DIAGNOSTIC_NEXT.md']:
        target=bundle/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
        files.append({'path':name,'sha256':h.sha(target)})
    for name in ['analyze_selector_compatibility_20261024.py','report_selector_compatibility_20261024.py','finalize_selector_compatibility_20261024.py']:
        target=bundle/'tools'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(WORK/'work'/name,target)
        files.append({'path':'tools/'+name,'sha256':h.sha(target)})
    new(bundle/'README.md','Research helper snapshot for review-53 diagnostics. Depends on the existing project and its local data. Do not rerun into the completed output directory. The manifest hashes source/helpers only; no audio, forecast or ratio arrays are included.')
    h.write_new(bundle/'manifest.json',{'created_utc':datetime.now(timezone.utc).isoformat(),'files':files,'raw_arrays_included':False,
       'protocol_sha256':h.sha(OUT/'protocol.json'),'verification_sha256':h.sha(OUT/'verification.json')})
    study.verified()
    assert h.sha(ROOT/'anc_lab/antihum.py')=='599bd571cf75c3c18719540e7c32dd0a1f67f3fca6c761273bce2ce955d01c23'
    assert h.sha(ROOT/'results-selector-tuning-01/results.json')=='2c54bde410207e530c2effde621ea7b2d480fa96a33c19c15ac602b959865232'
    for path in [OUT/'REPORT.md',ROOT/'docs/SELECTOR_COMPATIBILITY_STATUS.md',WORK/'outputs/selector-compatibility-20261024/RESULTS.md']:
        for link in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if not link.startswith(('http:','https:','#')):assert (path.parent/link).exists(),(path,link)
    h.write_new(OUT/'finalization.json',{'created_utc':datetime.now(timezone.utc).isoformat(),
      'docs_before_sha256':before,'docs_after_sha256':{n:h.sha(ROOT/n) for n in before},
      'export_sha256':{f.name:h.sha(f) for f in OUT.iterdir() if f.suffix in ('.csv','.png','.md')},
      'research_bundle_manifest_sha256':h.sha(bundle/'manifest.json'),
      'user_report_sha256':h.sha(WORK/'outputs/selector-compatibility-20261024/RESULTS.md'),
      'earlier_room_scores_unchanged':True,'live_engine_unchanged':True})
    print(json.dumps({'updated_docs':list(before),'helper_files':len(files),'earlier_results_and_engine':'unchanged'}))


if __name__=='__main__':main()
