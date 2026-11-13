"""Prerequisite: actual predictor phase references at 30/200 ms room leads."""
from datetime import datetime, timezone
import argparse
import json
import numpy as np
from threadpoolctl import threadpool_limits
from . import selector_headroom as h
from .selector_room_stream import stream
from .selector_stream_profile import cached_dpss

ROOT = h.ROOT
STUDY = ROOT/'results-selector-room-alignment-01'


def run():
    STUDY.mkdir(exist_ok=False)
    code = ('selector_room_alignment.py', 'selector_room_stream.py', 'selector_stream_profile.py',
            'antihum.py', 'tone_react.py', 'tone_floors.py', 'tone_forecasters.py', 'predictors.py')
    p = {'created_utc': datetime.now(timezone.utc).isoformat(), 'frequencies_hz': [47.3, 137.4, 299.3, 343.7],
         'drifts_hz_per_second': [0., .01], 'seconds': 12, 'evaluate_after_seconds': 10,
         'amplitude': .01, 'phase_radians': .71, 'noise_sd': 1e-6, 'seed': 20261022,
         'leads_ms': [30, 200], 'maximum_pair_phase_degrees': 1., 'maximum_pair_level_db': .1,
         'code_sha256': {f'anc_lab/{name}': h.sha(ROOT/'anc_lab'/name) for name in code},
         'source_protocol_sha256': h.sha(ROOT/'results-selector-fresh-01/protocol.json'),
         'scope': 'Known stable and very slowly drifting synthetic tones only; no room ear score. Genuine predictor bias distinguished from time-reference mistakes.'}
    h.write_new(STUDY/'protocol.json', p)
    h.write_new(STUDY/'frozen.json', {'sha256': h.sha(STUDY/'protocol.json')})
    original = h.read(ROOT/'results-selector-fresh-01/protocol.json')
    rows = []
    for index, (f, drift) in enumerate((f, d) for f in p['frequencies_hz'] for d in p['drifts_hz_per_second']):
        t = np.arange(24000)/2000
        phase = 2*np.pi*(f*t+.5*drift*t*t)+p['phase_radians']
        x = p['amplitude']*np.cos(phase)+np.random.default_rng(p['seed']+index).normal(0., p['noise_sd'], len(t))
        with threadpool_limits(limits=1), cached_dpss(True):
            trace = stream(x, original)
        keep = np.flatnonzero(trace['v2']['seen'] >= 20000)
        for group, lead_ms in enumerate(p['leads_ms']):
            predicted = []
            for a in (trace['v2'], trace['bank'][group]):
                times = (a['seen'][keep]-1)/2000
                match = np.abs(a['frequency'][keep]-(f+drift*times)[:, None]) < 2.
                assert np.all(match.any(axis=1)), ('missing tone', f, drift, group)
                z = np.sum(np.where(match, a['phasor'][keep]*np.exp(2j*np.pi*np.nan_to_num(a['frequency'][keep])*lead_ms/1000), 0j), axis=1)
                predicted.append(z)
            phase_error = np.degrees(np.angle(predicted[1]*np.conj(predicted[0])))
            level_error = 20*np.log10(np.abs(predicted[1])/np.abs(predicted[0]))
            row = {'frequency_hz': f, 'drift_hz_per_s': drift, 'lead_ms': lead_ms,
                   'compared_origins': len(keep), 'max_pair_phase_degrees': float(np.max(np.abs(phase_error))),
                   'max_pair_level_db': float(np.max(np.abs(level_error)))}
            row['passed'] = row['max_pair_phase_degrees'] <= 1 and row['max_pair_level_db'] <= .1
            rows.append(row)
        print(json.dumps({'completed_scenes': index+1, 'of': 8, 'rows': rows[-2:]}), flush=True)
    result = {'passed': all(r['passed'] for r in rows), 'rows': rows,
              'max_pair_phase_degrees': max(r['max_pair_phase_degrees'] for r in rows),
              'max_pair_level_db': max(r['max_pair_level_db'] for r in rows),
              'completed_utc': datetime.now(timezone.utc).isoformat()}
    h.write_new(STUDY/'results.json', result)
    print(json.dumps({k:v for k,v in result.items() if k != 'rows'}, indent=2))


if __name__ == '__main__':
    run()
