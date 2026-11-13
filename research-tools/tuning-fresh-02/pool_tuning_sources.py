"""List what remains of the Commons metadata pool for the second fresh test. No media access."""
import json, sys
from collections import Counter
from pathlib import Path

ROOT = Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
ONE = ROOT/'research-tools/tuning-fresh-01'
sys.path.insert(0, str(ONE))
from screen_tuning_sources import normal
USED = (ONE/'freeze_tuning_fresh.py').read_text(encoding='utf-8').split("USED_PEOPLE = '''")[1].split("'''")[0]


def people():
    """Everyone already used, including all 40 candidates of the first fresh test."""
    out = {normal(x) for line in USED.splitlines() for x in line.split('|')}
    for path in ROOT.glob('results-*/protocol.json'):
        p = json.loads(path.read_text(encoding='utf-8'))
        for key in ('sources', 'entries', 'dropped_before_freeze'):
            for e in p.get(key, []) if isinstance(p, dict) else []:
                if isinstance(e, dict):
                    out.update(normal(e[k]) for k in ('uploader', 'author') if e.get(k))
    return {x for x in out if x}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rows = json.loads((ROOT/'results-tuning-fresh-01/shortlist.json').read_text(encoding='utf-8'))
    seen = people()
    rows = [r for r in rows if normal(r['uploader']) not in seen and normal(r['author']) not in seen]
    uploaders = Counter(r['uploader'] for r in rows)
    print(len(rows), 'titles from', len(uploaders), 'uploaders; total MB', round(sum(r['mb'] for r in rows)))
    for r in rows:
        print(r['title'][5:80], '|', r['seconds'], '|', r['mb'], '|', r['uploader'][:16], '|', r['desc'][:60].replace('\n', ' '))


if __name__ == '__main__':
    main()
