"""results-live-listen-05: listen-03's check with a steady 200 Hz tone from Sid's phone as the hum.

Why a phone: Sid is in a different room now. Its fan makes a broadband rush with no hum
(results-live-listen-04; Sid: "that loud steady hush is the fan now im in [a different place] so
different fan"), so no fan here can answer listen-03's question: does the earbuds' call microphone
pass a steady hum, or does its noise reduction take it out? A tone generator gives a hum that is
steady by construction. Setup asked of Sid: fan off; a 200 Hz sine from the phone, loud enough to hear
clearly with the earbuds in; the phone on the desk between them and the laptop; the earbuds in with
their own noise cancelling off; sitting still and quiet for the 30 s.

listen_check_03 runs unchanged (listen-03's results pin its code) and writes to a new folder: the same
190-210 Hz rule, 30 s, input-only, no audio stored. This script plays nothing; the phone does.

Reading, fixed before listening, worked out from listen.json alone and saved as reading.json:
1. No answer unless the laptop microphone hears the tone (listen-03's rule: a line from 190 to 210 Hz
   at least 6 dB over its floor) and the faint detector, the one tune-earbud-mic.bat uses, lists it in
   at least half the blocks after the first 10 s there. The laptop is the control: it shows the tone
   was playing and that the detector can hold it.
2. The earbuds' microphone keeps a steady hum if it also hears the tone (within 2 Hz of the laptop's
   line, 6 dB over its own floor), the faint detector lists it in at least half of its blocks after
   the first 10 s, and no more than 10% of its take is digital silence (exact zeros). If it hears and
   holds the tone but goes silent more often than that, it passes the hum only in bursts. Otherwise it
   removes or loses the hum, and `tune --mic earbuds` could not work on one.
   The silence limit was added before any listening, after an offline run through the real detectors:
   a synthetic take shut to exact zeros in 62% of its blocks (the share the earbuds sent in listen-03)
   still had the tone listed in 91% of blocks. Microphone noise does not give exact zeros and a
   call-noise gate does. listen-03's laptop take had 3.9% and listen-04's takes 0.2% or less, so 10%
   sits above ordinary takes and well below that gate.
Reported alongside, not part of the verdict: each microphone's tone level in its first 3 s against
the median from 15 s on, the smoothed detector's share (the engine plain `tune` uses), the coherence
at the tone, and the 50 ms leftover of the tone and of the steady control where worked out.
"""
import statistics

import listen_check_03 as check

check.OUT = check.ROOT/'results-live-listen-05'
check.CODE = check.CODE+('research-tools/listen_check_05.py',)
HOLDS = .5                # share of blocks after the first 10 s in which the detector must list the tone
GATED = .1                # largest share of the earbuds' take that may be digital silence (exact zeros)
KEEPS = 'keeps a steady hum'


def share(m, engine):
    d = m.get('detectors')
    v = d.get(engine, {}).get('share_on_hum_after_10_s') if isinstance(d, dict) else None
    return v if isinstance(v, (int, float)) else None


def level_change(m):
    """The tone's level in the first 3 s stretch against the median of the stretches from 15 s on."""
    rows = m.get('every_3_s')
    if not isinstance(rows, list) or not rows:
        return None
    later = [r['hum_level_db'] for r in rows if r['start_s'] >= 15]
    if not later:
        return None
    first, rest = rows[0]['hum_level_db'], statistics.median(later)
    return {'first_3_s_db': first, 'median_from_15_s_db': rest, 'change_db': rest-first}


def leftover_50_ms(m, part):
    p = m.get('predictability')
    if isinstance(p, dict) and part in p:
        return p[part].get('leftover_db', {}).get('50')
    return p if isinstance(p, str) else (p or {}).get('error')


def reading(result):
    rule = result.get('rule_hum') or {}
    mics = {label: (result.get(label) if isinstance(result.get(label), dict) else {}) for label in ('earbuds', 'laptop')}
    heard = (mics['earbuds'].get('hum') or {}).get('heard')
    held = {label: share(m, 'faint') for label, m in mics.items()}
    zeros = mics['earbuds'].get('exact_zero_share')
    if 'heard' not in rule:
        verdict = 'no answer: the laptop take could not be analysed'
    elif not rule['heard']:
        verdict = 'no answer: the laptop microphone did not hear the tone'
    elif held['laptop'] is None or held['laptop'] < HOLDS:
        verdict = 'no answer: the faint detector did not hold the tone even on the laptop microphone'
    elif heard is None:
        verdict = "no answer: the earbuds' take could not be analysed"
    elif not heard:
        verdict = "removes or loses the hum: the earbuds' microphone did not hear the tone"
    elif held['earbuds'] is None:
        verdict = "no answer: the faint detector failed on the earbuds' take"
    elif held['earbuds'] < HOLDS:
        verdict = 'removes or loses the hum: heard over the take, but the faint detector did not hold it after 10 s'
    elif not isinstance(zeros, (int, float)):
        verdict = "no answer: the earbuds' take has no count of digital silence"
    elif zeros > GATED:
        verdict = ('passes the hum only in bursts: heard and held, but its microphone sent digital silence'
                   ' in %.0f%% of the take' % (100*zeros))
    else:
        verdict = KEEPS
    coherence = result.get('coherence')
    return {'verdict': verdict,
            'earbuds_keep_a_steady_hum': None if verdict.startswith('no answer') else verdict == KEEPS,
            'rule': {'laptop_hears_and_holds': 'listen-03 rule, and faint share after 10 s >= %g' % HOLDS,
                     'earbuds_keep': 'heard within 2 Hz at 6 dB, faint share after 10 s >= %g, and digital silence'
                                     ' <= %g of the take' % (HOLDS, GATED)},
            'tone_hz_on_laptop': rule.get('hz'),
            'microphones': {label: {'tone_above_floor_db': (m.get('hum') or {}).get('above_floor_db'),
                                    'heard': (m.get('hum') or {}).get('heard'),
                                    'faint_share_after_10_s': held[label],
                                    'smoothed_share_after_10_s': share(m, 'smoothed'),
                                    'tone_level': level_change(m),
                                    'leftover_50_ms_db': leftover_50_ms(m, 'hum'),
                                    'steady_control_leftover_50_ms_db': leftover_50_ms(m, 'steady_control'),
                                    'exact_zero_share': m.get('exact_zero_share')}
                            for label, m in mics.items()},
            'coherence_at_tone': coherence.get('at_hum') if isinstance(coherence, dict) else coherence}


def finish():
    """Reads the saved listen.json, writes reading.json next to it and prints the verdict."""
    out = reading(check.h.read(check.OUT/'listen.json'))
    check.h.write_new(check.OUT/'reading.json', check.clean(out))
    print("Earbuds' microphone:", out['verdict'], flush=True)
    for label, m in out['microphones'].items():
        print(f"  {label:8s} faint {m['faint_share_after_10_s']} | smoothed {m['smoothed_share_after_10_s']} |",
              f"tone level {m['tone_level']} | 50 ms leftover {m['leftover_50_ms_db']}", flush=True)
    return out


if __name__ == '__main__':
    check.main()
    finish()
