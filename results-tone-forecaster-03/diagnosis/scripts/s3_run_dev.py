"""Study 03 formal development run. Args: project path, output folder."""
import sys

sys.path.insert(0, sys.argv[1])

from anc_lab import forecaster_study_03 as fs3

if __name__ == '__main__':
    r = fs3.run_development(sys.argv[2], workers=6)
    print('pick:', r['development_pick'])
    for t in r['rule_table']:
        print(t['candidate'], 'boosts', t['boosts'], 'near', t['near_boosts'], 'tone', round(t['tone_bin_median_db'], 2),
              'failed', [k for k, ok in t['checks'].items() if not ok])
    for k, v in r['rule_reference'].items():
        print(k, 'boosts', v['boosts'], 'near', v['near_boosts'], 'tone', round(v['tone_bin_median_db'], 2))
    print(f"runtime {r['runtime_seconds']/60:.1f} min")
