"""Offline fixed-tuning outcomes. Called only after coverage is sealed."""
from dataclasses import asdict
import numpy as np
from scipy import signal
from . import antihum_study as room
from .antihum import ToneSetting, FS, BLOCK
from .tuning import (TuningSession, SimulatedListener, SWEEP_TURNS, SWEEP_HZ,
                     run_session, start_presentation)
from .selector_room_stream import render, hard_reference


def ear_sound(scene, settings, lead, method, rows=None, cap=True):
    trace = scene['trace']
    rows = np.arange(len(trace['v2']['seen'])) if rows is None else np.asarray(rows)
    if not len(rows):
        return 0, np.zeros(0), 0., 0.
    out = render(trace, settings, lead, method, rows).ravel()
    limit = room.PROTOCOL['levels']['peak_cap']
    drive = np.clip(out, -limit, limit) if cap else out
    b, a = scene['earphone']
    start = int(trace['v2']['seen'][rows[0]])-1+round(lead*FS)
    return start, scene['earphone_gain']*signal.lfilter(b, a, drive), float(np.max(np.abs(out))), float(np.mean(np.abs(out) > limit))


class ChooserPlayer(room.RoomPlayer):
    def __call__(self, presentation):
        s = self.scene
        length = round(presentation.seconds*FS)
        if self.cursor+length > s['prefix']:
            self.cursor = s['warm']
        n0, n1 = self.cursor, self.cursor+length
        if n1 > s['prefix']:
            raise ValueError('A tuning presentation must never enter the scored suffix')
        self.cursor = n1
        setting = start_presentation(presentation, (n0+1)/FS)
        settings = [f for f in self.fixed if abs(f.frequency-setting.frequency) > 2.]+[setting]
        delay = round(self.lead*FS)-1
        first = max(0, (n0-self.pre-s['unreported']-delay)//BLOCK-1)
        last = min(len(s['arrays']['seen']), -(-(n1-s['unreported']-delay)//BLOCK))
        start, sound, _, _ = ear_sound(s, settings, self.lead, 'chooser', np.arange(first, last))
        return room.add_at(s['ears'][0], start+s['unreported'], sound, n0, n1)


def tune_chooser(scene, lead, seed):
    # Same fixed prefix tone menu, starting levels and random seeds as v2.
    rng = np.random.default_rng(seed)
    T = room.PROTOCOL['tuning']
    turns = min(SWEEP_TURNS, int((scene['prefix']-scene['warm'])/FS*SWEEP_HZ))
    fixed, summaries = [], []
    if turns < 1:
        return fixed, [{'skipped': 'tuning part shorter than one sweep turn'}]
    player = ChooserPlayer(scene, lead, fixed)
    for tone in scene['tones']:
        w = tone['w']
        start = abs(w)*10**rng.uniform(-np.log10(T['start_gain_factor_max']), np.log10(T['start_gain_factor_max']))
        maximum = min(start*T['gain_range_factor'], T['max_gain_drive_fraction_of_cap']*room.PROTOCOL['levels']['peak_cap']/tone['mic_amplitude'])
        session = TuningSession(tone['frequency'], start, min_gain=start/T['gain_range_factor'], max_gain=maximum,
                                sweep_turns=turns, seed=int(rng.integers(1 << 30)))
        run_session(session, player, SimulatedListener(FS, 1., seed=int(rng.integers(1 << 30))))
        fixed.append(session.result())
        summaries.append(session.summary())
    return fixed, summaries


def band_boosts(off, on, first):
    f, po = signal.welch(off[first:], FS, nperseg=min(len(off)-first, 4*FS))
    _, pn = signal.welch(on[first:], FS, nperseg=min(len(on)-first, 4*FS))
    result = []
    for lo, hi, centre in room.third_octave_edges():
        mask = (f >= lo) & (f < hi)
        if mask.any():
            before, after = float(po[mask].sum()), float(pn[mask].sum())
            result.append({'centre_hz': centre, 'amplification_db': float(10*np.log10(max(after, 1e-30)/max(before, 1e-30))),
                           'off_power': before, 'on_power': after})
    return result


def evaluate(scene, settings, lead, method, reference_tones):
    off = scene['ears'][0]
    first = scene['prefix']+round(.5*FS)
    start, sound, peak, clipped = ear_sound(scene, settings, lead, method)
    on = room.add_at(off, start+scene['unreported'], sound)
    return {**room.metrics(off, on, first, reference_tones), 'drive_peak': peak,
            'clipped_fraction': clipped, 'active_tones': sum(s.gain > 0 for s in settings),
            'bands': band_boosts(off, on, first)}, on


def relaxed_retune_bound(scene, lead, events):
    """Noncausal band-energy bound, NOT a realizable retuning procedure.

    Unconstrained per-tone sine/cosine coefficients may change at each chooser
    switch, before the simulated earphone and evaluation filters. Path/filter
    transients are retained. Fits all segments jointly to suffix future targets,
    ignoring the output cap. An upper bound for this unclipped linear family,
    not a guarantee for a listener or a claim about arbitrary nonlinear control.
    """
    n = scene['n']
    first = scene['prefix']+round(.5*FS)
    off = signal.sosfilt(room.band_sos(), scene['ears'][0])
    if not scene['tones']:
        return {'band_db': 0., 'segments': 0, 'coefficients': [], 'relaxed_noncausal': True}
    start = int(scene['trace']['v2']['seen'][0])-1+round(lead*FS)+scene['unreported']
    cuts = sorted({start, n, *[e['arrival_sample'] for e in events if start < e['arrival_sample'] < n]})
    labels = []
    design = np.empty((n-first, 2*len(scene['tones'])*(len(cuts)-1)))
    b, a = scene['earphone']
    column = 0
    for tone in scene['tones']:
        for phase in (0., 90.):
            drive = render(scene['trace'], [ToneSetting(tone['frequency'], 1., phase)], lead).ravel()
            arrival = start+np.arange(len(drive))
            for lo, hi in zip(cuts[:-1], cuts[1:]):
                part = drive*((arrival >= lo) & (arrival < hi))
                sound = scene['earphone_gain']*signal.lfilter(b, a, part)
                at_ear = room.add_at(np.zeros(n), start, sound)
                design[:, column] = signal.sosfilt(room.band_sos(), at_ear)[first:]
                labels.append({'frequency_hz': tone['frequency'], 'phase_basis_deg': phase,
                               'first_sample': lo, 'last_exclusive': hi})
                column += 1
    coef = np.linalg.lstsq(design, -off[first:], rcond=None)[0]
    residual = off[first:]+design@coef
    coefficients = [{**label, 'coefficient': float(value)} for label, value in zip(labels, coef)]
    db = 10*np.log10(max(float(np.mean(off[first:]**2)), 1e-30)/max(float(np.mean(residual**2)), 1e-30))
    return {'band_db': float(db), 'segments': len(cuts)-1, 'coefficients': coefficients,
            'relaxed_noncausal': True, 'ignores_clipping': True, 'filter_transients_retained': True,
            'scope': 'Upper bound on band energy for unconstrained piecewise-constant tone gains/phases in the unclipped linear renderer'}


def reference_diagnostic(scene, lead):
    baseline, chooser = hard_reference(scene['trace'], lead)
    origins = scene['trace']['v2']['seen']-1
    hz = round(lead*FS)+np.arange(BLOCK)
    keep = (origins+hz[0] >= scene['prefix']+round(.5*FS)) & (origins+hz[-1] < scene['n'])
    target = scene['mic'][origins[keep, None]+hz]
    ref = float(np.mean(target**2))
    return {'scope': 'reference microphone only, hard gates including DC, unweighted forecasts at actual room lead',
            'target_blocks': int(keep.sum()),
            **{name: float(10*np.log10(max(ref, 1e-30)/max(float(np.mean((target-pred[keep])**2)), 1e-30)))
               for name, pred in [('v2_broadband_db', baseline), ('chooser_broadband_db', chooser)]}}


def score(scene, metadata):
    rows, details, windows = [], [], []
    for lead_ms in (30, 200):
        lead = lead_ms/1000
        seed = metadata['tuning_seeds'][str(lead_ms)]['1.0']
        v2, v2_summary = room.tune_by_ear(scene, lead, 1., seed)
        own, own_summary = tune_chooser(scene, lead, seed)
        conditions = [('v2_tuned', 'v2', v2), ('chooser_reuse_v2', 'chooser', v2),
                      ('chooser_tuned', 'chooser', own), ('zero', 'v2', [])]
        signals = {}
        for arm, method, settings in conditions:
            metrics, on = evaluate(scene, settings, lead, method, metadata['reference_tones_hz'])
            rows.append({'lead_ms': lead_ms, 'arm': arm, **metrics})
            signals[arm] = signal.sosfilt(room.band_sos(), on)
        for event in metadata['switches'][str(lead_ms)]:
            event = dict(event, lead_ms=lead_ms)
            if event['complete_200ms_window']:
                a, b = event['arrival_sample']-200, event['arrival_sample']+200
                powers = {arm: float(np.mean(y[a:b]**2)) for arm, y in signals.items()}
                event['band_powers'] = powers
                event['excess_over_v2_db'] = {arm: float(10*np.log10(max(powers[arm], 1e-30)/max(powers['v2_tuned'], 1e-30)))
                                            for arm in ('chooser_reuse_v2', 'chooser_tuned')}
            windows.append(event)
        details.append({'lead_ms': lead_ms, 'v2_tuning': v2_summary, 'chooser_tuning': own_summary,
                        'v2_settings': [asdict(s) for s in v2], 'chooser_settings': [asdict(s) for s in own],
                        'reference_diagnostic': reference_diagnostic(scene, lead),
                        'relaxed_retune_bound': relaxed_retune_bound(scene, lead, metadata['switches'][str(lead_ms)])})
    return {'rows': rows, 'details': details, 'switch_windows': windows}


def summarize(cases, coverage, bootstrap_seed=20261022):
    result = {}
    for lead in (30, 200):
        result[str(lead)] = {}
        for arm in ('chooser_reuse_v2', 'chooser_tuned'):
            paired, harms, windows, clipped = {}, [], [], []
            for c in cases:
                baseline = next(r for r in c['rows'] if r['lead_ms'] == lead and r['arm'] == 'v2_tuned')
                candidate = next(r for r in c['rows'] if r['lead_ms'] == lead and r['arm'] == arm)
                if baseline['tone_db'] is not None and candidate['tone_db'] is not None:
                    paired.setdefault(c['source_id'], []).append(candidate['tone_db']-baseline['tone_db'])
                old_bands = {r['centre_hz']:r['amplification_db'] for r in baseline['bands']}
                for band in candidate['bands']:
                    if band['amplification_db'] > 1.+1e-9 and old_bands[band['centre_hz']] <= 1.+1e-9:
                        harms.append({'case_id': c['case_id'], 'source_id': c['source_id'], 'band_hz': band['centre_hz'],
                                      'candidate_db': band['amplification_db'], 'v2_db': old_bands[band['centre_hz']]})
                if candidate['band_db'] < -.5-1e-9 and baseline['band_db'] >= -.5-1e-9:
                    harms.append({'case_id': c['case_id'], 'source_id': c['source_id'], 'band_hz': '35-350',
                                  'candidate_db': -candidate['band_db'], 'v2_db': -baseline['band_db']})
                if candidate['clipped_fraction'] > baseline['clipped_fraction']+1e-6:
                    clipped.append({'case_id': c['case_id'], 'candidate': candidate['clipped_fraction'], 'v2': baseline['clipped_fraction']})
                for window in c['switch_windows']:
                    if window['lead_ms'] == lead and window['complete_200ms_window']:
                        windows.append({'case_id': c['case_id'], 'row': window['row'], 'source_id': c['source_id'],
                                        'excess_db': window['excess_over_v2_db'][arm]})
            source_scores = {source: float(np.mean(values)) for source, values in paired.items()}
            values = np.array(list(source_scores.values()))
            if len(values):
                rng = np.random.default_rng(bootstrap_seed)
                sampled = values[rng.integers(0, len(values), size=(20000, len(values)))].mean(axis=1)
                ci = np.percentile(sampled, [2.5, 97.5]).tolist()
                mean, worst = float(values.mean()), float(values.min())
            else:
                ci, mean, worst = [None, None], None, None
            violations = [w for w in windows if w['excess_db'] > 3.+1e-9]
            sufficient = coverage[str(lead)]['exposed_complete_sources'] >= 6
            point_pass = bool(len(values) and mean >= -.5 and worst >= -1 and not harms and not violations and not clipped)
            if not sufficient:
                decision = 'inconclusive_insufficient_switch_coverage'
            elif not point_pass:
                decision = 'fails_simulated_noninferiority_or_harm_criteria'
            elif ci[0] < -.5:
                decision = 'inconclusive_noninferiority_interval'
            else:
                decision = 'passes_bounded_simulation_criteria'
            result[str(lead)][arm] = {'tonal_sources': len(values), 'source_mean_paired_db': source_scores,
                'mean_paired_db': mean, 'bootstrap95': ci, 'worst_source_mean_db': worst,
                'switch_coverage_sufficient': sufficient, 'point_criteria_passed': point_pass,
                'new_boosts': harms, 'switch_violations': violations, 'extra_clipping': clipped,
                'maximum_switch_excess_db': max([w['excess_db'] for w in windows], default=None),
                'decision': decision, 'role': 'primary' if lead == 30 and arm == 'chooser_reuse_v2' else 'secondary_or_exploratory'}
    return result
