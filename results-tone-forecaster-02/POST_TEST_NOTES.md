# Reading the study-02 test

Claude, 18 Oct 2026, written after the test ran. [REPORT.md](REPORT.md) is the frozen answer and is left exactly as the test wrote it. This note covers what its two "Yes" answers leave out. Nothing here changes the answer, and nothing was re-run or re-tuned. The measurements below were made after the test, only to explain it.

**Reference-signal prediction only.** Nothing was played and nothing was measured at an ear.

## In plain words

1. **Boosts: fewer, not gone.** On the fresh recordings, the joint check + gate had 2 boost cases, against 3 for v2 + gate and 4 for the study-01 bank. That passes the frozen question. Both of its boosts are on Buzzing_Speakers.ogg, in the two lowest bands (39 and 50 Hz). The worst band is +7.3 dB at 20 ms and +5.6 dB at 120 ms. v2 + gate makes the same two bands louder on the same file, by up to 11.5 dB.
2. **Tone gain: kept, but small.** The median gain at the tones at 20 ms is 1.2 dB, against v2's 0.8 dB. The joint check was ahead on two files (the pump by 0.4 dB, the clock mechanism by 0.6 dB). It tied on two where no tone method gained anything (Mars and the Lille subway). It was 0.1 dB behind on the buzzing speakers. Two wins and one loss out of five can't be told apart from chance (sign test p = 1.0). It keeps 18% of the study-01 bank's lead over v2, against 77% in development.

## What the remaining boosts are

The buzz on Buzzing_Speakers.ogg sits above 100 Hz. Measured on the scored part of the file, the 39 Hz and 50 Hz bands hold only about −52 and −50 dB of the 35–350 Hz power. So the boost is a rise of about 7 dB in two nearly empty bands. Afterwards they still sit about 45 dB below the whole band, and the whole band still improves by 1.5 dB. The rule counts change per band on purpose, because an anti-hum output that fills an empty band adds new sound. So these are still boosts.

The likely reason the check let it through comes from the code and from the run's counters. Nothing was re-run to confirm it. A setting is allowed if its worst band is no more than 0.5 dB louder than no output, or no more than 0.25 dB above the least-boosting setting, whichever is looser. The second limit is the fallback for drifting tones, and it has no ceiling. On this file the joint check never chose "no output". It kept its start setting until about 13 s into the 17 s file. After that it spent the rest at 0.2 s and 0.4 s minimum memories, without the line finder's tones. The gate made it worse here. Without the gate, the worst band rose 5.0 dB at 20 ms and 3.4 dB at 120 ms.

## The study-01 bank on the Mars recording

The NASA MOXIE recording has almost no sound below 300 Hz: under 0.01% of its power below 1 kHz is in 35–350 Hz. Its one reference "tone", at 160 Hz, holds essentially none of the band's power. The study-01 bank put forecast output into those empty bands and made nine of them 28 to 54 dB louder at both horizons. The gate did not catch it, because the whole band hardly changed (−0.01 dB). The report counts this as only 2 cases, one per horizon. v2 and the joint check output nothing on this file. On fresh material, this is the biggest difference between the study-01 bank and the joint check, and the boost counts hide it.

## Other things worth knowing

- **Little to predict.** Most fresh recordings gave the tone forecasters little to work with. Two had no reference tones at all (the Siemens tram engine and the Stirling engine). On two more (Mars and Lille), v2 and the joint check stayed silent. The tone medians rest on five files, and two of them are zero for both.
- **The gate did little.** On the fresh files it acted only on the buzzing speakers, for all three methods, and it left v2's and the study-01 bank's counts unchanged. For the joint check it made that file's boosts worse. In the fresh synthetic scenes it raised the joint check's late boosts from 16 to 19.
- **Adapted AR models** are reported separately. They were much better at the tones (3.0 and 3.7 dB medians at 20 ms). They had 13 and 10 boost cases, including about +70 dB on the near-empty Mars bands, and made the whole band worse on the Lille subway.
- **Seen recordings** (the study-01 test files, so not independent):
  - boosts: joint 0, v2 4, study-01 bank 6;
  - near-boosts: 2, 10 and 11;
  - tones at 20 ms: 4.1, 3.3 and 4.7 dB.
- **Fresh synthetic scenes:**
  - late windows with a boost: joint + gate 19, v2 + gate 29, study-01 bank 35;
  - objective: 6.97, 6.98 and 7.45 dB.
- **Compute.** The joint check's own time was 3.8 ms per 10 ms block at the 99th percentile in its worst run, under the 5 ms limit.

## What it means

- Under the frozen question, the joint check + gate passed both parts. It is the first line-finder forecaster in this project to pass a frozen test against v2.
- The pass is narrow on tones. The best evidence for it is on safety: it had fewer boosts than v2 + gate on the fresh files, the seen files and the synthetic scenes. And it did not blow up where the study-01 bank did.
- Nothing in the anti-hum engine was changed. Whether the joint check replaces v2 is Sid's call.
- Buzzing_Speakers.ogg has now been looked at in detail. A fix for the fallback, such as going silent when even the least-boosting setting is more than a few dB louder, would need a new development round. It would also need new test recordings, and this file can't serve as one.
