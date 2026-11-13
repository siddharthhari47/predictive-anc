"""Acquire only the frozen list; never decode, listen or score."""
import hashlib, json, sys, time, urllib.request
from pathlib import Path

ROOT = Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
sys.path.insert(0, str(ROOT))
from anc_lab import selector_headroom as h
from anc_lab import tuning_fresh as tf
from anc_lab import tuning_decision as td

STUDY = tf.STUDY


def main():
    p = tf.verified()
    stage = STUDY/'download'
    stage.mkdir(exist_ok=False)
    tf.AUDIO.mkdir(exist_ok=False)
    rows = []
    for index, entry in enumerate(p['sources'], 1):
        row = {'id': entry['id'], 'title': entry['title'], 'status': 'missing'}
        target = tf.AUDIO/entry['file']
        for attempt in range(3):
            part = target.with_suffix(target.suffix+f'.attempt-{attempt+1}.part')
            try:
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
                row.update(status='verified', local_path=str(target.relative_to(ROOT)), sha256=two.hexdigest(), bytes=size)
                row.pop('reason', None)
                break
            except Exception as exc:
                row['reason'] = f'{type(exc).__name__}: {exc}'
                print('issue', entry['id'], row['reason'][:120], flush=True)
                if isinstance(exc, ValueError):
                    break
                time.sleep(15*(attempt+1))
        rows.append(row)
        print(json.dumps({'file': index, 'of': len(p['sources']), 'status': row['status']}), flush=True)
        time.sleep(2)
    h.write_new(stage/'manifest.json', {'protocol_sha256': h.sha(STUDY/'protocol.json'), 'files': rows,
                                        'verified': sum(r['status'] == 'verified' for r in rows), 'completed_utc': td.now()})
    lines = ['# Fresh tuner-test sources', '', 'Media stay local. Every identity and licence was frozen before access.', '']
    lines += [f"- {e['file']} — {e['title']}; {e['author']}; {e['licence']}; {e['source_page']}" for e in p['sources']]
    (tf.AUDIO/'SOURCES.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print('verified', sum(r['status'] == 'verified' for r in rows), 'of', len(rows), flush=True)


if __name__ == '__main__':
    main()
