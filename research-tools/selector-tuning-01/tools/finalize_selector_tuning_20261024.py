"""Update mutable project handoff docs and package reproducibility helpers."""
from pathlib import Path
from datetime import datetime, timezone
import json
import re
import shutil
import sys

ROOT=Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
WORK=Path(r'C:\Users\talk2.000\Documents\Codex\2026-10-15\referenced-chatgpt-conversation-this-is-an')
sys.path.insert(0,str(ROOT))
from anc_lab import selector_headroom as h
from anc_lab import selector_room_completion as completion

OUT=ROOT/'results-selector-tuning-01'
SUMMARY='**24 October continuation:** All 72 fixed-tuning rooms are scored. The result is **inconclusive for switch coverage**, with one observed primary whole-band harm-limit breach: the reused-tuning chooser makes an air-compressor room 0.570 dB louder than no control (v2: 0.324 dB). Five sources meet the frozen switch condition, below six; only three have nonzero tuned output during complete scored switches. Mean paired tone change is +0.017 dB, 95% interval -0.012 to +0.055. Keep v2 live. Next diagnose persistent tuning compatibility on the compressor, then prewrite an active-output switch stress test. The quiet-machine timing gate remains unresolved. The fresh +0.536 dB reference-prediction result is unchanged and is not an ear-attenuation claim.'


def new(path,text):
    with path.open('x',encoding='utf-8',newline='\n') as f:f.write(text.rstrip()+'\n')


