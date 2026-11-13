# Study 04 fresh recordings: metadata-only preparation

Prepared by Codex, 20 Oct 2026. Sid chose: **Prepare study 04 first; no downloads.**

Eight recordings, **19,336,652 bytes (19.34 MB)**, are now frozen in `../protocol.json` with the existing `gcheck_fade8` candidate (80 ms cosine gate fade in both directions). **No audio download or held-out test has occurred.** No microphone or playback stream was opened.

## Selection and provenance

Selected on 20 Oct 2026 from the already-local 19 Oct Commons metadata cache results-tone-forecaster-05/fresh-metadata/commons_search02.json; no new web request or audio download. Eligibility: 10-150 seconds, no more than 25 MB per file, a recorded free-licence label, identifiable physical machinery, a distinct credited author for each recording, no previously used title/author and no study-05 reserved title/author, and no Work With Sounds collection. Eight files were selected to match studies 02/05 in sample count and cover appliances, a lift and transport machinery. Office/appliance captures are accompanied by an explicit start-up and a mixed engine/bird scene as gating stress cases. This is a purposive metadata sample, not random sampling. Music, speech, generated noise and unidentified ambient recordings were excluded. No outcome or measured spectrum was used in selection. Tonality, operating state, sound quality and usable in-band tones remain unknown.

No selected audio was downloaded, played, decoded or scored in this project before the freeze. Titles and SHA-1s are disjoint from local external audio, local microphone recordings and study 05's reserved recordings. Credited authors are disjoint from earlier source credits, study 02 and study 05, and unique within this list. These are provenance checks based on cached metadata, not proof of independent capture events or representative real-world performance. The shared metadata search with study 05 is disclosed; no audio or outcome is shared. Files with no reference tones remain in the boost and whole-band scores, as required by the existing scoring code.

The raw metadata for the picks is in `selected_metadata.json`. The [original metadata cache](C:/Users/talk2.000/Desktop/Claude/predictive-anc/results-tone-forecaster-05/fresh-metadata/commons_search02.json) is identified by its project-relative path and SHA-256 in the manifest and audit. Licence labels are from that 19 Oct cache. Recheck the source metadata before any later approved download; changed bytes or SHA-1 must stop the test, and unavailable files must be reported without replacement.

| Recording | Seconds | MB | Credited author | Cached licence |
|---|---:|---:|---|---|
| [Het_vermalen_van_fruit_in_een_blender_-_SoundCloud_-_marloeskunst.ogg](https://commons.wikimedia.org/wiki/File:Het_vermalen_van_fruit_in_een_blender_-_SoundCloud_-_marloeskunst.ogg) | 30.7 | 1.47 | marloeskunst | CC BY 3.0 |
| [Laser_printer,_2015-01-23.ogg](https://commons.wikimedia.org/wiki/File:Laser_printer%2C_2015-01-23.ogg) | 80.5 | 2.72 | Finn Årup Nielsen | CC BY-SA 3.0 |
| [Photocopie.ogg](https://commons.wikimedia.org/wiki/File:Photocopie.ogg) | 18.5 | 0.33 | Luk | CC BY-SA 3.0 |
| [Mobile_lift_stage.ogg](https://commons.wikimedia.org/wiki/File:Mobile_lift_stage.ogg) | 34.0 | 0.56 | T.Voekler | CC BY-SA 3.0 |
| [Mil_Mi-8MTV-1_helicopter_starting_up.ogg](https://commons.wikimedia.org/wiki/File:Mil_Mi-8MTV-1_helicopter_starting_up.ogg) | 19.2 | 0.62 | H.dav.are | CC BY-SA 4.0 |
| [Wiki_Motor_lancha.wav](https://commons.wikimedia.org/wiki/File:Wiki_Motor_lancha.wav) | 15.0 | 4.33 | Vega16 | CC BY-SA 4.0 |
| [Paisaje_sonoro_-_Aves_y_motor_de_auto.wav](https://commons.wikimedia.org/wiki/File:Paisaje_sonoro_-_Aves_y_motor_de_auto.wav) | 51.9 | 9.16 | Luis Alvaz | CC BY-SA 4.0 |
| [Cogwheel_loco_Rigi_vsb.ogg](https://commons.wikimedia.org/wiki/File:Cogwheel_loco_Rigi_vsb.ogg) | 21.7 | 0.14 | Audrius Meskauskas | Public domain |

- **Het_vermalen_van_fruit_in_een_blender_-_SoundCloud_-_marloeskunst.ogg:** A blender processing fruit: a stationary motor appliance, with possible load changes.
- **Laser_printer,_2015-01-23.ogg:** A laser printer in a printer room: stationary office machinery over a longer capture.
- **Photocopie.ogg:** A working Toshiba photocopier: another motor appliance, from a different contributor.
- **Mobile_lift_stage.ogg:** A mobile lift: machinery from a different setting; motor operation and any steady interval are unverified.
- **Mil_Mi-8MTV-1_helicopter_starting_up.ogg:** Helicopter engine start-up: an explicitly nonstationary stress case for gating, not evidence about steady hum.
- **Wiki_Motor_lancha.wav:** A boat motor, according to the title, from a field-recording project in Anapia; operating state is unspecified.
- **Paisaje_sonoro_-_Aves_y_motor_de_auto.wav:** A running car engine with birds: a mixed acoustic scene; the birds are not a prediction target.
- **Cogwheel_loco_Rigi_vsb.ogg:** A rack-railway steam locomotive: periodic machinery from another mechanism; in-band tonality is unverified.

These descriptions support selecting a machinery test set. They do not establish that all recordings contain steady tones in 35-350 Hz. Mixed and changing sounds are stress cases; success would not show that unpredictable sound can be cancelled.

## Metadata-format compatibility

The unchanged study-04 `freeze_protocol` expects an object with `recordings`, `independence` and `how_chosen`. The unchanged study-05 `fresh_problems` expects a bare list at study 04's default `fresh_recordings.json` path. Writing either format alone there breaks the other consumer.

`fresh_protocol_input.json` is the object passed explicitly to study 04's freeze. `fresh_recordings.json` is an identical list mirror for study 05's overlap check. The frozen protocol names and hashes the object input. The audit checks both contents and both studies' code hashes. No frozen Python file was edited. The freeze completed once; it should not be repeated or pointed at the bare list.

## Verification and next action

- All 128 pre-existing checks passed in 51.607 seconds before this preparation.
- 18 study-04 code hashes still match the formal development run; 18 study-05 code hashes and its protocol are unchanged.
- 28 local audio files were checked by identity only. No selected name or SHA-1 overlaps them or study 05; the selected credited authors are distinct and pass the earlier-author checks.
- 60 frozen synthetic scene specifications reproduce; no test waveform was generated or scored.
- The engine still uses v2. All available numerical gains remain reference-prediction or simulated-ear results.

When Sid later approves this exact batch, download to `external-audio/wikimedia-commons-fresh-04/`, validate the frozen sizes/SHA-1s, and run the frozen test once. Any run needs a new results folder and failed runs remain. The two original primary questions are unchanged: fewer synthetic late boosts with no added recording boosts versus joint + gate; and a higher 20 ms tone-bin median versus v2 + gate. Live-engine promotion and quiet-machine timing remain separate decisions.
