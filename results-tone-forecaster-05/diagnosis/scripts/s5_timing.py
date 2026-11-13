"""Study 05 diagnosis, step 6 (development material only): is the fade code slower, or was the trial's timing load?

In the all-development trial (6 worker processes on a shared machine) the worst-run 99th percentile of the own time
per block was 8.75 ms for the joint check and 11.22 ms for `stepcheck`, the fade code with one-block step fades, whose
output is exactly the joint check's. This runs the joint check, the step fade, the 0.1 s fade and the 0.1 s fade with
a 0.3 s switch fade in one process, one after another on the same inputs, twice in opposite orders, on one
development recording and four development scenes, and prints the own mean and p99 per block for each.
Args: project path, output json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])

import numpy as np

from anc_lab import forecaster_study as s1
from anc_lab import forecaster_study_02 as fs2
from anc_lab import forecaster_study_05 as fs5

METHODS = [{'name':'joint', 'kind':'joint', 'nb_tau':0., 'lines':True, 'options':{}},
           fs5.react('stepcheck', fade_in_seconds=.01, fade_out_seconds=.01, shape='step'),
           fs5.react('fade0.1', fade_in_seconds=.1, fade_out_seconds=.1),
           fs5.react('fade0.1_switch0.3', fade_in_seconds=.1, fade_out_seconds=.1, switch_fade_seconds=.3)]


def main():
    dest = Path(sys.argv[2])
    v2 = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
    rec = next(e for e in s1.load_split()['development_files'] if e['file'] == 'Table_ventilator.ogg')
    _, _, tasks = s1.development_scenes()
    scenes = [t for t in tasks if t[0].split('#')[0] in ('unrelated_tones', 'harmonic_tones', 'tones_stop_9s', 'source_change_9s')][:4]
    rows = []
    for order in (METHODS, METHODS[::-1]):
        runs = [fs2._recording_task((str(s1.checked_path(rec)), order, v2, True))]
        runs += [fs2._scene_task((*t, order, v2)) for t in scenes]
        for r in runs:
            for m in METHODS:
                i = r['methods'][m['name']]
                rows.append({'run':r.get('file') or r.get('scene'), 'order':'forward' if order is METHODS else 'reverse',
                             'method':m['name'], 'mean':i['own_block_ms_mean'], 'p99':i['own_block_ms_p99']})
    dest.write_text(json.dumps(rows, indent=1), encoding='utf-8')
    for m in METHODS:
        mine = [r for r in rows if r['method'] == m['name']]
        print(f"{m['name']:20s} mean {np.mean([r['mean'] for r in mine]):.2f} ms  p99 median {np.median([r['p99'] for r in mine]):.2f}"
              f"  p99 max {max(r['p99'] for r in mine):.2f}  per run p99: "+' '.join(f"{r['p99']:.1f}" for r in mine))


if __name__ == '__main__':
    main()
