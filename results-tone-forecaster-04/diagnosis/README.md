# Study 04 diagnosis: a softer gate

Development material only: the eight study-01 development recordings, the 44 development synthetic scenes and study
03's 8 buzz scenes. No study-01 test recording, study-02 fresh recording (Buzzing_Speakers.ogg included) or synthetic
test scene was read. Reference-signal prediction only; nothing was played and no ear was measured.

The scripts are in `scripts/` (`s4_lib.py` holds what they share). Each was run from this folder as
`..\..\.venv\Scripts\python.exe scripts\<script>.py <project folder> <name>.json`, with its printout kept as `<name>.log`.

## What was tried

Study 03 found that the v2 gate adds 5 of the joint check's late boosts on the buzz scenes (2 with no gate, 7 with
it). The gate zeros or passes a whole 10 ms block, so each switch is a step in the output. A step spreads tone energy
into the nearly empty bands below 100 Hz.

Two remedies, both in `anc_lab/tone_gate_fade.py`:

- **Fade.** The gate decides exactly as before. Its decision moves a gain up or down a fixed amount per block instead
  of switching. Names: `cos8` is a cosine fade over 8 blocks in and 8 out (80 ms each way); `cos8in3out` is 8 in and
  3 out; `lin1` is a straight 1-block ramp; `hard` is the v2 gate; `none` is no gate at all.
- **Gated check (`gcheck`).** The joint band check judges each setting after its own copy of the gate (and fade, for
  `gcheck_cos8`), so it sees the spread the switching adds.

In the tables, `joint|cos8` means the joint check's forecast with the output faded by `cos8`; `gcheck_cos8|cos8`
means the gated check with an 8-block fade inside its judgement, and the same fade on the output.

## Trial 1: the buzz scenes (`s4_buzz_fade.py`, `buzzfade01`)

Late boosts (a band 1 dB or more louder) over the 8 buzz scenes:

| Output | v2 | joint | gcheck_hard | gcheck_cos3 |
|---|---:|---:|---:|---:|
| none | 10 | 2 | 2 | 1 |
| hard | 10 | 7 | 5 | 5 |
| lin1 | 10 | 4 | 4 | 4 |
| cos3 | 10 | 4 | 3 | 4 |
| cos5 | 10 | 3 | 2 | 2 |
| cos8 | 10 | 2 | 2 | 1 |
| cos8in3out | 10 | 2 | 2 | 2 |

A fade of 8 blocks brings the joint check back to its no-gate count. Fades of 3 blocks or less barely help. v2's
boosts on these scenes are its own, not the gate's. Most switching is on one scene: the joint check's gate switched
29 times on buzz_wander#dev0 and at most 9 times elsewhere.

## Trial 2: all development material (`s4_dev_fade.py`, `devfade01`)

Boosts counted over the recordings (either horizon) plus late synthetic windows:

| Key | Boosts | Near-boosts (>= 0.5 dB) | Tone bins, median (dB) |
|---|---:|---:|---:|
| joint\|hard (study 02) | 1 + 24 = 25 | 40 | 5.56 |
| joint\|none | 1 + 20 = 21 | 35 | 5.48 |
| joint\|cos5 | 1 + 20 = 21 | 36 | 5.51 |
| joint\|cos8 | 1 + 19 = 20 | 35 | 5.50 |
| joint\|cos8in3out | 1 + 19 = 20 | 35 | 5.55 |
| gcheck_hard\|hard | 1 + 21 = 22 | 38 | 5.31 |
| gcheck_hard\|cos8 | 1 + 18 = 19 | 33 | 5.25 |
| gcheck_cos8\|cos8 | 1 + 17 = 18 | 36 | 5.24 |
| v2\|hard (today's engine) | 9 + 45 = 54 | 74 | 3.15 |
| v2\|cos8 | 8 + 40 = 48 | 69 | 3.30 |

The fade removes exactly the 5 buzz boosts and nothing else. The other 15 synthetic boosts of the joint check (5 when
a tone appears, 3 when tones stop, 6 at a source change, 1 on drifting tones) are the same under every fade: they come
from the check's 8 s medians reacting slowly, as study 03 found. The hard gate does help in one place: when tones
stop it cuts the forecast sooner (2.2 dB at 20 ms against 3.6 dB with the 8-block fade and 3.0 dB with 8 in, 3 out).

The gated check costs about 0.3 dB of tone median (5.24 to 5.31 against 5.56), well above what the rule asks for.
It removes one more wander_fast boost and one more buzz boost.

## Trial 3: synthetic windows and compute (`s4_windows.py`, `windows01`)

No fade changes the synthetic windows below -0.5 dB (6 for every key). Mean synthetic objective moves within 0.1 dB
(6.94 to 7.06). Late boosts by family for the keys that went forward:

| Key | Standard | Drifting | Buzz |
|---|---:|---:|---:|
| joint\|hard | 15 | 2 | 7 |
| joint\|cos8 | 15 | 2 | 2 |
| gcheck_hard\|hard | 15 | 1 | 5 |
| gcheck_cos8\|cos8 | 15 | 1 | 1 |
| gcheck_cos8in3out\|cos8in3out | 15 | 1 | 2 |

Own 99th-percentile time per 10 ms block, compared run by run with the joint check (median over all development
runs, 6 processes in parallel, with another heavy job on the machine): joint 5.35 ms, gated check +0.28 ms, gated
check with the 8-block fade +0.22 ms, with 8 in and 3 out +0.36 ms. The fade on its own is a few microseconds.

## Draws for a fresh synthetic test

Checked before writing the protocol, with throwaway scripts outside the project. With parity 1 (odd 10 Hz bands), the
standard and drifting draws cannot be made if study 02's synthetic test frequencies are also kept 2 Hz away
("Could not draw fresh frequencies."). Excluding only the frequencies the development scenes used (study 02's
development list plus study 03's buzz draws), all three families draw at once. The protocol does that and says so.

## What went into the formal development run

Candidates: `joint_fade8`, `joint_fade8in3out`, `gcheck`, `gcheck_fade8`, `gcheck_fade8in3out` (the method-level fade
is also the fade inside the gated check). v2 with the 8-block fade is a comparator for information. The rule is in
`anc_lab/forecaster_study_04.py` (DEVELOPMENT_RULE), written after these trials and before the formal run.
