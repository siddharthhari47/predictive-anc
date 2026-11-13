"""Freeze recording identities, the rule and all code hashes before any new media byte is read."""
import json, sys
from pathlib import Path
import imageio_ffmpeg

ROOT = Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
from anc_lab import selector_headroom as h
from anc_lab import tuning_fresh as tf
from anc_lab import tuning_decision as td
from anc_lab import engine_smoothing as es
from screen_tuning_sources import earlier, normal, plain

STUDY = tf.STUDY
USED_PEOPLE = '''Acabashi|Andy Mabbett|Pigsonthewing|Beeld en Geluid|MartsniezBot|Bluedawe|Cirosantilli2|ClemRutter|DY5W-sport|Dawidpl4553
Department of Homeland Security|Dmitry Novoklimov|Doug Coldwell|DrTrumpet|ElsyChester|Extemporalist|Gpkp|Johannes Maximilian|Kartik Singhal
Katana Harlan|Kauko Helavuo|LouiseBrown1981|Mukasora|Nottingham Hackspace|Ozonesn|Pacarazzi|Philippine Air Force|Philt3r|Helena Törnqvist
Provo rossi|Santasantaxxx|Sir Balefire|Szczecinolog|Tfme|TheFrog001|Work With Sounds|Z22|daSupremo|ezwa|Fæ|Сергей Филатов'''


def earlier_people():
    """Uploaders and credited authors of every earlier recording, as normalized names."""
    people = {normal(x) for line in USED_PEOPLE.splitlines() for x in line.split('|')}
    for path in ROOT.glob('results-*/protocol.json'):
        p = json.loads(path.read_text(encoding='utf-8'))
        for key in ('sources', 'entries'):
            for e in p.get(key, []) if isinstance(p, dict) else []:
                if isinstance(e, dict):
                    people.update(normal(e[k]) for k in ('uploader', 'author') if e.get(k))
    for sources in ROOT.glob('external-audio/*/SOURCES.md'):
        for line in sources.read_text(encoding='utf-8').splitlines():
            parts = line.split('; ')
            if len(parts) >= 3:
                people.add(normal(parts[1]))
    return {x for x in people if x}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    assert not (STUDY/'protocol.json').exists() and not tf.AUDIO.exists()
    meta = json.loads((STUDY/'metadata/all_metadata.json').read_text(encoding='utf-8'))
    names, hashes, _ = earlier()
    people = earlier_people()
    picks = [x for x in (Path(__file__).parent/'picks.txt').read_text(encoding='utf-8').splitlines() if x]
    sources, dropped, uploaders, authors = [], [], set(), set()
    for title in picks:
        m = meta['File:'+title]
        i, ext = m['info'], m['info']['extmetadata']
        author, uploader = plain(ext['Artist']['value']), i['user']
        why = None
        if normal(title) in names or i['sha1'] in hashes:
            why = 'used before'
        elif normal(uploader) in people or normal(author) in people:
            why = 'uploader or author used before'
        elif normal(uploader) in uploaders or normal(author) in authors:
            why = 'second recording from one uploader or author'
        if why:
            dropped.append({'title': title, 'uploader': uploader, 'author': author, 'reason': why})
            continue
        uploaders.add(normal(uploader))
        authors.add(normal(author))
        n = len(sources)+1
        sources.append({'id': f'tf-{n:03d}', 'title': 'File:'+title, 'file': f'tf-{n:03d}'+Path(title).suffix.lower(),
                        'url': i['url'], 'source_page': i['descriptionurl'], 'sha1': i['sha1'], 'bytes': i['size'],
                        'seconds_metadata': i['duration'], 'mime': i['mime'], 'uploader': uploader, 'author': author,
                        'licence': plain(ext['LicenseShortName']['value']),
                        'description': plain(ext.get('ImageDescription', {}).get('value', ''))[:300]})
    assert all(e['url'].startswith('https://upload.wikimedia.org/') for e in sources)
    assert sum(e['bytes'] for e in sources) <= 2_000_000_000
    decoder = Path(imageio_ffmpeg.get_ffmpeg_exe())
    protocol = {
        'created_utc': td.now(), 'kind': 'frozen_fresh_recording_test_of_tuner_candidate',
        'candidate': 'SD-s30 exactly as chosen by results-engine-smoothing-01; no constant changes.',
        'arms': {'O': 'Original tuner, v2 engine.', 'SD-s30': 'Search change + sequential check, alpha 0.3 engine.'},
        'sources': sources, 'dropped_before_freeze': dropped,
        'selection': 'Commons metadata and titles only. Mechanical filters in research-tools/tuning-fresh-01/screen_tuning_sources.py, then a title and description screen in picks.txt for machinery, appliances or vehicles. Uploaders and credited authors of earlier recordings excluded; at most one per uploader and author.',
        'rooms': f'{tf.ROOMS_PER_SOURCE} per source, seed fixed by room seed {tf.ROOM_SEED}, recording id and room index; eligible if the v2 engine holds a tone in the tuning part.',
        'preprocessing': f'First audio track, channel 0, first {tf.CAP_SECONDS:.0f} s, at least {tf.MIN_SECONDS:.0f} s, first 40% tuning prefix, mean/std from prefix; no crops, loops or replacements.',
        'seeds': f'{tf.SEEDS} per room from tuning_decision.seeds_for; same for both arms and noise levels.',
        'metrics': 'As decision-01: tone level, band_db, harmful keeps (prefix), room harms. Oracle errors not computed.',
        'aggregation': 'Paired differences per room and seed, averaged over seeds per room, rooms per source, then sources; 95% percentile interval from 10000 source-bootstrap resamples.',
        'decision': f'At sigma 1 SD-s30 passes only if (1) lower 95% bound of tone-level gain over O > 0, (2) harmful keeps <= O, (3) room harms <= O, (4) mean band_db difference >= -0.05 dB. Fewer than {tf.MIN_SOURCES} eligible sources or {tf.MIN_ROOMS} eligible rooms is inconclusive whatever the scores. Sigma 0.5 and 2 are descriptive.',
        'failures': 'Missing, undecodable, short or silent files are reported and never replaced. Algorithm exceptions abort.',
        'caveats': 'Purposive public collection; simulated listener, rooms and microphone; live timing unmeasured; no physical ANC claimed.',
        'authorization': 'u have full autonomy proceed anddownload whatever u feel necessary',
        'decoder': {'path': str(decoder), 'sha256': h.sha(decoder)},
        'code_sha256': {name: h.sha(ROOT/name) for name in tf.FILES},
        'engine_protocol_sha256': h.sha(es.STUDY/'protocol.json'), 'engine_summary_sha256': h.sha(es.STUDY/'summary.json'),
    }
    h.write_new(STUDY/'protocol.json', protocol)
    h.write_new(STUDY/'frozen.json', {'sha256': h.sha(STUDY/'protocol.json'), 'media_access_before_freeze': False})
    print(json.dumps({'sources': len(sources), 'mb': round(sum(e['bytes'] for e in sources)/1e6), 'dropped': dropped}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
