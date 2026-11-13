"""Acquire only the frozen list, slowly from the start; never decode, listen or score."""
import json, sys, time, urllib.error
from pathlib import Path

ROOT = Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'research-tools/tuning-fresh-01'))
from anc_lab import selector_headroom as h
from anc_lab import tuning_fresh_02  # noqa: F401
from anc_lab import tuning_fresh as tf
from anc_lab import tuning_decision as td
from resume_download_tuning_fresh import fetch, BETWEEN, TRIES, BACKOFF

STUDY = tf.STUDY


def main():
    p = tf.verified()
    (STUDY/'download').mkdir(exist_ok=False)
    tf.AUDIO.mkdir(exist_ok=False)
    rows = []
    for entry in p['sources']:
        row = {'id': entry['id'], 'title': entry['title'], 'status': 'missing'}
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
        rows.append(row)
        print(json.dumps({'id': entry['id'], 'status': row['status']}), flush=True)
        time.sleep(BETWEEN)
    h.write_new(STUDY/'download/manifest.json', {'protocol_sha256': h.sha(STUDY/'protocol.json'), 'files': rows,
                                                 'verified': sum(r['status'] == 'verified' for r in rows), 'completed_utc': td.now()})
    lines = ['# Second fresh tuner-test sources', '', 'Media stay local. Every identity and licence was frozen before access.', '']
    lines += [f"- {e['file']} — {e['title']}; {e['author']}; {e['licence']}; {e['source_page']}" for e in p['sources']]
    (tf.AUDIO/'SOURCES.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print('verified', sum(r['status'] == 'verified' for r in rows), 'of', len(rows), flush=True)


if __name__ == '__main__':
    main()
