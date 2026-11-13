"""Why does the band guard reject forecasts on a synthetic development scene? Development material only."""
import json
import sys
sys.path.insert(0, sys.argv[1])

import numpy as np

from anc_lab import forecaster_study as fsd
from anc_lab.generalization import normalized_prefix
from anc_lab.selection_study import BLOCK, FS, SECONDS, TRAIN_END, horizon_setup, synthesize_scene
from anc_lab.tone_forecasters import ProminentLines, stream_forecasts
from anc_lab.tone_guard import GuardedToneBank
from anc_lab.tone_selection import ToneSelector

v2 = json.loads(fsd.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
_, _, tasks = fsd.development_scenes()
pick = int(sys.argv[2]) if len(sys.argv) > 2 else 0
name, family, spec, seed, x = tasks[pick]
if x is None:
    raw = synthesize_scene(spec, seed) if family == 'standard' else fsd.synthesize_wander(spec, seed)
    x, _ = normalized_prefix(raw, TRAIN_END)
print(name, [(t['freq'], t['amp']) for t in spec['tones']], spec['noise'])
_, horizons, groups = horizon_setup()
grid = np.arange(BLOCK*50, SECONDS*FS-int(max(horizons)), BLOCK)
common = dict(nb_tau=0., release={'ratio':v2['forecaster']['release_ratio'], 'seconds':v2['forecaster']['release_window_seconds']},
              release_long_seconds=v2['forecaster']['window_seconds'], candidates=ProminentLines())
bank = GuardedToneBank(FS, BLOCK, ToneSelector(FS, **v2['selector']), margin_db=.5, **common)
log = []
orig = bank._choose


def logged():
    orig()
    log.append((bank.seen, bank.anchor.round(1).tolist(), bank.choice.tolist(), [c.tolist() for c in bank.group_choice]))


bank._choose = logged
stream_forecasts(bank, x, grid, horizons)
print('counters', {k:v for k, v in bank.counters.items() if k != 'choice_histogram'})
for seen, anchors, base, gc in log[::100]:
    print(f'{seen/FS:5.1f}s anchors {anchors} base {base} g0 {gc[0]} g1 {gc[1]}')
centres = np.round(bank.bands_hz).astype(int)
print('bands', centres)
for g in range(2):
    for i, (w, m) in bank.stats[g].items():
        j = list(bank.ids).index(i) if i in bank.ids else None
        f = bank.anchor[j] if j is not None else None
        print(f'group {g} id {i} tone {f}')
        print('   without dB', np.round(10*np.log10(w), 1))
        for b in range(bank.n):
            print(f'   tau {bank.taus[b]:.3f}', np.round(10*np.log10(m[b]/w), 2))
