"""Study 05 diagnosis, step 7 (development material only): does the vectorized fade output give exactly the forecasts
the trialled code gave, and how much own time per block does it save?

Runs the trialled FadeCheckBank (tone_react_as_trialled.py, the code behind every trial in this folder) and the
current anc_lab/tone_react.py side by side on two development recordings and two development change scenes, for the
0.1 s fade, the 0.1 s linear fade and the 0.1 s fade with a 0.3 s switch fade, plus the joint check for timing.
Args: project path, trialled module path, output json."""
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])

import numpy as np
from threadpoolctl import threadpool_limits

from anc_lab import forecaster_study as s1
from anc_lab import forecaster_study_02 as fs2
from anc_lab.generalization import normalized_prefix
from anc_lab.real_hum_study import PREFIX_FRACTION, load_any
from anc_lab.selection_study import BLOCK, SECONDS, FS, TRAIN_END, horizon_setup, synthesize_scene
from anc_lab.tone_forecasters import stream_forecasts
from anc_lab.tone_react import FadeCheckBank

spec = importlib.util.spec_from_file_location('anc_lab.tone_react_as_trialled', sys.argv[2])
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
fs2.BANK_KINDS['react_old'] = old.FadeCheckBank
fs2.BANK_KINDS['react_new'] = FadeCheckBank

OPTIONS = {'fade0.1':dict(fade_in_seconds=.1, fade_out_seconds=.1),
           'fade0.1_linear':dict(fade_in_seconds=.1, fade_out_seconds=.1, shape='linear'),
           'fade0.1_switch0.3':dict(fade_in_seconds=.1, fade_out_seconds=.1, switch_fade_seconds=.3)}


def inputs():
    split = s1.load_split()['development_files']
    for name in ('Table_ventilator.ogg', 'WWS_Compressor.ogg'):
        audio, _ = load_any(s1.checked_path(next(e for e in split if e['file'] == name)))
        prefix = int(PREFIX_FRACTION*len(audio))
        yield name, (audio-float(np.mean(audio[:prefix])))/max(float(np.std(audio[:prefix])), 1e-12)
    _, _, tasks = s1.development_scenes()
    for t in [t for t in tasks if t[0].split('#')[0] in ('tones_stop_9s', 'source_change_9s')][:2]:
        yield t[0], t[4]                       # development scenes come already synthesized and normalized


def main():
    v2 = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
    _, horizons, _ = horizon_setup()
    rows = []
    with threadpool_limits(limits=1):
        for name, x in inputs():
            grid = np.arange(BLOCK*50, len(x)-int(max(horizons)), BLOCK)
            joint = fs2.make_bank({'kind':'joint', 'nb_tau':0., 'lines':True, 'options':{}}, v2)
            stream_forecasts(joint, x, grid, horizons)
            row = {'input':name, 'joint_own_ms_mean':1e3*float(joint.block_seconds_own.mean())}
            for label, opts in OPTIONS.items():
                out = {}
                for kind in ('react_old', 'react_new'):
                    bank = fs2.make_bank({'kind':kind, 'nb_tau':0., 'lines':True, 'options':opts}, v2)
                    out[kind] = (stream_forecasts(bank, x, grid, horizons), 1e3*bank.block_seconds_own, bank.counters['ghosts'])
                a, b = out['react_old'][0], out['react_new'][0]
                row[label] = {'identical':bool(np.array_equal(a, b)), 'max_abs_diff':float(np.max(np.abs(a-b))),
                              'ghosts':out['react_new'][2],
                              'trialled_own_ms_mean':float(out['react_old'][1].mean()),
                              'trialled_own_ms_p99':float(np.percentile(out['react_old'][1], 99)),
                              'vectorized_own_ms_mean':float(out['react_new'][1].mean()),
                              'vectorized_own_ms_p99':float(np.percentile(out['react_new'][1], 99))}
            rows.append(row)
            print(json.dumps(row), flush=True)
    Path(sys.argv[3]).write_text(json.dumps(rows, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
