"""All deployable predictions at origin t use samples x[:t+1] only."""
import time
import warnings

import numpy as np
from scipy import signal
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor


def lag_matrix(x, origins, lags):
    origins = np.atleast_1d(origins)
    if np.any(origins < lags-1):
        raise ValueError("Not enough causal history.")
    return x[origins[:, None] - np.arange(lags)]


def estimate_tones(x, fs, count=3):
    f, power = signal.periodogram(x - np.mean(x), fs=fs, nfft=8*len(x), window="hann")
    peaks, _ = signal.find_peaks(power)
    peaks = [i for i in peaks if 35 <= f[i] <= 350]
    ranked = sorted(peaks, key=lambda i: power[i], reverse=True)
    chosen = []
    for i in ranked:
        if all(abs(f[i]-c) > 12 for c in chosen):
            chosen.append(float(f[i]))
        if len(chosen) == count:
            break
    if not chosen:
        raise ValueError("No reference tones in analysis band.")
    return sorted(chosen)


class DirectPredictor:
    """Direct multi-horizon ridge AR or trained nonlinear MLP, same causal lags."""
    def __init__(self, kind, horizons, lags=128, seed=0):
        self.kind, self.horizons, self.lags = kind, np.asarray(horizons), lags
        self.model = (Ridge(alpha=3.) if kind == "ridge_ar" else
                      MLPRegressor(hidden_layer_sizes=(64,), activation="tanh", alpha=.03,
                                   max_iter=180, batch_size=128, learning_rate_init=.001,
                                   early_stopping=False, random_state=seed, tol=1e-7,
                                   n_iter_no_change=25))

    def fit(self, x, train_end):
        # Last target strictly before split; no random train/test split, no future normalization.
        origins = np.arange(self.lags-1, train_end-int(max(self.horizons)), 5)
        X = lag_matrix(x, origins, self.lags)
        self.mean, self.scale = float(np.mean(x[:train_end])), max(float(np.std(x[:train_end])), 1e-8)
        Y = (x[origins[:, None] + self.horizons] - self.mean) / self.scale
        start = time.perf_counter()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ConvergenceWarning)
            self.model.fit((X-self.mean)/self.scale, Y)
        self.metadata = {"training_origins": len(origins), "last_training_target": int(origins[-1]+max(self.horizons)),
                         "train_end_exclusive": int(train_end), "fit_seconds": time.perf_counter()-start,
                         "warnings": [str(w.message) for w in caught],
                         "iterations": int(getattr(self.model, "n_iter_", 1) or 1)}
        return self

    def predict(self, x, origins, horizons):
        columns = np.searchsorted(self.horizons, horizons)
        if np.any(self.horizons[columns] != horizons):
            raise ValueError("Untrained horizon requested.")
        X = lag_matrix(x, origins, self.lags)
        y = self.model.predict((X-self.mean)/self.scale)
        return y[:, columns] * self.scale + self.mean


class ToneTracker:
    """Causal sliding sinusoidal fit plus local frequency correction (Gauss-Newton)."""
    def __init__(self, fs, frequencies, window_seconds=.6):
        self.fs = fs
        self.initial = np.asarray(frequencies)
        self.window = round(window_seconds*fs)

    def fit(self, observed):
        """Refined frequencies and [sin..., cos..., dc] coefficients; tau = 0 at the last sample."""
        tau = np.arange(1-len(observed), 1)/self.fs
        freq = self.initial.copy()
        # Fresh local fit at each origin: no data from later origins enters state.
        for _ in range(4):
            angle = 2*np.pi*tau[:, None]*freq
            sin, cos = np.sin(angle), np.cos(angle)
            design = np.column_stack([sin, cos, np.ones(len(tau))])
            coef = np.linalg.lstsq(design, observed, rcond=None)[0]
            k = len(freq)
            jac = 2*np.pi*tau[:, None]*(cos*coef[:k]-sin*coef[k:2*k])
            residual = observed-design@coef
            step = np.linalg.lstsq(np.column_stack([design, jac]), residual, rcond=None)[0][-k:]
            freq = np.clip(freq + np.clip(step, -.6, .6), self.initial-6, self.initial+6)
        angle = 2*np.pi*tau[:, None]*freq
        design = np.column_stack([np.sin(angle), np.cos(angle), np.ones(len(tau))])
        coef = np.linalg.lstsq(design, observed, rcond=None)[0]
        return freq, coef

    def predict(self, x, origins, horizons):
        output = []
        for t in np.atleast_1d(origins):
            freq, coef = self.fit(x[max(0, t-self.window+1):t+1])
            future = 2*np.pi*np.asarray(horizons)[:, None]/self.fs*freq
            output.append(np.column_stack([np.sin(future), np.cos(future), np.ones(len(horizons))])@coef)
        return np.asarray(output)
