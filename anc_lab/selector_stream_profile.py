"""Offline-only bounded-state adapter for timing the frozen L2 forecast chain.

No audio imports, no engine integration. Frozen scientific modules are unchanged.
"""
from collections import deque
from contextlib import contextmanager
import time
import numpy as np
from scipy import signal

from . import selector_headroom as h
from .selection_study import FS, BLOCK, horizon_setup
from .tone_selection import ToneSelector, SelectedToneForecaster


@contextmanager
def cached_dpss(enabled=False):
    """Scoped, empty-on-entry cache of deterministic tapers; no predictor settings change."""
    original=signal.windows.dpss
    cache={}
    def get(*args,**kwargs):
        key=(args,tuple(sorted(kwargs.items())))
        if key not in cache:
            value=original(*args,**kwargs)
            if not isinstance(value,np.ndarray):raise TypeError('This cache expects array DPSS results')
            value.setflags(write=False)
            cache[key]=value
        return cache[key]
    if enabled:signal.windows.dpss=get
    try:yield cache
    finally:signal.windows.dpss=original


class MaturedGate:
    """Original shared-short-horizon gate; queued shadow forecasts only."""
    def __init__(self,groups,config):
        assert config['shared_group']==0
        self.columns,self.horizons=groups[0]
        self.config=config
        self.pending=deque()
        self.reference=deque(maxlen=config['lookback'])
        self.errors=deque(maxlen=config['lookback'])

    def step(self,past,origin,shadow):
        offset=origin-len(past)+1
        while self.pending and self.pending[0][0]+self.horizons[-1]<=origin:
            old,pred=self.pending.popleft()
            target=past[old+self.horizons-offset]
            self.reference.append(float(np.sum(target**2)))
            self.errors.append(np.sum((target[None,:]-pred)**2,axis=1))
        enabled=np.zeros(len(shadow),bool)
        if len(self.reference)>=self.config['min_matured']:
            reference=max(float(np.sum(self.reference)),1e-30)
            errors=np.maximum(np.sum(self.errors,axis=0),1e-30)
            enabled=10*np.log10(reference/errors)>=self.config['min_gain_db']
        self.pending.append((origin,shadow[:,self.columns].copy()))
        return shadow*enabled[:,None],enabled


class MaturedMixer:
    """Streaming equivalent of selector_headroom.causal_mix for one horizon."""
    def __init__(self,horizons):
        self.horizons=np.asarray(horizons)
        self.pending=deque()
        self.sos=signal.butter(4,(35.,350.),fs=FS,btype='bandpass',output='sos')
        self.zi=np.zeros((len(self.sos),3,2))
        self.total=np.zeros(3)
        self.cumulative=deque([self.total.copy()],maxlen=201)
        self.matured=0
        self.weights=np.array([1.,0.,0.])
        self.start=self.weights.copy();self.goal=self.weights.copy()
        self.fade_n=round(.1*FS);self.elapsed=self.fade_n
        self.selected=0;self.switches=0

    def step(self,past,origin,arms):
        offset=origin-len(past)+1
        while self.pending and self.pending[0][0]+self.horizons[-1]<=origin:
            old,pred=self.pending.popleft()
            target=past[old+self.horizons-offset]
            filtered,self.zi=signal.sosfilt(self.sos,target[None,:]-pred,axis=1,zi=self.zi)
            self.total=self.total+np.sum(filtered**2,axis=1)
            self.cumulative.append(self.total.copy());self.matured+=1
        if origin>=3*FS and self.matured>=200 and self.elapsed>=self.fade_n:
            energy=np.maximum(self.cumulative[-1]-self.cumulative[0],1e-30)
            best=int(np.argmin(energy))
            if best!=self.selected and energy[self.selected]>=10**.1*energy[best]:
                self.start=self.weights.copy();self.goal=np.eye(3)[best]
                self.selected=best;self.elapsed=0;self.switches+=1
        alpha=np.clip((self.elapsed+np.arange(1,BLOCK+1))/self.fade_n,0.,1.)
        weights=self.start[None,:]+alpha[:,None]*(self.goal-self.start)[None,:]
        output=np.sum(weights.T*arms,axis=0)
        self.weights=weights[-1];self.elapsed+=BLOCK
        self.pending.append((origin,arms.copy()))
        return output


