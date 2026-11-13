"""Frozen offline timing gate for the unchanged chooser and a parity-preserving cache."""
from concurrent.futures import ProcessPoolExecutor,as_completed
from datetime import datetime,timezone
from pathlib import Path
from collections import defaultdict
import argparse,json,platform,time
import numpy as np
import psutil
from threadpoolctl import threadpool_limits,threadpool_info
from . import selector_headroom as h
from .selector_stream_profile import replay
from .selection_study import FS,BLOCK

ROOT=h.ROOT;STUDY=ROOT/'results-selector-timing-01'
FRESH=ROOT/'results-selector-fresh-01'
IDS=[1,2,4,5,10,21,18,25,26,35,7,23]

def frozen_hashes():
    p=h.read(FRESH/'protocol.json');hashes=dict(p['code_sha256'])
    a=h.read(FRESH/'decoder-amendment-02.json')
    for name,c in a['code_changes'].items():hashes[name]=c['after_sha256']
    for name in ('anc_lab/selector_stream_profile.py','anc_lab/selector_timing_study.py',
                 'tests/test_selector_stream_profile.py','docs/SELECTOR_TIMING.md','docs/SELECTOR_TUNING_CHECK.md'):
        hashes[name]=h.sha(ROOT/name)
    return hashes

def freeze():
    STUDY.mkdir(exist_ok=False)
    old=h.read(FRESH/'test/results.json');lookup={c['id']:c for c in old['cases']}
    cases=[lookup[f'fresh-{i:03d}'] for i in IDS]
    assert all(c['status']=='scored' for c in cases)
    p={'created_utc':datetime.now(timezone.utc).isoformat(),'kind':'offline_forecast_chain_timing',
       'fresh_protocol_sha256':h.sha(FRESH/'protocol.json'),'fresh_results_sha256':h.sha(FRESH/'test/results.json'),
       'code_sha256':frozen_hashes(),'cases':[{'id':c['id'],'title':c['title'],'arrays_path':c['arrays_path'],
            'arrays_sha256':c['arrays_sha256']} for c in cases],
       'input_seconds':30,'repetitions':2,'order':'declared order, then reverse; original/cache order alternates per source and repetition',
       'variants':['original','cached_dpss'],'baseline':'v2 alone separately, including its detector and gate',
       'criterion':'All per-source, per-repetition full-core wall p99 <5 ms per 10 ms block; max and misses reported, not hidden.',
       'parity':{'atol':1e-9,'rtol':1e-8,'decisions':'exact','variants':'both, every declared source'},
       'quiet':{'preflight_attempts':3,'seconds_per_attempt':10,'maximum_system_cpu_percent':5.,
          'during_max_background_percent':5.,'processor':'least busy permitted logical CPU in selected window; ties by index',
          'nonquiet':'Run diagnostic only; no quiet-machine pass or definitive quiet failure'},
       'scope':'2 kHz forecast core, both horizons, independent selectors, v2/fade, gates, L2 filtering/error/history and crossfade. Excludes file loading, normalization/resampling, UI, device-rate synthesis, audio callbacks and transport.',
       'safety':'No audio devices or live-engine changes; all input/forecast arrays local.',
       'checks_before_freeze':{'unit_tests':3,'seconds':.174},
       'fallback':'Only deterministic DPSS cache, new empty cache each run; original detectors and settings untouched. Reduced-bank models require separate accuracy studies.'}
    h.write_new(STUDY/'protocol.json',p)
    h.write_new(STUDY/'frozen.json',{'sha256':h.sha(STUDY/'protocol.json')})
    print(json.dumps({'protocol_sha256':h.sha(STUDY/'protocol.json'),'cases':len(cases)},indent=2))

def verified():
    p=h.read(STUDY/'protocol.json')
    assert h.sha(STUDY/'protocol.json')==h.read(STUDY/'frozen.json')['sha256']
    for name,digest in p['code_sha256'].items():assert h.sha(ROOT/name)==digest,name
    assert h.sha(FRESH/'test/results.json')==p['fresh_results_sha256']
    return p

