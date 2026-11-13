"""Smoke check for study 02 (development material only). Args: project path."""
import json
import sys
import time

sys.path.insert(0, sys.argv[1])
from anc_lab import forecaster_study as s1
from anc_lab import forecaster_study_02 as s2

release = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))
draws, wander, tasks = s1.development_scenes()
forbidden = s2.development_frequencies(release, wander)
print('forbidden', len(forbidden))
syn = dict(s2.SYNTHETIC_TEST, forbidden_frequencies=forbidden)
standard, wdraw = s2.draw_synthetic_test(syn, forbidden)
print('standard draws', [sorted(g) for g in standard][:1])
print('method names', s2.method_names(s2.COMPARATORS+s2.CANDIDATES))
v2 = release['v2']
# One short development scene through every method, to catch wiring errors.
t = time.perf_counter()
name, family, spec, seed, x = next(t_ for t_ in tasks if t_[1] == 'wander')
out = s2._scene_task((name, family, spec, seed, x, s2.COMPARATORS+s2.CANDIDATES, v2))
print(name, 'scene ok in', round(time.perf_counter()-t, 1), 's; objectives', {k:round(v['objective_db'], 2) for k, v in out['objective'].items()})
print('joint settings', out['methods']['joint']['settings'])
