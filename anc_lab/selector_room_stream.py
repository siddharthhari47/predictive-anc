"""Offline live-convention room bridge; no audio device imports.

Both predictors receive x[0] onwards and share newest-sample origins seen-1.
L2 still decides from hard-gated 20/120 ms errors. Tone output is independently
evaluated at the room's exact 30/200 ms leads, with the live per-arm gate ramp.
This integration convention is a development experiment, not a new fresh pass.
"""
import numpy as np
from .antihum import AntiHumEngine, log_arrays, replay as live_replay, FS, BLOCK
from .selector_stream_profile import MaturedGate, MaturedMixer
from .selection_study import horizon_setup
from . import selector_headroom as h

LEADS = (0.03, 0.2)


def pack_components(seen, records, gate):
    n = max([len(c) for c in records]+[1])
    frequency = np.full((len(records), n), np.nan)
    phasor = np.zeros((len(records), n), complex)
    for i, components in enumerate(records):
        for j, (f, p) in enumerate(components):
            frequency[i, j], phasor[i, j] = f, p
    return {'seen': np.asarray(seen), 'frequency': frequency, 'phasor': phasor,
            'gate': np.asarray(gate, bool)}


def stream(mic, protocol):
    engine = AntiHumEngine(keep_log=True)
    bank = h.s2.make_bank(next(m for m in protocol['methods'] if m['kind'] == 'react'), protocol['v2'])
    _, horizons, groups = horizon_setup()
    gate = MaturedGate(groups, protocol['v2']['gate'])
    mixers = [MaturedMixer(hz) for _, hz in groups]
    components = [[], []]
    fade_gates, dc, weights, selected, ghosts = [], [], [], [], []
    shadow_rows = []
    n = len(mic)//BLOCK*BLOCK
    for start in range(0, n, BLOCK):
        block = mic[start:start+BLOCK]
        engine.push(block)
        bank.push(block)
        origin = engine.origin_seen-1
        assert bank.seen-1 == origin
        shadow = np.stack([engine.shadow_forecast(horizons), bank.forecast(horizons)])
        gated, enabled = gate.step(engine.history, origin, shadow)
        assert bool(enabled[0]) == engine.gate_open, ('v2 gate parity', origin)
        group_weights = []
        for g, ((cols, _), mixer) in enumerate(zip(groups, mixers)):
            if origin >= 999:  # same half-second warm-up, on live block origins
                arms = np.stack([gated[0, cols], gated[1, cols], np.zeros(BLOCK)])
                mixer.step(engine.history, origin, arms)
                elapsed = mixer.elapsed-BLOCK
                alpha = np.clip((elapsed+np.arange(1, BLOCK+1))/mixer.fade_n, 0., 1.)
                w = mixer.start[None, :]+alpha[:, None]*(mixer.goal-mixer.start)[None, :]
            else:
                w = np.tile([1., 0., 0.], (BLOCK, 1))
            group_weights.append(w)
            components[g].append(list(bank.group_components[g]))
        weights.append(group_weights)
        selected.append([m.selected for m in mixers])
        fade_gates.append(bool(enabled[1]))
        dc.append(engine.dc)
        ghosts.append(len(bank.ghosts))
        shadow_rows.append(gated)
    v2 = log_arrays(engine.log)
    return {'v2': v2, 'bank': [pack_components(v2['seen'], c, fade_gates) for c in components],
            'dc': np.array(dc), 'weights': np.array(weights), 'selected': np.array(selected),
            'ghosts': np.array(ghosts), 'gated_reference': np.array(shadow_rows)}


def lead_group(lead):
    if lead not in LEADS:
        raise ValueError('Room bridge supports exactly 30 and 200 ms leads')
    return LEADS.index(lead)


def render(trace, settings, lead, method='chooser', rows=None):
    """Use the existing live tone renderer for each arm, then the exact L2 mix."""
    g = lead_group(lead)
    rows = np.arange(len(trace['v2']['seen'])) if rows is None else np.asarray(rows)
    v2 = live_replay(trace['v2'], settings, lead, rows=rows)
    if method == 'v2':
        return v2
    if method != 'chooser':
        raise ValueError(method)
    fade = live_replay(trace['bank'][g], settings, lead, rows=rows)
    w = trace['weights'][rows, g]
    return v2*w[:, :, 0]+fade*w[:, :, 1]


def hard_reference(trace, lead):
    """Secondary microphone forecasts, DC included and hard gated; no tuning."""
    g = lead_group(lead)
    horizon = round(lead*FS)+np.arange(BLOCK)
    arrays = (trace['v2'], trace['bank'][g])
    out = []
    for arm, a in enumerate(arrays):
        f = np.nan_to_num(a['frequency'])
        wave = np.sum(np.real(a['phasor'][:, :, None]*np.exp(2j*np.pi*f[:, :, None]*horizon/FS)), axis=1)
        if arm == 0:
            wave += trace['dc'][:, None]
        out.append(wave*a['gate'][:, None])
    w = trace['weights'][:, g]
    return out[0], out[0]*w[:, :, 0]+out[1]*w[:, :, 1]


def switch_events(trace, lead, prefix, n, unreported, frequencies):
    """Count suffix decisions and command exposure only; no ear pressure scores."""
    from .antihum import ToneSetting
    g = lead_group(lead)
    choices = trace['selected'][:, g]
    transitions = np.flatnonzero(np.diff(choices, prepend=0) != 0)
    settings = [ToneSetting(f, 1.) for f in frequencies]
    commands = render(trace, settings, lead)
    start_score = prefix+round(.5*FS)
    events = []
    for row in transitions:
        # First command sample is newest input sample + actual room lead.
        arrival = int(trace['v2']['seen'][row])-1+round(lead*FS)+unreported
        if arrival < start_score or arrival >= n:
            continue
        end = min(row+10, len(commands))
        exposed = bool(np.max(np.abs(commands[max(0, row-1):end]), initial=0.) > 1e-12)
        complete = arrival-200 >= start_score and arrival+200 <= n
        events.append({'row': int(row), 'arrival_sample': arrival, 'arrival_seconds': arrival/FS,
                       'from_arm': int(choices[row-1]) if row else 0, 'to_arm': int(choices[row]),
                       'command_exposed': exposed, 'complete_200ms_window': bool(complete)})
    return events


def save_trace_fields(trace):
    out = {key: trace[key] for key in ('dc', 'weights', 'selected', 'ghosts', 'gated_reference')}
    for label, arrays in [('v2', trace['v2']), ('bank0', trace['bank'][0]), ('bank1', trace['bank'][1])]:
        out.update({label+'_'+key: value for key, value in arrays.items()})
    return out


def load_trace_fields(a):
    arrays = lambda label: {key: a[label+'_'+key].copy() for key in ('seen', 'frequency', 'phasor', 'gate')}
    return {**{key: a[key].copy() for key in ('dc', 'weights', 'selected', 'ghosts', 'gated_reference')},
            'v2': arrays('v2'), 'bank': [arrays('bank0'), arrays('bank1')]}
