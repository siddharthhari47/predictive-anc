from pathlib import Path
import sys, csv, json, math
from collections import Counter
import numpy as np
from scipy import signal
from threadpoolctl import threadpool_limits

ROOT = Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
sys.path.insert(0, str(ROOT))
from anc_lab import tuning_accuracy_diagnostic as d
from anc_lab import selector_headroom as h
from anc_lab import antihum_study as room
from anc_lab.antihum import FS, ToneSetting
from anc_lab.tuning import erb_hz

OUT = d.STUDY
checks = 0
max_difference = 0.


def check(a, b, atol=1e-9):
    global checks, max_difference
    a, b = np.asarray(a, float), np.asarray(b, float)
    np.testing.assert_allclose(a, b, rtol=0, atol=atol)
    checks += int(a.size)
    max_difference = max(max_difference, float(np.max(np.abs(a-b), initial=0.)))


def db(off, on):
    return 10*math.log10(max(float(np.mean(off**2)), 1e-30)/max(float(np.mean(on**2)), 1e-30))


def q(values):
    x = np.array([v for v in values if v is not None], float)
    return dict(zip(('min', 'p25', 'median', 'p75', 'p90', 'max'),
                    np.percentile(x, [0, 25, 50, 75, 90, 100]).tolist())) if len(x) else None


def count_scope(rows):
    return {'tones': len(rows), 'rooms': len({r['case_id'] for r in rows}),
            'sources': len({r['source_id'] for r in rows})}


def choose(x, threshold=1.):
    return 'same' if abs(x) < threshold else ('on' if x < 0 else 'off')


def keep(answers):
    return 'off' not in answers and 'on' in answers


def probability(x):
    # Independent calculation using erfc, not the diagnostic's scipy.ndtr.
    p_on = .5*math.erfc((1+x)/2)
    p_off = .5*math.erfc((1-x)/2)
    return {'on': p_on, 'off': p_off, 'same': 1-p_on-p_off}


def csv_new(name, rows):
    columns = list(dict.fromkeys(k for r in rows for k in r))
    with (OUT/name).open('x', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, columns)
        w.writeheader()
        w.writerows(rows)


