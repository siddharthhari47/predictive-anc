"""Audit saved room signals/settings without rerunning predictors or tuning."""
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
import hashlib
import json
import sys

ROOT = Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
sys.path.insert(0, str(ROOT))
import numpy as np
from scipy import signal
from threadpoolctl import threadpool_limits
from anc_lab.antihum import ToneSetting, replay, FS, BLOCK
from anc_lab import selector_room_study as study
from anc_lab import selector_room_completion as completion
from anc_lab import selector_room_baseline as baseline
from anc_lab import antihum_study as room
from anc_lab import selector_headroom as h

OUT = ROOT/'results-selector-tuning-01'
checked = 0
largest_error = 0.


def equal(a, b, label=''):
    global checked, largest_error
    checked += 1
    if b is None or isinstance(b, (str, bool)):
        assert a == b, (label, a, b)
    elif isinstance(b, dict):
        assert a.keys() == b.keys(), label
        for k in b: equal(a[k], b[k], label+'/'+k)
    elif isinstance(b, list):
        assert len(a) == len(b), label
        for i, (x,y) in enumerate(zip(a,b)): equal(x,y,label+'/'+str(i))
    else:
        assert np.isclose(a,b,rtol=1e-8,atol=1e-9), (label,a,b)
        largest_error=max(largest_error,abs(float(a)-float(b)))


def ratio(a,b):
    return float(10*np.log10(max(float(a),1e-30)/max(float(b),1e-30)))


def drive(trace, settings, lead, g, method):
    first=replay(trace['v2'],settings,lead)
    if method == 'v2': return first.ravel()
    second=replay(trace['bank'][g],settings,lead)
    return (first*trace['weights'][:,g,:,0]+second*trace['weights'][:,g,:,1]).ravel()


def add_sound(off, sound, start):
    on=off.copy()
    lo,hi=max(0,start),min(len(on),start+len(sound))
    if hi>lo:on[lo:hi]+=sound[lo-start:hi-start]
    return on


def recompute_metrics(off,on,first,tones,peak,clipped,active):
    sos=signal.butter(4,(35.,350.),fs=FS,btype='bandpass',output='sos')
    bo,bn=signal.sosfilt(sos,off),signal.sosfilt(sos,on)
    f,po=signal.welch(off[first:],FS,nperseg=min(len(off)-first,4*FS))
    _,pn=signal.welch(on[first:],FS,nperseg=min(len(on)-first,4*FS))
    near=np.zeros(len(f),bool)
    for tone in tones:near|=np.abs(f-tone)<=room.PROTOCOL['evaluation']['tone_halfwidth_hz']
    bands=[]
    for low,high,centre in room.third_octave_edges():
        keep=(f>=low)&(f<high)
        if keep.any():
            p0,p1=float(po[keep].sum()),float(pn[keep].sum())
            bands.append({'centre_hz':centre,'amplification_db':ratio(p1,p0),'off_power':p0,'on_power':p1})
    worst=max((b['amplification_db'],b['centre_hz']) for b in bands)
    width=round(room.PROTOCOL['evaluation']['window_s']*FS)
    windows=[ratio(np.mean(bo[k:k+width]**2),np.mean(bn[k:k+width]**2))
             for k in range(first,len(off)-width+1,width)]
    metrics={'band_db':ratio(np.mean(bo[first:]**2),np.mean(bn[first:]**2)),
      'broadband_db':ratio(np.mean(off[first:]**2),np.mean(on[first:]**2)),
      'tone_db':ratio(po[near].sum(),pn[near].sum()) if tones else None,
      'max_third_octave_amplification_db':worst[0],
      'worst_third_octave_hz':worst[1] if active else None,
      'worst_1s_band_db':min(windows) if windows else None,
      'drive_peak':peak,'clipped_fraction':clipped,'active_tones':active,'bands':bands}
    return metrics,bn


