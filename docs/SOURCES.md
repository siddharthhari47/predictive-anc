# Primary sources and what they support

Reviewed 15 October 2026. Source excerpts were retrieved during setup; the project does not depend on these sites at runtime.

1. [MathWorks: Active Noise Control Using a Filtered-X LMS FIR Adaptive Filter](https://www.mathworks.com/help/audio/ug/active-noise-control-using-a-filtered-x-lms-fir-adaptive-filter.html). Primary implementation documentation distinguishes reference, primary acoustic path, actuator-to-error-microphone secondary path and error sensing. It demonstrates secondary-path identification and filtered-x adaptation. This motivates the separate paths and the additional-sensing label for our FxNLMS comparator. Our implementation and numerical parameters are independent; the example does not validate ordinary earphone ANC from a remote laptop microphone.

2. [Bluetooth SIG: Improving latency and broadening audio horizons with Bluetooth LE Audio](https://www.bluetooth.com/blog/improving-latency-and-broadening-audio-horizons-with-le-audio/). The SIG-hosted interview describes Classic Audio buffering and LE Isochronous Channels. It supports treating transport/profile/buffering as part of system characterization. It does not specify our chosen 120 ms or 2 ms jitter values, and it does not claim phase-accurate ANC through arbitrary Bluetooth earphones.

3. [Bluetooth SIG: A behind-the-scenes look at Bluetooth LE Audio](https://www.bluetooth.com/blog/a-behind-the-scenes-look-at-le-audio/). The SIG-hosted interview describes presentation-delay work and codec framing. It reinforces that audio framing and presentation timing need explicit accounting. It is not a measured latency guarantee for any particular headset or operating system.

The sinusoidal timing formula in MODEL.md is derived directly from subtracting two sinusoids; a numerical regression test checks it. The simulator's paths, frequency set, jitter process, performance targets and all reported attenuation are project assumptions/results, not values taken from these sources. No published experimental finding is used to claim physical success here.
