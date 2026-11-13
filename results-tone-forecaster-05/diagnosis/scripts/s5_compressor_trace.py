"""Study 05 diagnosis, step 5 (development material only): why do fades raise the whole-band gain on two recordings?

In the all-development fade trial, a 0.1 s fade-out lifted WWS_Compressor.ogg's whole band from 0.82 / 0.02 dB to
2.53 / 2.37 dB (20 / 120 ms), and Microwave_oven.ogg's 120 ms tone bins from 5.1 to 11.7 dB, while a fade-in alone
(in10) did not. This traces, per development recording, which output setting the band check holds after the scoring
prefix, how often the selector drops a tone (tone churn) and how many setting switches there are, for the joint
check, a 0.1 s fade both ways (f10), fade-in only (in10) and fade-out only (out10). Args: project path, output json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])

import numpy as np

from anc_lab import forecaster_study as s1
from anc_lab import forecaster_study_02 as fs2
from anc_lab.real_hum_study import PREFIX_FRACTION, load_any
from anc_lab.selection_study import BLOCK, FS, horizon_setup
from anc_lab.tone_floors import JointCheckBank
from anc_lab.tone_forecasters import stream_forecasts
from anc_lab.tone_react import FadeCheckBank

VARIANTS = {'joint':(JointCheckBank, {}),
            'f10':(FadeCheckBank, {'fade_in_seconds':.1, 'fade_out_seconds':.1}),
            'in10':(FadeCheckBank, {'fade_in_seconds':.1, 'fade_out_seconds':.01}),
            'out10':(FadeCheckBank, {'fade_in_seconds':.01, 'fade_out_seconds':.1})}


def traced(cls):
    class Traced(cls):
        def _reconcile(self):
            before = self.anchor.copy()
            super()._reconcile()
            kept = sum(any(abs(a-b) <= self.associate_hz for b in self.anchor) for a in before)
            self.trace_drops += len(before)-kept
            self.trace_new += len(self.anchor)-kept

        def _choose(self):
            super()._choose()
            self.trace_active.append((self.seen, tuple(int(a) for a in self.active)))
    return Traced


def main():
    dest = Path(sys.argv[2])
    v2 = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
    res = []
    for e in s1.load_split()['development_files']:
        audio, _ = load_any(s1.checked_path(e))
        prefix = int(PREFIX_FRACTION*len(audio))
        x = (audio-float(np.mean(audio[:prefix])))/max(float(np.std(audio[:prefix])), 1e-12)
        _, horizons, groups = horizon_setup()
        grid = np.arange(BLOCK*50, len(x)-int(max(horizons)), BLOCK)
        out = {'file':e['file'], 'seconds':len(x)/FS, 'variants':{}}
        for name, (cls, opts) in VARIANTS.items():
            fs2.BANK_KINDS['trace_'+name] = traced(cls)          # this process only
            bank = fs2.make_bank({'name':name, 'kind':'trace_'+name, 'nb_tau':0., 'lines':True, 'options':opts}, v2)
            bank.trace_drops, bank.trace_new, bank.trace_active = 0, 0, []
            stream_forecasts(bank, x, grid, horizons)
            act = np.array([a for s, a in bank.trace_active if s >= prefix])
            row = {'drops':bank.trace_drops, 'new':bank.trace_new,
                   'ghosts':bank.counters.get('ghosts'), 'band_checks':bank.counters['band_checks']}
            for g in range(act.shape[1] if len(act) else 0):
                hist = np.bincount(act[:, g], minlength=len(bank.options)+1)/len(act)
                row[f'group{g}'] = {'silent_share':round(float(hist[0]), 3),
                                    'settings':{('none' if a == 0 else f'{bank.options[a-1][0]:g}{"L" if bank.options[a-1][1] else "S"}'):
                                                round(float(h), 3) for a, h in enumerate(hist) if h > 0},
                                    'switches':int(np.sum(act[1:, g] != act[:-1, g]))}
            out['variants'][name] = row
        res.append(out)
        print(e['file'], f"{out['seconds']:.0f} s")
        for name, row in out['variants'].items():
            gs = '  '.join(f"g{g}: silent {row[f'group{g}']['silent_share']:.2f} sw {row[f'group{g}']['switches']} "
                           f"{row[f'group{g}']['settings']}" for g in range(2) if f'group{g}' in row)
            print(f"  {name:6s} drops {row['drops']:4d} new {row['new']:4d} ghosts {row['ghosts']}  {gs}")
    dest.write_text(json.dumps(res, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
