"""Offline post-hoc diagnostics requested in Claude review 53; no live changes."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter
import argparse
import json
import numpy as np
from scipy import signal
from threadpoolctl import threadpool_limits
from . import selector_headroom as h
from . import selector_room_study as rooms
from . import selector_room_completion as completion
from .selector_room_stream import stream
from .selector_stream_profile import cached_dpss
from .antihum import FS, BLOCK, ToneSetting, replay
from .tuning import erb_hz

ROOT=h.ROOT
STUDY=ROOT/'results-selector-compatibility-01'


def phase_difference(a,b):
    return float((a-b+180)%360-180)


def fit_fixed(target,basis,start,end):
    """Prefix-only unconstrained least squares; never estimates from the suffix."""
    y=np.asarray(target)[start:end]
    x=np.asarray(basis)[start:end]
    if np.max(np.abs(x),initial=0)<=1e-15:
        return {'identifiable':False,'reason':'no emitted basis in prefix'}
    coef,_,rank,singular=np.linalg.lstsq(x,-y,rcond=None)
    if rank<2:return {'identifiable':False,'reason':'rank deficient'}
    before=float(np.mean(y*y));after=float(np.mean((y+x@coef)**2))
    return {'identifiable':True,'coefficients':coef.tolist(),'gain':float(np.linalg.norm(coef)),
      'phase_deg':float(np.degrees(np.arctan2(coef[1],coef[0]))%360),
      'condition':float(singular[0]/singular[-1]),'prefix_band_gain_db':db(before,after),
      'prefix_off_power':before,'prefix_residual_power':after}


def db(a,b):return float(10*np.log10(max(float(a),1e-30)/max(float(b),1e-30)))


def matched_ratios(v2,bank,gate0,gate1,seen,selected,warm=1.5):
    """Same-time analytic forecast ratio, with missing/ambiguous tones explicit.

    All bank components uniquely within the native 2 Hz association of a v2
    component are summed. No ratio is assigned when either side is absent.
    Gated-on pairs use raw phasors; block-ramped mismatch is retained separately.
    """
    hs=60+np.arange(BLOCK)  # actual 30 ms, common newest-sample origin
    ratios=[];ramp_ratios=[];origins=[];freqs=[];amplitudes=[];choices=[]
    counts=Counter();prev0=np.r_[False,gate0[:-1]];prev1=np.r_[False,gate1[:-1]]
    alpha=np.arange(1,BLOCK+1)/BLOCK
    for i,origin in enumerate(seen-1):
        if origin<warm*FS:continue
        counts['frames_after_warmup']+=1
        f0,p0=v2['frequency'][i],v2['phasor'][i]
        f1,p1=bank['frequency'][i],bank['phasor'][i]
        ok0=np.isfinite(f0)&(np.abs(p0)>1e-12)
        ok1=np.isfinite(f1)&(np.abs(p1)>1e-12)
        f0,p0=f0[ok0],p0[ok0];f1,p1=f1[ok1],p1[ok1]
        counts['v2_components_before_gate']+=len(f0);counts['bank_components_before_gate']+=len(f1)
        if not gate0[i] or not gate1[i]:
            counts['frames_v2_only_gate' if gate0[i] else 'frames_bank_only_gate' if gate1[i] else 'frames_both_gates_closed']+=1
            continue
        counts['frames_both_gates_open']+=1
        distances=np.abs(f1[:,None]-f0[None,:]) if len(f0) else np.empty((len(f1),0))
        counts['bank_components_without_v2_match']+=int(np.sum(~np.any(distances<=2.,axis=1)))
        for j,(f,p) in enumerate(zip(f0,p0)):
            counts['eligible_v2_components']+=1
            near=distances[:,j]<=2.
            if not near.any():counts['v2_without_bank_match']+=1;continue
            if np.any(np.sum(distances[near]<=2.,axis=1)>1):counts['ambiguous_matches']+=1;continue
            a=p*np.exp(2j*np.pi*f*hs/FS)
            b=np.sum(p1[near,None]*np.exp(2j*np.pi*f1[near,None]*hs/FS),axis=0)
            if np.max(np.abs(b),initial=0)<=1e-12:counts['bank_sum_near_zero']+=1;continue
            ratio=b/a
            ramp0=float(prev0[i])+(float(gate0[i])-float(prev0[i]))*alpha
            ramp1=float(prev1[i])+(float(gate1[i])-float(prev1[i]))*alpha
            assert np.all(ramp0>0)
            ratios.append(ratio);ramp_ratios.append(ratio*ramp1/ramp0)
            origins.append(int(origin));freqs.append(float(f));amplitudes.append(float(abs(p)));choices.append(int(selected[i]))
            counts['matched_tone_frames']+=1
    arrays={'ratio':np.asarray(ratios,complex).reshape(-1,BLOCK),
      'ramped_ratio':np.asarray(ramp_ratios,complex).reshape(-1,BLOCK),
      'origin':np.asarray(origins,int),'frequency':np.asarray(freqs,float),
      'v2_amplitude':np.asarray(amplitudes,float),'selected':np.asarray(choices,int)}
    return arrays,dict(counts)


def ratio_summary(a,mask=None):
    mask=np.ones(len(a['origin']),bool) if mask is None else mask
    r=a['ratio'][mask]
    if not len(r):return {'matched_tone_frames':0}
    delta=np.sqrt(np.mean(np.abs(1-r)**2,axis=1))
    ramped=np.sqrt(np.mean(np.abs(1-a['ramped_ratio'][mask])**2,axis=1))
    cap=-20*np.log10(np.maximum(delta,1e-15))
    weight=a['v2_amplitude'][mask]**2
    pct=lambda x:dict(zip(['p05','p50','p95','p99','max'],map(float,np.percentile(x,[5,50,95,99,100]))))
    return {'matched_tone_frames':len(r),'mismatch':pct(delta),'ramped_mismatch':pct(ramped),
      'idealized_retained_attenuation_db':pct(cap),'fraction_mismatch_above_0_1':float(np.mean(delta>.1)),
      'fraction_mismatch_above_1':float(np.mean(delta>1)),
      'v2_energy_weighted_rms_mismatch':float(np.sqrt(np.sum(weight*delta**2)/max(weight.sum(),1e-30))),
      'absolute_phase_difference_deg':pct(np.abs(np.angle(r[:,0],deg=True))),
      'amplitude_ratio':pct(np.abs(r[:,0]))}


def freeze():
    base,_=completion.verified()
    inventory=[];excluded=[]
    sources=[('headroom',h.read(ROOT/'results-selector-headroom-01/audit/results.json')['cases']),
             ('fresh',h.read(ROOT/'results-selector-fresh-01/test/results.json')['cases'])]
    digests=set()
    for cohort,cases in sources:
        for c in cases:
            if cohort=='headroom' and c['kind']!='recording':continue
            path=c.get('local_arrays',c.get('arrays_path'))
            if not path:
                excluded.append({'id':c['id'],'title':c.get('title',c.get('file')),'reason':c.get('status',c.get('error','no decoded reference array'))});continue
            assert h.sha(ROOT/path)==c['arrays_sha256']
            with np.load(ROOT/path) as a:
                x=a['reference'];digest=h.array_digest(x)
                seconds=len(x)/FS
            if digest in digests:
                excluded.append({'id':c['id'],'reason':'duplicate normalized reference hash'});continue
            digests.add(digest)
            inventory.append({'id':c['id'],'title':c.get('title',c.get('file')),
                'cohort':c['cohort'],'acoustic':c.get('acoustic',True),
                'arrays_path':path,'arrays_sha256':c['arrays_sha256'],'reference_sha256':digest,
                'seconds':seconds,'prefix_seconds':c['prefix_seconds']})
    code=dict(base['code_sha256'])
    for name in ['anc_lab/selector_compatibility.py','tests/test_selector_compatibility.py']:
        code[name]=h.sha(ROOT/name)
    STUDY.mkdir(exist_ok=False)
    p={'created_utc':datetime.now(timezone.utc).isoformat(),'kind':'posthoc_seen_data_diagnostic_no_new_acceptance_test',
      'review_message':53,'code_sha256':code,'cases':inventory,'excluded':excluded,'workers':2,
      'input_scope':'Every decoded recording in the headroom inventory plus fresh-01; synthetic scenes excluded; no new audio; duplicate reference hashes removed. Full retained duration. Personal/electrical controls reported separately.',
      'room_scope':'All72 saved rooms for muting; exactly3 WWS_Aircompressor rooms for prefix-oracle comparison, at30ms only.',
      'oracle':'Each prefix-menu tone separately, two native per-tone basis waveforms (0/90 deg), linear earphone filter and delay, second-order causal ERB band around tone. Fit fixed coefficients over [1.5 s,prefix) to simulated ear, separately v2 and bank. Unconstrained/no cap during fit; report conditioning, native caps and prefix/suffix single-tone outcomes. No suffix fitting, no tuner changes. This is a signal-aware prefix calibration oracle, not merely the exact physical path ratio.',
      'ratio':'Native common-input grid seen-1, 30ms output, existing20ms bank group; after1.5s warmup. Both gates open, components amplitude>1e-12, unique2Hz association. Sum multiple uniquely matched bank components; count missing and ambiguous matches. Ratios at every sample of10ms output block; noDC. Also report gate-ramped ratios.',
      'statistics':'Per-source distributions of RMS |1-r| per tone-frame and -20log10(delta); v2-energy-weighted mismatch; report original scored suffix and frames within100ms of selector changes separately. No new pass/fail cutoff or intervention selected. Diagnostic0.1 means20dB only under ideal assumptions.',
      'formula_limits':'If a fixed scalar calibration cancels a single tone perfectly before switching and both methods represent the same physical tone/path, residual after a full switch is (1-r) times that tone. This is an idealized reference-domain identity, not a universal ANC ceiling or a bound on loss with existing residuals, room transfer, gating, clipping or tone mismatch.',
      'scope_limits':'Seen data; no fresh generalization, physical ANC or actual audibility result. No live engine changes, audio devices, new stress cohort or tuning-aware guard.'}
    h.write_new(STUDY/'protocol.json',p);h.write_new(STUDY/'frozen.json',{'sha256':h.sha(STUDY/'protocol.json')})
    print(json.dumps({'cases':len(inventory),'excluded':len(excluded),'seconds':sum(c['seconds'] for c in inventory),'protocol_sha256':h.sha(STUDY/'protocol.json')}))


def verified():
    p=h.read(STUDY/'protocol.json');assert h.sha(STUDY/'protocol.json')==h.read(STUDY/'frozen.json')['sha256']
    for name,digest in p['code_sha256'].items():assert h.sha(ROOT/name)==digest,name
    return p


def reference_task(c):
    assert h.sha(ROOT/c['arrays_path'])==c['arrays_sha256']
    with np.load(ROOT/c['arrays_path']) as a:x=a['reference'].copy()
    assert h.array_digest(x)==c['reference_sha256']
    with threadpool_limits(limits=1),cached_dpss(True):
        tr=stream(x,h.read(ROOT/'results-selector-fresh-01/protocol.json'))
        a,counts=matched_ratios(tr['v2'],tr['bank'][0],tr['v2']['gate'],tr['bank'][0]['gate'],tr['v2']['seen'],tr['selected'][:,0])
    transitions=np.flatnonzero(np.diff(tr['selected'][:,0],prepend=0)!=0)
    event_origins=(tr['v2']['seen']-1)[transitions]
    switch_mask=np.zeros(len(a['origin']),bool)
    for origin in event_origins:switch_mask|=np.abs(a['origin']-origin)<=200
    a['near_selector_switch']=switch_mask
    a['in_original_scored_suffix']=a['origin']>=round(c['prefix_seconds']*FS)
    path=STUDY/'ratios'/(c['id']+'.npz');np.savez_compressed(path,**a)
    result={**c,'counts':counts,'all':ratio_summary(a),
      'original_scored_suffix':ratio_summary(a,a['in_original_scored_suffix']),
      'near_selector_switch':ratio_summary(a,switch_mask),
      'selector_transitions':len(transitions),'transition_origins':event_origins.tolist(),
      'ratio_arrays_path':str(path.relative_to(ROOT)),'ratio_arrays_sha256':h.sha(path)}
    h.write_new(STUDY/'sources'/(c['id']+'.json'),result)
    return result


def reference_run():
    p=verified()
    (STUDY/'ratios').mkdir(exist_ok=False);(STUDY/'sources').mkdir(exist_ok=False)
    h.write_new(STUDY/'reference-start.json',{'started_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':h.sha(STUDY/'protocol.json')})
    results=[]
    with ProcessPoolExecutor(p['workers']) as pool:
        futures=[pool.submit(reference_task,c) for c in p['cases']]
        for future in as_completed(futures):
            result=future.result();results.append(result)
            print(json.dumps({'completed':len(results),'of':len(p['cases']),'id':result['id'],'pairs':result['all']['matched_tone_frames']}),flush=True)
    results.sort(key=lambda c:c['id'])
    h.write_new(STUDY/'reference-results.json',{'completed_utc':datetime.now(timezone.utc).isoformat(),'cases':results,
       'protocol_sha256':h.sha(STUDY/'protocol.json'),'interpretation':'Reference-domain disagreement; conditional idealized single-tone residual, not physical ANC.'})


def unit_sound(scene,arrays,frequency,phase):
    drive=replay(arrays,[ToneSetting(frequency,1.,phase)],.03).ravel()
    sound=scene['earphone_gain']*signal.lfilter(*scene['earphone'],drive)
    start=int(arrays['seen'][0])-1+60+scene['unreported']
    at=rooms.room.add_at(np.zeros(scene['n']),start,sound)
    return drive,at


def compressor():
    verified();coverage=h.read(rooms.STUDY/'coverage.json');out=[]
    for receipt in coverage['cases']:
        if receipt['source_id']!='old-013':continue
        scene,m=rooms.load_case(receipt)
        saved=h.read(rooms.STUDY/'scores'/(m['case_id']+'.json'))
        detail=next(d for d in saved['details'] if d['lead_ms']==30)
        off=scene['ears'][0];lo=scene['warm'];hi=scene['prefix']
        for tone in scene['tones']:
            f=tone['frequency'];half=erb_hz(f)/2
            sos=signal.butter(2,[max(20.,f-half),min(f+half,.45*FS)],btype='bandpass',fs=FS,output='sos')
            target=signal.sosfilt(sos,off);fits={}
            for method,arrays in [('v2',scene['trace']['v2']),('bank',scene['trace']['bank'][0])]:
                rendered=[unit_sound(scene,arrays,f,phase) for phase in (0.,90.)]
                basis=np.column_stack([signal.sosfilt(sos,y) for _,y in rendered])
                fit=fit_fixed(target,basis,lo,hi)
                if fit['identifiable']:
                    coef=np.asarray(fit['coefficients']);unclipped=np.column_stack([x for x,_ in rendered])@coef
                    cap=rooms.room.PROTOCOL['levels']['peak_cap'];start=int(arrays['seen'][0])-1+60+scene['unreported']
                    sound=scene['earphone_gain']*signal.lfilter(*scene['earphone'],np.clip(unclipped,-cap,cap))
                    on=rooms.room.add_at(off,start,sound);filtered=signal.sosfilt(sos,on)
                    fit.update(prefix_capped_band_gain_db=db(np.mean(target[lo:hi]**2),np.mean(filtered[lo:hi]**2)),
                        suffix_capped_band_gain_db=db(np.mean(target[hi+1000:]**2),np.mean(filtered[hi+1000:]**2)),
                        uncapped_drive_peak=float(np.max(np.abs(unclipped))),clipped_fraction=float(np.mean(np.abs(unclipped)>cap)))
                fits[method]=fit
            tune=next(s for s in detail['v2_tuning'] if s['frequency']==f)
            own=next(s for s in detail['chooser_tuning'] if s['frequency']==f)
            item={'case_id':m['case_id'],'frequency':f,'prefix_start_s':lo/FS,'prefix_end_s':hi/FS,
                  'v2':fits['v2'],'bank':fits['bank'],'v2_tuning':tune,'chooser_tuning':own,
                  'exact_physical_path_gain':float(abs(tone['w'])),
                  'exact_physical_path_phase_deg':float(np.angle(tone['w'],deg=True)%360)}
            if all(fit['identifiable'] for fit in fits.values()):
                item['oracle_phase_difference_deg']=phase_difference(fits['bank']['phase_deg'],fits['v2']['phase_deg'])
                item['oracle_gain_difference_db']=20*np.log10(max(fits['bank']['gain'],1e-30)/max(fits['v2']['gain'],1e-30))
                item['v2_tuned_phase_error_vs_own_oracle_deg']=phase_difference(tune['phase_deg'],fits['v2']['phase_deg'])
                item['chooser_tuned_phase_error_vs_bank_oracle_deg']=phase_difference(own['phase_deg'],fits['bank']['phase_deg'])
            out.append(item)
    h.write_new(STUDY/'compressor.json',{'completed_utc':datetime.now(timezone.utc).isoformat(),'tone_comparisons':out,
      'scope':'Single-tone ERB-band prefix-fit oracle, known simulated ear; no suffix fitting or changes to completed tuning.'})
    print(json.dumps({'compressor_tones':len(out),'focus':[x for x in out if x['case_id']=='old-013-r2' and x['v2_tuning']['kept']]}))


def all_clusters(arrays,rows):
    f=arrays['frequency'][rows];r=np.repeat(np.arange(len(rows))[:,None],f.shape[1],axis=1)
    ok=np.isfinite(f);f,r=f[ok],r[ok];presence=[]
    while len(f):
        centres,counts=np.unique(np.round(f*2)/2,return_counts=True);centre=centres[np.argmax(counts)]
        keep=np.abs(f-centre)<=2.;presence.append(len(np.unique(r[keep]))/len(rows));f,r=f[~keep],r[~keep]
    return presence


def muting():
    verified();coverage=h.read(rooms.STUDY/'coverage.json');out=[]
    for receipt in coverage['cases']:
        scene,m=rooms.load_case(receipt);c=h.read(rooms.STUDY/'scores'/(m['case_id']+'.json'))
        a=scene['arrays'];rows=np.flatnonzero((a['seen']>scene['warm'])&(a['seen']<=scene['prefix']))
        clusters=all_clusters(a,rows);ever=bool(np.isfinite(a['frequency'][rows]).any())
        for detail in c['details']:
            for method,key in [('v2','v2_tuning'),('chooser','chooser_tuning')]:
                entries=detail[key];valid=[x for x in entries if 'frequency' in x]
                active=sum(x['kept'] for x in valid)
                flags=Counter(flag for x in valid for flag in x['flags'])
                if not scene['tones']:reason='no_eligible_menu_intermittent_detections' if ever else 'no_eligible_menu_no_v2_detection'
                elif active:reason='active_setting'
                elif any('skipped' in x for x in entries):reason='prefix_too_short_for_sweep'
                elif flags['no quiet moment found: switched off']:reason='all_muted_including_missing_sweep'
                elif all('no benefit heard: switched off' in x['flags'] for x in valid):reason='all_muted_final_on_off_check'
                else:reason='unexplained_zero_settings'
                assert reason!='unexplained_zero_settings',(m['case_id'],entries)
                out.append({'case_id':m['case_id'],'source_id':m['source_id'],'cohort':m['cohort'],
                  'lead_ms':detail['lead_ms'],'tuned_on':method,'menu_tones':len(scene['tones']),
                  'prefix_ever_detected':ever,'max_cluster_presence':max(clusters,default=0.),
                  'active_settings':active,'reason':reason,'flags':dict(flags),'tones':valid,
                  'prefix_gate_open_fraction':float(np.mean(a['gate'][rows])) if len(rows) else None})
    counts={str(lead):{method:dict(Counter(c['reason'] for c in out if c['lead_ms']==lead and c['tuned_on']==method)) for method in ('v2','chooser')} for lead in (30,200)}
    h.write_new(STUDY/'muting.json',{'completed_utc':datetime.now(timezone.utc).isoformat(),'summary':counts,'rows':out,
      'limits':'Muted settings are classified from saved tuning summaries. Gain-limit flags constrain gain but do not themselves mute. No eligible menu is not the same as no tone ever detected. Real audibility unmeasured.'})
    print(json.dumps(counts,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=['freeze','reference','compressor','muting'])
    args=parser.parse_args()
    with threadpool_limits(limits=1):{'freeze':freeze,'reference':reference_run,'compressor':compressor,'muting':muting}[args.stage]()
