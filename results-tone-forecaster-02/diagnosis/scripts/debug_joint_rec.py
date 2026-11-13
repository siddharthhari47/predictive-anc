"""Trace the joint check on one DEVELOPMENT recording. Args: project path, file name, group, [margin_db]."""
import json
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])

import numpy as np

from anc_lab import forecaster_study as fsd
from anc_lab.real_hum_study import PREFIX_FRACTION, load_any
from anc_lab.selection_study import BLOCK, FS, horizon_setup
from anc_lab.tone_floors import JointCheckBank
from anc_lab.tone_forecasters import ProminentLines, stream_forecasts
from anc_lab.tone_selection import ToneSelector

split = fsd.load_split()
entry = next(e for e in split['development_files'] if e['file'] == sys.argv[2])
assert entry['file'] not in {e['file'] for e in split['test_files']}
v2 = json.loads(fsd.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
audio, _ = load_any(fsd.checked_path(entry))
prefix = int(PREFIX_FRACTION*len(audio))
x = (audio-audio[:prefix].mean())/max(audio[:prefix].std(), 1e-12)
_, horizons, groups = horizon_setup()
grid = np.arange(BLOCK*50, len(x)-int(max(horizons)), BLOCK)
print(entry['file'], f'{len(x)/FS:.1f} s, scoring from {prefix/FS:.1f} s')
kw = {'margin_db':float(sys.argv[4])} if len(sys.argv) > 4 else {}
bank = JointCheckBank(FS, BLOCK, ToneSelector(FS, **v2['selector']), nb_tau=0.,
                      release={'ratio':v2['forecaster']['release_ratio'], 'seconds':v2['forecaster']['release_window_seconds']},
                      release_long_seconds=v2['forecaster']['window_seconds'], candidates=ProminentLines(), **kw)
G = int(sys.argv[3])
print('options', [(0, 'off')]+[(i+1, o) for i, o in enumerate(bank.options)])
orig = bank._band_check


def logged(g):
    before = bank.active[g]
    orig(g)
    hist = bank.history_db[g]
    if g == G and (bank.counters['band_checks'][g] % 4 == 0 or bank.active[g] != before):
        bands = np.median([b for b, _ in hist], axis=0)
        total = np.median([t for _, t in hist], axis=0)
        print(f'{bank.seen/FS:5.1f}s active {before}->{bank.active[g]} total', np.round(total, 1).tolist())
        print('   worst band', [int(i) for i in bands.argmax(axis=1)], np.round(bands.max(axis=1), 1).tolist())
        print('   anchors', np.round(bank.anchor, 1).tolist(), 'sel', bank.from_selector.astype(int).tolist())


bank._band_check = logged
stream_forecasts(bank, x, grid, horizons)
print('histogram', bank.counters['setting_histogram'], 'switches', bank.counters['setting_switches'])
