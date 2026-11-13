"""Trace the joint check on one development scene. Args: project path, scene index."""
import json
import sys
sys.path.insert(0, sys.argv[1])

import numpy as np

from anc_lab import forecaster_study as fsd
from anc_lab.generalization import normalized_prefix
from anc_lab.selection_study import BLOCK, FS, SECONDS, TRAIN_END, horizon_setup, synthesize_scene
from anc_lab.tone_floors import FloorToneBank, JointCheckBank
from anc_lab.tone_forecasters import ProminentLines, ToneObserverBank, stream_forecasts
from anc_lab.tone_selection import ToneSelector

v2 = json.loads(fsd.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
_, _, tasks = fsd.development_scenes()
_, horizons, groups = horizon_setup()
name, family, spec, seed, x = tasks[int(sys.argv[2])]
if x is None:
    raw = synthesize_scene(spec, seed) if family == 'standard' else fsd.synthesize_wander(spec, seed)
    x, _ = normalized_prefix(raw, TRAIN_END)
print(name, [(t['freq'], t['amp']) for t in spec['tones']], spec['noise'])
grid = np.arange(BLOCK*50, SECONDS*FS-int(max(horizons)), BLOCK)
common = lambda: dict(nb_tau=0., release={'ratio':v2['forecaster']['release_ratio'], 'seconds':v2['forecaster']['release_window_seconds']},
              release_long_seconds=v2["forecaster"]["window_seconds"], candidates=ProminentLines())
a = ToneObserverBank(FS, BLOCK, ToneSelector(FS, **v2['selector']), **common())
b = FloorToneBank(FS, BLOCK, ToneSelector(FS, **v2['selector']), **common())
fa, fb = stream_forecasts(a, x, grid, horizons), stream_forecasts(b, x, grid, horizons)
print('floor0 vs base max abs diff', np.abs(fa-fb).max(), 'rows differing', int(np.sum(np.abs(fa-fb).max(axis=1) > 1e-9)))
bank = JointCheckBank(FS, BLOCK, ToneSelector(FS, **v2['selector']), **common())
orig = bank._band_check


def logged(g):
    orig(g)
    hist = bank.history_db[g]
    if g == 0 and bank.counters['band_checks'][0] % 5 == 0:
        bands = np.median([b for b, _ in hist], axis=0)
        total = np.median([t for _, t in hist], axis=0)
        last_b, _ = hist[-1]
        print(f'{bank.seen/FS:5.1f}s active {bank.active[0]} median total dB', np.round(total, 1).tolist())
        print('   median worst band', [int(i) for i in bands.argmax(axis=1)], np.round(bands.max(axis=1), 1).tolist())
        print('   last worst band  ', np.round(last_b.max(axis=1), 1).tolist())


bank._band_check = logged
stream_forecasts(bank, x, grid, horizons)
print('anchors', np.round(bank.anchor, 1), bank.from_selector)
print('histogram', bank.counters['setting_histogram'])