def load(entry,seconds=30):
    path=ROOT/entry['arrays_path'];assert h.sha(path)==entry['arrays_sha256']
    with np.load(path) as a:
        keep=a['origins']<round(seconds*FS)
        x=a['reference'][:round(seconds*FS)].copy();origins=a['origins'][keep].copy()
        expected={m:a[m][keep].copy() for m in ('v2_gated','fade0.1_linear_gated','causal_L2')}
        selected=np.column_stack([a['selected_h20'][keep],a['selected_h120'][keep]])
    return x,origins,expected,selected

def parity_task(entry):
    p=h.read(FRESH/'protocol.json');x,origins,expected,selected=load(entry)
    checks=[]
    with threadpool_limits(limits=1):
        for cache in (False,True):
            output,choices,info=replay(x,origins,p,cache=cache)
            errors={m:float(np.max(np.abs(output[m]-expected[m]))) for m in output}
            for m in output:np.testing.assert_allclose(output[m],expected[m],rtol=1e-8,atol=1e-9,err_msg=f'{entry["id"]}/{cache}/{m}')
            np.testing.assert_array_equal(choices,selected)
            assert info['max_retained_input_samples']<=2300
            checks.append({'cache':cache,'max_abs_error':errors,'exact_choices':True,'bounded_state':info})
    row={'id':entry['id'],'passed':True,'checks':checks,'origins':len(origins)}
    for check in checks:
        for name in ('wall_ms','thread_cpu_ms','parts_ms'):check['bounded_state'].pop(name)
    h.write_new(STUDY/'parity'/f'{entry["id"]}.json',row)
    return row

def parity():
    p=verified();stage=STUDY/'parity';stage.mkdir(exist_ok=False)
    h.write_new(stage/'start.json',{'started_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':h.sha(STUDY/'protocol.json')})
    rows=[]
    with ProcessPoolExecutor(2) as pool:
        futures=[pool.submit(parity_task,e) for e in p['cases']]
        for f in as_completed(futures):
            rows.append(f.result());print('Parity',len(rows),'/',len(futures),rows[-1]['id'],flush=True)
    h.write_new(stage/'complete.json',{'passed':all(r['passed'] for r in rows),'sources':len(rows),'variants':2,
         'source_variant_method_comparisons':len(rows)*2*3,'exact_decision_arrays':len(rows)*2,
         'completed_utc':datetime.now(timezone.utc).isoformat()})

def stat(x):
    x=np.asarray(x,float)
    return {'count':len(x),'mean':float(x.mean()),'p50':float(np.percentile(x,50)),
        'p95':float(np.percentile(x,95)),'p99':float(np.percentile(x,99)),'max':float(x.max()),
        'over_5ms':int(np.sum(x>5)),'over_10ms':int(np.sum(x>10))}

def busy_seconds(cpu):
    return sum(cpu)-getattr(cpu,'idle',0)-getattr(cpu,'iowait',0)

