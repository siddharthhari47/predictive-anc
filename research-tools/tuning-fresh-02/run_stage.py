"""Run one stage of the frozen second test. The import sits at module level so spawned workers apply the same paths and seed."""
import sys
from pathlib import Path

sys.path.insert(0, r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
from anc_lab import tuning_fresh_02  # noqa: F401
from anc_lab import tuning_fresh as tf
from threadpoolctl import threadpool_limits

if __name__ == '__main__':
    with threadpool_limits(limits=1):
        {'rooms': tf.rooms, 'run': tf.run_all, 'summarize': tf.summarize}[sys.argv[1]]()
