"""Explicit, input-only local capture with a provenance/quality sidecar."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import threading
import time

import numpy as np
from scipy.io import wavfile


def capture(path, seconds=30., rate=48000, device=None, source="unspecified"):
    import sounddevice as sd

    path = Path(path)
    sidecar = path.with_suffix(".capture.json")
    if path.exists() or sidecar.exists():
        raise ValueError("Capture/metadata already exists; choose a new filename.")
    if not 1 <= seconds <= 300 or rate < 2000:
        raise ValueError("Capture must be 1–300 seconds at >= 2000 Hz.")
    info = dict(sd.query_devices(device, "input"))
    api = dict(sd.query_hostapis(info["hostapi"]))
    sd.check_input_settings(device=device, channels=1, dtype="float32", samplerate=rate)
    wanted = round(seconds*rate)
    chunks, timing, statuses = [], [], []
    recorded = 0
    done = threading.Event()

    def callback(indata, frames, clock, status):
        nonlocal recorded
        if status:
            statuses.append(str(status))
        keep = min(frames, wanted-recorded)
        if keep > 0:
            chunks.append(indata[:keep, 0].copy())
            timing.append({"sample": recorded, "frames": keep,
                           "adc_time": float(clock.inputBufferAdcTime),
                           "callback_time": float(clock.currentTime)})
            recorded += keep
        if recorded >= wanted:
            done.set()
            raise sd.CallbackStop

    started = datetime.now(timezone.utc).isoformat()
    wall_start = time.perf_counter()
    print(f"Recording {seconds:g} s from {info['name']} ({api['name']}); input only.", flush=True)
    with sd.InputStream(device=device, samplerate=rate, channels=1, dtype="float32",
                        callback=callback, finished_callback=done.set) as stream:
        latency = float(stream.latency)
        actual_rate = float(stream.samplerate)
        if not done.wait(seconds+10):
            raise RuntimeError("Capture timed out before the requested audio arrived.")
    if recorded != wanted:
        raise RuntimeError(f"Incomplete capture: received {recorded}/{wanted} samples.")
    audio = np.concatenate(chunks)
    path.parent.mkdir(parents=True, exist_ok=True)
    # File creation is exclusive: a concurrent process cannot overwrite a recording.
    with path.open("xb") as handle:
        wavfile.write(handle, rate, audio)
    metadata = {"schema_version": 1, "provenance": "live_microphone", "source_label": source,
                "started_utc": started, "duration_seconds": len(audio)/rate,
                "sample_rate": rate, "reported_stream_rate": actual_rate, "samples": len(audio),
                "device": info, "host_api": api["name"], "channels": 1,
                "reported_input_latency_seconds": latency,
                "latency_note": "Driver report only; not measured microphone-to-ear latency.",
                "os_processing": "Unknown; AGC/noise suppression/echo cancellation not changed or verified.",
                "callback_statuses": statuses, "callback_timestamps": timing,
                "wall_seconds": time.perf_counter()-wall_start,
                "peak_digital": float(np.max(np.abs(audio))),
                "rms_digital": float(np.sqrt(np.mean(audio.astype(float)**2))),
                "near_full_scale_fraction": float(np.mean(np.abs(audio) >= .999)),
                "wav_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "playback": False, "spl_calibrated": False}
    with sidecar.open("x", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, allow_nan=False)
    print(f"Saved {path.resolve()} and capture metadata.", flush=True)
    return metadata