def benchmark():
    p=verified();assert h.read(STUDY/'parity/complete.json')['passed']
    stage=STUDY/'timing';stage.mkdir(exist_ok=False)
    proc=psutil.Process();affinity=proc.cpu_affinity();windows=[];quiet=False
    for attempt in range(3):
        samples=[psutil.cpu_percent(interval=1,percpu=True) for _ in range(10)]
        means=np.mean(samples,axis=0);system=float(means.mean());quiet=system<=5
        windows.append({'attempt':attempt+1,'per_cpu_samples':samples,'system_mean_percent':system,'qualifies':quiet})
        print('Quiet preflight',attempt+1,round(system,2),'percent',quiet,flush=True)
        if quiet:break
    cpu=min(affinity,key=lambda i:(means[i],i))
    environment={'platform':platform.platform(),'python':platform.python_version(),'logical_cpus':psutil.cpu_count(),
        'physical_cores':psutil.cpu_count(logical=False),'affinity_before':affinity,'selected_logical_cpu':cpu,
        'quiet_preflight':quiet,'preflight_windows':windows,'threadpools':threadpool_info(),
        'started_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':h.sha(STUDY/'protocol.json')}
    h.write_new(stage/'environment.json',environment)
    rows=[];original_protocol=h.read(FRESH/'protocol.json')
    try:
        proc.cpu_affinity([cpu])
        with threadpool_limits(limits=1):
            for repetition in range(2):
                cases=p['cases'] if repetition==0 else list(reversed(p['cases']))
                for i,entry in enumerate(cases):
                    x,origins,expected,selected=load(entry)
                    variants=['original','cached_dpss'] if (i+repetition)%2==0 else ['cached_dpss','original']
                    variants+=['v2_only']
                    for variant in variants:
                        before=psutil.cpu_times();own=proc.cpu_times();start=time.perf_counter()
                        output,choices,measure=replay(x,origins,original_protocol,cache=variant=='cached_dpss',
                            bank_enabled=variant!='v2_only',profile=True)
                        elapsed=time.perf_counter()-start;after=psutil.cpu_times();own_after=proc.cpu_times()
                        own_seconds=own_after.user+own_after.system-own.user-own.system
                        background=max(0.,(busy_seconds(after)-busy_seconds(before)-own_seconds)/(elapsed*psutil.cpu_count())*100)
                        comparable=['v2_gated'] if variant=='v2_only' else list(output)
                        for m in comparable:np.testing.assert_allclose(output[m],expected[m],rtol=1e-8,atol=1e-9)
                        if variant!='v2_only':np.testing.assert_array_equal(choices,selected)
                        name=f'{entry["id"]}-r{repetition+1}-{variant}'
                        path=stage/(name+'.npz')
                        np.savez_compressed(path,origins=origins,wall_ms=measure['wall_ms'],thread_cpu_ms=measure['thread_cpu_ms'],parts_ms=measure['parts_ms'])
                        late=origins>=15*FS
                        row={'id':entry['id'],'variant':variant,'repetition':repetition+1,
                            'wall_ms':stat(measure['wall_ms']),'thread_cpu_ms':stat(measure['thread_cpu_ms']),
                            'late_wall_ms':stat(measure['wall_ms'][late]),
                            'parts_ms':{n:stat(measure['parts_ms'][:,j]) for j,n in enumerate(measure['part_names'])},
                            'elapsed_seconds':elapsed,'estimated_background_cpu_percent':background,
                            'quiet_qualified':bool(quiet and background<=5),'parity_passed':True,
                            'sample_path':str(path.relative_to(ROOT)),'sample_sha256':h.sha(path)}
                        h.write_new(stage/(name+'.json'),row);rows.append(row)
                        print(json.dumps({'completed':len(rows),'of':len(p['cases'])*2*3,'id':entry['id'],'variant':variant,
                            'p99_ms':round(row['wall_ms']['p99'],3),'quiet':row['quiet_qualified']}),flush=True)
    finally:proc.cpu_affinity(affinity)
    summary={}
    for variant in ('original','cached_dpss','v2_only'):
        subset=[r for r in rows if r['variant']==variant];qualified=all(r['quiet_qualified'] for r in subset)
        budget=all(r['wall_ms']['p99']<5 for r in subset)
        summary[variant]={'runs':len(subset),'all_quiet':qualified,'all_observed_p99_under_5ms':budget,
            'worst_p99_ms':max(r['wall_ms']['p99'] for r in subset),'maximum_block_ms':max(r['wall_ms']['max'] for r in subset),
            'total_blocks':sum(r['wall_ms']['count'] for r in subset),'over_10ms_blocks':sum(r['wall_ms']['over_10ms'] for r in subset),
            'decision':('pass_forecast_core_budget' if budget else 'fail_forecast_core_budget') if qualified else 'inconclusive_quiet_machine_gate_contended_diagnostic'}
    h.write_new(stage/'results.json',{'environment':environment,'runs':rows,'summary':summary,'completed_utc':datetime.now(timezone.utc).isoformat()})
    h.write_new(STUDY/'SUMMARY.json',summary)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=['freeze','parity','benchmark'])
    args=parser.parse_args();{'freeze':freeze,'parity':parity,'benchmark':benchmark}[args.stage]()
