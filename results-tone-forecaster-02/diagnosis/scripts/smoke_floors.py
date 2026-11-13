"""Smoke test of tone_floors on development scenes only. Args: project path, scene indices..."""
import json
import sys
import time
sys.path.insert(0, sys.argv[1])

import numpy as np

from anc_lab import forecaster_study as fsd
from anc_lab.generalization import normalized_prefix
from anc_lab.release_study import gate_output, objective
from anc_lab.selection_study import BLOCK, FS, SECONDS, TRAIN_END, VAL_END, horizon_setup, synthesize_scene
from anc_lab.tone_floors import FloorToneBank, JointCheckBank
from anc_lab.tone_forecasters import ProminentLines, ToneObserverBank, stream_forecasts
from anc_lab.tone_selection import ToneSelector

v2 = json.loads(fsd.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
_, _, tasks = fsd.development_scenes()
_, horizons, groups = horizon_setup()
common = lambda: dict(nb_tau=0., release={'ratio':v2['forecaster']['release_ratio'], 'seconds':v2['forecaster']['release_window_seconds']},
              release_long_seconds=v2["forecaster"]["window_seconds"], candidates=ProminentLines())
makers = {'base':lambda: ToneObserverBank(FS, BLOCK, ToneSelector(FS, **v2['selector']), **common()),
          'floor0':lambda: FloorToneBank(FS, BLOCK, ToneSelector(FS, **v2['selector']), **common()),
          'lean1':lambda: FloorToneBank(FS, BLOCK, ToneSelector(FS, **v2['selector']), lean_db=1., min_tau_lines_seconds=.2, **common()),
          'joint':lambda: JointCheckBank(FS, BLOCK, ToneSelector(FS, **v2['selector']), **common())}
for pick in map(int, sys.argv[2:]):
    name, family, spec, seed, x = tasks[pick]
    if x is None:
        raw = synthesize_scene(spec, seed) if family == 'standard' else fsd.synthesize_wander(spec, seed)
        x, _ = normalized_prefix(raw, TRAIN_END)
    grid = np.arange(BLOCK*50, SECONDS*FS-int(max(horizons)), BLOCK)
    late = grid >= VAL_END
    steady = [tn['freq'] for tn in spec['tones'] if not tn['drift_hz_per_s'] and tn['start'] == 0 and tn['stop'] >= SECONDS]
    print('==', name)
    outs = {}
    for m, make in makers.items():
        bank = make()
        t0 = time.perf_counter()
        shadow = stream_forecasts(bank, x, grid, horizons)
        gated, _ = gate_output(x, grid, shadow, groups, v2['gate'])
        outs[m] = gated
        own = 1e3*bank.block_seconds_own
        rows = fsd.score_forecasts(x, grid[late], {m:gated[late]}, steady)
        value, gains = objective(x, spec, grid, gated, groups)
        extra = {k:v for k, v in bank.counters.items() if k in ('output_moved', 'output_off', 'setting_switches', 'setting_histogram')}
        print(f"  {m:7s} obj {value:6.2f} late max third {[round(max(r['third_octave_change_db']), 2) for r in rows]} "
              f"p99 {np.percentile(own, 99):.2f} ms  {time.perf_counter()-t0:.1f}s  {extra}")
    print('  floor0 == base:', np.allclose(outs['floor0'], outs['base']))
