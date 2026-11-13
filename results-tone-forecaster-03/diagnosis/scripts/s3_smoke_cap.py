"""Study 03 wiring check: CappedCheckBank with no cap must equal JointCheckBank exactly; with cap = margin it must
never keep a setting whose median worst band is above the margin. Synthetic signal only. Args: project path."""
import sys

sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[1]+'/tests')

import numpy as np

from anc_lab.antihum import V2_SELECTOR
from anc_lab.tone_cap import CappedCheckBank
from anc_lab.tone_floors import JointCheckBank
from anc_lab.tone_forecasters import ProminentLines, stream_forecasts
from anc_lab.tone_selection import ToneSelector
from test_tone_forecaster import BLOCK, FS, scene

BOTH = np.r_[np.arange(41, 61), np.arange(241, 261)]


def make(kind, **o):
    return kind(FS, BLOCK, ToneSelector(FS, **V2_SELECTOR), nb_tau=0., candidates=ProminentLines(), **o)


x = scene(seconds=14, tones=((83.3, .5), (171.7, .3), (233.9, .2)), noise=.6)
grid = np.arange(999, len(x)-int(BOTH[-1]), BLOCK)
a = stream_forecasts(make(JointCheckBank), x, grid, BOTH)
fc = make(CappedCheckBank, cap_db=np.inf)
b = stream_forecasts(fc, x, grid, BOTH)
print('inf cap identical:', np.array_equal(a, b), fc.counters['decisions'], fc.counters['fallback_decisions'])
fc = make(CappedCheckBank, cap_db=.5)
seen = []
orig = fc._decide


def traced(g):
    orig(g)
    louder = np.median([b for b, _ in fc.history_db[g]], axis=0).max(axis=1)
    seen.append(louder[fc.active[g]])
fc._decide = traced
c = stream_forecasts(fc, x, grid, BOTH)
print('cap .5: max active worst band', max(seen), 'decisions', fc.counters['decisions'], 'silent', fc.counters['silent_decisions'],
      'output nonzero fraction', np.mean(np.any(c != 0, axis=1)))
