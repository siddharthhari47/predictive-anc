import numpy as np
from scipy import signal


def attenuation(before, after):
    """Positive dB = lower residual power; negative dB = amplification."""
    return float(10*np.log10(max(np.mean(before**2), 1e-30)/max(np.mean(after**2), 1e-30)))


def band_power(x, fs, low, high):
    f, p = signal.welch(x, fs, nperseg=min(2048, len(x)))
    mask = (f >= low) & (f <= high)
    return float(np.sum(p[mask])*(f[1]-f[0]))


def residual_metrics(before, after, fs, frequencies):
    original_band, residual_band = band_power(before, fs, 35, 350), band_power(after, fs, 35, 350)
    tones = {str(f): 10*np.log10(max(band_power(before, fs, f-3, f+3), 1e-30) /
                              max(band_power(after, fs, f-3, f+3), 1e-30)) for f in frequencies}
    return {"attenuation_db": attenuation(before, after),
            "band_35_350_attenuation_db": float(10*np.log10(max(original_band, 1e-30)/max(residual_band, 1e-30))),
            "residual_rms": float(np.sqrt(np.mean(after**2))), "tone_attenuation_db": tones}


def forecast_metrics(actual, predicted):
    mse = float(np.mean((actual-predicted)**2))
    power = max(float(np.mean(actual**2)), 1e-30)
    return {"mse": mse, "nrmse": float(np.sqrt(mse/power)), "nmse_db": float(10*np.log10(max(mse, 1e-30)/power))}
