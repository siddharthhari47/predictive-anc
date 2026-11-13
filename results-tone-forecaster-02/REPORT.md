# Tone forecaster study 02: test on fresh recordings

**Reference-signal prediction only.** Every number is how well a forecaster predicts the recording microphone's own signal 20 ms or 120 ms ahead. Nothing was played, no acoustic path was modelled, and no attenuation at an ear was measured. No real-world cancellation is claimed.

**Independence.** Independent of all earlier work in this project: the eight recordings were chosen by their Commons title, description, length, licence and author only. None was downloaded, played or analysed before this protocol was frozen, and no author also made a development recording or a study-01 recording.

## Answer

1. **Are the boosts gone? Yes.** On the fresh recordings joint + gate has 2 third-octave boost case(s) (a band 1 dB or more louder) against 3 for v2 + gate and 4 for the study-01 line-finder bank + gate; whole-band boosts 0 against 0 and 0. Near-boosts (0.5 dB or more): 2, 4 and 6.
2. **Is the tone gain kept? Yes.** Median tone-bin gain at 20 ms over the 5 fresh acoustic recordings with reference tones: 1.2 dB for joint + gate, 0.8 dB for v2 + gate and 3.2 dB for the study-01 line-finder bank + gate; the candidate keeps 18% of that bank's lead over v2.

Per file at 20 ms the candidate beats v2 + gate at the tones on 2 of 5 files and loses on 1 (exact sign test p = 1.000); differences run from -0.1 to 0.6 dB. With this few files the median is coarse; the per-file tables are the evidence.

Whole band (35-350 Hz), the score that does not depend on how the reference tones were picked: median 0.00 dB for the candidate against 0.01 dB for v2 + gate at 20 ms; the candidate is ahead on 4 of 7 files.

**Caveat on the tone-bin score.** The reference tones are the scored segment's lines standing 10 dB above their +-10 Hz median, chosen with hindsight. The line finder uses a similar prominence rule causally, so tone-bin gains flatter it. The whole-band score has no such bias.

## What was frozen before this run

- Development run: `results-tone-forecaster-02\development\dev-01` (its DEVELOPMENT.md). Rule:

  > Written after the diagnostic trials on development material (results-tone-forecaster-02/diagnosis) and before the formal development run. Candidates, all gated: the line-finder bank with a 0.2 s memory floor for line-finder tones (floor_lines0.2), and the line-finder bank with the joint band check (joint). Eligible only if, on development material: (a) whole-band boosts (whole 35-350 Hz band below -0.5 dB at either horizon, any development recording) are no more than v2 + gate has; (b) third-octave boosts (a third-octave band 1 dB or more louder, any development recording and horizon) are no more than v2 + gate has and fewer than bank_wide_lines + gate has; (c) near-boosts (a band 0.5 dB or more louder, same cases) are fewer than v2 + gate has and fewer than bank_wide_lines + gate has, a margin because study 01's candidate passed (b) on development and failed it on test; (d) third-octave boosts in the late windows of the synthetic development scenes are fewer than v2 + gate has and fewer than bank_wide_lines + gate has; (e) the tone gain is kept: the median, over development acoustic recordings with reference tones, of the tone-bin gain averaged over both horizons is at least v2 + gate's plus half of the amount by which bank_wide_lines + gate exceeds v2 + gate; (f) the median whole-band gain over development acoustic recordings, averaged over both horizons, is at least v2 + gate's minus 0.1 dB; (g) the mean synthetic development objective is at least v2 + gate's minus 0.5 dB and its synthetic windows below -0.5 dB are no more than v2 + gate has; (h) its own compute time per 10 ms block, excluding the tone-selector update that v2 also runs, is below 5 ms at the 99th percentile on every development recording and scene (offline Python, one thread, measured under the parallel pool). Among eligible candidates, pick the one with the fewest near-boosts (development recordings plus late synthetic windows, 0.5 dB or more); ties go to the higher tone-bin median. If none is eligible, no candidate is frozen and v2 stays.

