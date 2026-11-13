# Real hums recorded by other people

Claude, 16 Oct 2026. Report: [results-real-hums-01/REPORT.md](../results-real-hums-01/REPORT.md).

**Reference-signal prediction only.** The forecast is scored at the microphone that made each recording. There is no acoustic path, no playback and no ear measurement.

## Why

Until now the only real audio was the user's own fan, recorded twice on one laptop. The tone selector and release settings (v1, v2) were tuned on synthetic scenes. Before building anything that plays sound, we needed to know whether those settings hold on hums from other machines, rooms and microphones.

## What was used

Nineteen recordings from Wikimedia Commons, downloaded with the user's approval on 16 Oct 2026 for local analysis only: fans, ventilation, air conditioners, compressors, a server room, a refrigerator, a microwave, an idling locomotive, a tram converter, and two electrical mains-hum clips. Licences, authors, source pages and checksums are in `external-audio/wikimedia-commons-2026-10-16/SOURCES.md` and `SOURCES.json`. The files are not redistributed and stay out of any archive. One file (an air-conditioner outdoor unit) could not be decoded and is kept unchanged on disk.

The files are treated as untrusted downloads. Ogg Skeleton pages are stripped in memory before decoding, and no program is ever run from their folder; the study reads them as data from the project folder.

## Protocol

- v1 and v2 exactly as frozen in `release_protocol.json`. Nothing was tuned on these files.
- First 40% of each file: normalization and the prefix-trained AR comparator. Remaining 60%: scored. Files longer than 180 s were cut there.
- Comparators: predicting nothing (0 dB by definition), the old fixed top-3 detector, v1 + gate, v2 without gate, v2 + gate, AR adapted on the prefix.
- Reference tones for scoring come from a separate after-the-fact spectral analysis of each test part. No forecaster sees them.

## Results

- **Whole 35–350 Hz band, 20 ms ahead, 16 acoustic files:** v2 + gate median 0.3 dB, and 3 dB or more on 1 file (ventilation, 9.9 dB). Median ceiling for a perfect tones-only canceller: 1.9 dB. Most of the low-frequency sound in these recordings is broadband, which no tone method can predict.
- **No harm:** v2 + gate never scored below −0.5 dB at either horizon. AR adapted on the prefix did on 3 files.
- **At the tones themselves** (13 acoustic files with tones): v2 + gate median 2.9 dB, AR median 6.3 dB. AR was more than 3 dB better on 8 files, v2 on 3. The v2 forecaster leaves a lot of tone prediction on the table; AR's advantage comes with occasional boosts elsewhere in the band.
- **Electrical mains hum** (5–6 s clips, almost perfectly periodic): 23–36 dB whole band. These show the detector works when the signal really is steady tone; they are reported separately because they are not sound in air.

## What it means

The frozen v2 settings transfer safely (no boosts) but weakly. Two separate limits show up:

1. Most real hum is not mostly tone. The median ceiling of 1.9 dB caps what any tone canceller can do across the band, however good its forecast.
2. Where there are tones, the v2 forecast reaches about half of what a prefix-adapted AR model reaches. Improving the real-tone forecaster is the clearest software step, and it has to be done on development data with fresh test files, not on these.

## Limits

- Unknown microphones, rooms, gain and editing. Most files are lossy (Ogg Vorbis, MP3) and some may be filtered or trimmed.
- Stereo files: channel 0 only.
- One recording per source, no repeats.
- A good forecast at the recording microphone is necessary for cancellation at an ear, not sufficient.

## Rerun

```powershell
.\.venv\Scripts\python.exe -m anc_lab real-hums --audio external-audio\wikimedia-commons-2026-10-16 --out results-real-hums-02
```

Run it from the project folder. The output folder must be new or empty. Decoding needs `soundfile` (installed with the `capture` extra).
