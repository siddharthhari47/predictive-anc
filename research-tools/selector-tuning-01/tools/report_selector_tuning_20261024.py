"""Export the completed frozen room test; never changes its scores or rules."""
from pathlib import Path
from collections import defaultdict
import csv
import json
import sys
import textwrap

ROOT=Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
WORK=Path(r'C:\Users\talk2.000\Documents\Codex\2026-10-15\referenced-chatgpt-conversation-this-is-an')
sys.path.insert(0,str(ROOT))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from anc_lab import selector_headroom as h
from anc_lab import selector_room_completion as completion

OUT=ROOT/'results-selector-tuning-01'


def write(path,content):
    with path.open('x',encoding='utf-8',newline='\n') as f:f.write(content.rstrip()+'\n')


def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rows)


def export(name,rows):
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with (OUT/name).open('x',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)


def main():
    completion.verified()
    r=h.read(OUT/'results.json');v=h.read(OUT/'verification.json');cover=h.read(OUT/'coverage.json')
    assert v['passed'] and h.sha(OUT/'results.json')==v['results_sha256']
    cases=r['cases'];byid={c['case_id']:c for c in cases}
    names={c['source_id']:c['file'] for c in cases}
    rows=[];bands=[];windows=[];settings=[];oracles=[];means=[];audit=[]
    exposures={(e['case_id'],e['lead_ms'],e['row']):e for e in v['exposure_diagnostic_posthoc']}
    for c in cases:
        base={k:c[k] for k in ('case_id','source_id','cohort','file','room_index')}
        for row in c['rows']:
            rows.append({**base,**{k:x for k,x in row.items() if k!='bands'}})
            bands.extend({**base,'lead_ms':row['lead_ms'],'arm':row['arm'],**b} for b in row['bands'])
        for w in c['switch_windows']:
            e=exposures[c['case_id'],w['lead_ms'],w['row']]
            windows.append({**base,**{k:x for k,x in w.items() if k not in ('band_powers','excess_over_v2_db')},
                **{k:x for k,x in e.items() if k.endswith('_command')},
                **{k+'_power':x for k,x in w.get('band_powers',{}).items()},
                **{k+'_excess_db':x for k,x in w.get('excess_over_v2_db',{}).items()}})
        m=h.read(OUT/'cache'/(c['case_id']+'.json'))
        with np.load(ROOT/m['cache_path']) as a:
            for g,lead in enumerate((30,200)):
                changes=np.flatnonzero(np.diff(a['selected'][:,g],prepend=0)!=0)
                detail=next(d for d in c['details'] if d['lead_ms']==lead)
                scored=[w for w in c['switch_windows'] if w['lead_ms']==lead]
                actual=[exposures[c['case_id'],lead,w['row']] for w in scored if w['complete_200ms_window']]
                suffix=a['v2_seen']-1+round(lead*2)+m['unreported']>=m['prefix']+1000
                audit.append({**base,'lead_ms':lead,'prefix_tones':len(m['tones']),
                    'v2_active_settings':sum(s['gain']>0 for s in detail['v2_settings']),
                    'own_active_settings':sum(s['gain']>0 for s in detail['chooser_settings']),
                    'prefix_switches':c['prefix_switches'][str(lead)],'suffix_switches':len(scored),
                    'qualifying_menu_switches':sum(w['command_exposed'] and w['complete_200ms_window'] for w in scored),
                    'actual_reuse_switches':sum(e['reuse_tuned_command'] for e in actual),
                    'actual_own_switches':sum(e['own_tuned_command'] for e in actual),
                    'score_start_s':m['prefix']/2000+.5,
                    'all_choice_transitions_s':json.dumps([round(float(a['v2_seen'][i]/2000),3) for i in changes]),
                    'all_new_choices':json.dumps(a['selected'][changes,g].tolist()),
                    **{'suffix_fraction_choice_'+str(k):float(np.mean(a['selected'][suffix,g]==k)) for k in (0,1,2)}})
        for d in c['details']:
            for method,key in [('v2','v2_settings'),('chooser','chooser_settings')]:
                settings.extend({**base,'lead_ms':d['lead_ms'],'tuned_on':method,**s} for s in d[key])
            b=d['relaxed_retune_bound']
            oracles.append({**base,'lead_ms':d['lead_ms'],'band_db':b['band_db'],'segments':b['segments'],
                'scope':'Noncausal unclipped linear-family bound; future ear targets and unconstrained coefficients; not realizable tuning'})
    for lead,arms in r['summary'].items():
        for arm,s in arms.items():
            means.extend({'source_id':source,'file':names[source],'lead_ms':lead,'arm':arm,'mean_paired_db':x}
                         for source,x in s['source_mean_paired_db'].items())
    for name,data in [('metrics.csv',rows),('bands.csv',bands),('switch-windows.csv',windows),
                      ('settings.csv',settings),('retune-bound.csv',oracles),('source-means.csv',means),
                      ('coverage-audit.csv',audit)]:export(name,data)
    h.write_new(OUT/'coverage-diagnostic.json',{'posthoc':True,'does_not_change_frozen_inclusion_or_decision':True,
        'cases':audit,'interpretation':'The frozen coverage criterion used unit-gain prefix-menu commands. Actual tuned output exposure is stricter and only three sources qualify at each lead. No extra cases are added after seeing outcomes.'})
    # Standalone scientific figure: source differences and the coverage funnel.
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,(ax,bx)=plt.subplots(1,2,figsize=(13,7),gridspec_kw={'width_ratios':[1.8,1]})
    scores=r['summary']['30']['chooser_reuse_v2']['source_mean_paired_db']
    ids=list(scores);values=np.array(list(scores.values()));y=np.arange(len(ids))
    labels=[s+'  '+names[s].removeprefix('File:').replace('_',' ')[:36] for s in ids]
    ax.barh(y,values,color=['#bc5347' if x<0 else '#2d7c83' for x in values],height=.65)
    ax.scatter(values,y,s=14,color='#263840',zorder=3)
    ax.set_yticks(y,labels,fontsize=8);ax.invert_yaxis();ax.axvline(0,color='#777777',lw=.7)
    ax.set_xlabel('Paired tone attenuation vs v2 (dB)');ax.set_title('Almost no average change at 30 ms',loc='left',fontweight='bold')
    ax.set_xlim(-.14,.29);ax.grid(axis='x',alpha=.15)
    bx.bar(['Internal\ndecisions','Menu\ncommands','After\ntuning'],[12,5,3],color=['#a9b5ba','#72999f','#2d7c83'])
    bx.axhline(6,color='#bc5347',ls='--',label='Required: 6 sources')
    for i,x in enumerate([12,5,3]):bx.text(i,x+.25,str(x),ha='center',fontweight='bold')
    bx.set_ylim(0,14);bx.set_ylabel('Distinct recordings with a suffix switch')
    bx.set_title('Too few active switches',loc='left',fontweight='bold');bx.legend(frameon=False,loc='upper right',fontsize=8)
    fig.suptitle('Fixed tuning through predictor switches: inconclusive',x=.02,ha='left',fontweight='bold',fontsize=16)
    fig.text(.02,.015,'Seen recordings in simulated rooms. One new whole-band amplification crossed the frozen limit. No physical ANC claim.',fontsize=10)
    fig.tight_layout(rect=(0,.045,1,.94));fig.savefig(OUT/'room-test-summary.png',dpi=160);plt.close(fig)

    primary=r['summary']['30']['chooser_reuse_v2']
    summary=[]
    for lead,arms in r['summary'].items():
        for arm,s in arms.items():
            summary.append([lead,'Reuse v2 tuning' if arm=='chooser_reuse_v2' else 'Tune chooser on its prefix',
              f'{s["mean_paired_db"]:+.4f}',f'[{s["bootstrap95"][0]:+.4f}, {s["bootstrap95"][1]:+.4f}]',
              f'{s["worst_source_mean_db"]:+.4f}',len(s['new_boosts']),f'{s["maximum_switch_excess_db"]:+.4f}',
              'No' if not s['switch_coverage_sufficient'] else 'Yes'])
    original=[]
    for lead,arms in r['original_only'].items():
        for arm,s in arms.items():original.append([lead,arm,f'{s["mean_paired_db"]:+.4f}',
            f'[{s["bootstrap95"][0]:+.4f}, {s["bootstrap95"][1]:+.4f}]',len(s['new_boosts'])])
    cov=[]
    for lead in ('30','200'):
        a=cover['original_summary'][lead];b=cover['summary'][lead]
        actual=[e for e in v['exposure_diagnostic_posthoc'] if str(e['lead_ms'])==lead and e['complete'] and e['reuse_tuned_command']]
        cov.append([lead,a['exposed_complete_sources'],b['exposed_complete_sources'],b['total_switches'],b['qualifying_switches'],
                    b['incomplete_windows'],len(actual),len({e['source_id'] for e in actual})])
    harms=[]
    for lead,arms in r['summary'].items():
        for arm,s in arms.items():
            for b in s['new_boosts']:
                harms.append([lead,arm,b['case_id'],b['band_hz'],f'{b["candidate_db"]:.4f}',f'{b["v2_db"]:.4f}'])
    report=f'''# Fixed tuning through chooser switches

Completed 24 October 2026. **Inconclusive switch coverage, with an observed primary harm-limit breach. Keep v2 live.**

All 72 preselected rooms were scored once. The original 48 rooms exercised four qualifying sources; the fixed 24-room supplement raised this only to five, below the required six. Reusing v2's tuning also produced one new whole-band amplification above the prewritten 0.5 dB limit. The formal frozen label gives coverage precedence; it must not be read as absence of harm or a pass.

This is **simulated ear attenuation on already-seen recordings**, not new-source validation, a listening test or physical ANC. The separate fresh microphone-prediction result of +0.536 dB remains unchanged. It does not transfer automatically to the ear or to this fixed-tone tuning interface.

![Source differences and switch coverage](room-test-summary.png)

## Primary and secondary outcomes

There are 24 source recordings, three room draws each. Twenty sources have reference tone metrics; all 72 rooms remain in the harm and exposure checks. Average paired tone differences within each source first, then give each source equal weight. Intervals are the frozen 20,000 source bootstrap draws, seed 20261022. Positive differences favor the chooser; they are means of dB differences, not pooled energy reductions.

{table(['Lead ms','Tuning','Mean paired dB','95% interval','Worst source dB','New amplification entries','Max switch excess dB','Coverage sufficient'],summary)}
Only 30 ms with reused v2 settings is primary. Own-prefix tuning is secondary. All 200 ms outcomes are exploratory: there is no inherited validation beyond the earlier 120 ms forecast horizon. None of these arms passes the coverage rule.

The primary mean is **+0.0174 dB**, interval **−0.0118 to +0.0550 dB**; the worst source mean is **−0.1051 dB**. Those satisfy the numerical mean/source noninferiority margins but do not erase the whole-band harm or missing exposure. No extra clipping was found in any arm. No complete switch window exceeded the +3 dB energy limit; this establishes neither inaudibility nor physical safety.

## Amplification must not be hidden by an average

{table(['Lead ms','Arm','Room','Band Hz','Candidate amplification dB','V2 amplification dB'],harms)}
At 30 ms, `old-013-r2` is **WWS_Aircompressor.ogg**. Its 35–350 Hz residual is 0.5703 dB above no control, versus 0.3243 dB for v2. The difference is +0.2460 dB in residual power level; the **absolute** 0.5 dB threshold is what it crosses. It switched from v2 to the bank around 5.63 s, before the scored suffix begins at 25.44 s, and never switched again. This is a persistent compatibility outcome, not an observed jump at a scored switch. Its active v2-tuned tone was about 193.91 Hz. Whether forecast phase, level, availability or their interaction with the ear path is responsible remains unmeasured.

At 200 ms, chooser-own tuning newly amplifies the helicopter room `fresh-035-r2` at 100 Hz by 1.2277 dB; v2 is essentially neutral there. This exploratory failure is retained. At 30 ms, reused tuning introduced no new third-octave crossing; its failure is the whole-band entry above.

## What the switch coverage actually exercised

{table(['Lead ms','Original qualifying sources','All qualifying sources','All suffix switches','Qualifying menu switches','Incomplete windows','Actual tuned-output switches','Actual tuned-output sources'],cov)}
The first coverage definition was fixed before scoring: a prefix-menu tone with unit gain must create nonzero command around a complete ±100 ms window. The last two columns are a **post-hoc descriptive audit** using the actual reused settings; they do not change inclusion or the frozen outcome. Only three distinct recordings have nonzero tuned output during a complete scored switch at either lead. A tiny nonzero command is still only an exposure test, not an audibility criterion.

At 30 ms the simulated listener muted every v2-tuned tone in **28/48 original rooms and 18/24 supplemental rooms**. The locomotive interior and freight train have no eligible prefix-menu tone in any of their three rooms. The helicopter switches before scoring in the two rooms where it switches at all. Thus adding recordings that benefited in the microphone test did not ensure meaningful fixed-tuning switch exposure. Silent ties cannot validate the switch behavior.

Every switch, including incomplete windows, is in [switch-windows.csv](switch-windows.csv). All source/room exposure counts and prefix transitions are in [coverage-audit.csv](coverage-audit.csv). No further recordings were added after the single planned expansion.

## Original cohort retained separately

{table(['Lead ms','Arm','Mean paired dB','95% interval','New amplification entries'],original)}
The original cohort has 16 sources, 13 with reference tone metrics; it also has insufficient switch coverage. The supplemental eight sources were intentionally enriched using already-seen accuracy results, not sampled as a representative deployment population. Source-bootstrap intervals here are descriptive for this development experiment.

## Rendering and calibration boundaries

Both predictors consume x[0] onward and share newest-sample origin `seen-1`. The unchanged chooser uses matured hard-gated 20/120 ms errors; the room renderer synthesizes actual 30/200 ms forecasts. The primary output has no DC and uses the live block-ramped gates, per-tone settings and sample-level chooser crossfade. It does not move an old 20 ms waveform into a 30 ms slot.

Each arm uses the original first-40% tuning prefix and the same source/room seeds. Settings stay fixed during scoring. The prefix-selected tone menu is shared; newly tracked frequencies outside that menu stay silent. The simulated listener's judgement noise is 1 dB. This checks the current interface's compatibility, not automatic calibration of arbitrary newly appearing tones.

Modal source-to-microphone and source-to-ear paths, a modeled earphone high-pass filter and an extra 3 ms delay are known to the simulator. Input levels and earphone gain are model normalizations. The output cap is digital, not calibrated SPL. These runs use fixed leads; they do not measure or establish robustness to Bluetooth jitter, acoustic leakage, clock drift or head movement. Physical validation still needs low-output calibrated hardware and near-ear measurement.

The [retuning bound](retune-bound.csv) uses future ear errors and unconstrained piecewise complex coefficients before the acoustic/evaluation filters, with no output cap. It is an upper bound only for that specified unclipped linear tone family, not achievable listener performance; it never enters the pass decision. Secondary hard/DC reference scores remain in the case JSON and are not ear-attenuation evidence.

## Verification and amendments

- Original 48-room reproduction: **59,939 numeric scalar comparisons, maximum error zero**, plus matching nonnumeric structure. Timing fields were excluded.
- Shared-origin control: all 16 synthetic scene/lead comparisons pass; worst inter-predictor phase difference 0.65782 degrees and level difference 0.0127263 dB. These bounded controls do not guarantee agreement on recorded sources.
- Seven targeted room checks pass, including causality, exact-lead rendering, the chooser rule, source weighting, a deliberately harmful phase switch and zero-output parity. The full historical suite was not rerun.
- All **576 metric rows**, **80 suffix events** (78 complete windows), saved noncausal coefficient reconstructions, source bootstrap results and harm decisions were audited from stored traces/settings. Maximum numerical difference: **{v['maximum_numeric_absolute_difference']:.3g}**. The native tone renderer and SciPy primitives are shared; this is not an independent implementation of the full predictor.
- The original v2 control reproduces the prior room tuning/outcome comparisons in the scoring run (2,668 compared values); the audit separately rechecked its scalar metrics and full tuning structures.
- A pre-scoring amendment changes only the muted command's `worst_third_octave_hz` from an arbitrary tied band to `null`, matching the original baseline. Active metrics/signals are identical. **All original frozen code and protocol files remain byte-for-byte unchanged.** The new completion wrapper, tests and check log have their own hash seal.

Protocol: `{h.sha(OUT/'protocol.json')}`. Coverage seal: `{h.sha(OUT/'coverage.json')}`. Pre-scoring amendment: `{h.sha(completion.AMENDMENT)}`. Results: `{h.sha(OUT/'results.json')}`. Verification: `{h.sha(OUT/'verification.json')}`.

The protocol, baseline and alignment checks were frozen/completed on 22 October. Coverage was sealed at 15:10 UTC on 22 October. The resumed run documented the null-value amendment before scoring on 24 October. There was no predictor change, threshold adjustment, replacement source, recording, playback or download in this continuation.

## Next bounded work

Keep v2 in the live app and retain the chooser as an offline reference-prediction candidate. Diagnose the three existing air-compressor rooms first: track the tuned tones' relative predictor phase, level, gate/availability and simulated ear residual at the actual 30 ms lead, including the prefix switch. Do not retune the selector on this result.

Then write a separate development stress-test protocol that deliberately exercises nonzero automatically discovered tones across controlled predictor switches, with known paths, phase/level mismatch controls and the same live renderer. Count actual tuned-command exposure before suffix scores and keep natural chooser switches separate from forced diagnostic switches. Do not call this fresh validation or keep extending this completed cohort until it passes.

The quiet-machine timing gate is still unresolved. Interleaved old/new measurements could improve the contended comparison, but would not replace that gate. Neither timing nor tuning currently justifies promotion. Claude is being asked to challenge this next scope before a new benchmark is frozen.

## Artifacts

[All metrics](metrics.csv), [all bands and their off/on powers](bands.csv), [source means](source-means.csv), [tuning settings](settings.csv), [switch windows](switch-windows.csv), [coverage audit](coverage-audit.csv), [noncausal bound](retune-bound.csv), [raw aggregate](results.json), [verification receipt](verification.json), [frozen protocol](protocol.json), [pre-scoring amendment](pre-scoring-amendment-01.json).
'''
    write(OUT/'REPORT.md',report)
    write(OUT/'VERIFICATION.md',f'''# Saved-signal verification

24 October 2026. **Passed**, with maximum numeric difference {v['maximum_numeric_absolute_difference']:.3g}.

Reconstructed all 576 metric rows and 78 complete switch-window powers (80 events total) from stored traces and saved settings. Independently rebuilt output placement, filtering, power ratios, per-source aggregation, bootstrap intervals and harm decisions. Reconstructed all 144 noncausal bound outcomes from their saved coefficients. Compared individual case JSON with the aggregate; checked source/cache/code/protocol receipts and the original v2 outcomes/tuning structures.

The verifier records {v['checks_including_nested_scalars_and_structures']:,} comparisons including nested values and structures; these are not that many independent experiments or unit tests. Seven targeted unit tests passed separately. The whole historical suite was not rerun. This verification shares the native tone renderer and SciPy primitives with the scorer; it is not an independent full predictor implementation.

Nothing was re-predicted or re-tuned. No frozen scores, settings, rules or original code were changed. Actual tuned-command exposure is an explicitly post-hoc diagnostic and does not alter the formal coverage decision.

Verifier SHA-256: `{v['script_sha256']}`.
Results SHA-256: `{v['results_sha256']}`.
Full receipt: [verification.json](verification.json).
''')
    user=WORK/'outputs/selector-tuning-20261024';user.mkdir(exist_ok=False)
    usertext=f'''# The tuning test is complete

**The chooser is not ready to replace v2.** All 72 simulated rooms are scored, but too few recordings exercised a real output switch to establish that tuning holds.

- **Coverage:** five recordings met the prewritten switch condition; six were required. After tuning, only three had nonzero anti-noise during a complete scored switch.
- **Average effect:** reusing v2's tuning changed tone attenuation by just **+0.02 dB** (95% interval −0.01 to +0.05).
- **One problem:** an air-compressor room became **0.57 dB louder than no control** across 35–350 Hz, crossing the 0.5 dB limit. V2 was 0.32 dB louder there. This persisted after an earlier switch; no scored switch window exceeded the separate jump-energy limit.
- **Checks:** all seven targeted tests pass. The saved-signal audit reproduces the room scores, switch windows and decisions. The original frozen code and results are preserved.

Next: diagnose the compressor's tuning mismatch, then design a focused test with enough **active** output switches. The live app remains on v2; its quiet-machine speed test is also unresolved.

These are simulated ear results. Nothing was played, recorded or measured at a real ear, and no physical ANC has been demonstrated.

[Full report]({(OUT/'REPORT.md').as_posix()}) · [Verification]({(OUT/'VERIFICATION.md').as_posix()}) · [All switch windows]({(OUT/'switch-windows.csv').as_posix()})

![Results and the switch-coverage shortfall]({(OUT/'room-test-summary.png').as_posix()})
'''
    write(user/'RESULTS.md',usertext)
    print(json.dumps({'report':str(OUT/'REPORT.md'),'user_report':str(user/'RESULTS.md'),'csv_rows':{
      'metrics':len(rows),'bands':len(bands),'windows':len(windows),'settings':len(settings),'oracles':len(oracles),'source_means':len(means),'coverage':len(audit)}}))


if __name__=='__main__':main()
