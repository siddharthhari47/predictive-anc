"""Apply the mechanical metadata filters and write the shortlist for screening by title. No media access."""
import hashlib, html, json, re, sys, unicodedata
from pathlib import Path

ROOT = Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
STUDY = ROOT/'results-tuning-fresh-01'
AUDIO_EXT = ('.wav', '.ogg', '.oga', '.mp3', '.flac', '.opus', '.webm', '.ogv', '.mp4', '.mkv')


def plain(text):
    return html.unescape(re.sub('<[^>]+>', '', text or '')).strip()


def normal(text):
    return ''.join(c for c in unicodedata.normalize('NFKC', plain(text)).casefold() if c.isalnum())


def sha1(path):
    d = hashlib.sha1()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(1 << 20), b''):
            d.update(data)
    return d.hexdigest()


def earlier():
    names, hashes, authors = set(), set(), set()
    for folder in (ROOT/'external-audio', ROOT/'recordings'):
        for path in folder.rglob('*'):
            if path.is_file() and path.suffix.lower() in AUDIO_EXT:
                hashes.add(sha1(path))
                names.add(normal(path.name))
    for p in ROOT.glob('results-*/protocol.json'):
        text = json.loads(p.read_text(encoding='utf-8'))
        for key in ('sources', 'entries', 'fresh_recordings', 'recordings'):
            for e in text.get(key, []) if isinstance(text, dict) else []:
                if isinstance(e, str):
                    names.add(normal(e))
                elif isinstance(e, dict):
                    for k in ('file', 'title'):
                        if e.get(k):
                            names.add(normal(e[k]))
                            names.add(normal(str(e[k]).removeprefix('File:')))
                    if e.get('sha1'):
                        hashes.add(e['sha1'])
                    if e.get('author'):
                        authors.add(normal(e['author']))
    for sources in ROOT.glob('external-audio/*/SOURCES.md'):
        for m in re.finditer(r'File:([^;\n]+)', sources.read_text(encoding='utf-8')):
            names.add(normal(m.group(1)))
    return names, hashes, authors


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    meta = json.loads((STUDY/'metadata/all_metadata.json').read_text(encoding='utf-8'))
    names, hashes, authors = earlier()
    rows, drops = [], {}
    for title, m in meta.items():
        i = m['info']
        ext = i.get('extmetadata', {})
        author = plain(ext.get('Artist', {}).get('value', ''))
        licence = plain(ext.get('LicenseShortName', {}).get('value', ''))
        why = None
        if not (i['mime'].startswith(('audio/', 'video/')) or i['mime'] == 'application/ogg'):
            why = 'mime'
        elif not 51 <= (i.get('duration') or 0) <= 1800 or not 0 < i['size'] <= 125_000_000:
            why = 'length_or_size'
        elif not (licence in ('CC0', 'Public domain') or re.fullmatch(r'CC BY(?:-SA)? [1-4]\.\d(?: [a-z]+)?', licence)):
            why = 'licence'
        elif not author or 'unknown author' in author.lower():
            why = 'author'
        elif normal(title[5:]) in names or i['sha1'] in hashes:
            why = 'used_before'
        if why:
            drops[why] = drops.get(why, 0)+1
            continue
        rows.append({'title': title, 'seconds': round(i['duration']), 'mb': round(i['size']/1e6, 1), 'mime': i['mime'],
                     'uploader': i['user'], 'author': author[:50], 'licence': licence, 'author_seen': normal(author) in authors,
                     'desc': plain(ext.get('ImageDescription', {}).get('value', ''))[:110]})
    rows.sort(key=lambda r: r['title'])
    (STUDY/'shortlist.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')
    print(len(meta), 'titles', drops, 'kept', len(rows), 'earlier names', len(names), 'hashes', len(hashes))
    for k, r in enumerate(rows):
        print(k, r['title'][5:90], '|', r['seconds'], 's |', r['uploader'][:18], '|', r['desc'][:70].replace('\n', ' '))


if __name__ == '__main__':
    main()
