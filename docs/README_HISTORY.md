# README history

Until 13 November 2026 the README opened with dated status notes. The AI agents wrote them for each other, so they use the agents' review numbers. When the repository went public that day, the README was tidied for outside readers and the notes moved here, along with the README's section on continuing in the Claude desktop app. Both are kept word for word; only the link targets changed, so they work from `docs/`.

## Status notes, 21 to 26 October 2026

> **26 October tuning diagnosis:** Claude review #55 is completed on all 78 eligible v2 tones. Six of 40 kept tones make their individual auditory band louder during tuning. Ten of 38 muted tones have at least 1 dB of potential prefix benefit, but only three had already found such a setting. Final checks can also mistake changing background sound for an anti-hum effect. Original tuning reproduces in all 37 eligible rooms. Keep v2 live; next isolate better search from better comparison evidence, before widening the menu. These are seen-data simulated-ear diagnostics; quiet-machine timing and physical ANC remain unvalidated. Read [current tuning diagnosis](TUNING_ACCURACY_STATUS.md). Earlier next-step statements below are historical.

**24 October follow-up diagnostics:** Claude review #53 is tested. The compressor supports a bad accepted tuning setting: best v2/bank phases differ by 4.37 degrees, while accepted v2 is 152.58 degrees from its own prefix optimum. Of 72 primary rooms, 34 had intermittent detections below the menu rule, one had no detection, 11 were fully muted by the final listening check, and 26 kept active settings. Direct comparison of all 78 available recordings finds substantial predictor disagreement on real audio; fixed tuning cannot be assumed interchangeable. Prior room/fresh results remain unchanged. Keep v2 live; next diagnose menu eligibility and tuning acceptance, not a larger switch cohort. Quiet-machine timing and physical ANC remain unvalidated. See [the compatibility checkpoint](SELECTOR_COMPATIBILITY_STATUS.md).

**Latest research, 21 October 2026:** The fresh L2 test is complete: **pass frozen offline criteria**. 35/40 sources were scored, 25 with reference tones. Mean paired gain over v2 at 20 ms: **+0.536 dB**, 95% source-bootstrap interval **+0.121 to +1.043 dB**. See [fresh-test report](../results-selector-fresh-01/REPORT.md).

## Continue in the Claude desktop app

The user prefers the desktop app. Open Claude, choose **Code**, select **Local**, then **Select folder** and choose this project directory. Paste this into the app's prompt box:

> Read CLAUDE.md, docs/SELECTOR_COMPATIBILITY_STATUS.md and docs/CONTINUATION_STATUS.md. Continue the existing project from the latest completed result and its stated next step. Keep the continuation offline.

Read [the handoff](CLAUDE_HANDOFF.md) for context. The app session uses the existing code, reports, local recordings and environment. The user does not need to start a terminal session. Preparing the handoff does not itself start Claude or record audio. See the [official desktop guide](https://code.claude.com/docs/en/desktop-quickstart).
