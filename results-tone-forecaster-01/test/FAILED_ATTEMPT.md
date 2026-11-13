# First test attempt: stopped before any score

18 Oct 2026, Claude. Kept as a record; nothing else was written here.

`run_test()` with `protocol.json` created this folder, verified the checksums of the ten test recordings, and then stopped while drawing the synthetic test frequencies:

```
File "anc_lab/forecaster_study.py", in test_scene_tasks
    standard = [draw_groups(rng, 1, forbidden) for _ in range(syn['standard_repeats'])]
File "anc_lab/release_study.py", in draw_groups / pick
RuntimeError: Could not draw fresh frequencies.
```

No forecaster ran on test material and no score existed. The frozen synthetic draw was infeasible. Test tones had to sit in the 2.5–7.5 Hz interior of an odd 10 Hz band and stay more than 2 Hz from 191 earlier frequencies. Ninety-two of those were the release study's own test draws, which fill almost all of those interiors.

The fix is `../protocol-amendment-01.json`, written before any test score existed. Only the forbidden-frequency list changes: the release study's test draws no longer count as forbidden, because no forecaster here was developed or tuned on them. Every development frequency is still excluded. The test then ran once into `../test-02/`.
