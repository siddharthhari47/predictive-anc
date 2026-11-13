"""Can study 02 draw fresh synthetic test frequencies? No forecaster runs; draws only. Args: project path, seed_std, seed_wander."""
import json
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])

import numpy as np

from anc_lab.forecaster_study import draw_wander
from anc_lab.release_study import draw_groups
from anc_lab.selection_study import frequency_extent

root = Path(sys.argv[1])
amend = json.loads((root/'results-tone-forecaster-01'/'protocol-amendment-01.json').read_text(encoding='utf-8'))
print(list(amend))
forb01 = amend.get('forbidden_frequencies') or amend.get('synthetic_test', {}).get('forbidden_frequencies')
if forb01 is None:
    print(json.dumps(amend, indent=1)[:2000])
    sys.exit()
test = json.loads((root/'results-tone-forecaster-01'/'test-02'/'test.json').read_text(encoding='utf-8'))
used = [f for g in test['synthetic_standard_draws'] for f in frequency_extent(g)]
used += [f for g in test['synthetic_wander_draws'] for fs in g.values() for f in fs]
forbidden = sorted(set(round(f, 2) for f in forb01+used))
print('study-01 forbidden', len(forb01), 'plus study-01 test', len(used), '->', len(forbidden))
for parity in (1, 0):
    try:
        rng = np.random.default_rng(int(sys.argv[2]))
        std = [draw_groups(rng, parity, forbidden) for _ in range(3)]
        rng = np.random.default_rng(int(sys.argv[3]))
        wan = [draw_wander(rng, parity, forbidden) for _ in range(3)]
        print('parity', parity, 'ok', [frequency_extent(g)[:4] for g in std], wan[0])
    except Exception as e:
        print('parity', parity, 'failed:', e)
