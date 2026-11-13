# Fan predictability, fair check (results-fan-predictability-02)

6 November 2026, Claude. Descriptive, no pass bar. Script `research-tools/fan_predictability_02.py`; it re-checks `results-fan-predictability-01/`, whose control this run supersedes.

## Question

Sid's idea makes the anti-hum from what the laptop microphone heard some milliseconds earlier, so it only works if the hum can be predicted that far ahead. How much of the fan's hum could the best linear predictor of the microphone signal remove at each look-ahead?

## Method

- Existing recordings only, read into memory: Sid's 6 November Windows Sound Recorder file (`Documents\Sound Recordings\Recording (7).m4a`, 13.2 s, AAC, Windows processing unknown) and two October laptop-microphone WAVs from the project's own input-only capture (`recordings/goal1_fan_01.wav`, `results-source-study-01/fan_on.wav`, 30 s each). No capture, no audio written, no device opened.
- The app's causal decimator to 2 kHz. The hum is the ±5 Hz band around the strongest line between 35 and 350 Hz.
- Ridge least-squares predictor, linear in past microphone samples, with 0.2 s or 0.8 s of history. Fit on the first three quarters of the first half; ridge and length picked on its last quarter (after a 1 s gap); refit on both stretches; scored once on the second half after a 1 s gap.
- Control: a steady tone added at a nearby frequency with no line within ±8 Hz, as strong over its local noise as the hum's line is over its own. All room noise is kept. (01's control removed the noise under the hum along with the hum, so it was cleaner than any room.)
- Noise under the line: the share of the band explained by the spectrum's floor (median over ±20 Hz). No predictor can remove it. "Line alone" subtracts it from the error and is approximate.

## Results

dB of the band left over on the untouched second half; negative means removed.

**Sid's recording**, line 199.75 Hz, +2.5 dB over the noise in its band (the noise is 4.4 dB below the band total):

| Look-ahead | 5 ms | 10 ms | 20 ms | 50 ms | 100 ms | 200 ms |
|---|---|---|---|---|---|---|
| Hum band | −5.0 | −4.5 | −3.6 | −1.9 | −1.0 | −0.5 |
| Line alone (approx.) | below the noise estimate | below the noise estimate | −9.0 | −3.5 | −1.7 | −0.7 |
| Steady tone in the same noise (242.75 Hz) | −7.4 | −6.9 | −6.1 | −4.8 | −5.7 | −4.8 |

The steady tone ends at or below its noise share (−4.2 dB) at every look-ahead, so its line is predicted completely, as far as this method can tell. Sid's hum loses most of its predictability between 20 and 100 ms.

**October goal1_fan_01**, line 51.5 Hz, +1.8 dB over band noise: hum band −3.1, −1.2, −0.0 and +0.2 dB at 20, 50, 100 and 200 ms (line alone about −8.1, −2.2, −0.1, +0.3); steady tone −6.7, −5.9, −5.7, −5.7.

**October fan_on**, line 41.25 Hz, +7.2 dB over band noise: hum band −8.7, −7.2, −6.8, −6.6 dB (line alone about −14.5 at 50 ms, −12.3 at 100 ms, −11.5 at 200 ms); steady tone −10.3, −9.1, −8.8, −8.7. This line was far steadier than the other two.

Validation picked the 0.2 s predictor at every look-ahead for Sid's hum and for goal1_fan_01's hum, and the 0.8 s one for the fan_on hum and for 13 of the 18 control look-aheads. The validation stretch is short (about 1.5 s on Sid's file), so these picks are noisy. In hindsight the 0.8 s predictor would have done a little better on Sid's test half at the longer look-aheads (−2.1, −1.5 and −1.6 dB at 50, 100 and 200 ms); that does not change the picture. On goal1_fan_01 the two lengths are within 0.15 dB of each other. Where the 0.2 s predictor was picked, 01's hum numbers reproduce within 0.1 dB; for fan_on the 0.8 s predictor adds 0.4 to 1.2 dB.

## Limits

- Short look-aheads are optimistic. The target is the band-passed signal, and at a short look-ahead part of it comes from samples the predictor has already seen (the band filter's memory). The steady controls show the size: a steady tone is equally predictable at any look-ahead, yet against their own 200 ms figure they come out 1.7 to 2.6 dB lower at 5 ms, 1.0 to 1.6 dB lower at 20 ms and less than 0.5 dB lower at 50 ms. Read 50 ms and longer as fair.
- "Line alone" is the difference of two similar numbers and moves by 1 to 2 dB with the floor estimate. The floor is not a hard limit either: goal1_fan_01's control ends 2.1 dB below its estimated noise share even at 200 ms (−5.7 against −3.6 dB), so the estimate runs high there or part of that noise is predictable.
- Chance spread. Sid's test half is about 5.4 s of a 10 Hz wide band, so each of its figures carries roughly ±0.6 dB of chance spread; about ±0.4 dB for the 13.8 s October test halves. This is a rough estimate from band width and length.
- Linear predictors only. A tracker built for a wandering pitch might do somewhat better; none was tried.
- At the microphone, not at the ear. The laptop microphone is not where the ear is, the earbuds leak, and moving the head shifts the timing. Those losses come on top.
- The delay on Sid's setup is unmeasured: no session was saved. Windows reports 10 ms default high latency for both the laptop microphone array and the earbuds; with the app's blocks and Windows' own buffering, tens of milliseconds in total is likely.
- Sid's file is compressed AAC with unknown Windows processing. The October WAVs give the same picture for their 51.5 Hz line.

## Sid's earbuds

The device list saved in 01 names the earbuds "Soundform ANC Wired Earbuds". They are Belkin's SoundForm ANC Wired Earbuds (USB-C), model G3H0003: active noise cancelling built in and powered over the cable (Belkin support article 337373). Reviews describe a long press on a button on the side of the inline module that switches between ANC on, transparency and off (Gizmodo; PCMag). Which mode they were in during Sid's live tries is unknown. Any future test of the app must record the mode, since the earbuds' own cancelling, or transparency, changes what reaches the ear.

## Conclusion

On Sid's fan the best linear predictor removes about 2 dB of the hum band at 50 ms and about 1 dB at 100 ms; of the line itself, roughly 3.5 to 4 dB and 2 to 3 dB, counting the hindsight choice of predictor length. That is the best case at the microphone, before the microphone-to-ear losses. A steady tone in the same noise is predicted completely, and the predictor still removes about 12 dB of the steadier October fan_on line at 100 ms, so the limit is this fan's hum, not the method. The app is unchanged.
