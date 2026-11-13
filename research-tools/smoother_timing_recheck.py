"""Recompute the timing summary from the raw per-block times; split by detector-update blocks. Descriptive, written after the result."""
import json, glob
from pathlib import Path
import numpy as np
S = Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc\results-smoother-timing-01')
res = json.load(open(S/'timing/results.json'))
print({k: v for k, v in res['environment'].items() if k in ('selected_logical_cpu', 'quiet_preflight', 'preflight_windows')})
for v in ('live', 'cached_dpss'):
    t = [np.load(p)['times_ms'] for p in sorted(glob.glob(str(S/'timing'/f'*-{v}.npz')))]
    print(v, 'runs', len(t), 'blocks', sum(len(x) for x in t))
    a = np.concatenate(t); path = a[:, 0]+a[:, 1]
    rp = [np.percentile(x[:, 0]+x[:, 1], 99) for x in t]; rs = [np.percentile(x[:, 1], 99) for x in t]
    print(' run path p99 range', round(min(rp), 2), round(max(rp), 2), 'runs under 5', sum(r < 5 for r in rp), 'run smoother p99 worst', round(max(rs), 4))
    print(' smoother mean/max us', round(a[:, 1].mean()*1e3, 1), round(a[:, 1].max()*1e3, 1), 'share of path %', round(100*a[:, 1].sum()/path.sum(), 2))
    print(' path p50/p95/p99/max', [round(float(q), 2) for q in np.percentile(path, [50, 95, 99, 100])], 'over5', int((path > 5).sum()), 'over10', int((path > 10).sum()), 'mean', round(path.mean(), 3))
    print(' synthesis p99', round(np.percentile(a[:, 2], 99), 3))
    # same blocks, engine alone versus with smoother
    push = a[:, 0]
    print(' push-alone p99', round(np.percentile(push, 99), 3), 'over5', int((push > 5).sum()), 'over10', int((push > 10).sum()))
    per = [r for r in res['runs'] if r['variant'] == v]
    print(' backlog worst', round(max(r['backlog_ms'] for r in per), 1), 'background range', round(min(r['estimated_background_cpu_percent'] for r in per), 1), round(max(r['estimated_background_cpu_percent'] for r in per), 1))
