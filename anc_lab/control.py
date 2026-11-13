"""Acoustic forward model, regularized path compensation, and an error-mic baseline."""
import numpy as np
from scipy import signal


def inverse_path(primary, secondary, advance=16, taps=40, regularization=1e-4):
    """Find causal q with S*q ~ z^-advance P; predictor supplies the advance."""
    rows = max(len(secondary)+taps-1, advance+len(primary))
    matrix = np.zeros((rows, taps))
    for k in range(taps):
        matrix[k:k+len(secondary), k] = secondary
    target = np.zeros(rows)
    target[advance:advance+len(primary)] = primary
    q = np.linalg.solve(matrix.T@matrix + regularization*np.eye(taps), matrix.T@target)
    return q, float(np.linalg.norm(matrix@q-target)/np.linalg.norm(target))


def transport(command, delay, jitter):
    """Receiver-time fractional delay; linear interpolation, no output reordering."""
    at = np.arange(len(command))-delay-jitter
    return np.interp(at, np.arange(len(command)), command, left=0., right=0.)


def render(command, secondary, delay, jitter):
    return signal.lfilter(secondary, [1.], transport(command, delay, jitter))


def predicted_command(prediction, horizons, origins, delay, advance, q, n, block, limit):
    wanted = delay+advance+np.arange(1, block+1)[:, None]-np.arange(len(q))[None, :]
    columns = np.searchsorted(horizons, wanted)
    if not np.array_equal(horizons[columns], wanted):
        raise ValueError("Missing control prediction horizons.")
    blocks = -np.einsum("ijk,k->ij", prediction[:, columns], q)
    command = np.zeros(n)
    indices = origins[:, None]+np.arange(1, block+1)
    command[indices] = np.clip(blocks, -limit, limit)
    return command, float(np.mean(np.abs(blocks) > limit))


def fxlms(reference, disturbance, secondary, estimated_secondary, nominal_delay,
          actual_delay, jitter, taps=128, mu=.015, limit=1.2):
    """Samplewise normalized filtered-x LMS with simulated near-ear error feedback.

    Receives an extra error sensor unavailable to open-loop predictors. Nominal
    output delay is included in the gradient; unknown jitter/path mismatch is not.
    Secondary path must be strictly delayed (validated below).
    """
    if secondary[0] != 0 or actual_delay <= np.max(np.abs(jitter)) + 1:
        raise ValueError("FxLMS simulation requires strictly causal delayed actuator.")
    n = len(reference)
    u, v, error = np.zeros(n), np.zeros(n), np.zeros(n)
    w = np.zeros(taps)
    xpad = np.pad(reference, (taps-1, 0))
    filtered = signal.lfilter(np.r_[np.zeros(nominal_delay), estimated_secondary], [1.], reference)
    fpad = np.pad(filtered, (taps-1, 0))
    s_indices = np.flatnonzero(secondary)
    clips = 0
    for t in range(n):
        xv = xpad[t:t+taps][::-1]
        value = w@xv
        u[t] = np.clip(value, -limit, limit)
        clips += abs(value) > limit
        location = t-actual_delay-jitter[t]
        left = int(np.floor(location))
        if left >= 0:
            fraction = location-left
            v[t] = (1-fraction)*u[left] + fraction*u[left+1]
        anti = sum(secondary[k]*v[t-k] for k in s_indices if t >= k)
        error[t] = disturbance[t]+anti
        fv = fpad[t:t+taps][::-1]
        # Freeze adaptation during output saturation; leak bounds weight drift.
        if abs(value) <= limit:
            w = .999999*w-mu*error[t]*fv/(1e-6+fv@fv)
    return u, error, clips/n
