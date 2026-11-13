"""Confirm the built rooms use this study's seed and paths before the one scoring run."""
import collections, json, sys
sys.path.insert(0, r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
from anc_lab import tuning_fresh_02  # noqa: F401
from anc_lab import tuning_fresh as tf
import inspect
print(tf.STUDY, tf.AUDIO, tf.ROOM_SEED)
print(inspect.getsource(tf.room_seed) if hasattr(tf, 'room_seed') else 'no room_seed')
r = json.load(open(tf.STUDY/'rooms.json', encoding='utf-8'))
print(collections.Counter(s['status'] for s in r['sources']))
print([(s['source_id'], s.get('reason')) for s in r['sources'] if s['status'] != 'built'])
if hasattr(tf, 'room_seed'):
    bad = [c['case_id'] for s in r['sources'] for c in s['cases'] if c['seed'] != tf.room_seed(s['source_id'], c['room_index'])]
    print('seed mismatches', len(bad))
print(collections.Counter(c['source_id'] for c in r['eligible_cases']))
print(len(list((tf.STUDY/'decoded').iterdir())), tf.WORKERS)
