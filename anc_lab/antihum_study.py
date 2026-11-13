"""Tune-by-ear in simulated rooms, with real recorded hums as the sources.

Every number from this module is SIMULATED EAR ATTENUATION: computed sound at a
simulated ear in a simulated room. Nothing is played or measured.

Per recording and room:
- A rectangular room of random size with a reverberation time of 0.2-0.5 s,
  modelled by its acoustic modes below 1.1 kHz (small rooms are modal at hum
  frequencies, so a few centimetres can change the sound a lot).
- Random positions for the hum source, the listener's left ear, and a laptop
  microphone 45 cm in front of the listener at desk height.
- The recording plays from the source position. Microphone and ear each hear it
  through their own room path, plus their own independent noise (-20 dB).
- Wired earphones with weak bass (first-order roll-off below 50-150 Hz) and a
  3 ms delay that the operating system does not report.
- The engine (frozen v2 detection, fast release and realized-error gate) runs on
  the microphone signal block by block and never sees the future.

Split: tones are chosen and tuned on the first 40% of each recording (the
listener hears that part, looped when it is short); the remaining 60% is
evaluated with every setting frozen. Comparators: no anti-hum (zero), untuned
(gain exact, earphone path known, only the room's phase difference between
microphone and ear ignored), path oracle (exact path ratio at the tuned
frequencies, i.e. what an ear-microphone measurement would give), and
tune-by-ear with simulated listeners at three judgement-noise levels.
Robustness: head moves of 2-20 cm and extra playback delay of 1-20 ms after
tuning, with nothing retuned.
"""
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import csv
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
from scipy import signal
from threadpoolctl import threadpool_limits

from .antihum import BLOCK, DEFAULT_PEAK_CAP, FS, AntiHumEngine, ToneSetting, log_arrays, replay
from .real_hum_study import load_any, near_mask
from .tuning import SWEEP_HZ, SWEEP_TURNS, SimulatedListener, TuningSession, run_session, start_presentation

WORKERS = max(1, min(19, (os.cpu_count() or 2)-2))
ROOT = Path(__file__).resolve().parents[1]

# Frozen before the first run on real recordings (written to protocol.json).
PROTOCOL = {
    'kind':'tune_by_ear_simulation', 'label':'simulated ear attenuation', 'fs':FS, 'block':BLOCK, 'seed':20261017,
    'rooms_per_recording':3,
    'room':{'length_m':[3., 6.], 'width_m':[2.5, 5.], 'height_m':[2.4, 3.], 'rt60_s':[.2, .5],
            'speed_of_sound_m_s':343., 'modes_up_to_hz':1100., 'taper_hz':[700., 1000.], 'fir_taps':2048,
            'modelling_delay_samples':16, 'wall_clearance_m':.3, 'leaky_room_no_zero_mode':True},
    'geometry':{'ear_height_m':1.2, 'ear_offset_m':.08, 'laptop_distance_m':.45, 'laptop_height_m':.9,
                'head_wall_clearance_m':.8, 'min_source_distance_m':1., 'source_height_m':[.2, 2.2], 'ear':'left'},
    'earphone':{'highpass_hz':[50., 150.], 'order':1, 'unreported_delay_ms':3.},
    'noise':{'level_db_re_prefix_band':-20., 'lowpass_hz':200., 'independent_at_mic_and_ear':True},
    'levels':{'mic_prefix_band_rms':.01, 'oracle_drive_sum':.02, 'peak_cap':DEFAULT_PEAK_CAP},
    'split':{'tuning_fraction':.4, 'engine_warmup_s':1.5, 'presentation_preroll_s':.2},
    'tones':{'max_tuned':3, 'min_presence':.5, 'cluster_hz':2.},
    'tuning':{'listener_sigma_db':[.5, 1., 2.], 'start_gain_factor_max':8., 'gain_range_factor':32.,
              'max_gain_drive_fraction_of_cap':.8},
    'leads_ms':[30., 200.],
    'robustness':{'head_moves_cm':[0., 2., 5., 10., 20.], 'latency_drift_ms':[0., 1., 5., 20.]},
    'evaluation':{'discard_s':.5, 'band_hz':[35., 350.], 'tone_halfwidth_hz':1.5, 'window_s':1.,
                  'third_octave_band_indices':[-15, -1]},
}
ARMS = ['untuned_room_phase_ignored', 'path_oracle']+[f'tuned_sigma_{s:g}' for s in PROTOCOL['tuning']['listener_sigma_db']]


