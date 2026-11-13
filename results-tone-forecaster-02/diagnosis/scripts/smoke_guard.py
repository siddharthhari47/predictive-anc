"""Smoke test: the guard with an enormous margin and no waiting reproduces the plain bank; timing of the band check."""
import json
import sys
import time
sys.path.insert(0, sys.argv[1])

import numpy as np

from anc_lab import forecaster_study as fsd
from anc_lab.selection_study import BLOCK, horizon_setup
from anc_lab.tone_forecasters import ProminentLines, ToneObserverBank, stream_forecasts
from anc_lab.tone_guard import GuardedToneBank
from anc_lab.tone_selection import ToneSelector

v2 = json.loads(fsd.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
rng = np.random.default_rng(3)
n = 20*2000
t = np.arange(n)/2000
x = .3*rng.standard_normal(n)+np.sin(2*np.pi*61.3*t)+.5*np.sin(2*np.pi*123.7*t+1)+.2*np.sin(2*np.pi*200.2*t)
common = dict(nb_tau=0., release={'ratio':v2['forecaster']['release_ratio'], 'seconds':v2['forecaster']['release_window_seconds']},
              release_long_seconds=v2['forecaster']['window_seconds'])
_, horizons, groups = horizon_setup()
grid = np.arange(BLOCK*50, n-int(max(horizons)), BLOCK)
a = ToneObserverBank(2000, 20, ToneSelector(2000, **v2['selector']), candidates=ProminentLines(), **common)
b = GuardedToneBank(2000, 20, ToneSelector(2000, **v2['selector']), candidates=ProminentLines(), margin_db=100., lines_wait=False, **common)
c = GuardedToneBank(2000, 20, ToneSelector(2000, **v2['selector']), candidates=ProminentLines(), margin_db=.2, **common)
fa = stream_forecasts(a, x, grid, horizons)
fb = stream_forecasts(b, x, grid, horizons)
fc = stream_forecasts(c, x, grid, horizons)
print('max |plain - guard(huge margin)|:', float(np.abs(fa-fb).max()))
print('ids', b.ids, 'anchors', np.round(b.anchor, 1))
print('guard counters', {k:v for k, v in c.counters.items() if k.startswith(('guard', 'floor'))})
for bank, name in ((a, 'plain'), (b, 'huge'), (c, 'guard0.2')):
    own = 1e3*bank.block_seconds_own
    print(name, 'own mean %.2f p99 %.2f max %.2f ms' % (own.mean(), np.percentile(own, 99), own.max()),
          'guard s', round(bank.timing.get('guard', 0), 3))
for g in range(2):
    s = c.stats[g]
    for i, (w, m) in s.items():
        j = list(c.ids).index(i)
        print('group', g, 'tone %.1f' % c.anchor[j], 'worst band change per memory (dB):',
              np.round(10*np.log10(np.max(m/w, axis=1)), 2))
print('band centres', np.round(c.bands_hz, 0))
for g in range(2):
    for i, (w, m) in c.stats[g].items():
        j = list(c.ids).index(i)
        print('group', g, 'tone %.1f' % c.anchor[j])
        print('  without (dB)', np.round(10*np.log10(w), 1))
        for b in range(c.n):
            print('  tau %.3f' % c.taus[b], np.round(10*np.log10(m[b]/w), 2))
