"""Report the single frozen run from saved scores. Never runs a predictor."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import json, math, sys, textwrap
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
sys.path.insert(0,str(ROOT))
from anc_lab import selector_headroom as h
from anc_lab.selector_fresh_study import score
S=ROOT/'results-selector-fresh-01'

def text_new(path,text):
    with path.open('x',encoding='utf-8',newline='\n') as stream:stream.write(text+'\n')

def title(c):return c['title'].removeprefix('File:').replace('|','/')
def fmt(x):return 'N/A' if x is None else f'{x:+.3f}'

def main():
    p=h.read(S/'protocol.json');a=h.read(S/'acquisition-amendment-01.json')
    d=h.read(S/'decoder-amendment-02.json');manifest=h.read(S/'download/manifest.json')
    result=h.read(S/'test/results.json');summary=h.read(S/'SUMMARY.json')
    cases=result['cases'];usable=[c for c in cases if c['status']=='scored']
    tonal=[c for c in usable if c['reference_tones_hz']]
    excluded=[c for c in cases if c['status']!='scored']
    cand=summary['methods']['causal_L2'];base=summary['methods']['v2_gated']
    checks={};checks['protocol_receipt']=h.sha(S/'protocol.json')==h.read(S/'frozen.json')['protocol_sha256']
    checks['acquisition_receipt']=h.sha(S/'acquisition-amendment-01.json')==h.read(S/'acquisition-amendment-frozen.json')['sha256']
    checks['decoder_receipt']=h.sha(S/'decoder-amendment-02.json')==h.read(S/'decoder-amendment-frozen.json')['sha256']
    checks['design_unchanged']=h.sha(ROOT/'docs/SELECTOR_FRESH_TEST.md')==p['evidence']['test_design_sha256']
    checks['decoder_binary']=h.sha(Path(p['decoder']['path']))==p['decoder']['sha256']
    hashes=dict(p['code_sha256'])
    for name,change in d['code_changes'].items():
        checks['preserved:'+name]=h.sha(ROOT/change['preserved_original'])==change['before_sha256']==hashes[name]
        hashes[name]=change['after_sha256']
    hashes.update(d['added_tests_sha256'])
    for name,digest in hashes.items():checks['code:'+name]=h.sha(ROOT/name)==digest
    for n in ('04','05'):
        old=ROOT/f'results-tone-forecaster-{n}'
        expected={'04':('874e9fd9e25b469d81c4431b4b454069f9404a701afe63b64087ed12ad5073ec','47e9828f6cdf4753b1738e29fdfac72d218f936ce7845daab2531704de287944'),
                  '05':('d02a63720f48f9765747bc48165ddd962c1c1edfbe3e6e7d6e4257acb2734116','0a098b6a4c9514b1f2247877ad969d9735ac9afec2241cc4c7e4f193e4d4df60')}[n]
        checks['study'+n+'_protocol']=h.sha(old/'protocol.json')==expected[0]
        checks['study'+n+'_test']=h.sha(old/'test/test.json')==expected[1]
    checks['old_audit']=h.sha(ROOT/'results-selector-headroom-01/audit/results.json')==p['evidence']['old_audit_results_sha256']
    checks['unique_cases']=len(cases)==len({c['id'] for c in cases})==40
    checks['source_ids']=set(c['id'] for c in cases)==set(e['id'] for e in p['sources'])
    checks['minimum_scored_duration']=all(c['actual_scored_seconds_per_horizon']>=30 for c in usable)
    checks['manifest_receipt']=h.sha(S/'download/manifest.json')==h.read(S/'test/execution.json')['manifest_sha256']
    started=datetime.fromisoformat(h.read(S/'test/execution.json')['started_utc'])
    checks['protocol_before_execution']=datetime.fromisoformat(p['created_utc'])<started
    checks['acquisition_amendment_before_execution']=datetime.fromisoformat(a['created_utc'])<started
    checks['decoder_amendment_before_execution']=datetime.fromisoformat(d['created_utc'])<started
    for receipt in manifest['files']:
        if receipt['status']=='verified':
            checks['input:'+receipt['id']]=h.sha(ROOT/receipt['local_path'])==receipt['sha256']
    for c in usable:
        checks['arrays:'+c['id']]=h.sha(ROOT/c['arrays_path'])==c['arrays_sha256']
    for horizon in (20,120):
        changes=np.array([score(c,'causal_L2',horizon)['tone_band_gain_db']-score(c,'v2_gated',horizon)['tone_band_gain_db'] for c in tonal])
        if len(changes):
            mean=math.fsum(changes)/len(changes)
            rng=np.random.default_rng(20261021)
            independent_ci=np.percentile(changes[rng.integers(len(changes),size=(50000,len(changes)))].mean(axis=1),[2.5,97.5])
            checks[f'mean_{horizon}']=abs(mean-cand[str(horizon)]['mean_db'])<1e-12
            checks[f'ci_{horizon}']=bool(np.allclose(independent_ci,cand[str(horizon)]['mean_bootstrap95'],atol=1e-12,rtol=0))
        for method in ('causal_L2','v2_gated'):
            count=sum(any(v>=1 for v in score(c,method,horizon)['third_octave_change_db']) for c in usable)
            checks[f'band_count_{method}_{horizon}']=count==summary['methods'][method][str(horizon)]['band_boost_cases']
    assert all(checks.values()),[k for k,v in checks.items() if not v]
    verification={'created_utc':datetime.now(timezone.utc).isoformat(),'checks':checks,'all_passed':True,
        'predictor_reruns':0,'method':'Independent aggregation/bootstrap from saved source scores; source/array/code receipts and earlier-study hashes.',
        'targeted_unit_checks_passed':18,'targeted_unit_elapsed_seconds':.510}
    h.write_new(S/'VERIFICATION.json',verification)
    # Paired differences are the effect of interest; marginal medians are secondary.
    if tonal:
        ordered=sorted(tonal,key=lambda c:score(c,'causal_L2',20)['tone_band_gain_db']-score(c,'v2_gated',20)['tone_band_gain_db'])
        fig,axes=plt.subplots(1,2,figsize=(13,max(6,.31*len(ordered)+2)),sharey=True)
        for ax,horizon in zip(axes,(20,120)):
            diff=[score(c,'causal_L2',horizon)['tone_band_gain_db']-score(c,'v2_gated',horizon)['tone_band_gain_db'] for c in ordered]
            ax.barh(range(len(ordered)),diff,color=['#17856b' if v>.01 else '#bc493d' if v<-.01 else '#93a0ac' for v in diff],height=.7)
            ax.scatter(diff,range(len(ordered)),s=12,color='#21303e',zorder=3)
            ax.axvline(0,color='#6b7682',lw=.8);ax.axvline(-1,color='#bc493d',ls=':',lw=.8)
            ax.set_title(f'{horizon} ms forecast\nMean paired gain {cand[str(horizon)]["mean_db"]:+.3f} dB',loc='left',fontsize=11)
            ax.set_xlabel('Chooser minus v2 (dB)');ax.grid(axis='x',alpha=.2)
            ax.spines[['top','right','left']].set_visible(False)
        axes[0].set_yticks(range(len(ordered)),[c['id']+'  '+textwrap.shorten(title(c),width=43,placeholder='…') for c in ordered],fontsize=8)
        fig.suptitle('Fresh recordings: where choosing by past errors helps or hurts',fontsize=14,x=.02,ha='left')
        fig.text(.02,.012,'Reference-microphone prediction only. Dotted line: −1 dB. Source IDs link to the full report. No ear-level measurement.',fontsize=9,color='#555555')
        fig.tight_layout(rect=(0,.04,1,.96));fig.savefig(S/'paired-gains.png',dpi=180);plt.close(fig)
    lines=['# Fresh test of the unchanged chooser','',
        f'21 October 2026. **{summary["decision"].replace("_"," ").capitalize()}.**',
        f'{len(usable)} of 40 fixed sources were scored; {len(tonal)} contained reference tones. The run used only the first 90 seconds at most, with a 40% calibration prefix and at least 30 seconds of scored target blocks per horizon.',
        '', 'These are reference-microphone prediction-error reductions. They are not measured sound cancellation at an ear. The live engine remains v2. No recording or playback occurred.',
        '', '## Frozen decision', '', '| Requirement | Result |','|---|---|']
    for name,passed in summary['criteria'].items():lines.append(f'| {name.replace("_"," ")} | {"Met" if passed else "Not met"} |')
    lines+=['','## Paired accuracy and amplification','','| Measure | 20 ms | 120 ms |','|---|---:|---:|']
    for name,key in [('Mean paired tone gain (dB)','mean_db'),('Median paired tone gain (dB)','median_db'),('Worst paired tone gain (dB)','minimum_db')]:
        lines.append('| '+name+' | '+' | '.join(fmt(cand[str(t)].get(key)) for t in (20,120))+' |')
    lines.append('| 95% source-bootstrap interval for mean | '+' | '.join('N/A' if cand[str(t)]['mean_bootstrap95'] is None else '['+', '.join(fmt(v) for v in cand[str(t)]['mean_bootstrap95'])+']' for t in (20,120))+' |')
    for tol in ('practical','numerical'):
        lines.append(f'| Wins / ties / losses ({tol} tolerance) | '+' | '.join(' / '.join(str(cand[str(t)].get(tol,{}).get(k,'N/A')) for k in ('wins','ties','losses')) for t in (20,120))+' |')
    for key,label in [('band_boost_cases','Sources with any third-octave boost ≥1 dB, chooser / v2'),('whole_band_boost_cases','Sources with whole low-band amplification >0.5 dB, chooser / v2')]:
        lines.append('| '+label+' | '+' | '.join(f'{cand[str(t)][key]} / {base[str(t)][key]}' for t in (20,120))+' |')
    lines+=['','Practical ties: ±0.01 dB; numerical ties: ±1e-8 dB. Counts are source-by-horizon cases, not the total number of amplified bands. Whole band here means 35–350 Hz. Each source has equal weight. The 120 ms result does not model Bluetooth jitter or validate wireless use.',
        '', '## Every scored source', '', '| Source | Scored seconds | Tone bins | v2 20 ms | Chooser 20 ms | Paired Δ20 | Paired Δ120 |', '|---|---:|---:|---:|---:|---:|---:|']
    for c in usable:
        s20=score(c,'causal_L2',20);b20=score(c,'v2_gated',20)
        tonal_case=bool(c['reference_tones_hz'])
        vals=[fmt(b20['tone_band_gain_db']),fmt(s20['tone_band_gain_db']),fmt(s20['tone_band_gain_db']-b20['tone_band_gain_db']),fmt(score(c,'causal_L2',120)['tone_band_gain_db']-score(c,'v2_gated',120)['tone_band_gain_db'])] if tonal_case else ['N/A']*4
        lines.append(f'| {c["id"]}: [{title(c)}]({c["source_page"]}) | {c["actual_scored_seconds_per_horizon"]:.2f} | {len(c["reference_tones_hz"])} | '+' | '.join(vals)+' |')
    lines+=['','All gains above are dB. No-tone sources remain in amplification counts; they do not acquire a fictional tone score. Full comparator scores (zero, v2, joint guard, fade, prefix AR and chooser) remain in `test/results.json`.','', '## Exclusions','']
    for c in excluded:lines.append(f'- **{c["id"]}: {title(c)}** — {c.get("reason","unspecified").replace(chr(10)," ")}')
    if not excluded:lines.append('None.')
    lines+=['','## Interpretation limits and audit trail','',
        'Claude’s correction was valid: a median of paired changes can be zero while the mean is positive when many outputs tie v2. The earlier audit’s median-based stop remains its historical prespecified outcome. Reinterpreting it and choosing L2 were development decisions; this new source test uses the mean endpoint frozen before audio access.',
        '', 'The 40-source metadata-selected pool has 2 fan/ventilation, 15 other machinery and 23 transport-engine recordings. It contains moving, changing and mixed-noise stress cases. It is not a representative sample of all steady hums. Forty distinct uploader and credited-author strings do not establish capture independence; '+str(sum(e['credited_author_seen_before'] for e in p['sources']))+' credited authors/collections overlap the earlier pool. Reference tone detection for scoring does not establish stationarity.',
        '', 'The bootstrap interval is conditional on this purposive source collection. It quantifies source variability under resampling, not uncertainty over every environment. The longer-clip association in the old audit does not prove that duration caused its ties.',
        '', 'The tested chooser is a causal DSP selection rule with a two-second completed-error history. It starts from v2 and can select the faded tracker or zero only on past evidence. Source calibration precedes scoring. This experiment does not test frozen neural-model transfer, measured output latency, clock drift, Bluetooth jitter, or the reference-to-ear acoustic path.',
        '', 'The public recordings have unknown microphones, processing and recording conditions. Official transcodes are lossy; these measurements concern the decoded reference waveforms, not calibrated raw acoustic pressure.',
        '', '**Two pre-scoring operational deviations are disclosed.** Commons requested smaller copies after rejecting larger originals. One representation per fixed source was nominated uniformly before downloading those copies; two sources had no eligible representation. Derivative checksums are local receipts tied to official API URLs and parent identities, not externally published checksums. A metadata-routing bug for Ogg video containers was then corrected before any decoding or scoring. The original runner and protocols are preserved; no prediction, source-selection, cropping or scoring rule was tuned.',
        '', f'Acquisition: {manifest["verified_count"]}/40 files; {sum(r.get("bytes",0) for r in manifest["files"]):,} bytes in the final input batch. Failed original attempts are retained separately. Scoring wall time: {result["runtime_seconds"]/60:.1f} minutes; this offline process-pool timing is not a real-time deadline benchmark.',
        '', f'Validation: {len(checks)} receipt/aggregation checks passed; 18 targeted unit checks passed (0.510 s), including causal maturity, transitions, seen-score parity and video dispatch. No full-suite rerun is claimed. No predictor was rerun to make this report.',
        '', '| Artifact | SHA-256 |','|---|---|']
    for name in ('protocol.json','acquisition-amendment-01.json','decoder-amendment-02.json','download/manifest.json','test/results.json','SUMMARY.json'):
        lines.append(f'| [{name}]({name}) | `{h.sha(S/name)}` |')
    if tonal:lines+=['','![Paired gains for every tonal source](paired-gains.png)']
    text_new(S/'REPORT.md','\n'.join(lines))
    print(json.dumps({'decision':summary['decision'],'usable':len(usable),'tonal':len(tonal),'verification_checks':len(checks),'report':str(S/'REPORT.md')},indent=2))

if __name__=='__main__':main()
