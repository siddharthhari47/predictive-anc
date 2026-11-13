# Fan predictability (results-fan-predictability-01)

6 November 2026, Claude. Descriptive, no pass bar. Script `research-tools/fan_predictability.py`. Read `results-fan-predictability-02/REPORT.md` first: it repeats this run with a fair control, a longer predictor and validation-chosen settings.

Same question and recordings as 02. One predictor length (0.2 s) and a fixed small ridge, fit on the first half and scored once on the second.

Hum band left over (dB) at 5, 10, 20, 50, 100 and 200 ms:

- Sid's recording, 199.75 Hz line: −4.9, −4.4, −3.5, −1.9, −1.0, −0.4
- goal1_fan_01, 51.5 Hz line: −4.3, −4.0, −3.1, −1.2, −0.0, +0.3
- fan_on, 41.25 Hz line: −9.5, −8.8, −8.1, −6.3, −5.6, −5.8

**The control here was flawed.** It replaced the whole ±5 Hz band, including the room noise under the hum, with a steady tone, so its −16 to −22 dB says nothing about a real room. 02 repeats it with a control that keeps the room noise. The short-look-ahead caveat in 02 applies here too.

`windows_reported_latency` lists the WASAPI devices present at the time, including "Headset Earphone (Soundform ANC Wired Earbuds)"; reading the device list opens no stream.
