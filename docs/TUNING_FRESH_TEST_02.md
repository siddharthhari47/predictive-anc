# Second fresh-recording test of the SD-s30 tuner

30 October 2026, Claude. Design note for `results-tuning-fresh-02`, frozen with the code and the recording list before any new media was downloaded.

## Why a second test

`results-tuning-fresh-01` was inconclusive: 7 sources and 18 rooms against a frozen minimum of 12 and 25. Its list was too small for the known yield of about 1 recording in 5. This test keeps everything the same except the recordings and their number.

## What is the same

The arms, 10 seeds per room, three listener noise levels, three rooms per recording, the first 90 s, the room and listener models, the four-condition rule and the minimum of 12 sources and 25 rooms. `anc_lab/tuning_fresh_02.py` changes only the paths, the room seed and the frozen file list.

## What is different

- **About 70 recordings.** At the observed yield (7 of 30, and 8 of 40) that gives an expected 14 to 16 eligible sources. This is an estimate, not a promise.
- **A wider metadata search.** New terms and phrases raise the pool to 6,728 titles. Selection is still by title and description only (`research-tools/tuning-fresh-02/picks.txt`), with no media touched.
- **Exclusions extended.** Every recording, uploader and credited author from the first test is excluded, including the 7 candidates dropped there.
- **Slow downloads from the start.** At least 45 s between files, honouring any retry wait, and rooms are built only after the manifest is read.

## Reporting

The two tests are reported separately and never pooled. If this test is inadequate again the result is inconclusive, and no recordings are added. The outcome of the first test was known when this one was designed, though its recordings are not reused and the rule is unchanged.

Listener noise levels 0.5 and 2 dB stay descriptive, including the rise in harmed rooms the first test showed at 2 dB.

## Limits

- **Selection.** Purposive public collection. Some picks are likely to be narrated or have music, which metadata cannot rule out; these stay in unless they fail mechanically.
- **Simulation.** The listener, rooms and microphone are simulated, with no earphone leakage.
- **Timing.** The smoother's compute timing in the live engine is unmeasured.
- **No physical claim.** No sound is played or recorded, and no physical ANC is claimed.
