"""Second fresh-recording test of SD-s30, sized for the observed room yield. Never opens audio devices.

results-tuning-fresh-01 was inconclusive on too few sources. This repeats the same
code, arms, rooms-per-source, seeds and rule on recordings neither study has used.
Only the paths, the room seed and the frozen file list differ, so no scoring logic
lives here. The two tests are reported separately and never pooled.
"""
from . import tuning_fresh as tf

tf.STUDY = tf.ROOT/'results-tuning-fresh-02'
tf.AUDIO = tf.ROOT/'external-audio/wikimedia-commons-tuning-fresh-02'
tf.ROOM_SEED = 20261031
tf.FILES = [name for name in tf.FILES if name not in ('docs/TUNING_FRESH_TEST.md',) and not name.startswith('research-tools/')]
tf.FILES += ['anc_lab/tuning_fresh_02.py', 'tests/test_tuning_fresh_02.py', 'docs/TUNING_FRESH_TEST_02.md',
             'research-tools/tuning-fresh-01/screen_tuning_sources.py', 'research-tools/tuning-fresh-01/resume_download_tuning_fresh.py',
             'research-tools/tuning-fresh-02/pool_tuning_sources.py', 'research-tools/tuning-fresh-02/discover_wider.py',
             'research-tools/tuning-fresh-02/screen_wider.py', 'research-tools/tuning-fresh-02/picks.txt',
             'research-tools/tuning-fresh-02/freeze_tuning_fresh_02.py', 'research-tools/tuning-fresh-02/download_tuning_fresh_02.py']
