# Study 03 diagnosis: does a ceiling on the tie fallback remove the joint check's boosts?

Development material only: the eight study-01 development recordings (`results-tone-forecaster-01/split.json`), the 44 development synthetic scenes, and 8 new development "buzz" scenes drawn for this study. No study-01 test recording, study-02 fresh recording (including Buzzing_Speakers.ogg), synthetic test scene or new recording was read for anything in this folder. The buzz scenes copy the *shape* of the study-02 failure as `../../results-tone-forecaster-02/POST_TEST_NOTES.md` describes it in words: tones above 100 Hz over nearly empty low bands. No audio or score from that file was used. These are design trials, run before the development rule was written; the formal comparison is `../development/dev-01`.

Reference-signal prediction only. Nothing here was played or measured at an ear.

## The question

Study 02's joint check (`anc_lab/tone_floors.py`, `JointCheckBank`) allows a setting whose worst third-octave band is within 0.5 dB of no output, or within 0.25 dB of the least-boosting setting, whichever limit is looser. The second limit (the tie fallback) has no ceiling. The study-02 post-test notes named it as the likely cause of the two boosts left on Buzzing_Speakers.ogg, without testing that. `anc_lab/tone_cap.py` (`CappedCheckBank`) adds the ceiling: above `cap_db` only no output is allowed.

## Trials

| File | Script | What it tried | Result |
|---|---|---|---|
| `trace01.json` | `scripts/s3_fallback_trace.py`, read with `scripts/s3_trace_look.py` | Logged every decision of the joint check on the development recordings: each setting's median worst band, the limit, and whether the fallback was in force | The fallback is in force often. On WWS_Aircompressor the active setting's worst band reached 2.9 dB in the check's own view and was above 0.5 dB in 59-65% of decisions, because even the least-boosting setting reached 2.7 dB. Yet the scored output on that file was fine: worst band +0.91 dB against v2's +2.53 dB, with tone gains of 8.1 / 7.1 dB against v2's 2.9 / 3.4 dB. The two mains recordings never reach a decision in their scored part (the check needs about 6.5 s), so the only development boost (Mains_hum_60_Hz, +1.35 dB) comes from the start setting, which no cap can touch. |
| `cap01.json`, `cap01.log` | `scripts/s3_cap_trial.py` | Caps of 0.5, 0.75, 1, 1.5 and 2 dB against the joint check and v2, on the development recordings and the 44 development scenes | No cap removed a boost. Recording boosts stayed at 1 (the start-setting case); late synthetic boosts were 17-20 against the joint check's 17. Low caps cost tone gain: the tone median fell from 5.56 dB (joint) to 2.50 dB (cap 0.5 to 1), all of it on WWS_Aircompressor (8.1 / 7.1 dB down to 2.4 / 2.3 dB at cap 1). Cap 2 kept 3.69 dB. The standard synthetic objective fell from 7.79 to 7.16 dB at cap 1. |
| `buzz01.json`, `buzz01.log` | `scripts/s3_buzz_trial.py` | 8 new development scenes with tones above 100 Hz over a quiet white floor (draws in the log), against caps 1, 2 and 3 dB | The boosts here come from the gate, not the fallback. Joint check with no gate: 2 late boosts; with the gate: 7. v2: 10 either way. Cap 1 is 7 gated, 2 ungated, and makes buzz_am worse (2.9 against 2.1 dB); caps 2 and 3 are identical to the joint check. Cap 1 left only no output in 4 of 184 decisions on these scenes, all on buzz_am. |

`scripts/s3_smoke_cap.py` checked the wiring (no cap reproduces the joint check exactly; a cap at the margin never keeps a setting above 0.5 dB). `scripts/s3_dev02_read.py` read study 02's development results before any trial. After the rule was written, `scripts/s3_run_dev.py` ran the formal development stage (`forecaster_study_03.run_development`, 6 workers), and `scripts/s3_dev_check.py` read the per-recording cap counts out of its result. The scripts were run from a scratch folder with the project path as the first argument and are kept as they ran. The trial timings (p99 6.7-7.3 ms per block for the joint check and the caps) are higher than study 02's (under 5 ms). Timing depends on what else the machine is doing, so the rule compares each cap with the joint check in the same run.

## What this means

The cap does not find what it was built for. On development material the remaining boosts come from two places the band check cannot see:

- **The gate.** The band check measures each setting's output before the gate. The gate (`selection_study.gate_output`) then switches whole blocks of output on and off, and that hard switching spreads error into nearby bands. On the buzz scenes the gate turns 2 late boosts into 7.
- **The start.** Before its first decision (about 6.5 s in) the check uses its start setting. On short recordings the scored part begins before that.

A low cap also switches the output off and on as the check's view crosses the cap, which is the same kind of hard switching. That is why cap 1 made buzz_am worse.

Whether the fallback caused the Buzzing_Speakers boosts is still not known; that file is seen and was not used. These trials do not support the study-02 notes' guess.

## Candidates taken forward

Caps of 0.5, 1, 2 and 3 dB, to the formal development run, under the rule in `anc_lab/forecaster_study_03.DEVELOPMENT_RULE` (also in `../development/dev-01/DEVELOPMENT.md`), written after these trials and before that run. On these trials no cap would meet it.
