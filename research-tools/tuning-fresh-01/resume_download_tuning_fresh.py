"""Finish the frozen list after the first attempt was rate limited (HTTP 429).

Same URLs and identity checks as download_tuning_fresh.py, slower, and it honours Retry-After.
No recording is added or replaced. The first attempt's manifest, rooms and decoded audio are kept
as *-attempt-1, and rooms are rebuilt from the completed manifest.
"""
import hashlib, json, sys, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
sys.path.insert(0, str(ROOT))
from anc_lab import selector_headroom as h
from anc_lab import tuning_fresh as tf
from anc_lab import tuning_decision as td

STUDY = tf.STUDY
FIRST_WAIT, BETWEEN, TRIES, BACKOFF = 600, 45, 6, 300


def fetch(entry, target, attempt):
    part = target.with_suffix(target.suffix+f'.resume-{attempt}.part')
    one, two, size = hashlib.sha1(), hashlib.sha256(), 0
    req = urllib.request.Request(entry['url'], headers={'User-Agent': 'PredictiveANCResearch/0.7 (local offline experiment; frozen Commons inputs)'})
    with urllib.request.urlopen(req, timeout=90) as r, part.open('xb') as out:
        if not r.url.startswith('https://upload.wikimedia.org/'):
            raise ValueError('unexpected redirect')
        while data := r.read(1 << 20):
            size += len(data)
            if size > entry['bytes']:
                raise ValueError('exceeded frozen size')
            out.write(data)
            one.update(data)
            two.update(data)
    if size != entry['bytes'] or one.hexdigest() != entry['sha1']:
        raise ValueError('identity mismatch')
    part.rename(target)
    return two.hexdigest(), size


def main():
    p = tf.verified()
    old = STUDY/'download/manifest.json'
    assert old.exists() and (STUDY/'rooms.json').exists() and not (STUDY/'runs').exists()
    (STUDY/'download').rename(STUDY/'download-attempt-1')
    (STUDY/'rooms.json').rename(STUDY/'rooms-attempt-1.json')
    (STUDY/'decoded').rename(STUDY/'decoded-attempt-1')
    rows = {r['id']: r for r in h.read(STUDY/'download-attempt-1/manifest.json')['files']}
    time.sleep(FIRST_WAIT)
    for entry in p['sources']:
        row = rows[entry['id']]
        if row['status'] == 'verified':
            continue
        row['first_attempt_reason'] = row.pop('reason', None)
        target = tf.AUDIO/entry['file']
        for attempt in range(1, TRIES+1):
            try:
                digest, size = fetch(entry, target, attempt)
                row.update(status='verified', local_path=str(target.relative_to(ROOT)), sha256=digest, bytes=size)
                row.pop('reason', None)
                break
            except urllib.error.HTTPError as exc:
                row['reason'] = f'HTTPError: {exc.code}'
                wait = max(int(exc.headers.get('Retry-After') or 0), BACKOFF*attempt)
                print('issue', entry['id'], exc.code, 'wait', wait, flush=True)
                time.sleep(wait)
            except ValueError as exc:
                row['reason'] = f'ValueError: {exc}'
                print('issue', entry['id'], row['reason'], flush=True)
                break
            except Exception as exc:
                row['reason'] = f'{type(exc).__name__}: {exc}'
                print('issue', entry['id'], row['reason'][:120], flush=True)
                time.sleep(BACKOFF)
        print(json.dumps({'id': entry['id'], 'status': row['status']}), flush=True)
        time.sleep(BETWEEN)
    files = [rows[e['id']] for e in p['sources']]
    (STUDY/'download').mkdir(exist_ok=False)
    h.write_new(STUDY/'download/manifest.json', {'protocol_sha256': h.sha(STUDY/'protocol.json'), 'files': files,
                                                 'verified': sum(r['status'] == 'verified' for r in files),
                                                 'resumed_after_rate_limit': True, 'completed_utc': td.now()})
    print('verified', sum(r['status'] == 'verified' for r in files), 'of', len(files), flush=True)


if __name__ == '__main__':
    main()