- Frozen candidate: **joint** ({"kind": "joint", "nb_tau": 0.0, "lines": true, "options": {}})
- Comparators: predict nothing; v2 with and without its realized-error gate (today's engine); ridge AR adapted on each file's first 40% (prefix AR) and refitted every second on past samples (online AR), which are adapted models that forecast the whole waveform; and the study-01 line-finder bank (bank_wide_lines).
- Primary question: On the fresh recordings, (1) are the boosts gone: does the frozen candidate + gate have no more third-octave boosts (a band 1 dB or more louder, any fresh recording, either horizon) and no more whole-band boosts than v2 + gate? (2) Is the tone gain kept: is its median tone-bin gain at 20 ms, over the fresh acoustic recordings with reference tones, above v2 + gate's? The two parts are answered separately. bank_wide_lines + gate, the study-01 candidate, is reported alongside so the report can say how much of its gain survives.
- Fresh recordings scored (8): Pump.ogg, The_Sound_of_MOXIE_at_Work_on_Mars_(PIA26041).wav, Montreal_Clock_Tower_clock_mechanism.flac, Siemens_Combino_Engine_Sound.wav, Lille_subway_noise.wav, Stirling_marble_engine_000.ogg, Buzzing_Speakers.ogg, 60-hz.wav.

## All methods on the fresh recordings

| Method | Tone bins median, 20 / 120 ms | Whole band median, 20 / 120 ms | Whole-band boosts | Third-octave boosts (>= 1 dB) | Near-boosts (>= 0.5 dB) | Synthetic objective | Synthetic windows < -0.5 dB | Synthetic late boosts (>= 1 / >= 0.5 dB) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Predict nothing | 0.0 / 0.0 | 0.00 / 0.00 | 0 | 0 | 0 | — | — | — |
| v2, no gate | 0.8 / 0.6 | 0.01 / 0.00 | 0 | 3 | 4 | — | — | — |
| v2 + gate | 0.8 / 0.6 | 0.01 / 0.00 | 0 | 3 | 4 | — | — | — |
| AR adapted on prefix | 3.0 / 1.8 | 0.44 / 0.27 | 2 | 13 | 13 | — | — | — |
| AR refitted online | 3.7 / 2.4 | 0.56 / 0.33 | 2 | 10 | 12 | — | — | — |
| bank_wide_lines, no gate | 3.2 / 2.7 | 0.01 / -0.01 | 0 | 4 | 6 | — | — | — |
| bank_wide_lines + gate | 3.2 / 2.7 | 0.01 / -0.01 | 0 | 4 | 6 | — | — | — |
| joint, no gate | 1.2 / 1.1 | 0.00 / 0.00 | 0 | 2 | 2 | — | — | — |
| joint + gate | 1.2 / 1.1 | 0.00 / 0.00 | 0 | 2 | 2 | — | — | — |

### Boosts

- v2 + gate: third-octave +8.1 dB on Buzzing_Speakers.ogg at 20 ms; third-octave +11.5 dB on Buzzing_Speakers.ogg at 120 ms; third-octave +1.1 dB on 60-hz.wav at 20 ms; near (0.5-1 dB): Montreal_Clock_Tower_clo 20 ms +0.67
- AR adapted on prefix: whole band -3.45 dB on Lille_subway_noise.wav at 20 ms; whole band -4.42 dB on Lille_subway_noise.wav at 120 ms; third-octave +1.4 dB on Pump.ogg at 20 ms; third-octave +71.6 dB on The_Sound_of_MOXIE_at_Work_on_Mars_(PIA26041).wav at 20 ms; third-octave +68.7 dB on The_Sound_of_MOXIE_at_Work_on_Mars_(PIA26041).wav at 120 ms; third-octave +1.1 dB on Montreal_Clock_Tower_clock_mechanism.flac at 20 ms; third-octave +1.3 dB on Siemens_Combino_Engine_Sound.wav at 20 ms; third-octave +7.7 dB on Lille_subway_noise.wav at 20 ms; third-octave +11.6 dB on Lille_subway_noise.wav at 120 ms; third-octave +3.0 dB on Stirling_marble_engine_000.ogg at 20 ms; third-octave +1.3 dB on Stirling_marble_engine_000.ogg at 120 ms; third-octave +19.2 dB on Buzzing_Speakers.ogg at 20 ms; third-octave +15.4 dB on Buzzing_Speakers.ogg at 120 ms; third-octave +3.9 dB on 60-hz.wav at 20 ms; third-octave +4.7 dB on 60-hz.wav at 120 ms
- AR refitted online: whole band -1.64 dB on Lille_subway_noise.wav at 20 ms; whole band -0.95 dB on Lille_subway_noise.wav at 120 ms; third-octave +67.0 dB on The_Sound_of_MOXIE_at_Work_on_Mars_(PIA26041).wav at 20 ms; third-octave +66.7 dB on The_Sound_of_MOXIE_at_Work_on_Mars_(PIA26041).wav at 120 ms; third-octave +1.6 dB on Montreal_Clock_Tower_clock_mechanism.flac at 20 ms; third-octave +1.1 dB on Siemens_Combino_Engine_Sound.wav at 20 ms; third-octave +6.8 dB on Lille_subway_noise.wav at 20 ms; third-octave +3.2 dB on Lille_subway_noise.wav at 120 ms; third-octave +17.3 dB on Buzzing_Speakers.ogg at 20 ms; third-octave +10.2 dB on Buzzing_Speakers.ogg at 120 ms; third-octave +3.6 dB on 60-hz.wav at 20 ms; third-octave +3.6 dB on 60-hz.wav at 120 ms; near (0.5-1 dB): Pump.ogg 20 ms +0.67, Stirling_marble_engine_0 20 ms +0.99
- bank_wide_lines + gate: third-octave +51.9 dB on The_Sound_of_MOXIE_at_Work_on_Mars_(PIA26041).wav at 20 ms; third-octave +54.4 dB on The_Sound_of_MOXIE_at_Work_on_Mars_(PIA26041).wav at 120 ms; third-octave +8.9 dB on Buzzing_Speakers.ogg at 20 ms; third-octave +9.2 dB on Buzzing_Speakers.ogg at 120 ms; near (0.5-1 dB): Montreal_Clock_Tower_clo 20 ms +0.58, 60-hz.wav 20 ms +0.53
- joint + gate: third-octave +7.3 dB on Buzzing_Speakers.ogg at 20 ms; third-octave +5.6 dB on Buzzing_Speakers.ogg at 120 ms

### Per recording: tone bins (dB, 20 / 120 ms)

| Recording | Tones (Hz) | v2 + gate | AR adapted on prefix | AR refitted online | bank_wide_lines + gate | joint + gate |
|---|---|---:|---:|---:|---:|---:|
| Pump.ogg | 70, 105, 120, 240, 268, 326 | 0.8 / 0.6 | 3.0 / 1.8 | 3.7 / 2.4 | 3.2 / 2.7 | 1.2 / 1.1 |
| The_Sound_of_MOXIE_at_Work_on_Mars_(PIA2 | 160 | 0.0 / 0.0 | -48.8 / -46.6 | -45.4 / -43.2 | -38.6 / -38.2 | 0.0 / 0.0 |
| Montreal_Clock_Tower_clock_mechanism.fla | 69, 95, 120, 138, 240 | 7.8 / 6.0 | 13.6 / 8.6 | 14.1 / 9.0 | 10.5 / 7.6 | 8.4 / 6.8 |
| Lille_subway_noise.wav | 58, 78, 169 | 0.0 / 0.0 | -1.5 / -1.6 | -1.0 / -0.9 | -0.0 / -0.0 | 0.0 / 0.0 |
| Buzzing_Speakers.ogg | 117, 150, 167, 217, 267, 283 | 5.1 / 4.6 | 7.3 / 6.1 | 9.8 / 7.0 | 7.6 / 6.3 | 5.0 / 4.8 |
| 60-hz.wav (capture unknown) | 60, 120, 180, 240, 300 | 41.7 / 37.4 | 48.5 / 40.0 | 49.0 / 40.2 | 40.2 / 37.3 | 37.5 / 37.3 |

### Per recording: whole band (dB, 20 / 120 ms)

| Recording | Tones (Hz) | v2 + gate | AR adapted on prefix | AR refitted online | bank_wide_lines + gate | joint + gate |
|---|---|---:|---:|---:|---:|---:|
| Pump.ogg | 70, 105, 120, 240, 268, 326 | 0.1 / 0.0 | 0.4 / 0.3 | 0.6 / 0.3 | 0.4 / 0.4 | 0.2 / 0.2 |
| The_Sound_of_MOXIE_at_Work_on_Mars_(PIA2 | 160 | 0.0 / 0.0 | 1.7 / 1.7 | 2.7 / 2.3 | -0.0 / -0.0 | 0.0 / 0.0 |
| Montreal_Clock_Tower_clock_mechanism.fla | 69, 95, 120, 138, 240 | 2.7 / 2.1 | 3.6 / 2.8 | 3.7 / 3.0 | 3.2 / 2.8 | 3.0 / 2.7 |
| Siemens_Combino_Engine_Sound.wav | none | 0.0 / -0.0 | 0.1 / -0.1 | 0.1 / -0.1 | 0.0 / -0.0 | 0.0 / -0.0 |
| Lille_subway_noise.wav | 58, 78, 169 | 0.0 / 0.0 | -3.5 / -4.4 | -1.6 / -1.0 | 0.0 / -0.0 | 0.0 / 0.0 |
| Stirling_marble_engine_000.ogg | none | -0.0 / -0.0 | -0.4 / -0.3 | -0.0 / -0.1 | -0.0 / -0.0 | -0.0 / -0.0 |
| Buzzing_Speakers.ogg | 117, 150, 167, 217, 267, 283 | 1.4 / 1.3 | 1.6 / 0.6 | 2.3 / 1.8 | 1.9 / 1.6 | 1.5 / 1.6 |
| 60-hz.wav (capture unknown) | 60, 120, 180, 240, 300 | 23.5 / 23.0 | 27.7 / 25.7 | 27.9 / 26.3 | 23.7 / 23.5 | 23.7 / 23.5 |

A file marked "capture unknown" is kept out of the medians; its boosts still count.

## Secondary: the study-01 test recordings (seen, not independent)

Secondary, not independent: the study-01 test recordings. Their study-01 boosts motivated this study, but no study-02 choice was made on them.

| Method | Tone bins median, 20 / 120 ms | Whole band median, 20 / 120 ms | Whole-band boosts | Third-octave boosts (>= 1 dB) | Near-boosts (>= 0.5 dB) | Synthetic objective | Synthetic windows < -0.5 dB | Synthetic late boosts (>= 1 / >= 0.5 dB) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Predict nothing | 0.0 / 0.0 | 0.00 / 0.00 | 0 | 0 | 0 | — | — | — |
| v2, no gate | 3.3 / 3.2 | 0.27 / 0.09 | 0 | 4 | 10 | — | — | — |
| v2 + gate | 3.3 / 3.2 | 0.27 / 0.09 | 0 | 4 | 10 | — | — | — |
| AR adapted on prefix | 7.2 / 3.7 | 0.37 / 0.01 | 1 | 17 | 17 | — | — | — |
| AR refitted online | 7.8 / 4.6 | 0.79 / 0.40 | 0 | 15 | 17 | — | — | — |
| bank_wide_lines, no gate | 4.7 / 4.2 | 0.49 / 0.12 | 0 | 6 | 11 | — | — | — |
| bank_wide_lines + gate | 4.7 / 4.2 | 0.49 / 0.12 | 0 | 6 | 11 | — | — | — |
| joint, no gate | 4.1 / 3.7 | 0.36 / 0.19 | 0 | 0 | 2 | — | — | — |
| joint + gate | 4.1 / 3.7 | 0.36 / 0.19 | 0 | 0 | 2 | — | — | — |

### Boosts

- v2 + gate: third-octave +1.6 dB on Air_conditioner_hum_2_Gravity_Sound_.wav at 20 ms; third-octave +1.9 dB on Air_conditioner_hum_2_Gravity_Sound_.wav at 120 ms; third-octave +1.6 dB on Air_conditioner_hum_Gravity_Sound_.wav at 20 ms; third-octave +1.9 dB on Air_conditioner_hum_Gravity_Sound_.wav at 120 ms; near (0.5-1 dB): Ventilator_in_een_tunnel 120 ms +0.72, Fan_Gravity_Sound_.wav 120 ms +0.93, Sistema_de_ventilaci_n.o 20 ms +0.77, Sistema_de_ventilaci_n.o 120 ms +0.95, Ventilador_de_estudio.og 20 ms +0.83, Ventilador_de_estudio.og 120 ms +0.73
- bank_wide_lines + gate: third-octave +1.0 dB on Server_Room_Antti_Luode_.mp3 at 20 ms; third-octave +1.7 dB on Omvormer_en_compressor_van_een_tram_-_SoundCloud_-_Beeld_en_Geluid.ogg at 120 ms; third-octave +1.1 dB on Fan_Gravity_Sound_.wav at 20 ms; third-octave +1.6 dB on Fan_Gravity_Sound_.wav at 120 ms; third-octave +1.5 dB on Sistema_de_ventilaci_n.ogg at 20 ms; third-octave +1.5 dB on Sistema_de_ventilaci_n.ogg at 120 ms; near (0.5-1 dB): Server_Room_Antti_Luode_ 120 ms +0.71, Omvormer_en_compressor_v 20 ms +1.00, Ventilator_in_een_tunnel 20 ms +0.66, Ventilator_in_een_tunnel 120 ms +0.88, Air_conditioner_hum_2_Gr 120 ms +0.58
- joint + gate: near (0.5-1 dB): Sistema_de_ventilaci_n.o 20 ms +0.53, Sistema_de_ventilaci_n.o 120 ms +0.93

### Per recording: tone bins (dB, 20 / 120 ms)

| Recording | Tones (Hz) | v2 + gate | AR adapted on prefix | AR refitted online | bank_wide_lines + gate | joint + gate |
|---|---|---:|---:|---:|---:|---:|
| Server_Room_Antti_Luode_.mp3 | 52, 147, 220, 247, 294, 330 | 1.2 / 0.8 | 6.7 / 2.3 | 7.0 / 3.0 | 3.3 / 1.4 | 3.0 / 1.2 |
| Ventilator_in_een_tunnel_-_SoundCloud_-_ | 43, 57, 64, 97, 129, 244 | 0.5 / 0.3 | 3.7 / 1.9 | 5.3 / 3.1 | 3.0 / 1.8 | 2.2 / 0.9 |
| Air_conditioner_hum_2_Gravity_Sound_.wav | 55, 164, 178, 219, 274, 328 | 4.4 / 3.9 | 7.6 / 7.2 | 8.5 / 7.4 | 5.7 / 5.2 | 5.2 / 4.9 |
| Air_conditioner_hum_Gravity_Sound_.wav | 55, 110, 164, 219, 274, 328 | 5.2 / 4.1 | 9.1 / 7.3 | 9.3 / 7.6 | 7.9 / 6.8 | 6.2 / 5.6 |
| Fan_Gravity_Sound_.wav | 42, 120 | 0.5 / 0.5 | 13.1 / 3.8 | 12.7 / 3.7 | 3.6 / 1.3 | 0.6 / 0.6 |
| Sistema_de_ventilaci_n.ogg | 82, 106, 120, 162, 173, 240 | 14.8 / 12.1 | 19.0 / 15.3 | 19.6 / 15.6 | 17.9 / 14.4 | 15.2 / 13.3 |
| Ventilador_de_estudio.ogg | 38, 113, 120, 226 | 2.3 / 2.4 | 2.7 / 3.6 | 3.0 / 4.4 | 3.5 / 3.2 | 2.6 / 2.5 |
| Sounds_made_by_a_fan.wav | 83, 165, 331 | 7.8 / 6.9 | -0.7 / -0.1 | 5.1 / 4.7 | 8.6 / 7.5 | 7.3 / 6.4 |

## Secondary: fresh synthetic scenes

48 scenes from seeds 20261020 and 20261021, odd 10 Hz bands, more than 2 Hz from every development frequency. The study-01 and release-study test draws are not excluded: no study-02 choice used them, and excluding the study-01 test draws as well within 2 Hz leaves no room in either band parity (checked with a draw before this freeze).

| Method | Objective (dB) | Windows < -0.5 dB | Late whole band, mean / min (dB) | Late tone bins, median (dB) | Late boosts (>= 1 / >= 0.5 dB) |
|---|---:|---:|---:|---:|---:|
| Predict nothing | — | — | 0.00 / 0.00 | 0.0 | 0 / 0 |
| v2, no gate | 6.98 | 7 | 9.93 / -0.60 | 16.6 | 24 / 36 |
| v2 + gate | 6.98 | 7 | 9.91 / -0.59 | 13.4 | 29 / 38 |
| AR adapted on prefix | — | — | 8.47 / -10.28 | 19.2 | 56 / 76 |
| AR refitted online | 5.07 | 6 | 9.81 / -0.56 | 19.1 | 47 / 63 |
| bank_wide_lines, no gate | 7.42 | 6 | 10.69 / -0.00 | 19.1 | 34 / 47 |
| bank_wide_lines + gate | 7.45 | 6 | 10.71 / -0.00 | 19.1 | 35 / 48 |
| joint, no gate | 6.90 | 6 | 9.87 / -0.03 | 18.0 | 16 / 28 |
| joint + gate | 6.97 | 6 | 9.92 / -0.03 | 18.0 | 19 / 28 |

By family (mean objective dB / late whole band dB):

| Method | standard | wander |
|---|---:|---:|
| Predict nothing | — / 0.00 | — / 0.00 |
| v2, no gate | 7.90 / 11.84 | 4.21 / 4.18 |
| v2 + gate | 7.92 / 11.83 | 4.17 / 4.14 |
| AR adapted on prefix | — / 9.07 | — / 6.67 |
| AR refitted online | 4.86 / 10.80 | 5.71 / 6.85 |
| bank_wide_lines, no gate | 8.06 / 12.32 | 5.49 / 5.80 |
| bank_wide_lines + gate | 8.10 / 12.35 | 5.49 / 5.80 |
| joint, no gate | 7.53 / 11.42 | 5.01 / 5.22 |
| joint + gate | 7.62 / 11.48 | 5.02 / 5.25 |

## Compute time

Offline Python, one thread per process, measured under the parallel pool. "Own" excludes the tone-selector update that v2 also runs. One block is 10 ms of audio.

| Method | Own ms per block, mean | Own p99, median over runs | Own p99, worst run | Own worst block | ms per block incl. selector, mean |
|---|---:|---:|---:|---:|---:|
| bank_wide_lines | 0.35 | 1.78 | 2.69 | 7.2 | 0.57 |
| joint | 0.85 | 2.72 | 3.80 | 7.0 | 1.07 |

## Fresh recordings and credits

| File | Author | Licence | Seconds | Counted as acoustic |
|---|---|---|---:|---|
| Pump.ogg | ezwa | Public domain | 32 | yes |
| The_Sound_of_MOXIE_at_Work_on_Mars_(PIA26041).wav | NASA/JPL-Caltech/CNES/IRAP | Public domain | 75 | yes |
| Montreal_Clock_Tower_clock_mechanism.flac | Andy Mabbett | CC BY-SA 4.0 | 41 | yes |
| Siemens_Combino_Engine_Sound.wav | Dawidpl4553 | CC BY-SA 4.0 | 120 | yes |
| Lille_subway_noise.wav | Dazhoid | CC BY-SA 4.0 | 18 | yes |
| Stirling_marble_engine_000.ogg | Nkim5706 | CC BY-SA 3.0 | 28 | yes |
| Buzzing_Speakers.ogg | buzzingspeakers.com | CC BY-SA 3.0 | 17 | yes |
| 60-hz.wav | Rayo v.2.0 | CC BY-SA 4.0 | 20 | no |

Files are local only, in `external-audio\wikimedia-commons-fresh-02`, from Wikimedia Commons (each file's page is https://commons.wikimedia.org/wiki/ followed by its title).

Runtime: 1.3 minutes. Created 2026-10-18T12:48:08.869255+00:00. Numbers: `test/test.json`. Frozen protocol: `protocol.json`.