def band_sos(band=None):
    return signal.butter(4, band or PROTOCOL['evaluation']['band_hz'], 'bandpass', fs=FS, output='sos')


# ---------------- rooms ----------------
def draw_room(rng):
    P, G = PROTOCOL['room'], PROTOCOL['geometry']
    dims = np.array([rng.uniform(*P['length_m']), rng.uniform(*P['width_m']), rng.uniform(*P['height_m'])])
    clear = P['wall_clearance_m']
    inside = lambda p, margin=clear: bool(np.all(p >= margin) and np.all(p <= dims-margin))
    for _ in range(10000):
        hc = G['head_wall_clearance_m']
        head = np.array([rng.uniform(hc, dims[0]-hc), rng.uniform(hc, dims[1]-hc), G['ear_height_m']])
        facing = rng.uniform(0, 2*np.pi)
        forward, left = np.array([np.cos(facing), np.sin(facing), 0.]), np.array([-np.sin(facing), np.cos(facing), 0.])
        ear = head+G['ear_offset_m']*left
        mic = head+G['laptop_distance_m']*forward
        mic[2] = G['laptop_height_m']
        source = np.array([rng.uniform(clear, dims[0]-clear), rng.uniform(clear, dims[1]-clear),
                           rng.uniform(G['source_height_m'][0], min(G['source_height_m'][1], dims[2]-clear))])
        move = rng.uniform(0, 2*np.pi)
        direction = np.array([np.cos(move), np.sin(move), 0.])
        ears = [ear+cm/100*direction for cm in PROTOCOL['robustness']['head_moves_cm']]
        if inside(mic) and np.linalg.norm(source-head) >= G['min_source_distance_m'] and all(inside(e, .1) for e in ears):
            return {'dims_m':dims.tolist(), 'rt60_s':float(rng.uniform(*P['rt60_s'])), 'source':source.tolist(),
                    'mic':mic.tolist(), 'ears':[e.tolist() for e in ears], 'facing_deg':float(np.degrees(facing)),
                    'move_direction_deg':float(np.degrees(move)),
                    'earphone_highpass_hz':float(rng.uniform(*PROTOCOL['earphone']['highpass_hz'])),
                    'source_to_ear_m':float(np.linalg.norm(source-ears[0])),
                    'source_to_mic_m':float(np.linalg.norm(source-mic))}
    raise RuntimeError('Could not place source and listener')


def modal_irs(dims, rt60, source, receivers, fs=FS):
    """Room impulse responses (receivers x taps) from a rigid-wall rectangular-room mode sum.

    Each mode is a damped resonator with decay 6.91/RT60; the zero-frequency
    mode is left out (real rooms leak). The sum is band-limited (raised-cosine
    taper 700-1000 Hz) and delayed by a few samples so the band-limiting ripple
    stays causal. Overall scale is arbitrary; ratios between receivers are not.
    """
    P = PROTOCOL['room']
    c, fmax, taps = P['speed_of_sound_m_s'], P['modes_up_to_hz'], P['fir_taps']
    dims, source, receivers = np.asarray(dims), np.asarray(source), np.atleast_2d(receivers)
    n = [np.arange(int(2*L*fmax/c)+1) for L in dims]
    nx, ny, nz = (a.ravel() for a in np.meshgrid(*n, indexing='ij'))
    fn = c/2*np.sqrt((nx/dims[0])**2+(ny/dims[1])**2+(nz/dims[2])**2)
    keep = (fn > 0) & (fn <= fmax)
    nx, ny, nz, wn = nx[keep], ny[keep], nz[keep], 2*np.pi*fn[keep]
    eps = np.where(nx > 0, 2., 1.)*np.where(ny > 0, 2., 1.)*np.where(nz > 0, 2., 1.)
    shape = lambda p: (np.cos(nx*np.pi*p[0]/dims[0])*np.cos(ny*np.pi*p[1]/dims[1])*np.cos(nz*np.pi*p[2]/dims[2]))
    weights = np.array([eps*shape(source)*shape(r) for r in receivers])
    f = np.fft.rfftfreq(taps, 1/fs)
    w = 2*np.pi*f
    delta = 6.91/rt60
    H = np.zeros((len(receivers), len(f)), complex)
    for start in range(0, len(wn), 2000):
        part = wn[start:start+2000, None]
        H += weights[:, start:start+2000]@(1j*w/(part**2-w**2+2j*delta*w))
    lo, hi = P['taper_hz']
    taper = np.where(f <= lo, 1., np.where(f >= hi, 0., .5*(1+np.cos(np.pi*(f-lo)/(hi-lo)))))
    H *= taper*np.exp(-1j*w*P['modelling_delay_samples']/fs)
    return np.fft.irfft(H, taps), int(keep.sum())