class ForecastChain:
    """Block input, independent original selectors, gates and rendered L2 output."""
    def __init__(self,protocol,first_sample,bank_enabled=True):
        self.protocol=protocol;self.bank_enabled=bank_enabled
        self.v2=protocol['v2']
        _,self.horizons,self.groups=horizon_setup()
        self.selector=ToneSelector(FS,**self.v2['selector']);self.selector.reset()
        self.forecaster=SelectedToneForecaster(FS,self.selector,**self.v2['forecaster'])
        self.active=[];self.next_update=self.selector.step-1
        self.bank=h.s2.make_bank(next(m for m in protocol['methods'] if m['kind']=='react'),self.v2) if bank_enabled else None
        self.gate=MaturedGate(self.groups,self.v2['gate'])
        self.mixers=[MaturedMixer(hz) for _,hz in self.groups] if bank_enabled else []
        self.history=np.array([first_sample],float);self.origin=0
        self.keep=self.selector.window+int(max(self.horizons))+2*BLOCK
        self.last_parts={}

    def push(self,block,profile=False):
        self.history=np.concatenate([self.history,np.asarray(block,float)])[-self.keep:]
        self.origin+=len(block)
        past=self.history;offset=self.origin-len(past)+1
        before=time.perf_counter_ns() if profile else 0
        if self.bank is not None:self.bank.push(block)
        after_bank=time.perf_counter_ns() if profile else 0
        while self.next_update<=self.origin:
            end=self.next_update-offset+1
            self.active=self.selector.update(past[max(0,end-self.selector.window):end])
            self.next_update+=self.selector.step
        after_selector=time.perf_counter_ns() if profile else 0
        if self.origin<BLOCK*50:
            return None
        local=len(past)-1
        # The existing forecaster handles amplitude release and least-squares fits.
        v2=self.forecaster.predict(past,[local],self.horizons,decisions=[(local,self.active)])[0]
        fade=self.bank.forecast(self.horizons) if self.bank is not None else np.zeros_like(v2)
        after_forecast=time.perf_counter_ns() if profile else 0
        gated,enabled=self.gate.step(past,self.origin,np.stack([v2,fade]))
        after_gate=time.perf_counter_ns() if profile else 0
        mixed=gated[0].copy()
        if self.bank is not None:
            for (columns,_),mixer in zip(self.groups,self.mixers):
                arms=np.stack([gated[0,columns],gated[1,columns],np.zeros(BLOCK)])
                mixed[columns]=mixer.step(past,self.origin,arms)
        if profile:
            end=time.perf_counter_ns()
            self.last_parts={'bank':after_bank-before,'v2_selector':after_selector-after_bank,
                'forecast':after_forecast-after_selector,'gate':after_gate-after_forecast,'mix':end-after_gate}
        return gated[0],gated[1],mixed


def replay(x,origins,protocol,cache=False,bank_enabled=True,profile=False):
    """Origin convention matches saved fresh study: x[0] primes v2, bank starts x[1]."""
    origins=np.asarray(origins,int)
    assert origins[0]==BLOCK*50 and np.all(np.diff(origins)==BLOCK)
    outputs={m:[] for m in ('v2_gated','fade0.1_linear_gated','causal_L2')}
    wall=[];cpu=[];parts=[];choices=[]
    with cached_dpss(cache):
        chain=ForecastChain(protocol,x[0],bank_enabled)
        for end in range(1+BLOCK,int(origins[-1])+2,BLOCK):
            t0=time.perf_counter_ns() if profile else 0
            c0=time.thread_time_ns() if profile else 0
            out=chain.push(x[end-BLOCK:end],profile)
            c1=time.thread_time_ns() if profile else 0
            t1=time.perf_counter_ns() if profile else 0
            if out is not None:
                for key,values in zip(outputs,out):outputs[key].append(values)
                choices.append([m.selected for m in chain.mixers] if bank_enabled else [0,0])
                if profile:
                    wall.append((t1-t0)*1e-6);cpu.append((c1-c0)*1e-6)
                    parts.append([chain.last_parts[k]*1e-6 for k in ('bank','v2_selector','forecast','gate','mix')])
    return {k:np.asarray(v) for k,v in outputs.items()},np.asarray(choices),{
        'wall_ms':np.asarray(wall),'thread_cpu_ms':np.asarray(cpu),'parts_ms':np.asarray(parts),
        'part_names':['bank','v2_selector','forecast','gate','mix'],
        'max_retained_input_samples':len(chain.history),'max_gate_pending':len(chain.gate.pending),
        'mixer_pending':[len(m.pending) for m in chain.mixers]}
