"""Present the already-completed studies side by side, without pooling their different test sets."""
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

ROOT=Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
OUT=Path(r'C:\Users\talk2.000\Documents\Codex\2026-10-15\referenced-chatgpt-conversation-this-is-an\outputs\anc-studies-20261020')
reviews={n:json.loads((OUT/f'study-{n}-review.json').read_text(encoding='utf-8')) for n in ('04','05')}

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(2,3,figsize=(13.5,8.1))
fig.patch.set_facecolor('#f8fafc')
colors=['#64748b','#34465d','#008c82']
for row,(n,r) in enumerate(reviews.items()):
    methods=['v2_gated','joint_gated',r['candidate']]
    names=['v2','Joint check','Gate fade' if n=='04' else 'Tone fade']
    keys=['tone_median_20ms_db','recording_band_boost_cases',
          'synthetic_late_band_boost_cases' if n=='04' else 'change_late_band_boost_cases']
    titles=['Median tone gain at 20 ms\nhigher is better',
            'Fresh-recording band boosts\nlower is better',
            ('All synthetic late boosts' if n=='04' else 'Sudden-change late boosts')+'\nlower is better']
    for col,(key,title) in enumerate(zip(keys,titles)):
        ax=axes[row,col]
        values=[r['metrics'][m][key] for m in methods]
        bars=ax.bar(names,[0 if v is None else v for v in values],color=colors,width=.58,zorder=3)
        ax.set_title(title,loc='left',fontsize=10,pad=14,color='#162333')
        ax.set_facecolor('#f8fafc');ax.grid(axis='y',alpha=.18,zorder=0)
        ax.axhline(0,color='#8994a4',linewidth=.7)
        ax.set_ylabel('dB of reference prediction gain' if col==0 else 'Recording × horizon cases' if col==1 else 'Scene × horizon cases')
        if col:
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        lo=min([0]+[v for v in values if v is not None]);hi=max([0]+[v for v in values if v is not None])
        spread=max(hi-lo,1)
        ax.set_ylim(lo-.13*spread,hi+.25*spread)
        for bar,v in zip(bars,values):
            ax.text(bar.get_x()+bar.get_width()/2,(v or 0)+.035*spread,
                    'n/a' if v is None else f'{v:.2f}' if col==0 else str(v),
                    ha='center',va='bottom',weight='bold',color='#162333')
    phrase='passed all frozen questions' if r['all_frozen_questions_pass'] else 'did not pass all frozen questions'
    title=f"Study {n} · {'80 ms gate fade' if n=='04' else '100 ms per-tone fade'} · {phrase}"
    y=.86 if row==0 else .46
    fig.text(.065,y,title,fontsize=12,weight='bold',color='#162333')
fig.suptitle('Do smoother fades help on new sounds?',x=.065,y=.985,ha='left',fontsize=20,weight='bold',color='#162333')
fig.text(.065,.937,'Offline reference-waveform prediction. These are not measured reductions in sound at an ear.',fontsize=11,color='#475569')
fig.text(.065,.025,'Each row uses its own frozen test set; compare methods within a row. Band-boost threshold: ≥1 dB. No playback occurred.',fontsize=10,color='#475569')
fig.subplots_adjust(left=.075,right=.98,top=.79,bottom=.105,hspace=.62,wspace=.34)
fig.savefig(OUT/'frozen-study-comparison.png',dpi=180,facecolor=fig.get_facecolor())
fig.savefig(OUT/'frozen-study-comparison.svg',facecolor=fig.get_facecolor())
plt.close(fig)
if '--figure-only' in sys.argv:
    print('Updated figure only; saved results untouched.')
    raise SystemExit(0)

lines=['# Fresh-sound results: studies 04 and 05','','20 October 2026 · Predictive ANC lab','',
       'Both studies used frozen code, fixed comparison rules and fresh recording lists. The tests ran once. '
       'All gains below describe prediction of the recording microphone waveform, not physical ANC.','',
       '| Study | Frozen outcome | Fresh recordings | Synthetic scenes | Tone gain: candidate / joint / v2 at 20 ms |',
       '|---|---|---:|---:|---:|']
for n,r in reviews.items():
    def f(m):
        v=r['metrics'][m]['tone_median_20ms_db']
        return 'n/a' if v is None else f'{v:.2f}'
    lines.append(f"| {n}: {'gate fade' if n=='04' else 'per-tone fade'} | "
                 f"{'All questions passed' if r['all_frozen_questions_pass'] else 'Not all questions passed'} | "
                 f"{len(r['fresh_files'])} | {r['synthetic_scenes']} | {f(r['candidate'])} / {f('joint_gated')} / {f('v2_gated')} dB |")
lines += ['',f"![Frozen study comparison]({(OUT/'frozen-study-comparison.png').as_posix()})",'',
          '## What the tests decide','']
for n,r in reviews.items():
    lines += [f"### Study {n}",'']
    lines.extend(f"- {k.replace('_',' ')}: **{'yes' if v else 'no'}**." for k,v in r['primary_questions'].items())
    lines += [f"- Missing recordings: {', '.join(r['fresh_missing']) if r['fresh_missing'] else 'none'}.",
              f"- [Detailed result and uncertainty]({(OUT/f'study-{n}-review.md').as_posix()}).",'']
lines += ['## Decision boundary','',
          'The current live engine remains v2. Passing a frozen reference-prediction rule is only one development step: '
          'quiet-machine processing time, measured output timing, acoustic transfer, and near-ear residual pressure '
          'remain necessary before a new controller can be described as real ANC. The two faded candidates were '
          'tested separately; their combination was not tested.', '',
          'These small, purposive samples do not establish performance on every tone or sound. The models infer '
          'tones from past samples; no fan frequency was hard-coded for these tests. Sudden and mixed noises are '
          'stress cases for amplification, not a claim to predict arbitrary broadband sound.', '',
          '## Reproducibility','',
          'Raw downloads stay local in the project. Each batch has current Commons metadata, licence attribution, '
          'the user authorization, and the frozen-size/SHA-1 checks. Reports have SHA-256 receipts. A separate review '
          'recounted boosts and recomputed medians from the stored scores; it did not rerun or retune the models.']
with (OUT/'RESULTS.md').open('x',encoding='utf-8',newline='\n') as f:f.write('\n'.join(lines)+'\n')
print('Saved combined report, PNG and SVG.')
