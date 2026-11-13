# Why the selector deserves a fresh test

21 October 2026. Post-hoc analysis of unchanged, already-seen results.

The original numbers are arithmetically consistent. A difference between two
method medians is not the median of their paired differences. Most paired
differences are zero because this rule often retains v2. That makes the median
insensitive to gains confined to a minority of sources. It does not mean the
rule provides no useful improvements.

Across 30 acoustic tonal recordings, the unchanged two-second rule has mean
paired gain **0.74956 dB** at 20 ms, against **1.02734 dB** for the window
benchmark (about **73%**). Its paired median is still **0.00 dB**. Ten gains
exceed 0.01 dB; one more positive difference is smaller than that. There are no
20 ms regressions in this seen pool. At 120 ms there are five strictly negative
differences, of which three exceed 0.01 dB; the worst is **-1.61318 dB**.

The 16 sources with nominal scored suffixes of at least 20 seconds have mean
gain **1.40541 dB**. This observational subgroup is not evidence that duration
caused the difference. The selector already has a two-second error history and
calibration replay before scoring; source identity and predictability also vary.

The original audit's frozen median stop remains its recorded outcome. Claude's
message #43 withdraws that rule for future decisions. The revised mean endpoint
was selected after looking at results and is exploratory. It supports one new,
fully frozen fresh-source test, not a retrospective pass or engine promotion.

The fresh candidate is L2 exactly as written, with no tuning. Code, source list,
durations, exclusions, confidence calculation and amplification checks must all
be frozen before the new audio is accessed. See docs/SELECTOR_FRESH_TEST.md.
