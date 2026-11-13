"""Publish descriptive compatibility findings without changing any benchmark."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,csv,shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
WORK=Path(r'C:\Users\talk2.000\Documents\Codex\2026-10-15\referenced-chatgpt-conversation-this-is-an')
sys.path.insert(0,str(ROOT))
from anc_lab import selector_headroom as h
from anc_lab import selector_compatibility as study
OUT=study.STUDY


def new(path,text):
    with path.open('x',encoding='utf-8',newline='\n') as f:f.write(text.rstrip()+'\n')


def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rows)


def main():
    p=study.verified();s=h.read(OUT/'summary.json');v=h.read(OUT/'verification.json');r=h.read(OUT/'reference-results.json')
    assert v['passed']
    oracle=h.read(OUT/'compressor.json')['tone_comparisons'];focus=next(x for x in oracle if x['case_id']=='old-013-r2' and x['v2_tuning']['kept'])
    public=[c for c in r['cases'] if c['acoustic'] and c['cohort']!='personal-seen-secondary']
    # Equal-source empirical distributions; successive frames are not independent.
    x=np.geomspace(.001,10.,600);curves={k:[] for k in ('all','switch')}
    for c in public:
        with np.load(ROOT/c['ratio_arrays_path']) as a:
            delta=np.sqrt(np.mean(np.abs(1-a['ratio'])**2,axis=1))
            for key,vals in [('all',delta),('switch',delta[a['near_selector_switch']])]:
                if len(vals):curves[key].append(np.searchsorted(np.sort(vals),x,side='right')/len(vals))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,(ax,bx)=plt.subplots(1,2,figsize=(12,5.7),gridspec_kw={'width_ratios':[1.05,1.35]})
    labels=['No detection','Detected, below\nmenu persistence','Muted by final\nlistening check','Active setting']
    counts=[1,34,11,26]
    ax.barh(np.arange(4),counts,color=['#a9b5ba','#667e91','#bd7651','#2d7c83'])
    ax.set_yticks(np.arange(4),labels);ax.invert_yaxis();ax.set_xlim(0,39)
    for i,n in enumerate(counts):ax.text(n+.6,i,str(n),va='center',fontweight='bold')
    ax.set_xlabel('Rooms, out of 72');ax.set_title('Why the primary v2 tuning is silent',loc='left',fontweight='bold')
    for key,label,color in [('all','All paired frames (65 sources)','#2d7c83'),('switch','Near chooser changes (23 sources)','#b56846')]:
        bx.plot(x,np.mean(curves[key],axis=0),label=label,color=color,lw=2)
    bx.axvline(.1,color='#555555',ls='--',lw=1);bx.text(.108,.17,'0.1: 20 dB only under\nideal single-tone assumptions',fontsize=8)
    bx.set_xscale('log');bx.set_xlim(.005,3);bx.set_ylim(0,1);bx.grid(alpha=.15)
    bx.set_ylabel('Fraction at or below mismatch, equal source weights')
    bx.set_xlabel('Relative forecast mismatch |1 − r| (block RMS)')
    bx.set_title('Recorded forecasts often disagree',loc='left',fontweight='bold');bx.legend(frameon=False,fontsize=8,loc='upper left')
    fig.suptitle('Tuning acceptance and tone eligibility come before promotion',x=.02,ha='left',fontsize=15,fontweight='bold')
    fig.text(.02,.015,'Seen-data diagnosis. Left: simulated rooms. Right: reference forecasts, conditional on matched active components. No physical ANC result.',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.93));fig.savefig(OUT/'compatibility-summary.png',dpi=170);plt.close(fig)
    stats=[]
    for section,label in [('all','All after warm-up'),('original_scored_suffix','Original scored suffix'),('near_selector_switch','Within 100 ms of chooser change')]:
        q=s['groups']['public_acoustic'][section]
        stats.append([label,f'{q["recordings_with_pairs"]}/71',f'{q["matched_tone_frames"]:,}',
          f'{q["mismatch_median_across_sources"]["median"]:.3f}',f'{q["mismatch_p95_across_sources"]["median"]:.3f}',
          f'{100*q["fraction_above_0_1_across_sources"]["mean"]:.1f}%',f'{q["idealized_db_median_across_sources"]["median"]:.2f}'])
    otable=[]
    for a in oracle:otable.append([a['case_id'],f'{a["frequency"]:.2f}',f'{a["v2"]["phase_deg"]:.2f}',
      f'{a["bank"]["phase_deg"]:.2f}',f'{a["oracle_phase_difference_deg"]:+.2f}',
      'yes' if a['v2_tuning']['kept'] else 'no',f'{a["v2_tuned_phase_error_vs_own_oracle_deg"]:+.2f}'])
    text=f'''# Compressor, silence and forecast-compatibility diagnosis

24 October 2026. Response to Claude review #53. **The compressor result supports a bad accepted tuning setting; silence is mostly a tone-menu eligibility issue. Predictor interchangeability is not established. Keep v2 live.**

This is a post-hoc diagnostic on existing data, not a new held-out acceptance test. The completed 72-room experiment remains inconclusive with its original harm crossing. No predictor, tuner, guard, menu threshold, live engine or frozen benchmark was changed. The earlier fresh reference-prediction gain also remains unchanged.

![Mute reasons and predictor disagreement](compatibility-summary.png)

## The compressor check supports the tuning explanation

For each of the nine prefix-menu tones in all three compressor rooms, fit the best fixed complex setting separately for v2 and bank output, using only the simulated ear's tuning prefix. These are unconstrained, single-tone least-squares calibration oracles with the native 30 ms renderer, modeled earphone path/delay and an auditory-width band. They use ear information the reference microphone does not provide; they are not a deployable replacement for tuning.

For the harmful room's **193.914 Hz** tone:

| Setting | Gain | Phase |
| --- | --- | --- |
| Best fixed prefix setting for v2 | 0.7823 | 204.27° |
| Best fixed prefix setting for the bank | 0.8094 | 199.90° |
| Actual accepted v2 tuning | 0.6303 | 51.68° |
| Actual accepted chooser tuning | 0.7187 | 200.09° |

The best phases differ by **4.37°**, and the gains by 0.296 dB. The accepted v2 phase is **152.58° away from its own optimum**; the chooser's accepted phase is 0.19° from the bank optimum. The known physical-path phase in this simulation is 203.48°, consistent with this diagnosis. Both two-column fits are well conditioned (about 1.0002), and neither oracle output clips.

Across all nine tone comparisons the largest optimal phase difference is **8.20°**. This supports a poorly accepted v2 setting as the main explanation for this particular case. It does not prove whether judgement noise, changing background sound between sequential presentations, or another tuning interaction caused acceptance. The chooser still changes the bad setting's resulting residual, and the frozen harm crossing is retained.

{table(['Room','Tone Hz','V2 optimum °','Bank optimum °','Bank − v2 °','V2 kept','V2 tuning error °'],otable)}
Fitting uses [1.5 s, prefix end), with two native 0°/90° basis outputs and a second-order causal ERB-width filter. No suffix samples enter the fit. The prefix oracle is signal-aware; it is not merely the exact transfer function at one frequency. Its single-tone auditory-band scores are not interchangeable with the prior all-tone 35–350 Hz or tone-bin outcomes. The complete fits and bounded-output prefix/suffix checks are in [compressor.json](compressor.json).

## Why 46 of 72 rooms have no active v2 setting

| Primary 30 ms outcome | Rooms |
| --- | ---: |
| No v2 tone detected during the eligible prefix | 1 |
| Detections occurred, but no cluster met the tuning-menu persistence rule | 34 |
| Eligible tones existed, but the final on/off listening check muted all of them | 11 |
| At least one accepted active setting | 26 |

Thus **35 rooms had no eligible menu**, not 35 rooms with no detection at all. For the 34 intermittent cases, the strongest cluster occupied a median 18.8% of eligible prefix blocks, range 1.9–48.8%; the menu requires 50%. Merely lowering the threshold would admit less persistent detections and is not justified by this count alone. They may be short useful tones, drift, detector instability or unwanted detections; the audit does not distinguish those causes yet.

All 11 remaining silent primary rooms are explained by the final listening acceptance check. None needed a short-prefix or missing-sweep explanation. There were three gain-limit flags and two one-direction sweep flags among the primary v2 tone summaries; those flags do not themselves mute the output. At 200 ms the split is 1 / 34 / 14 / 23. Chooser-own tuning has the same aggregate room counts, though its individual settings can differ. These are counts of zero settings, not counts of every moment when a positive setting happens to emit nothing due to tracking or gating.

Saved traces independently reproduce the menu membership. Saved flags reproduce the mute reasons. [Room table](muting-rooms.csv) and [tone table](muting-tones.csv) preserve every room/lead/method, including flags. Muting can be the correct response to an unhelpful tone; it is not automatically a defect. Real audibility remains unmeasured.

## Direct comparison across all available seen recordings

The frozen inventory contains **78 decoded recordings, 74.42 minutes**: 71 public acoustic sources, three electrical controls and four personal controls. Six older inventory entries have no retained usable reference array and are disclosed in the protocol; there were no replacements or downloads. The existing normalized references and full retained durations were reused, not the simulated rooms. Synthetic scenes were excluded.

Both predictors consume identical input from sample zero and use the same newest-sample origin. Forecasts are synthesized at the actual **30 ms** lead, using the existing bank's 20 ms decision group. Ratios are evaluated at all 20 samples of each 10 ms output block after a 1.5 s warm-up. Match active components within the native 2 Hz tolerance, sum uniquely associated bank components, and exclude/report ambiguous or missing matches. Both gates must be open and component magnitudes exceed 1e-12. The raw-phasor and separately gate-ramped versions are retained; DC is excluded.

Write r = bank forecast / v2 forecast at the same time, and delta = RMS |1 − r| across the block. These distributions are conditional on a comparable component existing on both sides. A match is an algorithmic association, not proof that both components represent the same physical tone. Values are also reported with v2-amplitude energy weighting so small denominators do not solely determine the conclusion.

{table(['Public acoustic scope','Recordings with pairs','Tone frames','Median source median delta','Median source p95 delta','Mean source fraction delta > 0.1','Median source median idealized dB'],stats)}
There are **597,201** matched tone frames across 65 public acoustic recordings. In the remaining six there is no matched active pair, so no ratio claim is made. Across the 65, the median per-source median mismatch is **0.428**; the median per-source 95th percentile is **1.230**. Averaging the within-source proportions equally, **89.7%** of matched frames exceed 0.1. No public source has its 95th-percentile mismatch at or below 0.1. Median source energy-weighted RMS mismatch is **0.544**. These are descriptors of correlated seen-data frames, not independent-trial confidence estimates.

Near actual chooser changes, 23 sources have matched pairs. Their typical median mismatch is still **0.322**, and the equal-source mean fraction above 0.1 is **86.6%**. This comparison includes changes involving zero as well as the two predictors; it is not a measured ear-level jump, and the actual 100 ms blend is not a full instantaneous switch.

Electrical controls are much closer at their typical paired frames (median source median mismatch 0.0174); their tails are still retained. Personal controls remain separate (two of four have matched pairs). Across all 78 recordings, there are 48,742 v2 tone frames without a bank match, 332,963 unmatched bank components, and 110 ambiguous v2 matches, in addition to gate-mismatch frames. Missing counterparts are not assigned a reassuring ratio. Full per-source counts and all three time scopes are in [reference-sources.csv](reference-sources.csv).

## What the ratio does and does not say

For one ideal physical tone s, suppose calibration cancels it perfectly before switching, so the old anti-noise is −s. If the new forecast changes that anti-noise by a common complex factor r while the path and frequency stay compatible, the new residual is (1−r)s. In this special case the retained attenuation is −20 log10 |1−r|: delta = 0.1 corresponds to 20 dB.

With an existing residual e, the new residual is instead **r e + (1−r)s**. Consequently the simple expression is not a general upper bound on ANC or a guaranteed change in cancellation. Real paths, multiple tones, clipping, unmatched components, gating and crossfades also matter. The tabulated idealized medians (about 7.36 dB over all paired public frames) are **not observed or promised ear cancellation**. A large ratio difference does not show which predictor is more accurate; the bank can be correcting a v2 error.

The proposed reassuring premise that mismatch generally stays below 0.1 is not supported. A fixed 0.1 switch guard would be restrictive in this diagnostic, but that is not an evaluation of such a guard at actually tuned tones and real switch opportunities. No guard or retuning intervention is selected here.

## The small incremental gains do not mean every room has tiny cancellation

The earlier +0.017 dB and +0.049 dB figures were **mean improvements over v2**, not the absolute attenuation produced by all tuning. The saved 30 ms v2 results include a ventilation room with **15.27 dB at the reference-tone bins and 9.81 dB across 35–350 Hz**, while the median tone score across tonal rooms is zero. Benefits are concentrated; many rooms output nothing. These remain modeled-ear outcomes, not physical measurements.

## Verification and next scope

Four targeted checks pass: prefix-only oracle fitting with a changed future, known phase-reversal ratio, explicit ambiguous matching, and component summation/gate-ramp handling. The original forced-switch renderer tests already cover equal-output and known-bias controls; no new natural-switch synthetic cohort was built.

The audit recomputes source ratio distributions from saved complex samples, checks all reference/ratio hashes and inventory, reproduces native menu membership and mute flags, and verifies all 18 oracle fits with separate normal-equation solutions. **{v['numerical_checks']:,} numeric checks; maximum discrepancy {v['max_numeric_difference']:.3g}.** Renderer and numerical primitives are shared, so this is not an independent full algorithm implementation. No full-suite claim.

Next priority is the tuning layer: distinguish useful intermittent tones from unstable detections before changing the menu, and instrument the existing final acceptance check to explain how a harmful setting was accepted. Reproduce its saved summaries and random sequence before interpreting new diagnostics. Do not lower eligibility or harden a switch guard merely to make this dataset pass. Own-prefix tuning and a compatibility-aware guard remain possible later candidates, requiring separate development and fresh validation.

Keep v2 live. Quiet-machine timing remains unresolved. Physical validation still requires the user-started procedure and calibrated near-ear measurement; this run opened no audio device. These findings refine the project toward usable cancellation without abandoning automatic prediction of new tones.

Protocol SHA-256: `{h.sha(OUT/'protocol.json')}`. The reference run completed at {r['completed_utc']}; the saved audit completed at {v['created_utc']}. Original frozen files, the 72-room scores and live engine remain unchanged.

[Protocol and exclusions](protocol.json) · [Summary](summary.json) · [Verification](verification.json) · [All reference results](reference-results.json) · [Compressor comparison](compressor-oracles.csv) · [Muting reasons](muting-rooms.csv)
'''
    new(OUT/'REPORT.md',text)
    dest=WORK/'outputs/selector-compatibility-20261024';dest.mkdir(exist_ok=False)
    new(dest/'RESULTS.md',f'''# What the follow-up checks found

**The immediate priority is better tone eligibility and tuning acceptance. The live app stays on v2.**

- **Compressor:** Claude's diagnosis is supported. The two predictors' best fixed phases differ by only **4.4°**, while the accepted v2 setting was **153° from its optimum**. The cause of that acceptance still needs investigation.
- **Silence:** out of 72 rooms, **34 detected tones that were too intermittent for the menu**, one detected none, and 11 muted every tone after the final listening check. The other 26 retained active settings.
- **Switching:** the complete comparison across **78 recordings** shows that the predictors often disagree on real audio. Their agreement on clean test tones does not establish that old tuning will remain valid after a switch.

The previous 0.02–0.05 dB figures were the chooser's extra gain over v2. Some simulated rooms already show substantial cancellation; most do not. These checks neither demonstrate physical ANC nor justify changing the live predictor.

All saved-result checks passed. Next: investigate useful intermittent tones and false acceptance in the tuning step; keep the completed benchmarks intact.

[Full report]({(OUT/'REPORT.md').as_posix()}) · [Every room's mute reason]({(OUT/'muting-rooms.csv').as_posix()}) · [All recording comparisons]({(OUT/'reference-sources.csv').as_posix()})

![Why rooms are silent and how forecasts differ]({(OUT/'compatibility-summary.png').as_posix()})
''')
    print(json.dumps({'report':str(OUT/'REPORT.md'),'user_report':str(dest/'RESULTS.md')}))


if __name__=='__main__':main()