def aggregate(cases,coverage):
    result={}
    for lead in (30,200):
        result[str(lead)]={}
        for arm in ('chooser_reuse_v2','chooser_tuned'):
            paired=defaultdict(list);harms=[];clipping=[];windows=[]
            for c in cases:
                rows={r['arm']:r for r in c['rows'] if r['lead_ms']==lead}
                a,b=rows[arm],rows['v2_tuned']
                if a['tone_db'] is not None and b['tone_db'] is not None:
                    paired[c['source_id']].append(a['tone_db']-b['tone_db'])
                for x,y in zip(a['bands'],b['bands']):
                    assert x['centre_hz']==y['centre_hz']
                    if x['amplification_db']>1+1e-9 and y['amplification_db']<=1+1e-9:
                        harms.append({'case_id':c['case_id'],'source_id':c['source_id'],
                          'band_hz':x['centre_hz'],'candidate_db':x['amplification_db'],'v2_db':y['amplification_db']})
                if a['band_db']<-.5-1e-9 and b['band_db']>=-.5-1e-9:
                    harms.append({'case_id':c['case_id'],'source_id':c['source_id'],'band_hz':'35-350',
                      'candidate_db':-a['band_db'],'v2_db':-b['band_db']})
                if a['clipped_fraction']>b['clipped_fraction']+1e-6:
                    clipping.append({'case_id':c['case_id'],'candidate':a['clipped_fraction'],'v2':b['clipped_fraction']})
                for w in c['switch_windows']:
                    if w['lead_ms']==lead and w['complete_200ms_window']:
                        windows.append({'case_id':c['case_id'],'row':w['row'],'source_id':c['source_id'],
                                        'excess_db':w['excess_over_v2_db'][arm]})
            means={k:float(np.mean(v)) for k,v in paired.items()}
            values=np.array(list(means.values()))
            rng=np.random.default_rng(20261022)
            ci=np.percentile(values[rng.integers(len(values),size=(20000,len(values)))].mean(axis=1),[2.5,97.5]).tolist()
            violations=[w for w in windows if w['excess_db']>3+1e-9]
            point=bool(values.mean()>=-.5 and values.min()>=-1 and not harms and not violations and not clipping)
            enough=coverage[str(lead)]['exposed_complete_sources']>=6
            decision=('inconclusive_insufficient_switch_coverage' if not enough else
              'fails_simulated_noninferiority_or_harm_criteria' if not point else
              'inconclusive_noninferiority_interval' if ci[0]<-.5 else 'passes_bounded_simulation_criteria')
            result[str(lead)][arm]={'tonal_sources':len(values),'source_mean_paired_db':means,
              'mean_paired_db':float(values.mean()),'bootstrap95':ci,'worst_source_mean_db':float(values.min()),
              'switch_coverage_sufficient':enough,'point_criteria_passed':point,
              'new_boosts':harms,'switch_violations':violations,'extra_clipping':clipping,
              'maximum_switch_excess_db':max(w['excess_db'] for w in windows),'decision':decision,
              'role':'primary' if lead==30 and arm=='chooser_reuse_v2' else 'secondary_or_exploratory'}
    return result


