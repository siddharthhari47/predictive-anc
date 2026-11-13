"""results-faint-tones-02 (rerun of 01): does the faint-tone detector find weak, wobbly hums without inventing tones?

Run once. Step 1 writes protocol.json (settings, file hashes, pass bars) and
refuses if the folder exists; step 2 scores the frozen settings on fresh
synthetic seeds that development never used, the 14 stored rooms and the real
hum recordings already in external-audio/. Plays nothing, records nothing,
opens no audio device. Downloaded WAVs are read as data from this script,
which lives outside external-audio/.

Development (before this file was written) used Sid's 13 s recording and
synthetic seed 100 only; see REPORT.md for those numbers.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from scipy import signal
from scipy.io import wavfile

from anc_lab import engine_candidate as ec
from anc_lab.antihum import FS, V2_SELECTOR, StreamingDecimator
from anc_lab.faint_tones import FAINT, CombinedSelector, FaintSelector
from anc_lab.live_engine import FaintEngine
from anc_lab.tone_selection import ToneSelector

OUT = ROOT/'results-faint-tones-02'   # 01 crashed on 44.1 kHz files before scoring was saved; see its RUN_FAILED.md
SEEDS = list(range(2001, 2011))          # never used in development (that was seed 100)
SECONDS = 60
HUM_LEVELS = (-25, -20, -15, -10)
REAL = sorted((ROOT/'external-audio').rglob('*.wav'))
BARS = {
    'noise': 'white and pink noise: no faint tone active in any update, on every seed',
    'voice': 'voice-like sound (with and without background noise): faint tone active in at most 10% of updates on at least 8 of 10 seeds',
    'hum': 'hum at -15 dB in pink noise: locked within 3 Hz of 200 Hz in at least 80% of updates after 15 s, and first lock by 15 s, on at least 8 of 10 seeds',
    'rooms': 'the 14 stored rooms: every tone the frozen detector reports is still reported at every update',
    'timing': 'one combined update (both detectors) p99 at most 2 ms on this machine, CPU only',
}
REPORTED_ONLY = 'hum at -25/-20/-10 dB in pink and every hum under voices; Sid\'s recording; the real recordings in external-audio/; gate-open share for the faint engine on the hums'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---- synthetic material (same generators as development) ----
def pink(rng, n):
    w = np.fft.rfft(rng.standard_normal(n)); f = np.fft.rfftfreq(n, 1/FS); w[1:] /= np.sqrt(f[1:]); w[0] = 0
    y = np.fft.irfft(w, n)
    return y/np.std(y)


def voice(rng, n):
    """Syllables 0.12-0.5 s with gaps; pitch 95-230 Hz with vibrato and glide; four harmonics."""
    t, out, i = np.arange(n)/FS, np.zeros(n), 0
    while i < n:
        length, gap = int(rng.uniform(.12, .5)*FS), int(rng.uniform(.03, .25)*FS)
        f0 = rng.uniform(95, 230)*(1+.04*np.sin(2*np.pi*rng.uniform(3, 6)*t[:length]))*np.linspace(1, rng.uniform(.85, 1.15), length)
        phase = 2*np.pi*np.cumsum(f0)/FS
        out[i:i+length] += (sum(np.sin(h*phase)/h for h in range(1, 5))*np.hanning(length))[:n-i]
        i += length+gap
    return out/np.std(out)


def hum(rng, n, f=200., wobble=1., am=.2):
    """Frequency wanders about +-1 Hz (0.5 s random walk), amplitude about +-20%."""
    k = np.convolve(rng.standard_normal(n), np.ones(FS//2)/np.sqrt(FS//2), 'same'); k = wobble*k/np.std(k)
    a = np.convolve(rng.standard_normal(n), np.ones(FS)/np.sqrt(FS), 'same'); a = 1+am*a/np.std(a)
    return np.sqrt(2)*a*np.sin(2*np.pi*np.cumsum(f+k)/FS+rng.uniform(0, 6.3))


def add_at(tone, noise, db):
    """Tone power `db` relative to the noise power inside 35-350 Hz."""
    b, a = signal.butter(4, [35, 350], 'band', fs=FS)
    return noise+tone*np.sqrt(np.var(signal.lfilter(b, a, noise))*10**(db/10))/np.std(tone)


def cases(seed):
    rng, n = np.random.default_rng(seed), SECONDS*FS
    c = {'white': (rng.standard_normal(n), None, 'noise'), 'pink': (pink(rng, n), None, 'noise'),
         'voice+pink': (voice(rng, n)+.3*pink(rng, n), None, 'voice'), 'voice': (voice(rng, n)+.05*pink(rng, n), None, 'voice')}
    for db in HUM_LEVELS:
        c[f'hum {db} dB in pink'] = (add_at(hum(rng, n), pink(rng, n), db), 200., 'hum' if db == -15 else 'reported')
        c[f'hum {db} dB under voice'] = (add_at(hum(rng, n), voice(rng, n)+.3*pink(rng, n), db), 200., 'reported')
    return c


# ---- scoring ----
def faint_run(y):
    s, out = FaintSelector(FS, **FAINT), []
    for t in range(s.step, len(y)+1, s.step):
        out.append(s.update(y[max(0, t-s.window):t]))
    return out


def score(out, target):
    row = {'any_faint_share': float(np.mean([len(a) > 0 for a in out]))}
    if target is not None:
        hit = [any(abs(f-target) < 3 for f, _ in a) for a in out]
        late = hit[int(15/.25):]
        row.update({'locked_share_after_15s': float(np.mean(late)), 'first_lock_s': (hit.index(True)+1)*.25 if True in hit else None,
                    'other_share': float(np.mean([any(abs(f-target) >= 3 for f, _ in a) for a in out]))})
    return row


def combined_vs_strict(y):
    """Updates where a frozen-detector tone is missing from the combined list, plus update timing."""
    strict, combined = ToneSelector(FS, **V2_SELECTOR), CombinedSelector(FS)
    missing, added, seconds = 0, 0, []
    for t in range(combined.step, len(y)+1, combined.step):
        a = strict.update(y[max(0, t-strict.window):t])
        started = time.perf_counter()
        b = combined.update(y[max(0, t-combined.window):t])
        seconds.append(time.perf_counter()-started)
        missing += int(any(all(abs(f-g) > 1e-9 for g, _ in b) for f, _ in a[:combined.max_tones]))
        added += len(b)-len([f for f, _ in b if any(abs(f-g) <= 1e-9 for g, _ in a)])
    return missing, added, seconds


def decimate(x, rate):
    dec, k = StreamingDecimator(rate, FS), 480*rate//48000
    return np.concatenate([dec.process(x[i*k:(i+1)*k]) for i in range(len(x)//k)])


def engine_gate(y):
    eng, with_tones, open_ = FaintEngine(), 0, 0
    for i in range(0, len(y)-20, 20):
        eng.push(y[i:i+20])
        if eng.strongest():
            with_tones += 1
            open_ += int(eng.gate_open)
    return {'origins_with_tones': with_tones, 'gate_open_share_with_tones': open_/max(with_tones, 1)}


def reference_peaks(y):
    f, p = signal.welch(y, FS, nperseg=4*FS)
    lv = 10*np.log10(np.maximum(p, 1e-30))
    ex = lv-signal.medfilt(lv, 2*round(10/(f[1]-f[0]))+1)
    pk, _ = signal.find_peaks(np.where((f >= 35) & (f <= 350), ex, -np.inf), height=10)
    return [float(f[i]) for i in pk]


def main():
    assert not OUT.exists(), 'Never overwrite a run'
    OUT.mkdir()
    protocol = {'study': 'results-faint-tones-02', 'rerun_of': 'results-faint-tones-01 (crashed before any score was saved; settings, seeds and bars unchanged)', 'utc': datetime.now(timezone.utc).isoformat(),
                'settings': {k: (list(v) if isinstance(v, tuple) else v) for k, v in FAINT.items()}, 'seeds': SEEDS,
                'seconds_per_case': SECONDS, 'hum_levels_db': HUM_LEVELS, 'bars': BARS, 'reported_only': REPORTED_ONLY,
                'real_files': [str(p.relative_to(ROOT)) for p in REAL],
                'hashes': {p: sha(ROOT/p) for p in ('anc_lab/faint_tones.py', 'anc_lab/live_engine.py', 'anc_lab/tone_selection.py',
                                                     'anc_lab/antihum.py', 'research-tools/faint_tones_study.py')}}
    (OUT/'protocol.json').write_text(json.dumps(protocol, indent=1))
    print('protocol frozen', flush=True)

    synthetic = []
    for seed in SEEDS:
        for name, (y, target, group) in cases(seed).items():
            row = {'seed': seed, 'case': name, 'group': group, **score(faint_run(y), target)}
            if target is not None and seed in SEEDS[:3]:
                row.update(engine_gate(y))
            synthetic.append(row)
        print('seed', seed, 'done', flush=True)

    rooms, timing = [], []
    for c, x in ec.rooms():
        y = decimate(x, 48000)
        missing, added, seconds = combined_vs_strict(y)
        timing += seconds
        rooms.append({'case': c['case_id'], 'updates_missing_a_frozen_tone': missing, 'faint_additions': added})
    print('rooms done', flush=True)

    real = []
    for path in REAL:
        rate, x = wavfile.read(path)
        x = x.astype(float)
        x = x.mean(axis=1) if x.ndim > 1 else x
        x = x[:180*rate]/max(np.abs(x).max(), 1e-12)
        if rate != 48000:
            g = np.gcd(48000, rate)
            x = signal.resample_poly(x, 48000//g, rate//g)
        y = decimate(x, 48000)
        out, ref = faint_run(y), reference_peaks(y)
        found = sorted({round(f, 1) for a in out for f, _ in a})
        strict = ToneSelector(FS, **V2_SELECTOR)
        strict_found = sorted({round(f, 1) for t in range(strict.step, len(y)+1, strict.step)
                               for f, _ in strict.update(y[max(0, t-strict.window):t])})
        real.append({'file': str(path.relative_to(ROOT)), 'seconds': len(y)/FS, 'any_faint_share': float(np.mean([len(a) > 0 for a in out])),
                     'faint_frequencies': found[:20], 'faint_near_reference_peak': [any(abs(f-r) < 3 for r in ref) for f in found[:20]],
                     'reference_peaks': ref, 'frozen_detector_frequencies': strict_found[:20]})
    print('real files done', flush=True)

    def group(g):
        return [r for r in synthetic if r['group'] == g]
    hums = group('hum')
    verdict = {
        'noise': all(r['any_faint_share'] == 0 for r in group('noise')),
        'voice': all(sum(r['any_faint_share'] <= .1 for r in group('voice') if r['case'] == c) >= 8 for c in ('voice', 'voice+pink')),
        'hum': sum(r['locked_share_after_15s'] >= .8 and r['first_lock_s'] is not None and r['first_lock_s'] <= 15 for r in hums) >= 8,
        'rooms': all(r['updates_missing_a_frozen_tone'] == 0 for r in rooms),
        'timing': float(np.percentile(timing, 99))*1000 <= 2.,
    }
    result = {'verdict': verdict, 'all_pass': all(verdict.values()), 'timing_ms': {
        'median': float(np.median(timing))*1000, 'p99': float(np.percentile(timing, 99))*1000, 'max': float(np.max(timing))*1000},
        'synthetic': synthetic, 'rooms': rooms, 'real': real, 'complete': True}
    (OUT/'results.json').write_text(json.dumps(result, indent=1))
    print(json.dumps({'verdict': verdict, 'all_pass': result['all_pass'], 'timing_ms': result['timing_ms']}, indent=1))
    print('PASS' if result['all_pass'] else 'FAIL')


if __name__ == '__main__':
    main()
