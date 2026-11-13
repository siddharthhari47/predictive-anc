# Tone forecaster: frozen test

**Reference-signal prediction only.** Every number is how well a forecaster predicts the recording microphone's own signal 20 ms or 120 ms ahead. Nothing was played, no acoustic path was modelled, and no attenuation at an ear was measured. No real-world cancellation is claimed.

**Independence.** NOT independent. Every file, development and test, was analysed in results-real-hums-01 (frozen v1/v2, prefix AR) and its per-file scores were read before this split, including the finding that prefix AR beats v2 at the tones. Test files are untouched by forecaster development in this study, but the motivating gap was measured on them.

## What was frozen before this run

- Development run: `results-tone-forecaster-01\development\dev-02` (see its DEVELOPMENT.md). Rule, stated before the first development run:

  > Among the gated candidates (v2 with longer fit windows, and the observer-bank variants), pick the one with the highest median, over development acoustic recordings that have reference tones, of the tone-bin gain averaged over both horizons. Eligible only if, on development material: (a) whole-band boosts (whole 35-350 Hz band below -0.5 dB at either horizon, any development recording) are no more than v2 + gate has; (b) third-octave boosts (a third-octave band 1 dB or more louder, any development recording and horizon) are no more than v2 + gate has; (c) the median whole-band gain over development acoustic recordings, averaged over both horizons, is at least v2 + gate's minus 0.1 dB; (d) the mean synthetic development objective (release-study objective) is at least v2 + gate's minus 0.5 dB and its synthetic windows below -0.5 dB are no more than v2 + gate has; (e) the compute time it adds per 10 ms block, excluding the tone-selector update that v2 also runs, is below 5 ms at the 99th percentile (offline Python, one thread, measured under the parallel pool). AR methods are comparators, not candidates: they give no per-tone output, which tune-by-ear needs. If no candidate is eligible, v2 stays.

