"""A ceiling on the joint band check's tie fallback (results-tone-forecaster-03).

Why: in study 02 (results-tone-forecaster-02) the joint band check + gate passed
its frozen test narrowly, with two third-octave boosts left on one fresh file
(Buzzing_Speakers.ogg, +7.3 and +5.6 dB in two nearly empty bands). The likely
reason is in JointCheckBank's decision: a setting is allowed if its worst band is
within `margin_db` of no output, or within `tie_db` of the least-boosting setting,
whichever is looser. The second limit keeps drifting tones alive when every
setting boosts a little, but it has no ceiling, so when every setting boosts a
lot the output still picks one of them.

CappedCheckBank
    The same check with a ceiling: a setting is allowed if its worst band is
    within max(margin_db, min(least-boosting + tie_db, cap_db)) of no output. When
    even the least-boosting setting is more than `cap_db` louder in some band, only
    no output is left. cap_db = inf is JointCheckBank; cap_db = margin_db switches
    the fallback off.

Everything else (the ten settings, the 4 s buffer, the medians over 16 checks,
the switch margin, the start setting) is JointCheckBank's. tone_floors.py is
frozen by study 02's protocol, so the band measurement is repeated here, unchanged,
instead of being split out there. The decision is a method of its own so the
tests can feed it band levels directly.

Development trials are kept in results-tone-forecaster-03/diagnosis.
Block-causal like the bank. Nothing here opens an audio device.
"""
import numpy as np

from .tone_floors import JointCheckBank


class CappedCheckBank(JointCheckBank):
    """JointCheckBank whose tie fallback stops at `cap_db`: above it, the output goes silent."""
    def __init__(self, *args, cap_db=1., **kwargs):
        super().__init__(*args, **kwargs)
        self.cap_db = float(cap_db)
        groups = len(self.group_h)
        # Per horizon group, counted over decisions (checks after min_checks_to_decide):
        # the fallback loosened the limit past margin_db / the cap set the limit / only no output was allowed.
        self.counters.update({'decisions':[0]*groups, 'fallback_decisions':[0]*groups, 'capped_decisions':[0]*groups,
                              'silent_decisions':[0]*groups})

    def settings(self):
        out = super().settings()
        out['joint_check']['cap_db'] = self.cap_db
        return out

    def _band_check(self, g):
        # As JointCheckBank._band_check (tone_floors.py), up to the decision.
        spec = np.fft.rfft(self.buffer[g]*np.roll(self.taper, self.write[g]), axis=1)
        p = (spec.real**2+spec.imag**2)@self.bands.T                              # (settings+1, bands)
        floor = 1e-12*max(float(p[0].sum()), 1e-30)
        bands_db = 10*np.log10(np.maximum(p, floor)/np.maximum(p[0], floor))
        total = np.maximum(p.sum(axis=1), floor)
        total_db = 10*np.log10(total/total[0])
        self.history_db[g].append((bands_db, total_db))
        self.counters['band_checks'][g] += 1
        if len(self.history_db[g]) >= self.min_decide:
            self._decide(g)

    def limit_db(self, louder):
        """Allowed worst-band level (dB over no output), given each setting's worst band (index 0 = no output)."""
        return max(self.margin_db, min(float(louder[1:].min())+self.tie_db, self.cap_db))

    def _decide(self, g):
        louder = np.median([b for b, _ in self.history_db[g]], axis=0).max(axis=1)   # worst band, dB over no output
        total = np.median([t for _, t in self.history_db[g]], axis=0)
        limit = self.limit_db(louder)
        ok = louder <= limit
        ok[0] = True
        c = self.counters
        c['decisions'][g] += 1
        c['fallback_decisions'][g] += int(limit > self.margin_db)
        c['capped_decisions'][g] += int(louder[1:].min()+self.tie_db > max(self.cap_db, self.margin_db))
        c['silent_decisions'][g] += int(not ok[1:].any())
        best = int(np.flatnonzero(ok)[np.argmin(total[ok])])
        now = self.active[g]
        if ok[now] and total[now] <= total[best]+self.switch_db:
            return
        c['setting_switches'][g] += int(best != now)
        self.active[g] = best
