"""Development-only diagnosis of third-octave boosts from the line-finder bank.
Runs bank variants on the development recordings (never a test file) and prints the
third-octave changes at both horizons, plus which tones sat near each boosted band.
Args: project path, output json path."""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, sys.argv[1])

import numpy as np

CENTRES = 1000*2**(np.arange(-14, -4)/3)

VARIANTS = {
    'base':{},
    'margin1':{'off_margin_db':1.},
    'tau_lines_0.2':{'min_tau_lines':.2},
    'tau_all_0.1':{'min_tau_all':.1},
    'check120':{'check_delay_ms':120.},
    'prom13':{'prominence_db':13.},
}


def make(v2, opts):
    from anc_lab.tone_forecasters import ProminentLines, ToneObserverBank
    from anc_lab.tone_selection import ToneSelector

    class Variant(ToneObserverBank):
        def _choose(self):
            super()._choose()
            lo_all = opts.get('min_tau_all', 0.)
            lo_lines = opts.get('min_tau_lines', 0.)
            if not (lo_all or lo_lines):
                return
            # Re-pick among allowed memories only (diagnostic, mirrors _choose's rule).
            p = self.c*np.exp(-1j*self.omega)
            choice = self.choice.copy()
            for j in range(len(self.anchor)):
                lo = max(lo_all, 0. if self.from_selector[j] else lo_lines)
                allowed = np.nonzero(self.taus >= lo-1e-9)[0]
                if choice[j] < 0 or self.taus[choice[j]] >= lo-1e-9:
                    continue
                if self.checks[j] < self.min_checks:
                    choice[j] = max(self.default, allowed[0])
                    continue
                best = allowed[int(np.argmin(self.power[allowed, j]))]
                choice[j] = best if self.power[best, j] <= self.off_ratio*self.power[self.n, j] else -1
            self.choice = choice
            self.components_now = [(float(self.omega[b, j]*self.fs/(2*np.pi)), complex(p[b, j]))
                                   for j, b in enumerate(choice) if b >= 0]

    lines = ProminentLines(prominence_db=opts.get('prominence_db', 10.))
    return Variant(2000, 20, ToneSelector(2000, **v2['selector']), nb_tau=0.,
                   check_delay_ms=opts.get('check_delay_ms', 20.), off_margin_db=opts.get('off_margin_db', 0.),
                   release={'ratio':v2['forecaster']['release_ratio'], 'seconds':v2['forecaster']['release_window_seconds']},
                   release_long_seconds=v2['forecaster']['window_seconds'], candidates=lines)


def task(args):
    path, v2 = args
    from threadpoolctl import threadpool_limits
    from anc_lab.forecaster_study import score_forecasts
    from anc_lab.real_hum_study import PREFIX_FRACTION, load_any, prominent_tones
    from anc_lab.release_study import gate_output
    from anc_lab.selection_study import BLOCK, horizon_setup
    from anc_lab.tone_forecasters import stream_forecasts
    with threadpool_limits(limits=1):
        audio, _ = load_any(Path(path))
        prefix = int(PREFIX_FRACTION*len(audio))
        x = (audio-audio[:prefix].mean())/max(audio[:prefix].std(), 1e-12)
        _, horizons, groups = horizon_setup()
        grid = np.arange(BLOCK*50, len(x)-int(max(horizons)), BLOCK)
        keep = grid >= prefix
        tones = prominent_tones(x[prefix:])
        out = {'file':Path(path).name, 'tones':tones, 'variants':{}}
        for name, opts in VARIANTS.items():
            bank = make(v2, opts)
            log = []
            orig_choose = bank._choose

            def logged():
                orig_choose()
                if bank.seen-1 >= prefix:
                    log.append([(round(f, 1), bool(s), float(bank.taus[b]) if b >= 0 else None)
                                for f, s, b in zip(bank.anchor, bank.from_selector, bank.choice)])
            bank._choose = logged
            shadow = stream_forecasts(bank, x, grid, horizons)
            gated, _ = gate_output(x, grid, shadow, groups, v2['gate'])
            rows = score_forecasts(x, grid[keep], {name:gated[keep]}, tones)
            # Tone usage summary after the prefix: frequency (rounded to 1 Hz) -> share of origins on, by memory.
            usage = {}
            for entry in log:
                for f, s, tau in entry:
                    key = f"{round(f):d}{'s' if s else 'L'}"
                    u = usage.setdefault(key, {'present':0, 'on':0, 'taus':{}})
                    u['present'] += 1
                    if tau is not None:
                        u['on'] += 1
                        u['taus'][f'{tau:g}'] = u['taus'].get(f'{tau:g}', 0)+1
            out['variants'][name] = {'scores':[{k:r[k] for k in ('horizon_start_ms', 'band_gain_db', 'tone_band_gain_db',
                                                                    'third_octave_change_db')} for r in rows],
                                     'usage':{k:v for k, v in sorted(usage.items(), key=lambda kv: float(kv[0][:-1]))},
                                     'origins':len(log)}
        return out


if __name__ == '__main__':
    from anc_lab import forecaster_study as fsd
    v2 = json.loads(fsd.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
    split = fsd.load_split()
    paths = [str(fsd.checked_path(e)) for e in split['development_files']]
    with ProcessPoolExecutor(min(8, fsd.WORKERS)) as pool:
        results = list(pool.map(task, [(p, v2) for p in paths]))
    Path(sys.argv[2]).write_text(json.dumps(results, indent=1), encoding='utf-8')
    for r in results:
        print(f"\n{r['file']}  tones={[round(t, 1) for t in r['tones']]}")
        for name, v in r['variants'].items():
            for s in v['scores']:
                louder = ' '.join(f"{c:.0f}:{d:+.1f}" for c, d in zip(CENTRES, s['third_octave_change_db']) if d >= .5)
                tb = s['tone_band_gain_db']
                print(f"  {name:14s} {s['horizon_start_ms']:>5.0f}ms band {s['band_gain_db']:+5.2f} tone "
                      f"{'  -  ' if tb is None else f'{tb:5.1f}'}  >=0.5dB: {louder}")