def main():
    global checks
    p = d.verified()
    oracle = h.read(OUT/'oracle-results.json')
    acceptance = h.read(OUT/'acceptance-results.json')
    cases = {c['case_id']: c for c in p['cases'] if c['menu_tones']}
    assert set(cases) == {c['case_id'] for c in oracle['cases']} == {c['case_id'] for c in acceptance['cases']}
    logs = {c['case_id']: c for c in acceptance['cases']}
    tones, trials, sources = [], [], {}
    historical = h.read(d.compatibility.STUDY/'compressor.json')['tone_comparisons']
    receipts = {}
    for case in oracle['cases']:
        c = cases[case['case_id']]
        scene, meta, saved = d.load(c)
        sources[meta['source_id']] = meta['file']
        receipts[c['case_id']] = {'cache_sha256': h.sha(ROOT/c['cache_path']),
                                 'score_sha256': h.sha(ROOT/c['score_path'])}
        check(len(case['tones']), c['menu_tones'])
        for row, session in zip(case['tones'], logs[c['case_id']]['sessions']):
            f = row['frequency']
            k = row['tone_index']
            assert session['frequency'] == f == saved['v2_tuning'][k]['frequency']
            assert row['oracle']['identifiable']
            assert session['summary']['kept'] == row['kept']
            for key, value in session['summary'].items():
                d.numbers_equal(value, saved['v2_tuning'][k][key])
            half = erb_hz(f)/2
            sos = signal.butter(2, [max(20., f-half), min(f+half, .45*FS)], 'bandpass', fs=FS, output='sos')
            y = signal.sosfilt(sos, scene['ears'][0])
            # Reconstruct the native unbounded basis independently of unit_sound.
            basis = []
            for phase in (0., 90.):
                # Temporarily raise only this local simulation's cap to obtain a
                # linear unit basis. The global dict is restored immediately.
                old_cap = room.PROTOCOL['levels']['peak_cap']
                try:
                    room.PROTOCOL['levels']['peak_cap'] = 1e20
                    start, sound, _, _ = room.ear_sound(scene, [ToneSetting(f, 1., phase)], .03)
                finally:
                    room.PROTOCOL['levels']['peak_cap'] = old_cap
                at = room.add_at(np.zeros(scene['n']), start+scene['unreported'], sound)
                basis.append(signal.sosfilt(sos, at))
            x = np.column_stack(basis)
            lo, hi = scene['warm'], scene['prefix']
            xx, yy = x[lo:hi], y[lo:hi]
            coef = np.linalg.solve(xx.T@xx, -xx.T@yy)
            check(coef, row['oracle']['coefficients'])
            check(db(yy, yy+xx@coef), row['oracle']['prefix_band_gain_db'])
            check(np.linalg.norm(coef), row['oracle']['gain'])
            for label, gain, phase in [
                ('oracle_effect', row['oracle']['gain'], row['oracle']['phase_deg']),
                ('bounded_candidate_effect', row['bounded_candidate_gain'], row['oracle']['phase_deg']),
                ('precheck_effect', row['precheck_gain'], row['tuning']['phase_deg']),
                ('final_effect', row['tuning']['gain'], row['tuning']['phase_deg'])]:
                start, sound, peak, clipped = room.ear_sound(scene, [ToneSetting(f, gain, phase)], .03)
                on = room.add_at(scene['ears'][0], start+scene['unreported'], sound)
                on = signal.sosfilt(sos, on)
                check(db(y[lo:hi], on[lo:hi]), row[label]['prefix_erb_db'])
                check(db(y[hi+1000:], on[hi+1000:]), row[label]['suffix_erb_db'])
                check([peak, clipped], [row[label]['unclipped_drive_peak'], row[label]['clipped_fraction']])
            check(session['initial']['min_gain'], row['min_gain'])
            check(session['initial']['max_gain'], row['max_gain'])
            if meta['source_id'] == 'old-013':
                old = next(v for v in historical if v['case_id'] == c['case_id'] and v['frequency'] == f)
                check(old['v2']['coefficients'], row['oracle']['coefficients'])
                check(old['v2']['prefix_capped_band_gain_db'], row['oracle_effect']['prefix_erb_db'])
                check(old['v2']['suffix_capped_band_gain_db'], row['oracle_effect']['suffix_erb_db'])
            check_rows = [r for r in session['comparisons'] if r['kind'] == 'check']
            assert len(check_rows) == 2
            combined_probability = 0.
            for a, pa in probability(check_rows[0]['on_minus_off_db']).items():
                for b, pb in probability(check_rows[1]['on_minus_off_db']).items():
                    if keep([a, b]):
                        combined_probability += pa*pb
            check(combined_probability, session['conditional_keep_probability'])
            original_answers = [r['choice_as_on_off'] for r in check_rows]
            assert keep(original_answers) == row['kept']
            noiseless_kept = keep([choose(r['on_minus_off_db']) for r in check_rows])
            matched_values = [v['on_minus_off_db'] for r in check_rows for v in r['same_interval']]
            true_benefit = -float(np.mean(matched_values))
            mean_drift = float(np.mean([r['off_background_on_interval_minus_off_interval_db'] for r in check_rows]))
            out = {'case_id': row['case_id'], 'source_id': row['source_id'], 'file': meta['file'],
                   'tone_index': k, 'frequency_hz': f, 'kept': row['kept'],
                   'phase_error_deg': row['phase_error_deg'], 'absolute_phase_error_deg': abs(row['phase_error_deg']),
                   'gain_error_db': row['gain_error_db'], 'projected_component_db': row['projected_component_db'],
                   'oracle_gain': row['oracle']['gain'], 'oracle_phase_deg': row['oracle']['phase_deg'],
                   'tuned_phase_deg': row['tuning']['phase_deg'], 'precheck_gain': row['precheck_gain'],
                   'oracle_in_gain_range': row['oracle_in_gain_range'], 'oracle_condition': row['oracle']['condition'],
                   'presses': row['tuning']['presses'], 'sweep_turns': row['tuning']['sweep_turns'],
                   'questions': row['tuning']['questions'], 'conditional_keep_probability': combined_probability,
                   'noiseless_original_checks_keep': noiseless_kept,
                   'same_interval_check_mean_benefit_db': true_benefit,
                   'same_interval_check_min_benefit_db': -max(matched_values),
                   'same_interval_check_max_benefit_db': -min(matched_values),
                   'mean_sequential_background_drift_db': mean_drift,
                   'noise_sd_per_presentation_db': 1., 'noise_sd_difference_db': math.sqrt(2),
                   'check1_answer': original_answers[0], 'check2_answer': original_answers[1]}
            for label in ('oracle', 'bounded_candidate', 'precheck', 'final'):
                for key, value in row[label+'_effect'].items():
                    out[label+'_'+key] = value
            tones.append(out)
            for i, r in enumerate(check_rows):
                check(np.array(r['noiseless_levels_db'])+r['noise_db'], r['noisy_levels_db'])
                assert choose(r['noisy_on_minus_off_db']) == r['choice_as_on_off']
                check(r['on_minus_off_db'], r['same_interval'][r['on_index']]['on_minus_off_db']+
                      r['off_background_on_interval_minus_off_interval_db'])
                probabilities = probability(r['on_minus_off_db'])
                check([probabilities[v] for v in ('on', 'same', 'off')],
                      [r['choice_probabilities'][v] for v in ('on', 'same', 'off')])
                for interval in r['intervals']:
                    assert lo/FS <= interval['start_s'] < interval['end_s'] <= hi/FS
                trials.append({'case_id': row['case_id'], 'source_id': row['source_id'], 'tone_index': k,
                               'frequency_hz': f, 'kept': row['kept'], 'check_number': i+1,
                               'on_first': r['on_index'] == 0, 'answer': r['choice_as_on_off'],
                               'noiseless_on_minus_off_db': r['on_minus_off_db'],
                               'noisy_on_minus_off_db': r['noisy_on_minus_off_db'],
                               'same_interval_first_on_minus_off_db': r['same_interval'][0]['on_minus_off_db'],
                               'same_interval_second_on_minus_off_db': r['same_interval'][1]['on_minus_off_db'],
                               'background_drift_db': r['off_background_on_interval_minus_off_interval_db'],
                               'A_noise_db': r['noise_db'][0], 'B_noise_db': r['noise_db'][1],
                               'A_start_s': r['intervals'][0]['start_s'], 'A_end_s': r['intervals'][0]['end_s'],
                               'B_start_s': r['intervals'][1]['start_s'], 'B_end_s': r['intervals'][1]['end_s'],
                               **{v+'_probability': probabilities[v] for v in probabilities}})
    kept = [r for r in tones if r['kept']]
    muted = [r for r in tones if not r['kept']]
    groups = {}
    for name, rows in [('all', tones), ('kept', kept), ('muted', muted)]:
        groups[name] = {**count_scope(rows),
            'absolute_phase_error_deg': q([r['absolute_phase_error_deg'] for r in rows]),
            'gain_error_db': q([r['gain_error_db'] for r in rows]),
            'absolute_gain_error_db': q([abs(r['gain_error_db']) for r in rows]),
            'phase_over60': count_scope([r for r in rows if r['absolute_phase_error_deg'] > 60]),
            'phase_over25': count_scope([r for r in rows if r['absolute_phase_error_deg'] > 25]),
            'projected_component_db': q([r['projected_component_db'] for r in rows]),
            'oracle_prefix_erb_db': q([r['oracle_prefix_erb_db'] for r in rows]),
            'precheck_prefix_erb_db': q([r['precheck_prefix_erb_db'] for r in rows]),
            'precheck_suffix_erb_db': q([r['precheck_suffix_erb_db'] for r in rows]),
            'same_interval_check_mean_benefit_db': q([r['same_interval_check_mean_benefit_db'] for r in rows]),
            'conditional_keep_probability': q([r['conditional_keep_probability'] for r in rows]),
            'noiseless_original_checks_keep': sum(r['noiseless_original_checks_keep'] for r in rows)}
    harm = []
    for t in (0., .1, .5, 1.):
        harm.append({'harm_db': t,
                     'kept_prefix': count_scope([r for r in kept if r['precheck_prefix_erb_db'] < -t-1e-9]),
                     'kept_suffix': count_scope([r for r in kept if r['precheck_suffix_erb_db'] < -t-1e-9]),
                     'kept_both': count_scope([r for r in kept if max(r['precheck_prefix_erb_db'], r['precheck_suffix_erb_db']) < -t-1e-9])})
    thresholds = []
    for t in d.THRESHOLDS:
        r = {'benefit_db': t}
        for label in ('oracle', 'bounded_candidate', 'precheck'):
            r[label+'_muted_prefix'] = count_scope([v for v in muted if v[label+'_prefix_erb_db'] >= t])
            r[label+'_muted_prefix_and_suffix'] = count_scope([v for v in muted if min(v[label+'_prefix_erb_db'], v[label+'_suffix_erb_db']) >= t])
        r['muted_good_oracle_but_precheck_below_threshold'] = count_scope([
            v for v in muted if v['bounded_candidate_prefix_erb_db'] >= t and v['precheck_prefix_erb_db'] < t])
        thresholds.append(r)
    summary = {'completed_utc': d.now(), 'scope': 'Seen-data primary 30 ms v2, simulated-ear single-tone ERB diagnosis',
        'protocol_sha256': h.sha(OUT/'protocol.json'), 'rooms_total': len(p['cases']), 'groups': groups,
        'harm_counts': harm, 'mute_opportunity_counts': thresholds,
        'oracle_outside_gain_bounds': sum(not r['oracle_in_gain_range'] for r in tones),
        'oracle_clips': sum(r['oracle_clipped_fraction'] > 0 for r in tones),
        'bounded_candidate_clips': sum(r['bounded_candidate_clipped_fraction'] > 0 for r in tones),
        'precheck_clips': sum(r['precheck_clipped_fraction'] > 0 for r in tones),
        'press_counts': dict(Counter(r['presses'] for r in tones)),
        'sweep_turn_counts': dict(Counter(r['sweep_turns'] for r in tones)),
        'condition': q([r['oracle_condition'] for r in tones]),
        'accepted_with_both_checks_locally_harmful': count_scope([r for r in kept if r['same_interval_check_max_benefit_db'] < 0]),
        'kept_mean_local_check_benefit_below1': count_scope([r for r in kept if r['same_interval_check_mean_benefit_db'] < 1.]),
        'kept_noise_only_accepts_fixed_presentations': count_scope([r for r in kept if not r['noiseless_original_checks_keep']]),
        'muted_noise_only_rejects_fixed_presentations': count_scope([r for r in muted if r['noiseless_original_checks_keep']]),
        'trial_background_drift_absolute_db': q([abs(r['background_drift_db']) for r in trials]),
        'kept_harm_details': [r for r in kept if r['precheck_prefix_erb_db'] < -1e-9],
        'sources': sources,
        'limits': 'No improvement intervention tested. Single-tone results do not sum to whole-room benefit; checks include earlier kept tones. Known simulated-ear oracle is not deployable. Noise-only labels hold settings/order fixed; not full noise-free retuning.'}
    csv_new('tone-diagnostics.csv', tones)
    csv_new('check-trials.csv', trials)
    h.write_new(OUT/'summary.json', summary)
    h.write_new(OUT/'verification.json', {'completed_utc': d.now(), 'numeric_checks': checks,
        'maximum_absolute_difference': max_difference, 'original_tuning_parity_fields': acceptance['parity_fields'],
        'verified_rooms': len(cases), 'verified_tones': len(tones), 'verified_check_pairs': len(trials),
        'all_native_prefix_oracle_fits_identifiable': True, 'receipts': receipts,
        'method': 'Independent normal-equation oracle fits; native direct setting renderer checks all capped prefix/suffix/drive metrics; original 9 compressor fits reproduce; erfc/enumerated Gaussian probabilities; original summaries/settings reproduce; counters/exports checked. Native renderer, cached traces and SciPy filtering are shared, not independent physics or predictor implementations.'})
    print(json.dumps({k: v for k, v in summary.items() if k not in ('kept_harm_details', 'sources', 'limits')}, indent=2))
    print(json.dumps({'numeric_checks': checks, 'max_difference': max_difference,
                      'parity_fields': acceptance['parity_fields']}))


if __name__ == '__main__':
    with threadpool_limits(limits=1):
        main()
