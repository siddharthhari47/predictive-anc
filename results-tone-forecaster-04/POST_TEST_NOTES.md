# Post-test observations: gate fade

20 Oct 2026. Descriptive analysis of the already-saved frozen test scores. No model rerun, parameter choice or new test.

The failed tone-gain criterion comes with a clear pattern: the joint-check baseline already trails v2 on four of six fresh recordings. The faded gated-check variant changes the 20 ms tone score by at most 0.001176 dB on any file. This does not identify the root cause inside the forecaster, but it shows that the gate fade does not resolve the observed accuracy gap.

| Recording | v2 gain dB | Joint gain dB | Gate-fade gain dB | Fade minus joint dB |
|---|---:|---:|---:|---:|
| Het_vermalen_van_fruit_in_een_blender_-_SoundCloud_-_marloeskunst.ogg | 0.033 | 0.046 | 0.046 | -0.000030 |
| Laser_printer,_2015-01-23.ogg | 0.391 | 0.525 | 0.525 | +0.000000 |
| Photocopie.ogg | 7.327 | 6.821 | 6.821 | +0.000000 |
| Mobile_lift_stage.ogg | 9.752 | 4.901 | 4.900 | -0.001176 |
| Mil_Mi-8MTV-1_helicopter_starting_up.ogg | 5.586 | 1.609 | 1.609 | +0.000230 |
| Wiki_Motor_lancha.wav | 20.025 | 8.607 | 8.607 | +0.000000 |

On the fresh synthetic buzz family the gated fade has one boost case, compared with seven for joint + gate and two for the ungated joint check. Thus the targeted switching mechanism improves in these simulations even though the full candidate fails the separate real-recording accuracy requirement.

Next hypothesis to investigate, after finishing the independently frozen study 05: why the joint-check forecasting path loses useful prediction on some new tonal sources, and whether a causal, past-error-based choice of predictor could retain v2's strengths. These recordings are now diagnostic material, not a fresh test set for any resulting change. This is a proposed research question, not a tested remedy.

Two selected study-04 files were unavailable after rate-limit retries and were not replaced. All figures are recording-reference prediction metrics; no physical ANC was measured.
