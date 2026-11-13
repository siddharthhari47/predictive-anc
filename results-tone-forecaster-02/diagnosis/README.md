# Study 02 diagnosis: where the line finder's third-octave boosts come from

Development material only: the eight study-01 development recordings (`results-tone-forecaster-01/split.json`) and the 44 development synthetic scenes. No study-01 test recording, fresh recording or test scene was read for anything in this folder. These are design trials, run before the development rule was written; the formal comparison is `../development/dev-01`.

Reference-signal prediction only. Nothing here was played or measured at an ear.

## What was wrong

Study 01's line-finder bank (`bank_wide_lines` + gate) beat v2 + gate at the tones on every test recording but made more third-octave bands louder (6 cases against 4). On the development recordings it had 4 cases at 1 dB or more and 12 at 0.5 dB or more out of 16 (file, horizon) cases.

Tracing the bank on those recordings showed two causes:

- **Short memories splatter.** When a tone's observer picks a very short memory (25-50 ms), its forecast error is spread across a wide band and lands in neighbouring third-octave bands. On a strong tone the tone bins still win, so the per-tone check keeps the short memory.
- **Spurious line-finder tones.** On the compressor recording the harmonics sit 9 Hz apart (36, 54, 63, 72, 81, 90 Hz). The line finder also tracked lines near 60 and 75 Hz between them; their forecasts made the 50 Hz band louder. The per-tone check judges each tone over about +-44 Hz, which is wider than the 9 Hz spacing, so it cannot see this.

## Trials

| File | Script | What it tried | Result on development material |
|---|---|---|---|
| `diag01.json` | `scripts/diagnose_boosts.py` | Bank variants: a stricter switch-off margin, a 0.2 s memory floor on line-finder tones, a 0.1 s floor on all tones, checking at 120 ms, a 13 dB prominence threshold | Boost cases (>= 1 dB / >= 0.5 dB): base 4 / 12, margin 4 / 11, line floor 3 / 11, floor on all 3 / 12, 120 ms check 9 / 12, prominence 13 dB 8 / 12. No single knob removed them. |
| `guard01.json` | `scripts/diagnose_guard.py` (`anc_lab/tone_guard.py`) | A per-band guard that drops a tone whose forecast makes its own band louder | **Failed.** 4 / 9 boost cases, but the synthetic objective fell from 7.66 to 0.75 dB and drifting tones from 20 to 0.2 dB; on the 60 Hz mains recording one band rose by about 27 dB. Dropping one tone of a jointly fitted set changes the others, and switching tones in and out makes its own splatter. Kept in `tone_guard.py` as a failed experiment. The floors-only variant was 2 / 11 but cost drifting tones (20 to 13.2 dB). |
| `floors01.json`, `floors01.log` | `scripts/diagnose_floors.py` (`anc_lab/tone_floors.py`) | `FloorToneBank` (memory floors, a lean towards longer memories) and `JointCheckBank` (one shared check over all third-octave bands that picks a whole output setting) | Line floor 0.2 s: 3 / 11, objective 7.65. Lean 1 dB + line floor: 3 / 8, but the 60 Hz mains band rose 18.5 dB. Joint check: 1 / 8, objective 7.27, synthetic late boosts 17 against 34 for the base. Joint check starting at 0.05 s: 2 / 8, objective 7.47. |

Tone medians in the trial files are over all 16 (file, horizon) rows, not the study's tone-bin median over acoustic files with reference tones, so they do not match the formal numbers.

The joint check went through several fixes during these trials, each found on development scenes: a single check could lock onto "no output" (fixed by taking the median over the last 16 checks), drifting tones went silent when two settings were within noise of each other (fixed by a tie rule that keeps the least-boosting setting), and a 1 s check window hid a boost that a 4 s window shows (fixed by using 4 s). Its final settings are in `anc_lab/tone_floors.py`.

Other scripts: `debug_guard.py`, `debug_joint.py`, `debug_joint_g.py` and `debug_joint_rec.py` trace one development scene or recording; `smoke_guard.py`, `smoke_floors.py` and `smoke02.py` are wiring checks; `scene_boosts.py`, `dev01_boosts.py`, `dev02_counts.py` and `boost_inventory.py` read the boosts out of study-01 development results; `draw_check.py` checked that fresh synthetic test frequencies can be drawn (draws only, no forecaster); `read_meta.py` summarized the Commons metadata in `../fresh-metadata/` without downloading any audio. The scripts were run from a scratch folder with the project path as the first argument; they are kept as they ran.

## Candidates taken forward

- `floor_lines0.2`: the line-finder bank with a 0.2 s memory floor on line-finder tones.
- `joint`: the line-finder bank with the joint band check.

The rule that chooses between them, written after these trials and before the formal run, is in `forecaster_study_02.DEVELOPMENT_RULE` and `../development/dev-01/DEVELOPMENT.md`.
