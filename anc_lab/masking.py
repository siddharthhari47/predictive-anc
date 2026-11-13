"""Hum masking: soft noise in the band around each detected hum, so the hum stops standing out.

This is not cancellation. The noise is random, so its timing against the hum
does not matter: earphone delay, the fan's pitch wander and where the
microphone sits all leave it unchanged. It adds sound; it does not make the
room quieter. Each band is one auditory filter wide (ERB, Glasberg and Moore
1990) around the hum, about 46 Hz at 200 Hz, so a hum that wanders a few hertz
stays covered without re-centring the band.

`MaskGenerator` is plain arithmetic on arrays and opens no device. The live
window (`MaskRunner` in mask_app.py) calls update() from the worker thread and
render() from the output callback, both under the runner's lock.
"""
import numpy as np
from scipy import signal

HOLD_SECONDS = 4.          # keep a band this long after its hum was last detected
FADE_SECONDS = .5          # band fade in/out
LEVEL_SECONDS = .2         # level-slider glide
MAX_BANDS = 6
CREST = 4.                 # Gaussian noise: peaks beyond 4 sigma are rare, so RMS = level*cap/4
ENBW = 1.11                # equivalent noise bandwidth of a 2nd-order Butterworth band, in band widths


def erb(frequency):
    """Equivalent rectangular bandwidth of the auditory filter at `frequency` (Hz)."""
    return 24.7*(4.37*frequency/1000+1)


class _Band:
    def __init__(self, centre, rate):
        self.centre, self.width = float(centre), erb(centre)
        low, high = max(centre-self.width/2, 5.), centre+self.width/2
        self.sos = signal.butter(2, [low, high], 'bandpass', fs=rate, output='sos')
        self.zi = np.zeros((2, self.sos.shape[0], 2))           # one filter state per ear
        self.scale = np.sqrt(rate/(2*ENBW*(high-low)))          # white noise of unit variance -> band of unit RMS
        self.gain, self.target, self.last_seen = 0., 1., 0.


class MaskGenerator:
    """Stereo band noise around the current hums. Silent until a hum is reported."""
    def __init__(self, rate, peak_cap, level=.3, seed=None):
        self.rate, self.peak_cap = rate, float(peak_cap)
        self.rng = np.random.default_rng(seed)
        self.bands = []
        self.level = self.level_target = float(np.clip(level, 0, 1))

    def set_level(self, level):
        """0 to 1 of the loudest masking this window allows (RMS = level x cap / 4)."""
        self.level_target = float(np.clip(level, 0, 1))

    def update(self, tones, now):
        """`tones`: [(frequency, amplitude)] from the engine; `now`: seconds of microphone heard."""
        for frequency, _ in tones:
            near = [b for b in self.bands if abs(b.centre-frequency) <= b.width/4]
            if near:
                band = min(near, key=lambda b: abs(b.centre-frequency))
                band.last_seen, band.target = now, 1.
            elif len(self.bands) < MAX_BANDS:
                band = _Band(frequency, self.rate)
                band.last_seen = now
                self.bands.append(band)
        for band in self.bands:
            if now-band.last_seen > HOLD_SECONDS:
                band.target = 0.
        self.bands = [b for b in self.bands if b.target > 0 or b.gain > 0]

    def centres(self):
        return [b.centre for b in self.bands if b.target > 0]

    def render(self, frames):
        out = np.zeros((frames, 2))
        if not frames:
            return out
        steps = np.arange(1, frames+1)
        level_ramp = self._glide(self.level, self.level_target, steps, LEVEL_SECONDS)
        self.level = float(level_ramp[-1])
        active = [b for b in self.bands if b.target > 0 or b.gain > 0]
        if not active:
            return out
        share = 1/np.sqrt(max(1, sum(b.target > 0 for b in active)))     # equal power per band, same total
        for band in active:
            ramp = self._glide(band.gain, band.target, steps, FADE_SECONDS)
            band.gain = float(ramp[-1])
            for ear in (0, 1):
                noise, band.zi[ear] = signal.sosfilt(band.sos, self.rng.standard_normal(frames), zi=band.zi[ear])
                out[:, ear] += noise*band.scale*share*ramp
        return out*(level_ramp*self.peak_cap/CREST)[:, None]

    def _glide(self, start, target, steps, seconds):
        step = 1/max(1, round(seconds*self.rate))
        return np.clip(start+np.sign(target-start)*step*steps, min(start, target), max(start, target))
