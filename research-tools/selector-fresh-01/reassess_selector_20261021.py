"""New, explicitly post-hoc read of the saved audit. No predictor execution."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
sys.path.insert(0,str(ROOT))
from anc_lab import selector_fresh_study as f

a=f.h.read(ROOT/'results-selector-headroom-01/audit/results.json')
cases=[c for c in a['cases'] if not c.get('skipped') and c.get('primary_pool') and c.get('acoustic') and c['reference_tones_hz']]
rows=[]
for c in cases:
    row={'id':c['id'],'file':c['file'],'nominal_suffix_seconds':c['audio']['decoded_seconds']-c['score_start_seconds']}
    for horizon in (20,120):
        base=f.score(c,'v2_gated',horizon)['tone_band_gain_db']
        row[str(horizon)]={'v2':base,'causal_L2':f.score(c,'causal_L2',horizon)['tone_band_gain_db'],
            'paired_L2':f.score(c,'causal_L2',horizon)['tone_band_gain_db']-base,
            'paired_oracle':f.score(c,'oracle_window',horizon)['tone_band_gain_db']-base}
    rows.append(row)
stats={str(t):{m:f.paired_summary([r[str(t)][m] for r in rows]) for m in ('paired_L2','paired_oracle')} for t in (20,120)}
long=[r for r in rows if r['nominal_suffix_seconds']>=20]
result={'created_utc':datetime.now(timezone.utc).isoformat(),'kind':'post_hoc_changed_endpoint_on_seen_data',
    'original_results_sha256':f.h.sha(ROOT/'results-selector-headroom-01/audit/results.json'),
    'methods_and_outputs_unchanged':True,'rows':rows,'statistics':stats,
    'nominal_suffix_at_least_20s':f.paired_summary([r['20']['paired_L2'] for r in long]),
    'mean_headroom_fraction_20ms':stats['20']['paired_L2']['mean_db']/stats['20']['paired_oracle']['mean_db'],
    'limits':'Endpoint and duration subgroup interpreted after scores were known. Duration association is not causal attribution. Source-bootstrap intervals are descriptive on a purposive seen collection.'}
dest=ROOT/'results-selector-fresh-01'
f.h.write_new(dest/'seen-data-reassessment.json',result)
text='''# Why the selector deserves a fresh test

21 October 2026. Post-hoc analysis of unchanged, already-seen results.

The original numbers are arithmetically consistent. A difference between two
method medians is not the median of their paired differences. Most paired
differences are zero because this rule often retains v2. That makes the median
insensitive to gains confined to a minority of sources. It does not mean the
rule provides no useful improvements.

Across 30 acoustic tonal recordings, the unchanged two-second rule has mean
paired gain **0.74956 dB** at 20 ms, against **1.02734 dB** for the window
benchmark (about **73%**). Its paired median is still **0.00 dB**. Ten gains
exceed 0.01 dB; one more positive difference is smaller than that. There are no
20 ms regressions in this seen pool. At 120 ms there are five strictly negative
differences, of which three exceed 0.01 dB; the worst is **-1.61318 dB**.

The 16 sources with nominal scored suffixes of at least 20 seconds have mean
gain **1.40541 dB**. This observational subgroup is not evidence that duration
caused the difference. The selector already has a two-second error history and
calibration replay before scoring; source identity and predictability also vary.

The original audit's frozen median stop remains its recorded outcome. Claude's
message #43 withdraws that rule for future decisions. The revised mean endpoint
was selected after looking at results and is exploratory. It supports one new,
fully frozen fresh-source test, not a retrospective pass or engine promotion.

The fresh candidate is L2 exactly as written, with no tuning. Code, source list,
durations, exclusions, confidence calculation and amplification checks must all
be frozen before the new audio is accessed. See docs/SELECTOR_FRESH_TEST.md.
'''
(dest/'REASSESSMENT.md').write_text(text,encoding='utf-8')
print(json.dumps({'n':len(rows),'mean20':stats['20']['paired_L2']['mean_db'],
    'headroom_fraction':result['mean_headroom_fraction_20ms'],'statistics120':stats['120']['paired_L2']},indent=2))
