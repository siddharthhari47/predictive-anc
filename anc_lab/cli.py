import argparse
from pathlib import Path

from .experiment import Config, run
from .report import generate


def main():
    parser = argparse.ArgumentParser(description="Predictive ANC research. Only 'tune' plays sound, and only after on-screen confirmation.")
    sub = parser.add_subparsers(dest="action", required=True)
    bench = sub.add_parser("benchmark", help="Generate or replay a reference; simulate ear acoustics")
    bench.add_argument("--out", type=Path, default=Path("results"))
    bench.add_argument("--seeds", type=int, nargs="+", default=[7, 19, 43])
    bench.add_argument("--scenes", choices=["steady", "drifting", "unpredictable"], nargs="+", default=["steady", "drifting", "unpredictable"])
    bench.add_argument("--input", type=Path, help="Mono reference WAV; does NOT contain measured ear residual")
    report = sub.add_parser("report", help="Regenerate report from existing results")
    report.add_argument("--out", type=Path, default=Path("results"))
    record = sub.add_parser("record", help="Explicit microphone capture only; never plays audio")
    record.add_argument("--out", type=Path, required=True)
    record.add_argument("--seconds", type=float, default=12.)
    record.add_argument("--rate", type=int, default=16000)
    record.add_argument("--device", help="sounddevice input device name or numeric ID")
    record.add_argument("--source", default="unspecified", help="Description of the environmental source")
    assess_parser = sub.add_parser("assess", help="Evaluate held-out real reference prediction; no simulated ear pressure")
    assess_parser.add_argument("--input", type=Path, required=True)
    assess_parser.add_argument("--out", type=Path, required=True)
    trial = sub.add_parser("trial", help="Record a 30-second reference and evaluate Goal 1; input only")
    trial.add_argument("--out", type=Path, required=True, help="A new local trial directory")
    trial.add_argument("--device", help="Explicit input name/ID recommended; default may be a headset")
    trial.add_argument("--source", default="fan", help="Description of the environmental source")
    trial.add_argument("--rate", type=int, default=48000)
    source = sub.add_parser("compare-sources", help="Compare matched fan-off/on captures in absolute digital units; no playback")
    source.add_argument("--off", type=Path, required=True)
    source.add_argument("--on", type=Path, required=True)
    source.add_argument("--out", type=Path, required=True)
    generalize = sub.add_parser("generalize", help="Test automatic tone adaptation and frozen ML on new synthetic frequency groups")
    generalize.add_argument("--out", type=Path, required=True)
    select = sub.add_parser("select-tones", help="Causal automatic tone count/confidence study on fresh synthetic sources; optional re-analysis of local WAVs")
    select.add_argument("--out", type=Path, required=True)
    select.add_argument("--real", type=Path, nargs="*", default=[], help="Previously recorded mono WAVs to re-analyse (not independent evidence)")
    release = sub.add_parser("release-study", help="Tune faster tone release on development scenes, then test on fresh random frequency draws with repeats")
    release.add_argument("--out", type=Path, required=True)
    hums = sub.add_parser("real-hums", help="Predictability of downloaded real hum recordings (reference prediction only)")
    hums.add_argument("--audio", type=Path, required=True, help="Folder with the recordings and SOURCES.json")
    hums.add_argument("--out", type=Path, required=True)
    forecaster = sub.add_parser("tone-forecaster", help="Real-tone forecaster study (results-tone-forecaster-01): develop on "
                                                        "development material, freeze the protocol, then test once (reference prediction only)")
    forecaster.add_argument("stage", choices=["develop", "freeze", "test"])
    forecaster.add_argument("--out", type=Path, help="develop: a new development folder; test: a new test folder")
    forecaster.add_argument("--development", type=Path, help="freeze: the development folder whose choice is frozen")
    forecaster.add_argument("--protocol", type=Path, help="test: frozen protocol (default protocol.json in the study folder)")
    tune_sim = sub.add_parser("tune-sim", help="Tune-by-ear in simulated rooms with real recordings as sources; nothing is played")
    tune_sim.add_argument("--audio", type=Path, required=True, help="Folder with the recordings")
    tune_sim.add_argument("--real-hums", type=Path, required=True, help="real_hums.json from the real-hums study")
    tune_sim.add_argument("--out", type=Path, required=True)
    tune = sub.add_parser("tune", help="Open the live tune-by-ear window (laptop microphone in unless --mic earbuds, wired earphones out); "
                                       "plays only after every on-screen readiness box is ticked and Start is pressed")
    tune.add_argument("--cap", type=float, default=.05, help="Output peak limit, fraction of digital full scale (at most 0.2)")
    tune.add_argument("--minutes", type=float, default=15., help="Session stops by itself after this long (at most 30)")
    tune.add_argument("--mask", action="store_true", help="Open the hum masker instead: soft noise around each hum it hears, so the hum stands out less (not cancellation); uses the faint engine unless --engine is given")
    tune.add_argument("--engine", choices=["smoothed", "faint", "v2"], default=None, help="Engine behind the tuner (default smoothed; faint for --mask); faint also listens for weak, wobbly hums (failed its frozen test, see results-faint-tones-02); v2 is the earlier unsmoothed one")
    tune.add_argument("--mic", choices=["laptop", "earbuds"], default="laptop", help="Which microphone listens: the laptop's own microphone array (default) or the earbuds' own microphone, which Windows calls 'Headset Microphone (...)'; Bluetooth hands-free microphones are never used")
    tune.add_argument("--allow-speaker-named-output", action="store_true",
                      help="List outputs named 'Speakers' too (some headphone jacks appear under that name)")
    sub.add_parser("devices", help="List input devices (requires optional capture dependency)")
    args = parser.parse_args()
    if args.action == "benchmark":
        result = run(args.out, Config(seeds=tuple(args.seeds), scenes=tuple(args.scenes)), args.input)
        generate(args.out, result)
        print(f"Complete: {args.out.resolve() / 'report.html'}")
    elif args.action == "report":
        generate(args.out)
    elif args.action == "compare-sources":
        from .source_study import run_study
        from .source_report import generate_source_report
        result = run_study(args.off, args.on, args.out)
        generate_source_report(args.out, result)
        print(f"Complete: {args.out.resolve() / 'report.html'}")
    elif args.action == "generalize":
        from .generalization import run_generalization
        run_generalization(args.out)
        print(f"Complete: {args.out.resolve() / 'REPORT.md'}")
    elif args.action == "select-tones":
        from .selection_study import run_selection_study
        run_selection_study(args.out, args.real)
        print(f"Complete: {args.out.resolve() / 'REPORT.md'}")
    elif args.action == "release-study":
        from .release_study import run_release_study
        run_release_study(args.out)
        print(f"Complete: {args.out.resolve() / 'REPORT.md'}")
    elif args.action == "real-hums":
        from .real_hum_study import run_real_hum_study
        run_real_hum_study(args.audio, args.out)
        print(f"Complete: {args.out.resolve() / 'REPORT.md'}")
    elif args.action == "tone-forecaster":
        from . import forecaster_study as study
        if args.stage == "develop":
            if not args.out:
                parser.error("develop needs --out (a new folder)")
            study.run_development(args.out)
            print(f"Complete: {args.out.resolve() / 'DEVELOPMENT.md'}")
        elif args.stage == "freeze":
            if not args.development:
                parser.error("freeze needs --development")
            study.freeze_protocol(args.development)
            print(f"Frozen: {study.STUDY / 'protocol.json'}")
        else:
            from .forecaster_report import write_test_report
            if not args.out:
                parser.error("test needs --out (a new folder; the test runs once)")
            result = study.run_test(args.out, args.protocol or study.STUDY / "protocol.json")
            write_test_report(args.out, result)          # inside the new folder, so no earlier report is overwritten
            print(f"Complete: {args.out.resolve() / 'REPORT.md'}")
    elif args.action == "tune-sim":
        from .antihum_study import run_tune_by_ear_study
        run_tune_by_ear_study(args.audio, args.real_hums, args.out)
        print(f"Complete: {args.out.resolve() / 'REPORT.md'}")
    elif args.action == "tune":
        try:
            from .tune_app import run_window
        except ImportError as exc:
            raise SystemExit('Live tuning needs the optional audio packages. Install with: python -m pip install -e ".[capture]"') from exc
        if args.mask:
            from .mask_app import run_mask_window
            run_mask_window(args.cap, args.minutes, args.allow_speaker_named_output, args.engine or 'faint', microphone=args.mic)
        else:
            run_window(args.cap, args.minutes, args.allow_speaker_named_output, args.engine or 'smoothed', microphone=args.mic)
    elif args.action in ("assess", "trial"):
        from .assessment import assess
        from .assessment_report import generate_assessment_report
        if args.action == "trial":
            if args.out.exists() and (not args.out.is_dir() or any(args.out.iterdir())):
                raise ValueError("Trial output must be a new or empty directory; capture was not started.")
            from .capture import capture
            device = int(args.device) if args.device and args.device.isdigit() else args.device
            reference = args.out/"reference.wav"
            capture(reference, seconds=30, rate=args.rate, device=device, source=args.source)
        else:
            reference = args.input
        result = assess(reference, args.out)
        generate_assessment_report(args.out, result)
        print(f"Complete: {args.out.resolve() / 'report.html'}")
    else:
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise SystemExit('Capture is optional. Install with: python -m pip install -e ".[capture]"') from exc
        if args.action == "devices":
            print(sd.query_devices())
            return
        from .capture import capture
        device = int(args.device) if args.device and args.device.isdigit() else args.device
        capture(args.out, seconds=args.seconds, rate=args.rate, device=device, source=args.source)


if __name__ == "__main__":
    main()
