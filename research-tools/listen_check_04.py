"""results-live-listen-04: the listen-03 check again, with fresh readiness.

listen-03 ran when the user was not ready: a usage limit held up the run after they said go, so its
numbers do not describe the fan-on, earbuds-in setup (results-live-listen-03/NOT_READY.md). This runs
listen_check_03 unchanged, since listen-03's results pin its code, and writes to a new folder.
Same rule, same 30 s, input-only, no audio stored, plays nothing.
"""
import listen_check_03 as check

check.OUT = check.ROOT/'results-live-listen-04'
check.CODE = check.CODE+('research-tools/listen_check_04.py',)

if __name__ == '__main__':
    check.main()
