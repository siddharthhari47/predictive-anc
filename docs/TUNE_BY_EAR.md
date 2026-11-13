# Tune by ear

Claude, 16–17 Oct 2026. Reports: [results-tune-by-ear-sim-01/REPORT.md](../results-tune-by-ear-sim-01/REPORT.md) and [results-tune-by-ear-cues-01/REPORT.md](../results-tune-by-ear-cues-01/REPORT.md).

**Simulated ear attenuation, and a live app that has not been run.** Every quieting figure below is computed at a simulated ear in a simulated room. Nothing has been played through earphones and nothing has been measured at an ear.

## The idea

What matters is the hum that reaches the ear, and a laptop microphone does not hear that. The room path to the ear differs from the path to the microphone, and the earphones add their own delay and sensitivity. For one steady tone, though, all of that collapses into two numbers: how loud the anti-hum should be, and how far it should be shifted. A listener can find both by answering simple "which is quieter?" questions. The ear is the sensor.

This works only for steady tones (fan blade rate, mains hum, compressor whine). The broadband rush underneath them cannot be predicted, so it is not attempted.

## Pieces

| File | What it does |
|---|---|
| `anc_lab/antihum.py` | Engine: frozen v2 tone selector, 0.3 s fits, v2 gate, per-tone gain and phase, hard output cap with fades. Opens no audio device. |
| `anc_lab/tuning.py` | The question sequence for one tone. Hands out sounds to play and takes answers; plays nothing itself. |
| `anc_lab/antihum_study.py`, `anc_lab/tune_by_ear_report.py` | Simulated rooms and listeners, with the real recordings as hum sources (`tune-sim`). |
| `anc_lab/tune_app.py` | Live window: laptop microphone in, wired earphones out (`tune`). |

## The procedure, per tone (strongest first)

1. **Level, with beats.** The anti-hum plays 1 Hz off the hum, so the hum swells and fades once a second. The fades are deepest when the anti-hum matches the hum's loudness at the ear, whatever the phase. "In which sound do the quiet moments get quieter?"
2. **Phase, with slow sweeps.** The anti-hum turns against the hum once every 4 s. The listener presses at each quietest moment, three turns one way, then three the other. Reaction delay shifts the two directions oppositely, so their average cancels it.
3. **Fine phase**, then **fine gain**: steady A/B comparisons with shrinking steps.
4. **Check:** anti-hum off against on, twice, in shuffled order. The tone is kept only if "on" was quieter. Otherwise its anti-hum is switched off.

## Simulation results (`results-tune-by-ear-sim-01`)

Protocol frozen before the run (`protocol.json`, seed 20261017). Sixteen acoustic recordings from [REAL_HUMS.md](REAL_HUMS.md), three random rooms each (48 scenes). Tones were found and tuned on the first 40% of each recording; the rest was scored with everything frozen. Comparators: no anti-hum (0 dB), untuned (room phase ignored), and a path oracle that stands for an ear-microphone measurement.

- **28 of 48 scenes had a steady tone to tune** (median 1 per scene). In the other 20 every arm stays silent.
- **At the tones, typical simulated listener, 30 ms lead:** median 0.3 dB. Oracle 2.3 dB, untuned 1.3 dB. Across the whole 35–350 Hz band: 0.0 dB (oracle 0.3 dB).
- **Where it works:** the ventilation recording, 13.2 dB at the tones and 6.8 dB across the band (oracle 13.8 dB). One air-conditioner recording, 3.7 dB at the tones. Elsewhere about nothing.
- **It rarely makes things worse.** A one-third-octave band got more than 1 dB louder in 7% of tuned scenes, against 18% untuned and 18% for the oracle. The whole band never got more than 0.5 dB louder. The final check costs some quieting (only 49% of tuned tones were kept), and in exchange it prevents most boosts. That is why "untuned" scores higher at the tones yet boosts more often.
- **Cost:** about 90 s of listening and 15 answers per tone.
- **After tuning:** moving the head 20 cm takes the oracle from 2.3 to 0.4 dB. A playback delay change of 5 ms turns it to −2.2 dB. Any delay change needs a retune.
- **Bluetooth-like 200 ms lead:** 0.1 dB tuned, 1.4 dB oracle.

## Why it helps so rarely (`results-tune-by-ear-cues-01`)

An after-the-fact check asked how much quieter the listener's hearing band around each tone would get with the *exact* setting, the best tuning could ever find. Median: 1.4 dB. Of 57 tones, 24 were under 1 dB, and on 5 even the exact setting made that band louder. Tones with a cue of 3 dB or more were kept 58–100% of the time; those under 1 dB, 0–37%.