- Frozen candidate: **bank_wide_lines** ({"kind": "bank", "nb_tau": 0.0, "lines": true})
- Comparators: predict nothing; v2 with and without its realized-error gate (today's engine); ridge AR adapted on each file's first 40% (prefix AR); ridge AR refitted every second on past samples (online AR). The AR comparators are adapted models and forecast the whole waveform, not separate tones.
- Secondary (ablation, not part of the primary question): bank_wide, the frozen candidate without its line finder.
- **Amendment before any test score** (`protocol-amendment-01.json`): The frozen synthetic test draw is infeasible: release_study.draw_groups raised "Could not draw fresh frequencies" because the odd-band interiors (2.5-7.5 Hz of every odd 10 Hz band) are almost all within 2 Hz of the release study's own test draws, which protocol.json also excluded. The first attempt (folder test/) stopped while drawing scene frequencies, before any forecaster ran and before any score existed; test recordings were only read to verify their checksums. Only synthetic_test.forbidden_frequencies changes: the release study's test-draw frequencies are no longer excluded (they evaluated v2 in an earlier study; no forecaster here was developed or tuned on them). Every development frequency (release-study and wandering-scene development draws, the older TEST_GROUPS, DEVELOPMENT and HELD_OUT sets) is still excluded within 2 Hz. Seeds, repeats, parity, candidate, comparators, test recordings and code are unchanged. The stopped attempt is recorded in `test/FAILED_ATTEMPT.md`.
- Test recordings (10): Server_Room_Antti_Luode_.mp3, Omvormer_en_compressor_van_een_tram_-_SoundCloud_-_Beeld_en_Geluid.ogg, Ventilator_in_een_tunnel_-_SoundCloud_-_Beeld_en_Geluid.ogg, Air_conditioner_hum_2_Gravity_Sound_.wav, Air_conditioner_hum_Gravity_Sound_.wav, Fan_Gravity_Sound_.wav, Sistema_de_ventilaci_n.ogg, Ventilador_de_estudio.ogg, Ventilator_Marsmanplein_120919_05_-_SoundCloud_-_the_riel_thing.ogg, Sounds_made_by_a_fan.wav.
- Synthetic test scenes: 48, drawn fresh from seeds 20261018 and 20261019 in odd 10 Hz bands (development used even bands), at least 2 Hz from every frequency used before.

## Primary question

On the test recordings that have reference tones, does the frozen candidate (gated) raise the median tone-bin gain at 20 ms above v2 + gate, toward the prefix-adapted AR, without more whole-band or third-octave boosts than v2 + gate?

**Answer: No: it has more third-octave boosts than v2 + gate (6 against 4), which the frozen question does not allow.**

On the 8 test acoustic recordings with reference tones, the median tone-bin gain at 20 ms is 4.7 dB for bank_wide_lines + gate, 3.3 dB for v2 + gate and 7.2 dB for prefix AR (35% of the v2-to-prefix-AR gap closed).

Whole-band boosts (whole band below -0.5 dB): 0 for the candidate, 0 for v2 + gate. Third-octave boosts (a third-octave band 1 dB or more louder): 6 for the candidate (on 4 files, largest +1.7 dB), 4 for v2 + gate (on 2 files, largest +1.9 dB). A boost here is a count of (file, horizon) cases; the full list is below.

Per file at 20 ms, the candidate beats v2 + gate at the tones on 8 of 8 files and loses on 0 (exact sign test p = 0.008); differences range from 0.8 to 3.1 dB. With this few files the median is a coarse summary; the per-file tables below are the evidence.

Whole band (35-350 Hz, all acoustic test files) is the cross-check that does not depend on how the reference tones were picked: median 0.49 dB for the candidate against 0.27 dB for v2 + gate at 20 ms; the candidate is ahead on 9 of 10 files.

**Caveat on the tone-bin score.** The reference tones are the scored segment's lines standing 10 dB above their +-10 Hz median (chosen with hindsight). A line finder that uses a similar prominence rule causally will tend to follow exactly those lines, so tone-bin gains flatter it. The whole-band score has no such bias.

## All methods on the test recordings

| Method | Tone bins median, 20 / 120 ms | Whole band median, 20 / 120 ms | Whole-band boosts | Third-octave boosts |
|---|---:|---:|---:|---:|
| Predict nothing | 0.0 / 0.0 | 0.00 / 0.00 | 0 | 0 |
| v2, no gate | 3.3 / 3.2 | 0.27 / 0.09 | 0 | 4 |
| v2 + gate | 3.3 / 3.2 | 0.27 / 0.09 | 0 | 4 |
| AR adapted on prefix | 7.2 / 3.7 | 0.37 / 0.01 | 1 | 17 |
| AR refitted online | 7.8 / 4.6 | 0.79 / 0.40 | 0 | 15 |
| bank_wide, no gate | 3.0 / 3.0 | 0.31 / 0.10 | 0 | 1 |
| bank_wide + gate | 3.0 / 3.0 | 0.31 / 0.10 | 0 | 1 |
| bank_wide_lines, no gate | 4.7 / 4.2 | 0.49 / 0.12 | 0 | 6 |
| bank_wide_lines + gate | 4.7 / 4.2 | 0.49 / 0.12 | 0 | 6 |

## Per recording: tone bins (dB, 20 / 120 ms)

| Recording | Tones (Hz) | v2 + gate | AR adapted on prefix | AR refitted online | bank_wide + gate | bank_wide_lines + gate |
|---|---|---:|---:|---:|---:|---:|
| Server_Room_Antti_Luode_.mp3 | 52, 147, 220, 247, 294, 330 | 1.2 / 0.8 | 6.7 / 2.3 | 7.0 / 3.0 | 1.3 / 0.8 | 3.3 / 1.4 |
| Ventilator_in_een_tunnel_-_SoundCl | 43, 57, 64, 97, 129, 244 | 0.5 / 0.3 | 3.7 / 1.9 | 5.3 / 3.1 | 0.4 / 0.2 | 3.0 / 1.8 |
| Air_conditioner_hum_2_Gravity_Soun | 55, 164, 178, 219, 274, 328 | 4.4 / 3.9 | 7.6 / 7.2 | 8.5 / 7.4 | 4.2 / 4.0 | 5.7 / 5.2 |
| Air_conditioner_hum_Gravity_Sound_ | 55, 110, 164, 219, 274, 328 | 5.2 / 4.1 | 9.1 / 7.3 | 9.3 / 7.6 | 5.1 / 4.8 | 7.9 / 6.8 |
| Fan_Gravity_Sound_.wav | 42, 120 | 0.5 / 0.5 | 13.1 / 3.8 | 12.7 / 3.7 | 0.6 / 0.6 | 3.6 / 1.3 |
| Sistema_de_ventilaci_n.ogg | 82, 106, 120, 162, 173, 240 | 14.8 / 12.1 | 19.0 / 15.3 | 19.6 / 15.6 | 17.5 / 14.3 | 17.9 / 14.4 |
| Ventilador_de_estudio.ogg | 38, 113, 120, 226 | 2.3 / 2.4 | 2.7 / 3.6 | 3.0 / 4.4 | 1.8 / 1.9 | 3.5 / 3.2 |
| Sounds_made_by_a_fan.wav | 83, 165, 331 | 7.8 / 6.9 | -0.7 / -0.1 | 5.1 / 4.7 | 8.0 / 7.0 | 8.6 / 7.5 |

## Per recording: whole band (dB, 20 / 120 ms)

| Recording | Tones (Hz) | v2 + gate | AR adapted on prefix | AR refitted online | bank_wide + gate | bank_wide_lines + gate |
|---|---|---:|---:|---:|---:|---:|
| Server_Room_Antti_Luode_.mp3 | 52, 147, 220, 247, 294, 330 | 0.2 / 0.1 | 1.7 / 0.6 | 1.8 / 0.6 | 0.3 / 0.1 | 0.6 / 0.0 |
| Omvormer_en_compressor_van_een_tra | none | 0.4 / 0.1 | 0.0 / -0.1 | 0.1 / -0.1 | 0.4 / -0.2 | 0.4 / -0.4 |
| Ventilator_in_een_tunnel_-_SoundCl | 43, 57, 64, 97, 129, 244 | 0.0 / -0.0 | 0.0 / -0.1 | 0.4 / 0.2 | 0.0 / -0.0 | 0.2 / 0.1 |
| Air_conditioner_hum_2_Gravity_Soun | 55, 164, 178, 219, 274, 328 | 1.3 / 1.0 | 1.7 / 1.6 | 1.9 / 1.7 | 1.5 / 1.5 | 1.8 / 1.8 |
| Air_conditioner_hum_Gravity_Sound_ | 55, 110, 164, 219, 274, 328 | 0.6 / 0.4 | 0.7 / 0.6 | 0.9 / 0.9 | 0.9 / 0.9 | 1.2 / 1.2 |
| Fan_Gravity_Sound_.wav | 42, 120 | 0.1 / 0.0 | 1.0 / 0.1 | 1.1 / 0.2 | 0.1 / 0.0 | 0.1 / -0.1 |
| Sistema_de_ventilaci_n.ogg | 82, 106, 120, 162, 173, 240 | 9.9 / 8.9 | 10.6 / 9.3 | 10.7 / 9.4 | 10.6 / 9.5 | 10.6 / 9.5 |
| Ventilador_de_estudio.ogg | 38, 113, 120, 226 | 0.0 / 0.0 | 0.0 / -0.1 | 0.2 / 0.2 | 0.1 / 0.1 | 0.2 / 0.2 |
| Ventilator_Marsmanplein_120919_05_ | none | 0.0 / 0.0 | 0.1 / -0.0 | 0.1 / -0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| Sounds_made_by_a_fan.wav | 83, 165, 331 | 1.4 / 1.3 | -0.5 / -0.3 | 0.6 / 0.6 | 1.5 / 1.3 | 1.5 / 1.4 |

## Boosts on the test recordings

- Predict nothing: none
- v2, no gate: 1 third-octave band(s) up to +1.6 dB on Air_conditioner_hum_2_Gravity_Sound_.wav at 20 ms; 1 third-octave band(s) up to +1.9 dB on Air_conditioner_hum_2_Gravity_Sound_.wav at 120 ms; 1 third-octave band(s) up to +1.6 dB on Air_conditioner_hum_Gravity_Sound_.wav at 20 ms; 1 third-octave band(s) up to +1.9 dB on Air_conditioner_hum_Gravity_Sound_.wav at 120 ms
- v2 + gate: 1 third-octave band(s) up to +1.6 dB on Air_conditioner_hum_2_Gravity_Sound_.wav at 20 ms; 1 third-octave band(s) up to +1.9 dB on Air_conditioner_hum_2_Gravity_Sound_.wav at 120 ms; 1 third-octave band(s) up to +1.6 dB on Air_conditioner_hum_Gravity_Sound_.wav at 20 ms; 1 third-octave band(s) up to +1.9 dB on Air_conditioner_hum_Gravity_Sound_.wav at 120 ms
- AR adapted on prefix: whole band -0.54 dB on Sounds_made_by_a_fan.wav at 20 ms; 2 third-octave band(s) up to +5.9 dB on Server_Room_Antti_Luode_.mp3 at 20 ms; 2 third-octave band(s) up to +1.4 dB on Omvormer_en_compressor_van_een_tram_-_SoundCloud_-_Beeld_en_Geluid.ogg at 20 ms; 3 third-octave band(s) up to +2.7 dB on Ventilator_in_een_tunnel_-_SoundCloud_-_Beeld_en_Geluid.ogg at 20 ms; 1 third-octave band(s) up to +1.9 dB on Ventilator_in_een_tunnel_-_SoundCloud_-_Beeld_en_Geluid.ogg at 120 ms; 4 third-octave band(s) up to +1.6 dB on Air_conditioner_hum_2_Gravity_Sound_.wav at 20 ms; 1 third-octave band(s) up to +2.0 dB on Air_conditioner_hum_2_Gravity_Sound_.wav at 120 ms; 2 third-octave band(s) up to +2.2 dB on Air_conditioner_hum_Gravity_Sound_.wav at 20 ms; 1 third-octave band(s) up to +1.5 dB on Air_conditioner_hum_Gravity_Sound_.wav at 120 ms; 2 third-octave band(s) up to +2.2 dB on Fan_Gravity_Sound_.wav at 120 ms; 3 third-octave band(s) up to +2.9 dB on Sistema_de_ventilaci_n.ogg at 20 ms; 1 third-octave band(s) up to +2.1 dB on Sistema_de_ventilaci_n.ogg at 120 ms; 3 third-octave band(s) up to +1.3 dB on Ventilador_de_estudio.ogg at 20 ms; 2 third-octave band(s) up to +1.4 dB on Ventilador_de_estudio.ogg at 120 ms; 3 third-octave band(s) up to +10.0 dB on Ventilator_Marsmanplein_120919_05_-_SoundCloud_-_the_riel_thing.ogg at 20 ms; 2 third-octave band(s) up to +5.8 dB on Ventilator_Marsmanplein_120919_05_-_SoundCloud_-_the_riel_thing.ogg at 120 ms; 4 third-octave band(s) up to +2.1 dB on Sounds_made_by_a_fan.wav at 20 ms; 1 third-octave band(s) up to +1.6 dB on Sounds_made_by_a_fan.wav at 120 ms
- AR refitted online: 2 third-octave band(s) up to +5.5 dB on Server_Room_Antti_Luode_.mp3 at 20 ms; 2 third-octave band(s) up to +2.0 dB on Omvormer_en_compressor_van_een_tram_-_SoundCloud_-_Beeld_en_Geluid.ogg at 20 ms; 3 third-octave band(s) up to +1.6 dB on Ventilator_in_een_tunnel_-_SoundCloud_-_Beeld_en_Geluid.ogg at 20 ms; 1 third-octave band(s) up to +1.6 dB on Ventilator_in_een_tunnel_-_SoundCloud_-_Beeld_en_Geluid.ogg at 120 ms; 3 third-octave band(s) up to +1.5 dB on Air_conditioner_hum_2_Gravity_Sound_.wav at 20 ms; 1 third-octave band(s) up to +1.9 dB on Air_conditioner_hum_2_Gravity_Sound_.wav at 120 ms; 2 third-octave band(s) up to +1.9 dB on Air_conditioner_hum_Gravity_Sound_.wav at 20 ms; 1 third-octave band(s) up to +1.4 dB on Air_conditioner_hum_Gravity_Sound_.wav at 120 ms; 1 third-octave band(s) up to +2.0 dB on Fan_Gravity_Sound_.wav at 120 ms; 3 third-octave band(s) up to +2.9 dB on Sistema_de_ventilaci_n.ogg at 20 ms; 1 third-octave band(s) up to +1.7 dB on Sistema_de_ventilaci_n.ogg at 120 ms; 3 third-octave band(s) up to +7.7 dB on Ventilator_Marsmanplein_120919_05_-_SoundCloud_-_the_riel_thing.ogg at 20 ms; 2 third-octave band(s) up to +4.1 dB on Ventilator_Marsmanplein_120919_05_-_SoundCloud_-_the_riel_thing.ogg at 120 ms; 2 third-octave band(s) up to +2.1 dB on Sounds_made_by_a_fan.wav at 20 ms; 1 third-octave band(s) up to +1.6 dB on Sounds_made_by_a_fan.wav at 120 ms
- bank_wide, no gate: 1 third-octave band(s) up to +1.0 dB on Omvormer_en_compressor_van_een_tram_-_SoundCloud_-_Beeld_en_Geluid.ogg at 120 ms
- bank_wide + gate: 1 third-octave band(s) up to +1.0 dB on Omvormer_en_compressor_van_een_tram_-_SoundCloud_-_Beeld_en_Geluid.ogg at 120 ms
- bank_wide_lines, no gate: 1 third-octave band(s) up to +1.0 dB on Server_Room_Antti_Luode_.mp3 at 20 ms; 1 third-octave band(s) up to +1.7 dB on Omvormer_en_compressor_van_een_tram_-_SoundCloud_-_Beeld_en_Geluid.ogg at 120 ms; 1 third-octave band(s) up to +1.1 dB on Fan_Gravity_Sound_.wav at 20 ms; 1 third-octave band(s) up to +1.6 dB on Fan_Gravity_Sound_.wav at 120 ms; 2 third-octave band(s) up to +1.5 dB on Sistema_de_ventilaci_n.ogg at 20 ms; 2 third-octave band(s) up to +1.5 dB on Sistema_de_ventilaci_n.ogg at 120 ms
- bank_wide_lines + gate: 1 third-octave band(s) up to +1.0 dB on Server_Room_Antti_Luode_.mp3 at 20 ms; 1 third-octave band(s) up to +1.7 dB on Omvormer_en_compressor_van_een_tram_-_SoundCloud_-_Beeld_en_Geluid.ogg at 120 ms; 1 third-octave band(s) up to +1.1 dB on Fan_Gravity_Sound_.wav at 20 ms; 1 third-octave band(s) up to +1.6 dB on Fan_Gravity_Sound_.wav at 120 ms; 2 third-octave band(s) up to +1.5 dB on Sistema_de_ventilaci_n.ogg at 20 ms; 2 third-octave band(s) up to +1.5 dB on Sistema_de_ventilaci_n.ogg at 120 ms

## Synthetic test scenes

| Method | Objective (dB) | Windows < -0.5 dB | Late whole band, mean / min (dB) | Late windows < -0.5 dB | Late tone bins, median (dB) |
|---|---:|---:|---:|---:|---:|
| Predict nothing | — | — | 0.00 / 0.00 | 0 | 0.0 |
| v2, no gate | 7.06 | 7 | 9.97 / -0.47 | 0 | 19.4 |
| v2 + gate | 7.07 | 7 | 9.95 / -0.47 | 0 | 12.9 |
| AR adapted on prefix | — | — | 8.42 / -10.29 | 8 | 21.6 |
| AR refitted online | 5.04 | 6 | 9.77 / -0.49 | 0 | 21.9 |
| bank_wide, no gate | 7.26 | 6 | 10.40 / -0.39 | 0 | 21.2 |
| bank_wide + gate | 7.29 | 6 | 10.42 / -0.40 | 0 | 21.2 |
| bank_wide_lines, no gate | 7.42 | 6 | 10.63 / -0.26 | 0 | 21.6 |
| bank_wide_lines + gate | 7.46 | 6 | 10.65 / -0.26 | 0 | 21.6 |

By family (mean objective dB / late whole band dB):

| Method | standard | wander |
|---|---:|---:|
| Predict nothing | — / 0.00 | — / 0.00 |
| v2, no gate | 7.88 / 11.81 | 4.61 / 4.45 |
| v2 + gate | 7.90 / 11.80 | 4.56 / 4.41 |
| AR adapted on prefix | — / 9.03 | — / 6.59 |
| AR refitted online | 4.82 / 10.76 | 5.73 / 6.81 |
| bank_wide, no gate | 8.00 / 12.26 | 5.01 / 4.81 |
| bank_wide + gate | 8.05 / 12.30 | 5.01 / 4.81 |
| bank_wide_lines, no gate | 8.00 / 12.25 | 5.68 / 5.76 |
| bank_wide_lines + gate | 8.05 / 12.29 | 5.68 / 5.76 |

## Compute time

Offline Python, one thread per process, measured while the test ran in a parallel pool (so slower than a quiet machine). "Own" excludes the tone-selector update that v2 also runs. One block is 10 ms of audio.

| Method | Own ms per block, mean | Own p99, median over files | Own p99, worst file | Own worst block | ms per block incl. selector, mean |
|---|---:|---:|---:|---:|---:|
| v2 | 1.12 (per origin, refit) | — | — | — | — |
| bank_wide | 0.54 | 1.15 | 2.76 | 19.1 | 0.86 |
| bank_wide_lines | 0.65 | 3.31 | 5.47 | 8.8 | 0.96 |

Quiet machine, one process, one thread, after the test (`timing-quiet-01.json`): 126 s of the development recording WWS_Compressor.ogg (12490 blocks).

| Method | Own ms per block: mean / p99 / p99.9 / worst | Including the selector: mean / p99 / worst | Blocks over 10 ms incl. selector | Faster than real time |
|---|---:|---:|---:|---:|
| bank_wide_lines | 0.28 / 1.59 / 2.69 / 4.8 | 0.47 / 6.37 / 12.1 | 7 | 21x |
| bank_wide | 0.07 / 0.48 / 0.88 / 1.1 | 0.24 / 4.66 / 9.6 | 0 | 41x |

The selector update (every 0.25 s) is the same work v2 does today and causes the slow blocks in both rows; the forecaster's own share peaks at 4.8 ms in a 10 ms block. For comparison, v2's own refit costs 0.13 ms per block on the same file.

Runtime: 1.0 minutes. Created 2026-10-18T10:06:22.664608+00:00.

Numbers: `test-02/test.json`. Frozen protocol: `protocol.json` with `protocol-amendment-01.json`. Split: `split.json`.