def response_at(h, frequency, fs=FS):
    return complex(np.sum(h*np.exp(-2j*np.pi*frequency*np.arange(len(h))/fs)))


def earphone_filter(highpass_hz):
    return signal.butter(PROTOCOL['earphone']['order'], highpass_hz, 'highpass', fs=FS)


def earphone_response(b, a, frequency, delay_samples):
    return complex(signal.freqz(b, a, worN=[frequency], fs=FS)[1][0]*np.exp(-2j*np.pi*frequency*delay_samples/FS))


# ---------------- scene ----------------
def prepare_scene(x, room, seed):
    """Microphone and ear signals, engine log, chosen tones and their exact path ratios."""
    rng = np.random.default_rng(seed)
    n = len(x)-len(x) % BLOCK
    x = np.asarray(x[:n], float)
    irs, modes = modal_irs(room['dims_m'], room['rt60_s'], room['source'], [room['mic']]+room['ears'])
    received = [signal.fftconvolve(x, h)[:n] for h in irs]
    prefix = int(PROTOCOL['split']['tuning_fraction']*n)//BLOCK*BLOCK
    band = band_sos()
    band_power = lambda s: float(np.mean(signal.sosfilt(band, s)**2))
    scale = PROTOCOL['levels']['mic_prefix_band_rms']/np.sqrt(band_power(received[0][:prefix]))
    received = [r*scale for r in received]
    nb, na = signal.butter(1, PROTOCOL['noise']['lowpass_hz'], 'lowpass', fs=FS)

    def noise_like(reference):
        noise = signal.lfilter(nb, na, rng.standard_normal(n))
        target = band_power(reference[:prefix])*10**(PROTOCOL['noise']['level_db_re_prefix_band']/10)
        return noise*np.sqrt(target/band_power(noise[:prefix]))
    mic = received[0]+noise_like(received[0])
    ear_noise = noise_like(received[1])
    ears = [r+ear_noise for r in received[1:]]

    engine = AntiHumEngine(keep_log=True)
    started = time.perf_counter()
    for i in range(0, n, BLOCK):
        engine.push(mic[i:i+BLOCK])
    engine_seconds = time.perf_counter()-started
    arrays = log_arrays(engine.log)
    warm = round(PROTOCOL['split']['engine_warmup_s']*FS)
    tuning_rows = np.nonzero((arrays['seen'] > warm) & (arrays['seen'] <= prefix))[0]
    test_rows = np.nonzero(arrays['seen'] > prefix)[0]
    tones = choose_tones(arrays, tuning_rows)
    b, a = earphone_filter(room['earphone_highpass_hz'])
    unreported = round(PROTOCOL['earphone']['unreported_delay_ms']*FS/1000)
    for tone in tones:
        f = tone['frequency']
        tone['ear_over_mic'] = response_at(irs[1], f)/response_at(irs[0], f)
        tone['w_unit_earphone'] = tone['ear_over_mic']/earphone_response(b, a, f, unreported)
    drive = sum(abs(t['w_unit_earphone'])*t['mic_amplitude'] for t in tones)
    gain = drive/PROTOCOL['levels']['oracle_drive_sum'] if tones else 1.
    for tone in tones:
        tone['w'] = tone['w_unit_earphone']/gain
        tone['earphone_phase_deg'] = float(np.degrees(np.angle(earphone_response(b, a, tone['frequency'], unreported))))
    test_with_tones = np.sum(~np.isnan(arrays['frequency'][test_rows]), axis=1) > 0
    ir_energy = np.sum(irs**2, axis=1)
    info = {'modes':modes, 'ir_tail_energy_fraction_max':float(np.max(np.sum(irs[:, -len(irs[0])//10:]**2, axis=1)/ir_energy)),
            'engine_ms_per_block':1e3*engine_seconds/len(arrays['seen']), 'engine_counters':engine.counters,
            'test_fraction_with_tones':float(np.mean(test_with_tones)),
            'test_fraction_gate_open_with_tones':float(np.mean(arrays['gate'][test_rows][test_with_tones])) if test_with_tones.any() else None,
            'earphone_gain':float(gain), 'n':n, 'prefix':prefix}
    return {'mic':mic, 'ears':ears, 'arrays':arrays, 'prefix':prefix, 'n':n, 'warm':warm, 'tones':tones,
            'earphone':(b, a), 'earphone_gain':gain, 'unreported':unreported, 'info':info}


def choose_tones(arrays, rows):
    """Tones the engine held in at least half of the tuning blocks, strongest first (at most 3)."""
    T = PROTOCOL['tones']
    if not len(rows):
        return []
    freq, amp = arrays['frequency'][rows], np.abs(arrays['phasor'][rows])
    row_id = np.repeat(np.arange(len(rows))[:, None], freq.shape[1], 1)
    ok = ~np.isnan(freq)
    f, a, r = freq[ok], amp[ok], row_id[ok]
    clusters = []
    while len(f):
        centres, counts = np.unique(np.round(f*2)/2, return_counts=True)
        centre = centres[np.argmax(counts)]
        members = np.abs(f-centre) <= T['cluster_hz']
        clusters.append({'frequency':float(np.median(f[members])), 'presence':len(np.unique(r[members]))/len(rows),
                         'mic_amplitude':float(np.mean(a[members]))})
        f, a, r = f[~members], a[~members], r[~members]
    keep = sorted((c for c in clusters if c['presence'] >= T['min_presence']), key=lambda c:-c['mic_amplitude'])
    return keep[:T['max_tuned']]


# ---------------- sound at the ear ----------------
def ear_sound(scene, settings, lead_s, rows=None):
    """Earphone sound at the ear for the engine's output after `rows`: (first engine output index, sound, peak, clipped)."""
    arrays = scene['arrays']
    rows = np.arange(len(arrays['seen'])) if rows is None else rows
    if not len(rows):
        return 0, np.zeros(0), 0., 0.
    out = replay(arrays, settings, lead_s, rows=rows).ravel()
    cap = PROTOCOL['levels']['peak_cap']
    drive = np.clip(out, -cap, cap)
    b, a = scene['earphone']
    start = int(arrays['seen'][rows[0]])+round(lead_s*FS)-1
    return start, scene['earphone_gain']*signal.lfilter(b, a, drive), float(np.max(np.abs(out))), float(np.mean(np.abs(out) > cap))


def add_at(base, start, sound, lo=0, hi=None):
    """base[lo:hi] plus `sound` placed at absolute index `start`."""
    hi = len(base) if hi is None else hi
    out = np.array(base[lo:hi], float)
    a, b = max(start, lo), min(start+len(sound), hi)
    if b > a:
        out[a-lo:b-lo] += sound[a-start:b-start]
    return out


class RoomPlayer:
    """Plays presentations into the simulated ear, cycling through the tuning part of the recording."""
    def __init__(self, scene, lead_s, fixed):
        self.scene, self.lead, self.fixed = scene, lead_s, fixed
        self.cursor = scene['warm']
        self.pre = round(PROTOCOL['split']['presentation_preroll_s']*FS)

    def __call__(self, presentation):
        s = self.scene
        length = round(presentation.seconds*FS)
        if self.cursor+length > s['prefix']:
            self.cursor = s['warm']
        n0, n1 = self.cursor, self.cursor+length
        if n1 > s['prefix']:
            raise ValueError('Presentation longer than the tuning part; held-out audio must stay unheard')
        self.cursor = n1
        # Engine output index m carries engine time (m+1)/FS; the presentation starts at index n0.
        setting = start_presentation(presentation, (n0+1)/FS)
        settings = [f for f in self.fixed if abs(f.frequency-setting.frequency) > 2.]+[setting]
        delay = round(self.lead*FS)-1
        first = max(0, (n0-self.pre-s['unreported']-delay)//BLOCK-1)
        last = min(len(s['arrays']['seen']), -(-(n1-s['unreported']-delay)//BLOCK))
        start, sound, _, _ = ear_sound(s, settings, self.lead, np.arange(first, last))
        return add_at(s['ears'][0], start+s['unreported'], sound, n0, n1)


def tune_by_ear(scene, lead_s, sigma, seed):
    rng = np.random.default_rng(seed)
    T = PROTOCOL['tuning']
    turns = min(SWEEP_TURNS, int((scene['prefix']-scene['warm'])/FS*SWEEP_HZ))
    fixed, rows = [], []
    if turns < 1:
        return fixed, [{'skipped':'tuning part shorter than one sweep turn'}]
    player = RoomPlayer(scene, lead_s, fixed)
    for k, tone in enumerate(scene['tones']):
        w = tone['w']
        start = abs(w)*10**rng.uniform(-np.log10(T['start_gain_factor_max']), np.log10(T['start_gain_factor_max']))
        max_gain = min(start*T['gain_range_factor'], T['max_gain_drive_fraction_of_cap']*PROTOCOL['levels']['peak_cap']/tone['mic_amplitude'])
        session = TuningSession(tone['frequency'], start, min_gain=start/T['gain_range_factor'], max_gain=max_gain,
                                sweep_turns=turns, seed=int(rng.integers(1 << 30)))
        run_session(session, player, SimulatedListener(FS, sigma, seed=int(rng.integers(1 << 30))))
        fixed.append(session.result())
        summary = session.summary()
        tuned = summary['gain_before_check'] or summary['gain']
        rho = tuned*np.exp(1j*np.deg2rad(summary['phase_deg']))/w
        summary.update({'oracle_gain':abs(w), 'oracle_phase_deg':float(np.degrees(np.angle(w)) % 360),
                        'start_gain':start, 'gain_error_db':float(20*np.log10(tuned/abs(w))) if tuned > 0 else None,
                        'phase_error_deg':float((summary['phase_deg']-np.degrees(np.angle(w))+180) % 360-180),
                        'predicted_tone_attenuation_db':float(-20*np.log10(max(abs(1-rho), 1e-6))),
                        'sweep_turns':turns})
        rows.append(summary)
    return fixed, rows


def arm_settings(scene, arm, tuned):
    if arm == 'path_oracle':
        return [ToneSetting(t['frequency'], abs(t['w']), float(np.degrees(np.angle(t['w'])) % 360)) for t in scene['tones']]
    if arm == 'untuned_room_phase_ignored':
        return [ToneSetting(t['frequency'], abs(t['w']), float(-t['earphone_phase_deg']) % 360) for t in scene['tones']]
    return tuned[arm]


# ---------------- evaluation ----------------
def third_octave_edges():
    lo, hi = PROTOCOL['evaluation']['third_octave_band_indices']
    centres = 1000*10**(np.arange(lo, hi+1)/10)
    return [(c*10**(-1/20), c*10**(1/20), c) for c in centres]


def metrics(off, on, start, reference_tones):
    E = PROTOCOL['evaluation']
    band = band_sos()
    bo, bn = signal.sosfilt(band, off)[start:], signal.sosfilt(band, on)[start:]
    o, a = off[start:], on[start:]
    ratio = lambda p, q: float(10*np.log10(max(p, 1e-30)/max(q, 1e-30)))
    f, po = signal.welch(o, FS, nperseg=min(len(o), 4*FS))
    _, pn = signal.welch(a, FS, nperseg=min(len(a), 4*FS))
    tone_db = None
    if reference_tones:
        near = near_mask(f, reference_tones, E['tone_halfwidth_hz'])
        tone_db = ratio(po[near].sum(), pn[near].sum())
    amplification = []
    for lo, hi, centre in third_octave_edges():
        inside = (f >= lo) & (f < hi)
        if inside.any():
            amplification.append((ratio(pn[inside].sum(), po[inside].sum()), float(centre)))
    worst = max(amplification)
    w = round(E['window_s']*FS)
    windows = [ratio(np.mean(bo[i:i+w]**2), np.mean(bn[i:i+w]**2)) for i in range(0, len(bo)-w+1, w)]
    return {'band_db':ratio(np.mean(bo**2), np.mean(bn**2)), 'broadband_db':ratio(np.mean(o**2), np.mean(a**2)),
            'tone_db':tone_db, 'max_third_octave_amplification_db':worst[0], 'worst_third_octave_hz':worst[1],
            'worst_1s_band_db':min(windows) if windows else None}


def evaluate(scene, settings, lead_s, reference_tones):
    R, E = PROTOCOL['robustness'], PROTOCOL['evaluation']
    first = scene['prefix']+round(E['discard_s']*FS)
    conditions = [(i, cm, 0.) for i, cm in enumerate(R['head_moves_cm'])]+[(0, 0., ms) for ms in R['latency_drift_ms'][1:]]
    active = [s for s in settings if s.gain > 0]
    rows = []
    if not active:
        zero = {'band_db':0., 'broadband_db':0., 'tone_db':0. if reference_tones else None,
                'max_third_octave_amplification_db':0., 'worst_third_octave_hz':None, 'worst_1s_band_db':0.}
        return [{'move_cm':cm, 'drift_ms':ms, **zero, 'drive_peak':0., 'clipped_fraction':0., 'active_tones':0}
                for _, cm, ms in conditions]
    start, sound, peak, clipped = ear_sound(scene, active, lead_s)
    for i, cm, ms in conditions:
        on = add_at(scene['ears'][i], start+scene['unreported']+round(ms*FS/1000), sound)
        rows.append({'move_cm':cm, 'drift_ms':ms, **metrics(scene['ears'][i], on, first, reference_tones),
                     'drive_peak':peak, 'clipped_fraction':clipped, 'active_tones':len(active)})
    return rows


def case_seeds(records):
    """One seed per (recording, room), in protocol order."""
    rooms = PROTOCOL['rooms_per_recording']
    seeds = np.random.SeedSequence(PROTOCOL['seed']).spawn(len(records)*rooms)
    return {(r['file'], k):int(seeds[i*rooms+k].generate_state(1)[0]) for i, r in enumerate(records) for k in range(rooms)}


def build_scene(path, seed):
    """Room and scene for one case; the returned generator continues the case's random stream."""
    x, _ = load_any(Path(path), FS)
    rng = np.random.default_rng(seed)
    room = draw_room(rng)
    return room, prepare_scene(x, room, int(rng.integers(1 << 30))), rng


def _task(args):
    path, record, room_index, seed = args
    with threadpool_limits(limits=1):
        started = time.perf_counter()
        room, scene, rng = build_scene(path, seed)
        reference = record['reference_tones_hz']
        out_rows, tuning_rows = [], []
        for lead_ms in PROTOCOL['leads_ms']:
            lead = lead_ms/1000
            tuned = {}
            for sigma in PROTOCOL['tuning']['listener_sigma_db']:
                arm = f'tuned_sigma_{sigma:g}'
                tuned[arm], summaries = tune_by_ear(scene, lead, sigma, int(rng.integers(1 << 30)))
                tuning_rows += [{'file':record['file'], 'room':room_index, 'lead_ms':lead_ms, 'sigma_db':sigma, **s} for s in summaries]
            for arm in ARMS:
                for row in evaluate(scene, arm_settings(scene, arm, tuned), lead, reference):
                    out_rows.append({'file':record['file'], 'room':room_index, 'lead_ms':lead_ms, 'arm':arm,
                                     'tuned_tones':len(scene['tones']), **row})
        tones = [{k:(v if not isinstance(v, complex) else [v.real, v.imag]) for k, v in t.items()} for t in scene['tones']]
        return {'file':record['file'], 'room_index':room_index, 'room':room, 'tones':tones, 'scene':scene['info'],
                'reference_tones_hz':reference, 'rows':out_rows, 'tuning':tuning_rows,
                'seconds':time.perf_counter()-started}


def _jsonable(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, complex):
        return [value.real, value.imag]
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(type(value))


def run_tune_by_ear_study(audio_folder, real_hums, output):
    output, audio_folder = Path(output), Path(audio_folder)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output folder must be new or empty; earlier results are preserved.')
    real = json.loads(Path(real_hums).read_text(encoding='utf-8'))
    records = [r for r in real['files'] if not r['electrical_not_acoustic']]
    missing = [r['file'] for r in records if not (audio_folder/r['file']).exists()]
    if missing:
        raise FileNotFoundError(f'Missing recordings: {missing}')
    output.mkdir(parents=True, exist_ok=True)
    protocol = {**PROTOCOL, 'arms':ARMS, 'recordings':[r['file'] for r in records],
                'code_sha256':{name:hashlib.sha256((ROOT/'anc_lab'/name).read_bytes()).hexdigest()
                               for name in ('antihum_study.py', 'antihum.py', 'tuning.py')},
                'frozen_utc':datetime.now(timezone.utc).isoformat()}
    (output/'protocol.json').write_text(json.dumps(protocol, indent=2), encoding='utf-8')
    seeds = case_seeds(records)
    tasks = [(str(audio_folder/r['file']), {'file':r['file'], 'reference_tones_hz':r['reference_tones_hz']}, k, seeds[r['file'], k])
             for r in records for k in range(PROTOCOL['rooms_per_recording'])]
    started = time.perf_counter()
    with ProcessPoolExecutor(WORKERS) as pool:
        cases = list(pool.map(_task, tasks))
    by_file = {r['file']:r for r in real['files']}
    result = {'kind':PROTOCOL['kind'], 'label':'SIMULATED EAR ATTENUATION. Nothing was played or measured.',
              'created_utc':datetime.now(timezone.utc).isoformat(), 'protocol':'protocol.json', 'cases':cases,
              'recordings':{f:{'source':by_file[f]['source'], 'tone_only_ceiling_db':by_file[f]['tone_only_ceiling_db'],
                               'reference_tone_band_power_fraction':by_file[f]['reference_tone_band_power_fraction']}
                            for f in protocol['recordings']},
              'runtime_seconds':time.perf_counter()-started, 'workers':WORKERS}
    (output/'tune_by_ear.json').write_text(json.dumps(result, indent=1, default=_jsonable), encoding='utf-8')
    rows = [r for c in cases for r in c['rows']]
    with open(output/'metrics.csv', 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    tuning = [r for c in cases for r in c['tuning'] if 'skipped' not in r]
    if tuning:
        with open(output/'tuning.csv', 'w', newline='', encoding='utf-8') as handle:
            fields = [k for k in tuning[0] if k != 'flags']+['flags']
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows([{**r, 'flags':'; '.join(r['flags'])} for r in tuning])
    from .tune_by_ear_report import write_tune_by_ear_report
    write_tune_by_ear_report(output, result, protocol)
    return result


# ---------------- after-the-fact diagnostic: could the listener hear the tone at all? ----------------
CUE_BINS_DB = [-np.inf, 0., 1., 3., 10., np.inf]


def _cue_task(args):
    path, file, room_index, seed, run_tones, lead_s = args
    with threadpool_limits(limits=1):
        _, scene, _ = build_scene(path, seed)
        frequencies = [t['frequency'] for t in scene['tones']]
        if not np.allclose(frequencies, [t['frequency'] for t in run_tones], rtol=0, atol=1e-9):
            raise RuntimeError(f'{file} room {room_index}: rebuilt scene differs from the run')
        listener = SimulatedListener(FS)
        warm, prefix = scene['warm'], scene['prefix']
        off = scene['ears'][0][warm:prefix]
        band = band_sos()
        rows = []
        for tone in scene['tones']:
            oracle = [ToneSetting(tone['frequency'], abs(tone['w']), float(np.degrees(np.angle(tone['w'])) % 360))]
            start, sound, _, _ = ear_sound(scene, oracle, lead_s)
            on = add_at(scene['ears'][0], start+scene['unreported'], sound, warm, prefix)
            f = tone['frequency']
            band_change = 10*np.log10(max(np.mean(signal.sosfilt(band, off)**2), 1e-30)/max(np.mean(signal.sosfilt(band, on)**2), 1e-30))
            rows.append({'file':file, 'room':room_index, 'frequency':f, 'mic_amplitude':tone['mic_amplitude'],
                         'cue_db':listener.level('steady', off, f)-listener.level('steady', on, f),
                         'band_change_db':float(band_change)})
        return rows


def audible_cue_diagnostic(audio_folder, run_folder, output, lead_ms=30.):
    """For every tuned tone of a finished run: how much quieter the listener's own band gets with the
    exact path (oracle) setting for that tone alone, over the tuning part. Below the listener's 1 dB
    "same" threshold, tuning by ear cannot find the setting, however careful the listener."""
    output, run_folder, audio_folder = Path(output), Path(run_folder), Path(audio_folder)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output folder must be new or empty; earlier results are preserved.')
    run = json.loads((run_folder/'tune_by_ear.json').read_text(encoding='utf-8'))
    protocol = json.loads((run_folder/'protocol.json').read_text(encoding='utf-8'))
    seeds = case_seeds([{'file':f} for f in protocol['recordings']])
    tasks = [(str(audio_folder/c['file']), c['file'], c['room_index'], seeds[c['file'], c['room_index']], c['tones'], lead_ms/1000)
             for c in run['cases'] if c['tones']]
    with ProcessPoolExecutor(WORKERS) as pool:
        cues = [r for rows in pool.map(_cue_task, tasks) for r in rows]
    tuned = {}
    for c in run['cases']:
        for t in c['tuning']:
            if 'skipped' not in t and t['lead_ms'] == lead_ms:
                tuned.setdefault((c['file'], c['room_index'], round(t['frequency'], 6)), {})[t['sigma_db']] = t
    for r in cues:
        for sigma, t in tuned.get((r['file'], r['room'], round(r['frequency'], 6)), {}).items():
            r[f'predicted_db_sigma_{sigma:g}'] = t['predicted_tone_attenuation_db']
            r[f'kept_sigma_{sigma:g}'] = t['kept']
    output.mkdir(parents=True, exist_ok=True)
    label = 'simulated ear; after-the-fact analysis of '+run_folder.name
    (output/'cues.json').write_text(json.dumps({'kind':'audible_cue_diagnostic', 'label':label, 'lead_ms':lead_ms, 'tones':cues},
                                               indent=1, default=_jsonable), encoding='utf-8')
    with open(output/'cues.csv', 'w', newline='', encoding='utf-8') as handle:
        fields = sorted({k for r in cues for k in r}, key=lambda k: (k not in ('file', 'room', 'frequency'), k))
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(cues)
    sigmas = PROTOCOL['tuning']['listener_sigma_db']
    lines = ['# Could the simulated listener hear the tone being tuned?', '',
             f'After-the-fact diagnostic of `{run_folder.name}` (simulated ear, {lead_ms:g} ms lead, tuning part only). '
             'Nothing in the run was changed.', '',
             "Cue: how much quieter the listener's auditory band around the tone gets when that tone alone is cancelled with "
             'the exact path setting, the best that tuning could ever find. The simulated listener answers "same" below 1 dB.', '',
             '| Cue (dB) | Tones | Predicted quieting after tuning, typical listener (median) | Kept after check: '
             + ', '.join(f'±{s:g} dB listener' for s in sigmas)+' |', '|---|---:|---:|---|']
    for lo, hi in zip(CUE_BINS_DB[:-1], CUE_BINS_DB[1:]):
        group = [r for r in cues if lo <= r['cue_db'] < hi]
        if not group:
            continue
        predicted = [r['predicted_db_sigma_1'] for r in group if r.get('predicted_db_sigma_1') is not None]
        kept = ', '.join(f"{100*np.mean([bool(r.get(f'kept_sigma_{s:g}')) for r in group]):.0f}%" for s in sigmas)
        name = f'below {hi:g}' if not np.isfinite(lo) else (f'{lo:g} to {hi:g}' if np.isfinite(hi) else f'{lo:g} or more')
        lines.append(f'| {name} | {len(group)} | {np.median(predicted):.1f} dB | {kept} |')
    lines += ['', f"Tones: {len(cues)}. Cue below 1 dB: {sum(r['cue_db'] < 1 for r in cues)}, of which "
              f"{sum(r['cue_db'] < 0 for r in cues)} negative (even the exact setting makes that band louder, because the "
              f"forecast error is larger than the tone). Median cue {np.median([r['cue_db'] for r in cues]):.1f} dB."]
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return cues
