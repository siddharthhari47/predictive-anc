"""Independent saved-result audit and source-balanced descriptive aggregation."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import csv,json,sys
import numpy as np
from scipy import signal

ROOT=Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
sys.path.insert(0,str(ROOT))
from anc_lab import selector_headroom as h
from anc_lab import selector_compatibility as study
from anc_lab import selector_room_study as rooms
from anc_lab.antihum import ToneSetting,replay,FS
from anc_lab.tuning import erb_hz
OUT=study.STUDY
checks=0;maxerror=0.


def close(a,b):
    global checks,maxerror
    checks+=1
    assert np.allclose(a,b,rtol=1e-8,atol=1e-9),(a,b)
    maxerror=max(maxerror,float(np.max(np.abs(np.asarray(a)-np.asarray(b)),initial=0)))


def category(c):
    return 'personal_controls' if c['cohort']=='personal-seen-secondary' else 'electrical_controls' if not c['acoustic'] else 'public_acoustic'


def exports(name,rows):
    with (OUT/name).open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)


def main():
    p=study.verified();r=h.read(OUT/'reference-results.json');m=h.read(OUT/'muting.json');o=h.read(OUT/'compressor.json')
    assert sorted(c['id'] for c in r['cases'])==sorted(c['id'] for c in p['cases'])
    source_rows=[];groups={};counts=Counter();checksums={}
    for c in r['cases']:
        assert h.read(OUT/'sources'/(c['id']+'.json'))==c
        path=ROOT/c['ratio_arrays_path'];assert h.sha(path)==c['ratio_arrays_sha256']
        assert h.sha(ROOT/c['arrays_path'])==c['arrays_sha256']
        checksums[c['id']]=h.sha(path)
        with np.load(path) as a:
            for section,mask in [('all',np.ones(len(a['origin']),bool)),('original_scored_suffix',a['in_original_scored_suffix']),('near_selector_switch',a['near_selector_switch'])]:
                z=a['ratio'][mask];s=c[section];close(len(z),s['matched_tone_frames'])
                record={'id':c['id'],'title':c['title'],'category':category(c),'cohort':c['cohort'],
                    'section':section,'matched_tone_frames':len(z),'eligible_v2_tone_frames':c['counts'].get('eligible_v2_components',0),
                    'v2_unmatched':c['counts'].get('v2_without_bank_match',0),'bank_unmatched':c['counts'].get('bank_components_without_v2_match',0),
                    'ambiguous':c['counts'].get('ambiguous_matches',0),'frames_both_gates_open':c['counts'].get('frames_both_gates_open',0),
                    'frames_after_warmup':c['counts']['frames_after_warmup'],'selector_transitions':c['selector_transitions']}
                if len(z):
                    d=np.sqrt(np.mean((z.real-1)**2+z.imag**2,axis=1));cap=-20*np.log10(np.maximum(d,1e-15))
                    ramp=a['ramped_ratio'][mask];dr=np.sqrt(np.mean((ramp.real-1)**2+ramp.imag**2,axis=1))
                    for key,vals in [('mismatch',d),('idealized_retained_attenuation_db',cap),('ramped_mismatch',dr),
                        ('absolute_phase_difference_deg',np.abs(np.arctan2(z[:,0].imag,z[:,0].real)*180/np.pi)),('amplitude_ratio',np.abs(z[:,0]))]:
                        for label,value in zip(['p05','p50','p95','p99','max'],np.percentile(vals,[5,50,95,99,100])):close(value,s[key][label])
                    close(np.mean(d>.1),s['fraction_mismatch_above_0_1']);close(np.mean(d>1),s['fraction_mismatch_above_1'])
                    w=a['v2_amplitude'][mask]**2;weighted=np.sqrt(np.dot(w,d*d)/max(w.sum(),1e-30))
                    close(weighted,s['v2_energy_weighted_rms_mismatch'])
                    record.update(mismatch_median=s['mismatch']['p50'],mismatch_p95=s['mismatch']['p95'],
                        mismatch_max=s['mismatch']['max'],fraction_above_0_1=s['fraction_mismatch_above_0_1'],
                        fraction_above_1=s['fraction_mismatch_above_1'],energy_weighted_rms_mismatch=weighted,
                        idealized_db_median=s['idealized_retained_attenuation_db']['p50'],
                        idealized_db_p05=s['idealized_retained_attenuation_db']['p05'],phase_abs_median=s['absolute_phase_difference_deg']['p50'],
                        phase_abs_p95=s['absolute_phase_difference_deg']['p95'],ramped_mismatch_p95=s['ramped_mismatch']['p95'])
                source_rows.append(record)
        counts.update(c['counts'])
    for group in ('public_acoustic','electrical_controls','personal_controls'):
        groups[group]={}
        for section in ('all','original_scored_suffix','near_selector_switch'):
            rows=[c for c in source_rows if c['category']==group and c['section']==section]
            active=[c for c in rows if c['matched_tone_frames']]
            result={'available_recordings':len(rows),'recordings_with_pairs':len(active),
                'matched_tone_frames':sum(c['matched_tone_frames'] for c in rows),
                'recordings_with_any_mismatch_above_0_1':sum(c.get('fraction_above_0_1',0)>0 for c in rows),
                'recordings_with_p95_mismatch_at_most_0_1':sum(c.get('mismatch_p95',np.inf)<=.1 for c in rows)}
            if active:
                for field in ('mismatch_median','mismatch_p95','fraction_above_0_1','fraction_above_1','energy_weighted_rms_mismatch','idealized_db_median','idealized_db_p05','phase_abs_median'):
                    vals=np.array([c[field] for c in active]);result[field+'_across_sources']={
                        'median':float(np.median(vals)),'mean':float(np.mean(vals)),'min':float(vals.min()),'max':float(vals.max())}
            groups[group][section]=result
    # Verify the no-menu split from the stored native tone history, without rerunning it.
    cover=h.read(rooms.STUDY/'coverage.json');lookup={c['case_id']:c for c in cover['cases']}
    tone_rows=[];room_rows=[]
    for case_id in lookup:
        scene,meta=rooms.load_case(lookup[case_id]);a=scene['arrays']
        prefix=(a['seen']>scene['warm'])&(a['seen']<=scene['prefix'])
        observed=bool(np.isfinite(a['frequency'][prefix]).any())
        native_menu=rooms.room.choose_tones(a,np.flatnonzero(prefix))
        assert len(native_menu)==len(scene['tones'])
        saved=h.read(rooms.STUDY/'scores'/(case_id+'.json'))
        for lead in (30,200):
            detail=next(d for d in saved['details'] if d['lead_ms']==lead)
            for method,key in [('v2','v2_tuning'),('chooser','chooser_tuning')]:
                row=next(x for x in m['rows'] if x['case_id']==case_id and x['lead_ms']==lead and x['tuned_on']==method)
                assert row['prefix_ever_detected']==observed
                close(row['active_settings'],sum(s['kept'] for s in detail[key] if 'kept' in s))
                if not native_menu:
                    assert row['reason']==('no_eligible_menu_intermittent_detections' if observed else 'no_eligible_menu_no_v2_detection')
                    assert row['max_cluster_presence']<.5
                elif row['active_settings']==0:
                    assert all('no benefit heard: switched off' in s['flags'] for s in detail[key])
                room_rows.append({k:v for k,v in row.items() if k not in ('flags','tones')})
                for t in row['tones']:
                    tone_rows.append({'case_id':case_id,'lead_ms':lead,'tuned_on':method,
                        **{k:t[k] for k in ['frequency','gain','phase_deg','kept','gain_before_check','presses','sweeps']},
                        'flags':' | '.join(t['flags'])})
    # Independent normal-equation solutions verify the prefix least-squares fits.
    oracle_rows=[]
    for item in o['tone_comparisons']:
        scene,meta=rooms.load_case(lookup[item['case_id']]);f=item['frequency'];half=erb_hz(f)/2
        sos=signal.butter(2,[max(20,f-half),min(f+half,.45*FS)],fs=FS,btype='bandpass',output='sos')
        first,last=scene['warm'],scene['prefix'];target=signal.sosfilt(sos,scene['ears'][0])
        for method,a in [('v2',scene['trace']['v2']),('bank',scene['trace']['bank'][0])]:
            basis=[]
            for phase in (0.,90.):
                drive=replay(a,[ToneSetting(f,1,phase)],.03).ravel()
                sound=scene['earphone_gain']*signal.lfilter(*scene['earphone'],drive)
                start=int(a['seen'][0])-1+60+scene['unreported'];full=np.zeros(scene['n'])
                size=min(len(sound),len(full)-start);full[start:start+size]=sound[:size]
                basis.append(signal.sosfilt(sos,full))
            x=np.column_stack(basis)[first:last];y=target[first:last]
            coef=np.linalg.solve(x.T@x,-x.T@y);close(coef,item[method]['coefficients'])
            close(np.linalg.norm(coef),item[method]['gain'])
            close(np.degrees(np.arctan2(coef[1],coef[0]))%360,item[method]['phase_deg'])
        oracle_rows.append({'case_id':item['case_id'],'frequency':f,
          'v2_optimal_gain':item['v2']['gain'],'v2_optimal_phase':item['v2']['phase_deg'],
          'bank_optimal_gain':item['bank']['gain'],'bank_optimal_phase':item['bank']['phase_deg'],
          'optimal_phase_difference':item['oracle_phase_difference_deg'],
          'v2_tuned_phase':item['v2_tuning']['phase_deg'],'v2_kept':item['v2_tuning']['kept'],
          'v2_tuned_phase_error':item['v2_tuned_phase_error_vs_own_oracle_deg'],
          'chooser_tuned_phase':item['chooser_tuning']['phase_deg'],'chooser_kept':item['chooser_tuning']['kept'],
          'chooser_tuned_phase_error':item['chooser_tuned_phase_error_vs_bank_oracle_deg']})
    study.verified()
    summary={'completed_utc':datetime.now(timezone.utc).isoformat(),'groups':groups,'all_counts':dict(counts),
      'muting_summary':m['summary'],'compressor_tone_comparisons':len(oracle_rows),
      'no_global_threshold_pass_claim':True,'source_equal_weight_summary':'Across-source medians/means of per-source descriptors; no pooling as independent samples and no statistical acceptance test.'}
    h.write_new(OUT/'summary.json',summary)
    exports('reference-sources.csv',source_rows);exports('muting-rooms.csv',room_rows)
    exports('muting-tones.csv',tone_rows);exports('compressor-oracles.csv',oracle_rows)
    receipt={'created_utc':datetime.now(timezone.utc).isoformat(),'passed':True,'numerical_checks':checks,
      'max_numeric_difference':maxerror,'source_ratio_sha256':checksums,
      'input_receipts_sha256':{name:h.sha(OUT/name) for name in ['protocol.json','reference-results.json','compressor.json','muting.json']},
      'script_sha256':h.sha(Path(__file__)),'scope':'Recomputed ratio distributions from saved complex samples; checked source/array receipts and inventory; native menu/flags reproduce muting; normal equations reproduce all18 prefix-oracle fits. No predictors/tuners rerun. Native renderer and numerical primitives remain shared.'}
    h.write_new(OUT/'verification.json',receipt)
    print(json.dumps({'verified':True,'checks':checks,'max_error':maxerror,'public':groups['public_acoustic']},indent=2))


if __name__=='__main__':
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=1):main()
