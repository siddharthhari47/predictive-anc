import numpy as np

from anc_lab.antihum import FS, V2_SELECTOR, AntiHumEngine
from anc_lab.faint_tones import FAINT, CombinedSelector, FaintSelector, faint_lines
from anc_lab.live_engine import ENGINES, FaintEngine, SmoothedEngine
from anc_lab.tone_selection import ToneSelector


def wobbly(seconds, db=-12., seed=0):
    rng = np.random.default_rng(seed)
    n = int(seconds*FS)
    k = np.convolve(rng.standard_normal(n), np.ones(FS//2)/np.sqrt(FS//2), 'same')
    tone = np.sin(2*np.pi*np.cumsum(200+k/np.std(k))/FS)
    noise = rng.standard_normal(n)
    return noise+tone*np.sqrt(np.var(noise)*315/1000*10**(db/10))/np.std(tone)


def run(selector, y):
    out = []
    for t in range(selector.step, len(y)+1, selector.step):
        out.append(selector.update(y[max(0, t-selector.window):t]))
    return out


def test_faint_lines_finds_a_steady_peak_and_ignores_flat_noise():
    y = wobbly(4.)
    assert any(abs(f-200) < 3 for f, _ in faint_lines(y))
    assert faint_lines(np.random.default_rng(1).standard_normal(4*FS)) == []
    assert faint_lines(np.zeros(4*FS)) == [] and faint_lines(np.ones(100)) == []


def test_faint_selector_needs_seconds_of_hold_before_reporting():
    out = run(FaintSelector(FS, **FAINT), wobbly(20.))
    first = next(i for i, a in enumerate(out) if a)
    # window fills at 4 s, then 20 of 24 updates must agree
    assert (first+1)*.25 >= 4+(FAINT['acquire']-1)*.25-1e-9
    assert all(any(abs(f-200) < 3 for f, _ in a) for a in out[first:])


def test_combined_keeps_every_frozen_tone():
    rng = np.random.default_rng(3)
    t = np.arange(10*FS)/FS
    y = np.sin(2*np.pi*120*t)+.5*rng.standard_normal(len(t))+wobbly(10., seed=4)
    strict, combined = ToneSelector(FS, **V2_SELECTOR), CombinedSelector(FS)
    for k in range(combined.step, len(y)+1, combined.step):
        a = strict.update(y[max(0, k-strict.window):k])
        b = combined.update(y[max(0, k-combined.window):k])
        assert all(any(f == g for g, _ in b) for f, _ in a[:combined.max_tones])


def test_engines_and_default_selector_unchanged():
    assert set(ENGINES) == {'faint', 'smoothed', 'v2'}
    assert isinstance(SmoothedEngine().raw.selector, ToneSelector)
    assert isinstance(AntiHumEngine().selector, ToneSelector)
    engine = FaintEngine()
    assert isinstance(engine.raw.selector, CombinedSelector)
    assert engine.raw.keep >= 4*FS


def test_faint_engine_reports_the_wobbly_hum():
    engine = FaintEngine()
    y, near = wobbly(15.), 0
    for i in range(0, len(y), 20):
        engine.push(y[i:i+20])
        near += any(abs(f-200) < 3 for f, _ in engine.strongest())
    # locks after about 9 s; the fast release may drop a few single origins after that
    assert near >= 500


def test_combined_never_lets_a_faint_tone_push_out_a_strict_one():
    class Fixed:
        def __init__(self, tones, window, step=500, associate_hz=2.):
            self.tones, self.window, self.step, self.associate_hz, self.max_tones = tones, window, step, associate_hz, 6
        def update(self, segment):
            return self.tones
    combined = CombinedSelector(FS)
    strict = [(144., 1.), (151., 1.), (165., 1.), (188., 1.), (194., 1.), (288., 1.)]
    combined.strict, combined.faint = Fixed(strict, 2000), Fixed([(156., .9)], 8000)
    assert combined.update(np.zeros(8000)) == strict
    combined.strict = Fixed(strict[:4], 2000)
    assert combined.update(np.zeros(8000)) == strict[:4]+[(156., .9)]