So there are two bottlenecks, and neither is the question procedure:

1. **The forecast of real tones.** Even a perfect setting cannot remove more than the engine predicted. On the same recordings, an AR model adapted on the prefix predicted the tones better (median 6.3 against 2.9 dB, [REAL_HUMS.md](REAL_HUMS.md)).
2. **Audibility.** When a tone barely stands out, the listener cannot hear the difference between settings, and the check rightly switches it off.

## Change after the protocol was frozen

After `protocol.json` was written, `OutputLimiter` in `antihum.py` was changed to accept stereo blocks for the live app. Nothing else the `-01` run used was changed, and `-01` was not rerun.

## The live app

### What it does

```powershell
.\.venv\Scripts\python.exe -m anc_lab tune
```

The window shows the microphone it will use and an earphone list, then four readiness boxes:

- wired earphones in, their own noise cancelling off;
- system volume low (about a quarter);
- the chosen output is the earphones, not loudspeakers;
- the earphones can be taken out at any time.

**Start** is disabled until all four are ticked, and nothing plays before Start. The app listens for 3 s, then offers **Tune the strongest untuned tone**, asks the questions above, and can save the settings.

Limits:

- Output is capped at 0.05 of digital full scale (−26 dBFS) by default; `--cap` allows up to 0.2. The cap is not a loudness calibration: how loud it is depends on the volume and the earphones.
- Fades in and out.
- Stops for good on Stop (Esc), on closing the window, after 15 minutes (`--minutes`, at most 30), on any non-finite output, or if either audio stream drops samples after tuning has begun.
- Outputs named "Speakers" are refused unless `--allow-speaker-named-output` is given.
- The input is always the Intel laptop Microphone Array under Windows WASAPI, looked up by name each time.
- No audio is stored. A session file under `tuning-sessions/` holds settings, questions and answers, device names and counters, with `audio_stored: false` and `spl_calibrated: false`.

On this laptop the earphones are USB Soundform ANC Wired Earbuds. Their own noise cancelling must be off for a fair test.

### Timing

The microphone and USB earphones run on separate clocks, so "48 kHz" differs slightly between them. A 50 ppm difference turns a 100 Hz anti-hum by about 2° a second against the hum, enough to undo a tuning within a minute. The app keeps the two streams separate. It fits each stream's sample count against the system clock from callback timestamps, and synthesizes every output sample for the microphone time at which it will be heard. Constant offsets (timestamp errors, earphone delay, room path) are not measured; tuning absorbs them. The engine runs on its own thread, because one update can take longer than an audio block.

Evidence, all in simulation (two clocks, 1 ms timestamp jitter, setting fitted at 4–6 s and then held):

| Case | Quieting at 4–6 s | at 22–24 s |
|---|---:|---:|
| Same clock | 29.7 dB | 17.4 dB |
| Microphone +100 ppm, earphones −100 ppm, with clock correction | 28.9 dB | 19.8 dB |
| Same mismatch, no correction | 28.2 dB | −2.2 dB |

- The fade from about 29 to 17–20 dB is consistent with error in the clock fit, even when the clocks match: with 1 ms jitter the fit is accurate to about 5 ppm (it estimated −5.5 ppm for matched clocks). This bounds how long one tuning holds.
- Simulated forecast lead: 13–20 ms.
- Phase found from simulated sweep presses: within 0.2° of the oracle.
- The window itself was driven end to end with fake audio devices: 158 simulated seconds, peak output 0.025 against the 0.05 cap, and the saved session file held no audio. This checks the wiring, not anyone's hearing.

### What has not been done

- The app has never been run on real devices. Nobody has listened to it.
- Nothing has been measured at an ear. An ear-microphone measurement mode is not built.
- In the simulation the earphone sound never leaks back into the laptop microphone; in a real room some will.
- Bluetooth is not supported: its delay drifts, and the table above shows what a few milliseconds do.

Realistic expectation for a first live try: it may help with one strong, steady tone (a fan or ventilation hum that clearly stands out), and on most sounds the check will switch everything off. Switching off is the safety check working, not a crash.

## Next

1. A better real-tone forecaster (AR-style or longer fits), developed on development files only and tested on fresh ones.
2. A first live trial, started by the user, on a strong steady source.
3. Physical proof still needs a low-output calibrated fixture with a near-ear measurement microphone.
