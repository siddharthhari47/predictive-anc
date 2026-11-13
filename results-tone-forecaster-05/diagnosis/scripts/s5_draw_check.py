"""Can study 05 draw fresh synthetic test frequencies away from every development frequency, study 02's test draws
and study 03's buzz draws? Metadata only (frequency lists); no scene is synthesized or scored."""
import json, sys
sys.path.insert(0, sys.argv[1])
import numpy as np
from anc_lab import forecaster_study as s1
from anc_lab import forecaster_study_02 as fs2
from anc_lab import forecaster_study_03 as fs3
from anc_lab.selection_study import frequency_extent
release = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))
draws, wander, _ = s1.development_scenes()
dev = fs2.development_frequencies(release, wander)
p2 = json.loads((fs2.STUDY/'protocol.json').read_text(encoding='utf-8'))['synthetic_test']
t2 = [f for g in p2['standard_draws'] for f in frequency_extent(g)]+[f for g in p2['wander_draws'] for fs in g.values() for f in fs]
buzz = [f for g in fs3.buzz_scenes()[0] for fs in g.values() for f in fs]
forbidden = sorted(set(round(float(f), 2) for f in dev+t2+buzz))
print(len(dev), len(t2), len(buzz), len(forbidden))
for parity in (0, 1):
    syn = dict(fs2.SYNTHETIC_TEST, standard_seed=20261022, wander_seed=20261023, parity=parity)
    try:
        st, wa = fs2.draw_synthetic_test(syn, forbidden)
        print('parity', parity, 'ok', st[0], wa[0])
    except Exception as e:
        print('parity', parity, 'failed:', e)
print('--- without study 02 test draws')
forbidden = sorted(set(round(float(f), 2) for f in dev+buzz))
for parity in (1,):
    for reps in (3, 6):
        syn = dict(fs2.SYNTHETIC_TEST, standard_seed=20261022, wander_seed=20261023, parity=parity, standard_repeats=reps)
        try:
            st, wa = fs2.draw_synthetic_test(syn, forbidden)
            near = [f for g in st for f in frequency_extent(g) if any(abs(f-b) <= 2 for b in t2)]
            print('parity', parity, 'reps', reps, 'ok;', len(near), 'of', sum(len(frequency_extent(g)) for g in st), 'within 2 Hz of a study-02 test frequency')
            print(st)
        except Exception as e:
            print('parity', parity, 'failed:', e)
from anc_lab.selection_study import scene_set
print(list(scene_set(st[0]).keys()))
for k, v in scene_set(st[0]).items():
    if k in ('tone_appears_9s', 'tones_stop_9s', 'source_change_9s'):
        print(k, v)