def main():
    p,coverage=completion.verified()
    assert h.read(OUT/'verification.json')['passed']
    before={}
    pattern=r'\*\*22 October continuation:\*\*[^\n]*?existing scope limits\.'
    for name in ['CLAUDE.md','README.md','docs/CONTINUATION_STATUS.md','docs/CODEX_HANDOFF.md','docs/SELECTOR_TIMING_STATUS.md']:
        path=ROOT/name;before[name]=h.sha(path);text=path.read_text(encoding='utf-8')
        text,n=re.subn(pattern,SUMMARY,text)
        assert n in (1,2),(name,n)
        text=text.replace('current timing/integration status](docs/SELECTOR_TIMING_STATUS.md)','current room-test status](docs/SELECTOR_ROOM_STATUS.md)')
        text=text.replace('current timing/integration status](SELECTOR_TIMING_STATUS.md)','current room-test status](SELECTOR_ROOM_STATUS.md)')
        text=text.replace('the timing and integration checkpoint](docs/SELECTOR_TIMING_STATUS.md)','the room-test checkpoint](docs/SELECTOR_ROOM_STATUS.md)')
        if name=='CLAUDE.md':
            text=text.replace('Read `docs/SELECTOR_TIMING_STATUS.md`, `results-selector-timing-01/REPORT.md` and `results-selector-components-01/REPORT.md`.',
                'Read `docs/SELECTOR_ROOM_STATUS.md`, `results-selector-tuning-01/REPORT.md` and `docs/SELECTOR_ROOM_NEXT.md`. Timing background remains in `docs/SELECTOR_TIMING_STATUS.md`.')
        if name=='README.md':
            text=text.replace('Read CLAUDE.md, docs/SELECTOR_FRESH_STATUS.md and docs/CONTINUATION_STATUS.md.',
                              'Read CLAUDE.md, docs/SELECTOR_ROOM_STATUS.md and docs/CONTINUATION_STATUS.md.')
        if name=='docs/CONTINUATION_STATUS.md':
            text=text.replace('Updated 22 October 2026, India time.','Updated 24 October 2026, India time.')
            text=text.replace('Current direction (22 Oct):','Current direction (24 Oct):')
            text+='\n\n### 24 Oct: fixed-tuning room test completed\n\n'+SUMMARY+'\n\nThe original 48 rooms reproduced exactly (59,939 numeric comparisons). Shared-origin controls passed at 30/200 ms. The fixed supplement brought the experiment to 72 rooms/24 sources, 20 with tone metrics. The primary mean/source margins passed numerically, but the whole-band harm and missing coverage prevent promotion. At 200 ms, own-prefix tuning also newly boosts one helicopter band by 1.228 dB. All 576 metric rows and 80 suffix events were audited from saved traces/settings; seven targeted unit checks pass. A pre-scoring null-value amendment preserves all original frozen files. No live output, recording or downloads. See [full results](../results-selector-tuning-01/REPORT.md), [verification](../results-selector-tuning-01/VERIFICATION.md), and [the proposed next diagnostic](SELECTOR_ROOM_NEXT.md).\n'
        if name=='docs/SELECTOR_TIMING_STATUS.md':
            text=text.replace('The component adapter preserves the original tone frequencies, phasors, ghosts and sample-level fades.',
                'The earlier 20/120 ms component adapter preserves the original tone frequencies, phasors, ghosts and sample-level fades.')
            text+='\n\nThe separate exact-lead room bridge and 72-room comparison are now complete. Read [room status](SELECTOR_ROOM_STATUS.md); timing evidence above is unchanged. The room result does not resolve the quiet-machine gate or warrant engine promotion.\n'
        path.write_text(text,encoding='utf-8',newline='\n')
    new(ROOT/'docs/SELECTOR_ROOM_STATUS.md',f'''# Fixed-tuning room checkpoint — 24 October 2026

{SUMMARY}

The frozen experiment has ended. Preserve its 72 rooms and do not append cases until it passes. Original48 alone: four qualifying sources, mean -0.010 dB. The planned enrichment adds only one qualifying source. Post-hoc actual-command exposure is three sources at both leads; 46/72 primary v2 tuning sessions mute every tone.

Reusing settings at 30 ms introduces one new whole 35–350 Hz amplification crossing, no new third-octave crossing, no extra clipping and no switch-window energy violation. Own-prefix tuning is secondary and also lacks coverage. At 200 ms it adds one 100 Hz helicopter-band boost; all 200 ms results are exploratory.

The air-compressor switch occurs about 5.63 s into its prefix; scoring starts at 25.44 s. The loss is persistent, not a scored switch transient. Cause is not yet established. The phase/origin controls pass, so a gross shared-origin bug was not observed on the synthetic checks; this does not rule out source-dependent phase or level errors.

Read [full report](../results-selector-tuning-01/REPORT.md), [verification](../results-selector-tuning-01/VERIFICATION.md), [frozen design](SELECTOR_ROOM_TEST.md) and [next diagnostic proposal](SELECTOR_ROOM_NEXT.md). The original protocol and code are unchanged; [pre-scoring amendment](../results-selector-tuning-01/pre-scoring-amendment-01.json) only restores null for the worst band when output is muted.

Evidence: seven targeted checks, all 576 outcome rows and 80 suffix events audited, maximum numerical discrepancy about 1.1e-14. The frozen v2 control matches its earlier tuning/outcomes. No full-suite claim. The first 48-room baseline reproduced 59,939 numbers exactly; 16 alignment scene/lead controls pass within 0.658 degrees and 0.0128 dB.

Research helpers and a hash manifest are in `research-tools/selector-tuning-01/`. Raw audio and cached signal arrays remain local. No real-time engine was changed, no audio device opened, and no physical ear-level attenuation was measured.
''')
    new(ROOT/'docs/SELECTOR_ROOM_NEXT.md','''# Proposed next offline diagnostic

24 October 2026. Development proposal following the completed room test; **not a frozen benchmark, acceptance result or engine change**. Claude is being asked to challenge this scope. No new recordings or downloads are required for the first step.

## Question

Why does one air-compressor room become louder when the chooser uses a better microphone predictor with the old tuning, and how can the next test ensure that real output switches are exercised?

## 1. Diagnose existing evidence before changing anything

Use all three existing WWS_Aircompressor rooms, not only the harmful one. Read their saved traces, fixed settings and ear paths. Reconstruct parity with the frozen outcomes first. At the exact 30 ms lead, log each tuned tone's frequency, relative level, relative phase, gate state and availability for v2 and the bank, plus the emitted component and ear residual. Use common-time phasors and explicitly matched frequencies; do not compare phase when the relevant component is absent.

Cover the tuning prefix, the actual switch and the entire scored suffix. In the harmful room the switch is near 5.63 s and scoring begins at 25.44 s, so this is not solely a switch-edge question. Separate forecast bias from a tone disappearing, gate changes and frequency/menu mismatch. Use existing zero, v2-tuned/v2-output, v2-tuned/chooser-output and chooser-own-tuning outcomes. Any further intervention is labelled post-hoc development and saved separately.

Do not change predictor settings, selector thresholds, source inclusion or the completed benchmark. The diagnosis should yield a specific measured mechanism or an explicit unresolved finding, not a new winner selected from many retries.

## 2. Prepare an active-output stress test

Write a new protocol before generating or scoring its suffixes. Use automatically discovered random steady tones plus separately labelled drift cases through known source/mic/ear paths. Choose frequency ranges and seeds independently of the observed compressor frequencies. Ensure the prefix establishes useful nonzero tuning; count actual emitted-command exposure before suffix ear scores. Fix failure/exclusion reporting in advance so unsuccessful tuning is not silently discarded.

Keep two questions separate: forced switches exercise the renderer and fixed calibration under controlled phase/level mismatch; natural chooser switches exercise the decision rule. Forced transitions must never be counted as natural selector coverage. Include equal-predictor null controls, known phase-bias harm controls, v2-only and zero output. Keep the actual 30 ms/no-DC/ramped output convention and disclose whether decisions remain on 20 ms errors. Defer the exploratory 200 ms branch unless it answers a distinct question.

Report per-tone and whole-band changes, all amplification and clipping, and every switch window. A digital energy threshold is not an audibility or SPL claim. Do not keep adding cases until the completed experiment's six-source floor is reached; this must be a separate development experiment. A later fresh source test will still be needed.

## Timing and physical work

The quiet-machine compute gate remains pending. An alternating cached-v2/cached-chooser measurement is an optional contended diagnostic, not a substitute. Keep live v2 unchanged. Physical continuation needs the existing user-started procedure and calibrated near-ear measurement; this proposal opens no audio device.

## Review questions for Claude

Is the compressor diagnosis the cheapest next useful step, or is the prefix-tone menu the dominant integration obstacle? Does a two-part forced/natural switch stress test answer fixed-tuning compatibility without overstating real coverage? What single intervention would the diagnosis justify testing next, if any?
''')
    log=Path(r'C:\Users\talk2.000\Documents\Obsidian Vault\Predictive ANC\Progress log.md')
    with log.open('a',encoding='utf-8',newline='\n') as f:
        f.write('\n\n## 2026-10-24 — fixed-tuning room test completed\n\n'+SUMMARY+'\n\nAll 72 cases completed once; 576 metric rows and 80 suffix events audited. Maximum discrepancy 1.1e-14; seven targeted checks pass. Actual tuned-output exposure is only three sources, explaining why nominal switches are weak coverage. Compressor loss follows a prefix switch, not a suffix jump. The original48 control reproduced exactly before the test; shared-origin checks passed. A pre-scoring null-value fix uses a separately sealed completion wrapper and leaves all original frozen files unchanged. No audio devices, downloads or engine changes. Report: `results-selector-tuning-01/REPORT.md`; next proposal: `docs/SELECTOR_ROOM_NEXT.md`.\n')
    # Preserve helpers with explicit hashes; no waveform/trace arrays are copied.
    bundle=ROOT/'research-tools/selector-tuning-01';bundle.mkdir(exist_ok=False)
    names=['anc_lab/'+n for n in ['selector_room_stream.py','selector_room_scoring.py','selector_room_study.py',
        'selector_room_completion.py','selector_room_baseline.py','selector_room_alignment.py']]
    names+=['tests/test_selector_room_'+n+'.py' for n in ['stream','scoring','completion']]
    names+=['docs/'+n for n in ['SELECTOR_ROOM_TEST.md','SELECTOR_ROOM_STATUS.md','SELECTOR_ROOM_NEXT.md']]
    copies=[]
    for name in names:
        target=bundle/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
        assert h.sha(ROOT/name)==h.sha(target)
        copies.append({'path':name,'sha256':h.sha(target)})
    for name in ['verify_selector_tuning_20261024.py','report_selector_tuning_20261024.py','finalize_selector_tuning_20261024.py']:
        target=bundle/'tools'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(WORK/'work'/name,target)
        copies.append({'path':'tools/'+name,'sha256':h.sha(target)})
    new(bundle/'README.md','''# Room-test research helpers

Snapshot for the 24 October completion of `results-selector-tuning-01`. These modules depend on the existing project and its local datasets; this folder is not a standalone package. The original frozen runner remains unchanged. The separately sealed completion wrapper changes only the null label for a muted command's worst band.

Do not rerun freeze/coverage/scoring into the completed output folders. Verification and export scripts also create files exclusively. Read the existing reports and receipts first. No raw audio or cached waveform arrays are included. See `manifest.json` for file hashes.
''')
    h.write_new(bundle/'manifest.json',{'created_utc':datetime.now(timezone.utc).isoformat(),'files':copies,
        'raw_audio_or_forecast_arrays_included':False,'protocol_sha256':h.sha(OUT/'protocol.json'),
        'results_sha256':h.sha(OUT/'results.json'),'verification_sha256':h.sha(OUT/'verification.json')})
    # Check distinct input files and older protocol/results without rerunning them.
    sources={e['source_path']:e['source_sha256'] for e in p['original_cases']+p['conditional_supplement_cases']}
    for name,digest in sources.items():assert h.sha(ROOT/name)==digest,name
    older={
      'results-tone-forecaster-04/protocol.json':'874e9fd9e25b469d81c4431b4b454069f9404a701afe63b64087ed12ad5073ec',
      'results-tone-forecaster-05/protocol.json':'d02a63720f48f9765747bc48165ddd962c1c1edfbe3e6e7d6e4257acb2734116',
      'results-selector-fresh-01/protocol.json':'f395e6a2b9b20dfc4ac5d9d2b33f07e6f9b4c8ed4ead0240fb333e5b8b974308',
      'anc_lab/antihum.py':'599bd571cf75c3c18719540e7c32dd0a1f67f3fca6c761273bce2ce955d01c23'}
    for name,digest in older.items():assert h.sha(ROOT/name)==digest,name
    completion.verified()
    h.write_new(OUT/'finalization.json',{'created_utc':datetime.now(timezone.utc).isoformat(),
      'source_sha256_verified':sources,'older_sha256_verified':older,
      'mutable_docs_before_sha256':before,'mutable_docs_after_sha256':{n:h.sha(ROOT/n) for n in before},
      'research_bundle_manifest_sha256':h.sha(bundle/'manifest.json'),
      'export_sha256':{f.name:h.sha(f) for f in OUT.iterdir() if f.suffix in ('.csv','.md','.png')},
      'user_report_sha256':h.sha(WORK/'outputs/selector-tuning-20261024/RESULTS.md')})
    print(json.dumps({'updated_docs':list(before),'packaged_files':len(copies),'verified_distinct_inputs':len(sources),'engine_unchanged':True}))


if __name__=='__main__':main()