def main():
    protocol,coverage=completion.verified()
    results=h.read(OUT/'results.json')
    equal([c['case_id'] for c in results['cases']],[c['case_id'] for c in coverage['cases']],'inclusion')
    exposure=[];expected_receipts={c['case_id']:c for c in coverage['cases']}
    baseline_scalars=0;case_hashes={}
    for i,c in enumerate(results['cases']):
        path=OUT/'scores'/(c['case_id']+'.json')
        equal(h.read(path),c,'case_saved')
        case_hashes[c['case_id']]=h.sha(path)
        scene,meta=study.load_case(expected_receipts[c['case_id']])
        off=scene['ears'][0];first=scene['prefix']+FS//2;trace=scene['trace']
        tones=meta['reference_tones_hz'];source=c['source_id']
        equal(c['prefix_switches'],meta['prefix_switches'],'prefix_switches')
        for g,lead_ms in enumerate((30,200)):
            lead=lead_ms/1000;start=int(trace['v2']['seen'][0])-1+round(lead*FS)+scene['unreported']
            detail=next(d for d in c['details'] if d['lead_ms']==lead_ms)
            v2=[ToneSetting(**s) for s in detail['v2_settings']]
            own=[ToneSetting(**s) for s in detail['chooser_settings']]
            filtered={};commands={}
            for arm,method,settings in [('v2_tuned','v2',v2),('chooser_reuse_v2','chooser',v2),('chooser_tuned','chooser',own),('zero','v2',[])]:
                command=drive(trace,settings,lead,g,method)
                commands[arm]=command
                cap=room.PROTOCOL['levels']['peak_cap']
                sound=scene['earphone_gain']*signal.lfilter(*scene['earphone'],np.clip(command,-cap,cap))
                on=add_sound(off,sound,start)
                metrics,filtered[arm]=recompute_metrics(off,on,first,tones,float(np.max(np.abs(command))),
                     float(np.mean(np.abs(command)>cap)),sum(s.gain>0 for s in settings))
                expected=next(r for r in c['rows'] if r['lead_ms']==lead_ms and r['arm']==arm)
                equal(metrics,{k:v for k,v in expected.items() if k not in ('lead_ms','arm')},'metrics/'+c['case_id']+'/'+arm)
            for e in meta['switches'][str(lead_ms)]:
                actual=next(w for w in c['switch_windows'] if w['lead_ms']==lead_ms and w['row']==e['row'])
                for k,v in e.items():equal(actual[k],v,'event/'+k)
                row=e['row'];lo=max(0,row-1)*BLOCK;hi=min(row+10,len(trace['v2']['seen']))*BLOCK
                exposure.append({'case_id':c['case_id'],'source_id':source,'lead_ms':lead_ms,
                    'row':row,'complete':e['complete_200ms_window'],'unit_menu_exposed':e['command_exposed'],
                    'v2_tuned_command':bool(np.max(np.abs(commands['v2_tuned'][lo:hi]),initial=0)>1e-12),
                    'reuse_tuned_command':bool(np.max(np.abs(commands['chooser_reuse_v2'][lo:hi]),initial=0)>1e-12),
                    'own_tuned_command':bool(np.max(np.abs(commands['chooser_tuned'][lo:hi]),initial=0)>1e-12)})
                if e['complete_200ms_window']:
                    a,b=e['arrival_sample']-200,e['arrival_sample']+200
                    powers={arm:float(np.mean(y[a:b]**2)) for arm,y in filtered.items()}
                    equal(powers,actual['band_powers'],'window_power')
                    equal({arm:ratio(powers[arm],powers['v2_tuned']) for arm in ('chooser_reuse_v2','chooser_tuned')},actual['excess_over_v2_db'],'window_ratio')
            # Reconstruct the fitted noncausal bound from saved coefficients,
            # applying each piecewise coefficient before either filter.
            oracle=detail['relaxed_retune_bound']
            fitted=np.zeros(len(trace['v2']['seen'])*BLOCK)
            arrival=start+np.arange(len(fitted))
            for coef in oracle['coefficients']:
                unit=drive(trace,[ToneSetting(coef['frequency_hz'],1.,coef['phase_basis_deg'])],lead,g,'chooser')
                keep=(arrival>=coef['first_sample'])&(arrival<coef['last_exclusive'])
                fitted+=unit*keep*coef['coefficient']
            sound=scene['earphone_gain']*signal.lfilter(*scene['earphone'],fitted)
            on=add_sound(off,sound,start)
            sos=signal.butter(4,(35.,350.),fs=FS,btype='bandpass',output='sos')
            equal(ratio(np.mean(signal.sosfilt(sos,off)[first:]**2),np.mean(signal.sosfilt(sos,on)[first:]**2)),oracle['band_db'],'oracle_reconstruction')
        if c['cohort']=='original48':
            old=h.read(baseline.STUDY/'cases'/f'{meta["old_index"]:03d}.json')
            for lead in (30,200):
                actual=next(r for r in c['rows'] if r['arm']=='v2_tuned' and r['lead_ms']==lead)
                expected=next(r for r in old['rows'] if r['arm']=='tuned_sigma_1' and r['lead_ms']==lead and r['move_cm']==r['drift_ms']==0)
                for k,v in actual.items():
                    if k in expected and k!='arm':equal(v,expected[k],'baseline/'+k);baseline_scalars+=1
                expected=[{k:v for k,v in t.items() if k not in ('file','room','lead_ms','sigma_db')} for t in old['tuning'] if t['lead_ms']==lead and t['sigma_db']==1.]
                actual=next(d['v2_tuning'] for d in c['details'] if d['lead_ms']==lead)
                equal(actual,expected,'baseline_tuning')
        if (i+1)%12==0:print(json.dumps({'verified_cases':i+1}),flush=True)
    equal(aggregate(results['cases'],coverage['summary']),results['summary'],'all_aggregate')
    equal(aggregate([c for c in results['cases'] if c['cohort']=='original48'],coverage['original_summary']),results['original_only'],'original_aggregate')
    # Receipt hashes and all older frozen code remain intact.
    completion.verified()
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'passed':True,
      'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'results_sha256':h.sha(OUT/'results.json'),'case_sha256':case_hashes,
      'checks_including_nested_scalars_and_structures':checked,'maximum_numeric_absolute_difference':largest_error,
      'cases':len(results['cases']),'score_rows':sum(len(c['rows']) for c in results['cases']),
      'switch_windows':len(exposure),'exposure_diagnostic_posthoc':exposure,
      'original_v2_scalar_metrics_rechecked':baseline_scalars,
      'scope':'Saved traces rendered with the native renderer; independent placement, filtering, metrics, switch powers, oracle coefficient reconstruction, source bootstrap, harm rules and original baseline comparison. No predictor or tuning rerun. Native tone renderer and SciPy primitives are shared, so this is not an independent implementation of the whole algorithm.'}
    h.write_new(OUT/'verification.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('case_sha256','exposure_diagnostic_posthoc')},indent=2))


if __name__=='__main__':
    with threadpool_limits(limits=1):main()
