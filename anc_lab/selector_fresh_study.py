"""One frozen fresh test of the existing two-second rule. Offline only."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import subprocess
import time

import numpy as np
from threadpoolctl import threadpool_limits

from . import selector_headroom as h
from .real_hum_study import load_any, prominent_tones, tonal_fraction
from .selection_study import BLOCK, FS, horizon_setup

ROOT=h.ROOT
STUDY=ROOT/'results-selector-fresh-01'
METHODS=('zero','v2_gated','joint_gated','fade0.1_linear_gated','prefix_ar','causal_L2')


def paired_summary(values, resamples=50000, seed=20261021):
    """One equally weighted paired difference per source; never per window."""
    values=np.asarray(values,dtype=float)
    if not len(values):
        return {'n':0,'mean_db':None,'median_db':None,'mean_bootstrap95':None}
    if not np.isfinite(values).all():
        raise ValueError('Non-finite paired source score')
    rng=np.random.default_rng(seed)
    means=np.empty(resamples)
    for start in range(0,resamples,1000):
        size=min(1000,resamples-start)
        means[start:start+size]=values[rng.integers(0,len(values),(size,len(values)))].mean(axis=1)
    out={'n':len(values),'mean_db':float(values.mean()),'median_db':float(np.median(values)),
         'mean_bootstrap95':np.percentile(means,[2.5,97.5]).tolist(),
         'minimum_db':float(values.min()),'maximum_db':float(values.max())}
    for label,tolerance in [('numerical',1e-8),('practical',.01)]:
        wins=int(np.sum(values>tolerance)); losses=int(np.sum(values< -tolerance))
        out[label]={'tolerance_db':tolerance,'wins':wins,'losses':losses,'ties':len(values)-wins-losses}
    return out


def score(case,method,horizon=20):
    return next(s for s in case['scores'] if s['method']==method and s['horizon_start_ms']==horizon)


def evaluate(cases, resamples=50000):
    usable=[c for c in cases if c.get('status')=='scored']
    tonal=[c for c in usable if c['reference_tones_hz']]
    all_methods={}
    for method in METHODS:
        horizons={}
        for horizon in (20,120):
            values=[score(c,method,horizon)['tone_band_gain_db']-score(c,'v2_gated',horizon)['tone_band_gain_db'] for c in tonal]
            stat=paired_summary(values,resamples=resamples)
            stat['strong_losses_over_1db']=[{'id':c['id'],'title':c['title'],
                'paired_gain_db':score(c,method,horizon)['tone_band_gain_db']-score(c,'v2_gated',horizon)['tone_band_gain_db']}
                for c in tonal if score(c,'v2_gated',horizon)['tone_band_gain_db']>=3 and
                score(c,method,horizon)['tone_band_gain_db']-score(c,'v2_gated',horizon)['tone_band_gain_db']< -1]
            stat['band_boost_cases']=sum(score(c,method,horizon)['third_octave_boosts_over_1db']>0 for c in usable)
            stat['whole_band_boost_cases']=sum(score(c,method,horizon)['band_gain_db']< -.5 for c in usable)
            stat['whole_band_gain_mean_db']=float(np.mean([score(c,method,horizon)['band_gain_db'] for c in usable])) if usable else None
            horizons[str(horizon)]=stat
        all_methods[method]=horizons
    candidate=all_methods['causal_L2'];base=all_methods['v2_gated']
    ci=candidate['20']['mean_bootstrap95']
    criteria={
        'at_least_30_usable_recordings':len(usable)>=30,
        'at_least_20_tonal_recordings':len(tonal)>=20,
        'mean_paired_20ms_ci_lower_above_zero':bool(ci is not None and ci[0]>0),
        'no_strong_20ms_loss_over_1db':not candidate['20']['strong_losses_over_1db'],
        'no_more_band_boost_cases_both_horizons':sum(candidate[str(t)]['band_boost_cases'] for t in (20,120))<=sum(base[str(t)]['band_boost_cases'] for t in (20,120)),
        'no_whole_band_boost_cases_both_horizons':sum(candidate[str(t)]['whole_band_boost_cases'] for t in (20,120))==0,
    }
    adequate=criteria['at_least_30_usable_recordings'] and criteria['at_least_20_tonal_recordings']
    decision='inconclusive_insufficient_eligible_sources' if not adequate else ('pass_frozen_offline_criteria' if all(criteria.values()) else 'fail_frozen_offline_criteria')
    return {'usable_sources':len(usable),'tonal_sources':len(tonal),'methods':all_methods,
            'criteria':criteria,'decision':decision,
            'interpretation':'Source-bootstrap uncertainty is conditional on a purposive public collection. One uploader/author per source does not prove population representativeness. This is reference prediction, not physical ANC.'}


def score_existing(x,grid,keep,predictions,tones):
    """Use the unchanged selector on both horizons and score actual faded output."""
    _,_,groups=horizon_setup()
    mixed=np.zeros_like(predictions['zero']);details={};trace={}
    for columns,horizons in groups:
        target=x[grid[:,None]+horizons]
        arms=np.stack([predictions[m][:,columns] for m in h.ARMS])
        output,info=h.causal_mix(target,arms,grid,int(horizons[-1]),2.)
        mixed[:,columns]=output
        label=str(round((horizons[0]-1)*1000/FS))
        trace['selected_h'+label]=info.pop('selected')
        trace['matured_h'+label]=info.pop('matured_rows')
        details[label]=info
    predictions={**predictions,'causal_L2':mixed}
    rows=h.s1.score_forecasts(x,grid[keep],{m:predictions[m][keep] for m in METHODS},tones)
    return rows,predictions,details,trace


def forecasts(x,prefix,grid,protocol):
    live=[m for m in protocol['methods'] if m['kind']!='prefix_ar']
    predictions,info=h.s2.run_methods(x,grid,np.ones(len(grid),bool),live,protocol['v2'],prefix)
    ar,arinfo=h.s2.run_methods(x,grid,grid>=prefix,[{'name':'prefix_ar','kind':'prefix_ar'}],protocol['v2'],prefix)
    predictions['prefix_ar']=np.zeros_like(predictions['zero'])
    predictions['prefix_ar'][grid>=prefix]=ar['prefix_ar']
    info.update(arinfo)
    return predictions,info


def grid_for_length(samples):
    _,horizons,_=horizon_setup()
    prefix=int(.4*samples)
    grid=np.arange(BLOCK*50,samples-int(max(horizons)),BLOCK)
    keep=grid>=prefix
    return prefix,grid,keep


def needs_container_decode(entry,download):
    """Commons calls some Ogg videos application/ogg; use container metadata too."""
    media_type=download.get('representation',{}).get('metadata',{}).get('type','')
    return (entry['mime'].startswith('video/') or media_type.startswith('video/')
            or Path(entry['file']).suffix.lower() in ('.ogv','.webm','.mp4','.mkv'))


def task(args):
    entry,download,protocol=args
    started=time.perf_counter()
    result={**entry,'status':'excluded'}
    if download['status']!='verified':
        result['reason']=download['reason']
    else:
        path=ROOT/download['local_path']
        assert h.sha(path)==download['sha256']
        decoded=path
        if needs_container_decode(entry,download):
            decoded=STUDY/'test/decoded'/f"{entry['id']}.wav"
            # Preserve all channels and the original rate. load_any uses channel zero.
            process=subprocess.run([protocol['decoder']['path'],'-nostdin','-v','error','-n','-i',str(path),
                '-t','90','-map','0:a:0','-vn','-c:a','pcm_f64le',str(decoded)],capture_output=True,text=True,timeout=180)
            if process.returncode:
                result['reason']='No decodable first audio track: '+process.stderr[-700:]
                h.write_new(STUDY/'test/cases'/f"{entry['id']}.json",result)
                return result
        try:
            x,info=load_any(decoded,max_seconds=90.)
        except Exception as exc:
            result['reason']=f'Audio decode failure: {type(exc).__name__}: {exc}'
        else:
            prefix,grid,keep=grid_for_length(len(x))
            seconds=float(keep.sum()*BLOCK/FS)
            result.update(audio=info,actual_scored_seconds_per_horizon=seconds,prefix_seconds=prefix/FS)
            if seconds<30:
                result['reason']='Fewer than 30 seconds of actual scored target blocks'
            elif np.std(x[:prefix])<1e-12:
                result['reason']='Silent/constant calibration prefix; normalization undefined'
            else:
                with threadpool_limits(limits=1):
                    x=(x-float(np.mean(x[:prefix])))/float(np.std(x[:prefix]))
                    predictions,method_info=forecasts(x,prefix,grid,protocol)
                    tones=prominent_tones(x[prefix:])
                    rows,predictions,details,trace=score_existing(x,grid,keep,predictions,tones)
                arrays=STUDY/'test/arrays'/f"{entry['id']}.npz"
                np.savez_compressed(arrays,reference=x,origins=grid,keep=keep,
                    **{m:predictions[m] for m in METHODS},**trace)
                result.update(status='scored',reference_tones_hz=tones,
                    reference_tone_band_power_fraction=tonal_fraction(x[prefix:],tones),
                    scores=rows,selector_details=details,method_info=method_info,
                    arrays_path=str(arrays.relative_to(ROOT)),arrays_sha256=h.sha(arrays))
            if decoded!=path and decoded.exists():
                result['decoded_path']=str(decoded.relative_to(ROOT))
                result['decoded_sha256']=h.sha(decoded)
    result['runtime_seconds']=time.perf_counter()-started
    h.write_new(STUDY/'test/cases'/f"{entry['id']}.json",result)
    return result


def run(workers=4):
    protocol=h.read(STUDY/'protocol.json')
    hashes=dict(protocol['code_sha256'])
    amendment_path=STUDY/'decoder-amendment-02.json'
    if amendment_path.exists():
        amendment=h.read(amendment_path)
        assert h.sha(amendment_path)==h.read(STUDY/'decoder-amendment-frozen.json')['sha256']
        assert amendment['original_protocol_sha256']==h.sha(STUDY/'protocol.json')
        assert amendment['before_fresh_decoding_and_scoring'] is True
        for name,change in amendment['code_changes'].items():
            assert hashes[name]==change['before_sha256']
            assert h.sha(ROOT/change['preserved_original'])==change['before_sha256']
            hashes[name]=change['after_sha256']
        for name,digest in amendment['added_tests_sha256'].items():assert h.sha(ROOT/name)==digest,name
    for name,digest in hashes.items():assert h.sha(ROOT/name)==digest,name
    assert h.sha(Path(protocol['decoder']['path']))==protocol['decoder']['sha256']
    manifest=h.read(STUDY/'download/manifest.json')
    assert manifest['protocol_sha256']==h.sha(STUDY/'protocol.json')
    stage=STUDY/'test';stage.mkdir(exist_ok=False)
    for name in ('cases','arrays','decoded'):(stage/name).mkdir()
    h.write_new(stage/'execution.json',{'started_utc':datetime.now(timezone.utc).isoformat(),
        'protocol_sha256':h.sha(STUDY/'protocol.json'),'manifest_sha256':h.sha(STUDY/'download/manifest.json'),'workers':workers})
    downloads={d['id']:d for d in manifest['files']}
    start=time.perf_counter();cases=[]
    with ProcessPoolExecutor(workers) as pool:
        futures=[pool.submit(task,(entry,downloads[entry['id']],protocol)) for entry in protocol['sources']]
        for future in as_completed(futures):
            case=future.result();cases.append(case)
            print(json.dumps({'completed':len(cases),'planned':len(futures),'id':case['id'],
                'status':case['status'],'elapsed_minutes':round((time.perf_counter()-start)/60,2)}),flush=True)
    cases.sort(key=lambda c:c['id'])
    results={'protocol':protocol,'cases':cases,'completed_utc':datetime.now(timezone.utc).isoformat(),
        'runtime_seconds':time.perf_counter()-start}
    h.write_new(stage/'results.json',results)
    summary=evaluate(cases)
    h.write_new(STUDY/'SUMMARY.json',summary)
    h.write_new(stage/'complete.json',{'protocol_sha256':h.sha(STUDY/'protocol.json'),
        'results_sha256':h.sha(stage/'results.json'),'summary_sha256':h.sha(STUDY/'SUMMARY.json')})
    print(json.dumps({k:summary[k] for k in ('usable_sources','tonal_sources','criteria','decision')},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args()
    run(args.workers)
