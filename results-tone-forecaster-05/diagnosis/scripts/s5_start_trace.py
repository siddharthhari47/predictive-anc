"""Study 05 diagnosis, step 3 (development material only): the boost before the first decision.

On the two development mains clips (5.0 and 5.5 s; scored after the 40 % prefix, so from 2.0 / 2.2 s) the joint
check never reaches a decision and outputs its start setting (0.1 s floor, line-finder tones off) throughout. This
scores every one of the 10 settings held fixed, from one recorded run, plus v2, to see whether any start setting
avoids the +1.35 dB band, and at what tone cost. Args: project path, output json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from anc_lab import forecaster_study as s1
from anc_lab import forecaster_study_02 as fs2
from anc_lab.real_hum_study import PREFIX_FRACTION, load_any, prominent_tones, tone_band_gain
from anc_lab.release_study import gate_output
from anc_lab.selection_study import BLOCK, FS, horizon_setup
from anc_lab.tone_forecasters import stream_forecasts
from anc_lab.tone_selection import SelectedToneForecaster, ToneSelector
from s5_change_trace import Recorded

MAINS = ('Mains_hum_60_Hz.ogg', 'MainsBrum50Hz.ogg')


def main():
    dest = Path(sys.argv[2])
    v2 = json.loads(s1.RELEASE_PROTOCOL.read_text(encoding='utf-8'))['v2']
    split = s1.load_split()
    res = []
    for e in split['development_files']:
        if e['file'] not in MAINS:
            continue
        audio, _ = load_any(s1.checked_path(e))
        prefix = int(PREFIX_FRACTION*len(audio))
        x = (audio-float(np.mean(audio[:prefix])))/max(float(np.std(audio[:prefix])), 1e-12)
        _, horizons, groups = horizon_setup()
        grid = np.arange(BLOCK*50, len(x)-int(max(horizons)), BLOCK)
        keep = grid >= prefix
        tones = prominent_tones(x[prefix:])
        fc = SelectedToneForecaster(FS, ToneSelector(FS, **v2['selector']), window_seconds=.3,
                                    release_ratio=v2['forecaster']['release_ratio'],
                                    release_window_seconds=v2['forecaster']['release_window_seconds'])
        v2s = fc.predict(x, grid, horizons)
        bank = fs2.make_bank({'name':'joint', 'kind':'joint', 'nb_tau':0., 'lines':True, 'options':{}}, v2)
        bank.__class__ = Recorded
        bank.rec, bank.act = {}, {}
        js = stream_forecasts(bank, x, grid, horizons)
        off = int(grid[0]+1) % BLOCK
        preds = {'v2_ungated':v2s, 'v2_gated':gate_output(x, grid, v2s, groups, v2['gate'])[0],
                 'joint_ungated':js, 'joint_gated':gate_output(x, grid, js, groups, v2['gate'])[0]}
        settings = np.zeros((len(bank.options), len(grid), len(horizons)))
        for row, o in enumerate(grid):
            for g, (cols, _) in enumerate(groups):
                settings[:, row, cols] = bank.rec[int(o)-off][g]
        for s, (level, lines) in enumerate(bank.options):
            p = settings[s]
            preds[f'fixed_{level:g}_{"lines" if lines else "sel"}'] = p
            preds[f'fixed_{level:g}_{"lines" if lines else "sel"}_gated'] = gate_output(x, grid, p, groups, v2['gate'])[0]
        out = {'file':e['file'], 'seconds':len(x)/FS, 'prefix_seconds':prefix/FS, 'tones_hz':tones,
               'band_checks':bank.counters['band_checks'], 'active_end':list(bank.active),
               'anchors_end':bank.anchor.tolist(), 'from_selector_end':bank.from_selector.tolist(), 'scores':{}}
        for m, p in preds.items():
            rows = []
            for (cols, hz), ms in zip(groups, (20., 120.)):
                target = x[grid[keep][:, None]+hz]
                ch = s1.third_octave_changes(target, p[keep][:, cols])
                rows.append({'ms':ms, 'max':max(ch), 'band':int(np.argmax(ch)), 'changes':[round(c, 2) for c in ch],
                             'tone_gain':tone_band_gain(target, p[keep][:, cols], tones) if tones else None})
            out['scores'][m] = rows
        res.append(out)
        print(e['file'], f"{out['seconds']:.2f} s, prefix {out['prefix_seconds']:.2f} s, tones {tones}, "
              f"band checks {out['band_checks']}, anchors {out['anchors_end']} sel {out['from_selector_end']}")
        for m, rows in out['scores'].items():
            print(f'  {m:24s}', '   '.join(f"{r['ms']:3.0f}ms max {r['max']:5.2f} (b{r['band']}) "
                                          f"tone {r['tone_gain'] if r['tone_gain'] is None else round(r['tone_gain'], 2)}"
                                          for r in rows))
    dest.write_text(json.dumps(res, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
