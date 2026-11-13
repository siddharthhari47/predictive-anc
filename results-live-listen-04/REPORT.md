# results-live-listen-04: second 30 s listen, earbuds' mic and laptop mic together

Fresh readiness: Sid answered "Ready, go" (fan on, earbuds in with their own noise cancelling off, quiet room, sitting still), and the listen started right after. Input-only, 30 s, nothing played, no audio stored. It used the same code as `results-live-listen-03` (`research-tools/listen_check_03.py`, sha256 `25d9b348...`), run through the wrapper `research-tools/listen_check_04.py`. Both inputs delivered all 1,440,000 samples with no stream warnings, opened mono the way the tune app opens them. Numbers are in `listen.json`.

## The check could not answer its question

The rule was fixed before listening: the laptop microphone has to find the fan's hum first. It did not. Its best line from 190 to 210 Hz was at 208.75 Hz, 3.2 dB over its floor, under the 6 dB bar. What it heard instead was a loud, steady rush:

- -25.5 dBFS overall, and -24.8 to -27.0 dBFS in every 3 s stretch.
- About 25 dB louder than on 6 November (-50.9 dBFS).
- No spectral line anywhere from 30 Hz to 6 kHz stood 10 dB over its floor.

Assume the microphone's gain was the same as on 6 November. Then the floor around 200 Hz alone was about 6 dB above the hum's peak level that day. So the hum, if it was in the room, was buried.

The earbuds' microphone did not hear a 200 Hz hum either. Its best line within 2 Hz of the laptop's pick was 3.9 dB over its floor.

- It was quiet: -70.6 dBFS overall, and -77 to -84 dBFS after the first 3 s.
- Unlike listen-03, it almost never sent exact zeros (0.19% of samples).
- Its only lines were at 364, 367 and 485 Hz.
- It did not share the laptop's rush. Coherence between the two microphones had a median of 0.05 from 100 to 300 Hz, the level expected for unrelated signals over 14 segments, and was 0.14 at the laptop's pick.

Neither detector held a tone. On the laptop, tones at 190 to 195 Hz appeared in 97 of 3000 blocks. On the earbuds, tones at 120 to 125 Hz appeared in 78 of 3000. Predictability was not worked out, since neither microphone heard the hum.

## What the rush could be (not measured)

The rush was steady, broadband and local to the laptop, since the earbuds' microphone did not share it. Possible causes:

- The laptop's own cooling fan. It may still have been running after the analysis and offline checks of the minutes before.
- Air from the room fan reaching the laptop's microphones.
- The room fan running faster than on 6 November.

This take cannot tell these apart.

## What the two takes say about the earbuds' microphone

The earbuds' microphone never showed the 200 Hz hum in either take. In listen-03 (not ready) it sent exact zeros 62% of the time. That fits its call noise reduction removing steady sound, but it is not shown: the reference microphone confirmed the hum in neither take. A next take should start with:

- the laptop idle for a few minutes, so its fan settles, with no analysis run just before;
- the laptop out of the room fan's airflow, where it was on 6 November;
- the fan at its 6 November speed.

## Added after the take: what the rush was

Sid's answer after reading this: "that loud steady hush is the fan now im in [a different place] so different fan". So the rush is the room fan, and it is not the 6 November fan: Sid is in a different room now. This take cannot split that fan's sound in the room from its air blowing across the laptop's microphones. Either way, it changes what the two takes mean:

- The 6 November hum was never there to hear. listen-03's question needs a hum, and the laptop microphone found none in this fan: no line 10 dB over its floor anywhere from 30 Hz to 6 kHz, and nothing above 3.2 dB from 190 to 210 Hz.
- A rush with no line in it gives a forecaster almost nothing to predict 50 ms ahead. That is not measured here (no audio is kept). It follows from the spectrum, since only a narrow line stays alike over tens of milliseconds. No detector, predictor or tuning change can alter it.
- The earbuds' microphone dropped 16 to 23 dB after the first 3 s and stayed there (-61.1 dBFS, then -77.2 to -84.1), while the laptop microphone stayed within -24.8 to -27.0. That fits call noise reduction learning the background, or Sid settling in at the start. With no hum in the room, it says nothing yet about a hum.

Proposed next: a steady 200 Hz tone from Sid's phone as a stand-in hum, fan off (`research-tools/listen_check_05.py`, writing to `results-live-listen-05`).
