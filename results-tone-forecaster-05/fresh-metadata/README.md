# Study 05 fresh recordings: chosen from metadata only

Nothing in this folder is audio. On 19 Oct 2026 the Wikimedia Commons API was asked for file titles, descriptions, lengths, sizes, SHA-1 checksums, licences and authors; no recording was downloaded, played or analysed. The eight picks are frozen in `anc_lab/forecaster_study_05.FRESH_RECORDINGS` (copied here as `fresh_recordings.json`, with the Commons description and categories) before the formal development run, so the code hash covers them.

## Searches

`s5_commons_search.py` (namespace 6, `filetype:audio`, up to 50 hits per phrase, then `imageinfo`), run from a scratch folder:

- `commons_search01.json`: motor starting, machine switched on, switched off hum, start up hum, compressor starts, refrigerator compressor, pump starting, fan turning on, transformer hum, electric motor, engine start idle, hum switch, turning on and off, dehumidifier, vacuum cleaner, washing machine, air conditioner starting, generator start. 18 files; the first try with all phrases was rate-limited (HTTP 429).
- `commons_search02.json`: motor starting, machine switched on, switched off, start up, compressor, refrigerator, pump, fan noise, transformer hum, electric motor, engine idle, hum, turning on, dehumidifier, vacuum cleaner, washing machine, air conditioner, generator, drone motor, electric shaver, hair dryer, aquarium, ventilation, boiler, elevator, escalator, freezer, dishwasher, blender, printer. 971 files.

Commons' search matches loosely, so most hits are music, speech or generated noise.

## Filter

`s5_pick_filter.py`, then reading the titles and descriptions: 10 to 150 s, at most 25 MB, a free licence (CC0, public domain, CC BY, CC BY-SA), not already under `external-audio/`, and an author not credited in any `SOURCES.md` there or in study 02's fresh list. Every Work With Sounds file was also left out, because three development recordings come from that collection. That left 171 files. Of those, only recordings of a machine likely to hold steady tones were kept (motor, fan, pump, compressor, propeller, electric train), one per author. Music, speech, animals, generated noise, hand pumps and revving engines were dropped.

## Picks

| File | Seconds | Author | Licence | Why |
|---|---|---|---|---|
| Ventilador.ogg | 18.4 | Armartinell | CC BY-SA 4.0 | A fan; the description says it is switched on and off in the clip |
| Akkuschrauber_–_Cordless_Screwdriver.ogg | 39.3 | Maximilian Schönherr | CC BY-SA 4.0 | An electric motor switched on, run at three powers, then shut down |
| ÖBB_Taurus_Start-Up.ogg | 17.0 | 3LM6wjuS | CC BY-SA 4.0 | Start-up of an electric locomotive |
| Son_démarrage_Mp14-8.ogg | 25.4 | Lodaï | CC BY-SA 4.0 | Start-up of a Paris metro train |
| Elektrorasur-01.ogg | 20.0 | Priwo | Public domain | An electric razor |
| Propeller-plane-flying-steady-01.wav | 20.0 | Versatile Virtuoso | CC BY-SA 4.0 | A propeller plane in steady flight |
| Sewerage_pumping_station_(Starnberg-Leutstetten_PW83)_c.ogg | 99.9 | PaulSch | CC0 | Pumping and flushing, recorded outside the building |
| Noise-Pollution-Filters-Bird-Communities-Based-on-Vocal-Frequency-pone.0027052.s001.ogg | 15.1 | Francis C, Ortega C, Cruz A | CC BY 2.5 | Background noise 100 m from a gas compressor exhaust (PLOS ONE supplement) |

Four were picked because their descriptions say the sound starts, stops or changes speed, since the study asks about sudden changes and starts. All eight are counted as acoustic captures. Whether each holds a tone the forecasters can find is not known until the test; a file with no reference tone still counts for boosts and whole-band gain.

Study 04 (gate fades) runs in parallel and may pick its own fresh files; `forecaster_study_05.fresh_problems` refuses any file on its list at `results-tone-forecaster-04/fresh-metadata/fresh_recordings.json`, and a note in the shared session folder lists these eight so it can avoid them.
