"""Dimensionless synthetic acoustics and record/replay input."""
from dataclasses import dataclass
from math import gcd
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile


@dataclass
class Scene:
    reference: np.ndarray
    disturbance: np.ndarray
    primary: np.ndarray
    secondary: np.ndarray
    frequencies: list[float]
    provenance: str


def paths(fs=2000):
    """Assumed FIRs, never claimed to represent measured headphones."""
    p = np.zeros(round(.004 * fs) + 1)
    p[round(.001 * fs)] = .85
    p[-1] = .18
    s = np.zeros(round(.005 * fs) + 1)
    s[round(.003 * fs)] = .70
    s[-1] = .12
    return p, s


def make_scene(kind, fs, seconds, seed, replay=None, normalization_seconds=6.):
    rng = np.random.default_rng(seed)
    n = round(fs * seconds)
    t = np.arange(n) / fs
    p, s = paths(fs)
    if replay is not None:
        rate, raw = wavfile.read(replay)
        if raw.ndim != 1:
            raise ValueError("Replay requires mono WAV; choose the reference channel explicitly.")
        if np.issubdtype(raw.dtype, np.unsignedinteger):
            info = np.iinfo(raw.dtype)
            raw = (raw.astype(float) - (info.max + 1) / 2) / ((info.max + 1) / 2)
        elif np.issubdtype(raw.dtype, np.integer):
            raw = raw.astype(float) / max(abs(np.iinfo(raw.dtype).min), np.iinfo(raw.dtype).max)
        raw = np.asarray(raw, float)
        if not np.all(np.isfinite(raw)):
            raise ValueError("WAV contains non-finite samples.")
        if len(raw)/rate < seconds:
            raise ValueError(f"Need at least {seconds:g} seconds; recordings are never looped across splits.")
        divisor = gcd(rate, fs)
        up, down = fs // divisor, rate // divisor
        if up == down == 1:
            source = raw.copy()
        else:
            # Causal anti-alias conversion: retain the FIR's group delay. Do not
            # use zero-phase, delay-trimmed resampling before causal evaluation.
            factor = max(up, down)
            taps = signal.firwin(20*factor+1, 1/factor, window=("kaiser", 5.)) * up
            source = signal.upfirdn(taps, raw, up=up, down=down)
        source = source[:n]
        prefix = min(len(source), round(normalization_seconds*fs))
        source -= np.mean(source[:prefix])
        rms = np.sqrt(np.mean(source[:prefix]**2))
        if rms < 1e-8:
            raise ValueError("Recording is silent.")
        source *= .4 / rms  # Offline normalization only. Not an SPL calibration.
        reference = source.copy()
        frequencies = []
        provenance = f"Replay {Path(replay).name}; ear signal is SYNTHETIC, not measured"
    else:
        frequencies = [73., 146., 219.]
        phase = rng.uniform(-np.pi, np.pi, len(frequencies))
        source = np.zeros(n)
        for k, (freq, amplitude) in enumerate(zip(frequencies, [.45, .22, .12])):
            if kind == "drifting":
                inst_freq = freq + (k + 1) * (.65 * np.sin(2*np.pi*.13*t) + .025*t)
                phi = 2*np.pi*np.cumsum(inst_freq)/fs + phase[k]
                envelope = 1 + .08*np.sin(2*np.pi*.27*t + k)
            else:
                phi = 2*np.pi*freq*t + phase[k]
                envelope = 1
            source += amplitude * envelope * np.sin(phi)
        source += .012 * rng.standard_normal(n)
        if kind == "unpredictable":
            # Negative control: innovations dominate, with one unannounced broadband burst.
            source += .32 * rng.standard_normal(n)
            source += .65 * rng.standard_normal(n) * ((t > seconds-2) & (t < seconds-1.8))
        reference = source + .008 * rng.standard_normal(n)
        provenance = f"Synthetic {kind}; seed={seed}; dimensionless amplitude"
    ear_local = .025 * rng.standard_normal(n)  # Not observable at the reference mic.
    disturbance = signal.lfilter(p, [1.], source) + ear_local
    return Scene(reference, disturbance, p, s, frequencies, provenance)


def jitter_trace(n, fs, rms_ms, seed, block=20):
    """Smooth unknown delay fluctuations, not a Bluetooth codec/packet emulator."""
    if rms_ms == 0:
        return np.zeros(n)
    rng = np.random.default_rng(seed)
    knots = np.arange(0, n + block, block)
    values = rng.standard_normal(len(knots))
    smooth = np.interp(np.arange(n), knots, values)
    smooth -= smooth.mean()
    smooth *= rms_ms * fs / 1000 / np.std(smooth)
    return smooth
