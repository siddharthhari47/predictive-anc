"""Freeze the second test's recording identities and code before any of its media is read."""
import json, sys
from pathlib import Path
import imageio_ffmpeg

ROOT = Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'research-tools/tuning-fresh-01'))
sys.path.insert(0, str(Path(__file__).parent))
from anc_lab import selector_headroom as h
from anc_lab import tuning_fresh_02  # noqa: F401
from anc_lab import tuning_fresh as tf
from anc_lab import tuning_decision as td
from screen_tuning_sources import earlier, normal, plain
from pool_tuning_sources import people

STUDY = tf.STUDY


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    assert not (STUDY/'protocol.json').exists() and not tf.AUDIO.exists()
    meta = json.loads((STUDY/'metadata/all_metadata.json').read_text(encoding='utf-8'))
    short = json.loads((STUDY/'shortlist.json').read_text(encoding='utf-8'))
    names, hashes, _ = earlier()
    seen = people()
    sources, dropped, uploaders, authors = [], [], set(), set()
    for line in (Path(__file__).parent/'picks.txt').read_text(encoding='utf-8').splitlines():
        who, start = line.split('|')
        hits = [r for r in short if r['uploader'].startswith(who) and r['title'][5:].startswith(start)]
        hits = hits or [r for r in short if r['title'][5:].startswith(start)]
        assert len(hits) == 1, (line, len(hits))
        title = hits[0]['title']
        i, ext = meta[title]['info'], meta[title]['info']['extmetadata']
        author, uploader = plain(ext['Artist']['value']), i['user']
        why = None
        if normal(title[5:]) in names or i['sha1'] in hashes:
            why = 'used before'
        elif normal(uploader) in seen or normal(author) in seen:
            why = 'uploader or author used before'
        elif normal(uploader) in uploaders or normal(author) in authors:
            why = 'second recording from one uploader or author'
        if why:
            dropped.append({'title': title, 'uploader': uploader, 'author': author, 'reason': why})
            continue
        uploaders.add(normal(uploader))
        authors.add(normal(author))
        n = len(sources)+1
        sources.append({'id': f'tg-{n:03d}', 'title': title, 'file': f'tg-{n:03d}'+Path(title).suffix.lower(),
                        'url': i['url'], 'source_page': i['descriptionurl'], 'sha1': i['sha1'], 'bytes': i['size'],
                        'seconds_metadata': i['duration'], 'mime': i['mime'], 'uploader': uploader, 'author': author,
                        'licence': plain(ext['LicenseShortName']['value']),
                        'description': plain(ext.get('ImageDescription', {}).get('value', ''))[:300]})
    assert all(e['url'].startswith('https://upload.wikimedia.org/') for e in sources)
    assert sum(e['bytes'] for e in sources) <= 3_000_000_000
    first = h.read(ROOT/'results-tuning-fresh-01/protocol.json')
    decoder = Path(imageio_ffmpeg.get_ffmpeg_exe())
    protocol = {
        **{k: first[k] for k in ('kind', 'candidate', 'arms', 'preprocessing', 'seeds', 'metrics', 'aggregation', 'decision', 'failures', 'caveats', 'authorization')},
        'created_utc': td.now(), 'sources': sources, 'dropped_before_freeze': dropped,
        'selection': 'Commons metadata and titles only, from the widened pool. Mechanical filters in research-tools/tuning-fresh-02/screen_wider.py, then a title and description screen in picks.txt. Every recording, uploader and author of earlier tests excluded; at most one per uploader and author.',
        'rooms': f'{tf.ROOMS_PER_SOURCE} per source, seed fixed by room seed {tf.ROOM_SEED}, recording id and room index; eligible if the v2 engine holds a tone in the tuning part.',
        'relation_to_first_test': 'results-tuning-fresh-01 was inconclusive and its outcome was known at design. Its rule, arms and thresholds are copied unchanged; the tests are never pooled.',
        'go_ahead': 'Yes, freeze a larger fresh test of SD-s30 on new recordings, sized for the 1-in-5 yield, and run it.',
        'decoder': {'path': str(decoder), 'sha256': h.sha(decoder)},
        'code_sha256': {name: h.sha(ROOT/name) for name in tf.FILES},
    }
    h.write_new(STUDY/'protocol.json', protocol)
    h.write_new(STUDY/'frozen.json', {'sha256': h.sha(STUDY/'protocol.json'), 'media_access_before_freeze': False})
    print(json.dumps({'sources': len(sources), 'mb': round(sum(e['bytes'] for e in sources)/1e6), 'dropped': dropped}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
