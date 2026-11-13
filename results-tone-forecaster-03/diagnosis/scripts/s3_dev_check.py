"""Read study-03 dev-01: per-recording cap activity, frozen file count. Args: project path."""
import json
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])

from anc_lab import forecaster_study_03 as fs3

d = json.loads((Path(sys.argv[1])/'results-tone-forecaster-03'/'development'/'dev-01'/'development.json').read_text(encoding='utf-8'))
print('frozen files', len(fs3.FROZEN_CODE), 'study 02', len(fs3.fs2.FROZEN_CODE))
for m in ('cap0.5', 'cap1', 'cap2'):
    print(m)
    for r in d['recordings']:
        c = r['methods'][m]['counters']
        print(f"  {r['file'][:28]:28s} decisions {sum(c['decisions']):4d} fallback {sum(c['fallback_decisions']):4d} "
              f"capped {sum(c['capped_decisions']):4d} silent {sum(c['silent_decisions']):4d}")
