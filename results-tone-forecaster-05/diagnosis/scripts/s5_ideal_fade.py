"""Study 05 diagnosis, step 2 (development material only): would fading a tone in and out remove the change boosts?

Step 1 (s5_change_trace.py) found that even a perfect tracker of the clean tones, switched on and off with no delay,
boosts the band next to a strong tone that starts or stops near a band edge. Its output starts and stops in one block,
so the error carries a short burst with two hard edges, where the signal has one. Here the same ideal tracker
switches each tone on and off with a raised-cosine fade of F seconds, starting D s after the tone starts or stops
(the fade-out keeps forecasting the stopped tone, more weakly, for F s). Same 9 development change scenes, late
windows, both horizons. Args: project path, output json."""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, sys.argv[1])
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from threadpoolctl import threadpool_limits

from anc_lab import forecaster_study as s1
from anc_lab.selection_study import BLOCK, FS, SECONDS, VAL_END, horizon_setup
from s5_change_trace import CHANGE, clean_tones, scene_seed, score


def envelope(t, start, stop, delay, fade):
    """Output weight at origin times t: 0 before start+delay, rising over `fade`, falling from stop+delay over `fade`."""
    def ramp(u):
        if fade <= 0:
            return (u >= 0).astype(float)
        return .5-.5*np.cos(np.pi*np.clip(u/fade, 0, 1))
    up = ramp(t-(start+delay)) if start > 0 else np.ones_like(t)
    down = 1-ramp(t-(stop+delay)) if stop < SECONDS else np.ones_like(t)
    return up*down


def task(args):
    name, spec, x = args
    with threadpool_limits(limits=1):
        _, horizons, groups = horizon_setup()
        grid = np.arange(BLOCK*50, SECONDS*FS-int(max(horizons)), BLOCK)
        late = grid >= VAL_END
        tones = clean_tones(spec, scene_seed(name))
        noise_only = x.copy()
        for tn, wave in tones:
            on = (np.arange(len(x)) >= tn['start']*FS) & (np.arange(len(x)) < tn['stop']*FS)
            noise_only = noise_only-on*wave
        out = {'scene':name, 'residual_check_std':float(np.std(noise_only)), 'scores':{}}
        for d in (0., .05, .1):
            for f in (0., .05, .1, .2, .4):
                p = np.zeros((len(grid), len(horizons)))
                for tn, wave in tones:
                    w = envelope(grid/FS, tn['start'], tn['stop'], d, f)
                    p += w[:, None]*wave[grid[:, None]+horizons[None, :]]
                out['scores'][f'ideal_d{d:g}_fade{f:g}'] = score(x, grid, p, late)
        return out


def main():
    dest = Path(sys.argv[2])
    _, _, tasks = s1.development_scenes()
    jobs = [(n, spec, x) for n, fam, spec, seed, x in tasks if n.split('#')[0] in CHANGE]
    with ProcessPoolExecutor(6) as pool:
        res = list(pool.map(task, jobs))
    dest.write_text(json.dumps(res, indent=1), encoding='utf-8')
    print('noise-only residual std per scene (should be the white floor in normalized units):',
          [round(r['residual_check_std'], 3) for r in res])
    print('boost counts (>=1 dB, 9 scenes x 2 horizons), near (>=0.5 dB), mean late band gain:')
    for m in res[0]['scores']:
        n = sum(x['max'] >= 1. for r in res for x in r['scores'][m])
        nn = sum(x['max'] >= .5 for r in res for x in r['scores'][m])
        g = np.mean([x['band_gain'] for r in res for x in r['scores'][m]])
        worst = max(x['max'] for r in res for x in r['scores'][m])
        print(f'  {m:22s} {n:2d} boosts {nn:2d} near  worst {worst:5.2f} dB  mean gain {g:5.2f} dB')


if __name__ == '__main__':
    main()
