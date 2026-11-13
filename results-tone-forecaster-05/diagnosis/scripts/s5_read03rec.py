import json, sys
from pathlib import Path
root = Path(sys.argv[1])
d = json.loads((root/'results-tone-forecaster-03/development/dev-01/development.json').read_text())
for r in d['recordings']:
    print(r['file'][:40], 'len', round(r['analysed_seconds'],1), 'prefix', round(r['prefix_seconds'],1), 'tones', [round(t,1) for t in r['reference_tones_hz']], 'elec', r['electrical_not_acoustic'])
    for m in ['v2_gated','joint_gated','joint_ungated','bank_wide_lines_gated']:
        for s in r['scores']:
            if s['method']==m:
                print(f"   {m:22s} {s['horizon_start_ms']:5.0f} band {s['band_gain_db']:6.2f} tone {s['tone_band_gain_db'] if s['tone_band_gain_db'] is None else round(s['tone_band_gain_db'],2)} max {s['max_third_octave_change_db']:5.2f}  ", ' '.join(f'{c:5.1f}' for c in s['third_octave_change_db']))
    jc = r['methods']['joint']['counters']
    print('   joint counters', {k:jc[k] for k in ('band_checks','setting_switches','setting_histogram')})
