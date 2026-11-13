"""Apply the first test's mechanical filters to the wider pool, then drop speech-led and music titles. No media access."""
import json, re, sys
from collections import Counter
from pathlib import Path

ROOT = Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
sys.path.insert(0, str(ROOT/'research-tools/tuning-fresh-01'))
sys.path.insert(0, str(ROOT/'research-tools/tuning-fresh-02'))
from screen_tuning_sources import earlier, normal, plain
from pool_tuning_sources import people

STUDY = ROOT/'results-tuning-fresh-02'
NOT_MACHINE = re.compile(r'spoken word|wikipedia|wikinews|wikimania|wikimedia|wiki loves|librivox|article|\bsong|music|album|\bband\b|orchestra|concert|choir|sing|piano|guitar|'
                         r'interview|speech|remarks|press |hearing|lecture|podcast|episode|trailer|tutorial|workshop|news|documentary|animation|'
                         r'explained|how to|introduction|presentation|conference|briefing|recital|poem|reading|sermon|bird|frog|cricket|insect|whale|'
                         r'dance|festival|parade|ceremony|anthem|march|film|movie|\(\d{4}\)|\d{6,7}\)|cctv|crash|explosion|timelapse|time-lapse|slow motion|'
                         r'pronunciation|voice|language|greeting|hymn|opera|rap\b|remix|\bep\b|track \d|symphony|sonata|prelude', re.I)
BOT = re.compile(r'bot$|^computerhotline$|^mupper-san$|open access media', re.I)
MACHINE = re.compile(r'engine|motor|diesel|bus\b|tram|train|subway|metro|railway|rail|locomotive|railcar|ferry|ship|boat|helicopter|aircraft|airplane|plane|'
                     r'flight|cabin|cockpit|fan\b|ventilat|air.?condition|hvac|compressor|pump|generator|turbine|mill|factory|machine|lathe|drill|grinder|sander|'
                     r'saw\b|mower|tractor|truck|lorry|\bcar\b|van\b|taxi|motorcycle|motorbike|scooter|moped|excavator|crane|forklift|escalator|elevator|lift\b|'
                     r'refrigerator|fridge|freezer|washing|dryer|dishwasher|vacuum|blender|mixer|kettle|shaver|printer|server|hum\b|hum |buzz|whir|rumble|drone sound|'
                     r'noise|ambience|ambient|room tone|boiler|power (plant|station)|transformer|substation', re.I)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    meta = json.loads((STUDY/'metadata/all_metadata.json').read_text(encoding='utf-8'))
    names, hashes, _ = earlier()
    seen = people()
    rows = []
    for title, m in meta.items():
        i = m['info']
        ext = i.get('extmetadata', {})
        author = plain(ext.get('Artist', {}).get('value', ''))
        licence = plain(ext.get('LicenseShortName', {}).get('value', ''))
        desc = plain(ext.get('ImageDescription', {}).get('value', ''))
        text = title+' '+desc
        if not (i['mime'].startswith(('audio/', 'video/')) or i['mime'] == 'application/ogg') or i['mime'].endswith('midi'):
            continue
        if not 51 <= (i.get('duration') or 0) <= 1800 or not 0 < i['size'] <= 125_000_000:
            continue
        if not (licence in ('CC0', 'Public domain') or re.fullmatch(r'CC BY(?:-SA)? [1-4]\.\d(?: [a-z]+)?', licence)):
            continue
        if not author or 'unknown author' in author.lower() or normal(title[5:]) in names or i['sha1'] in hashes:
            continue
        if normal(i['user']) in seen or normal(author) in seen or BOT.search(i['user']) or NOT_MACHINE.search(text) or not MACHINE.search(text):
            continue
        rows.append({'title': title, 'seconds': round(i['duration']), 'mb': round(i['size']/1e6, 1), 'uploader': i['user'], 'author': author[:50], 'desc': desc[:110]})
    rows.sort(key=lambda r: (r['uploader'].casefold(), r['title']))
    (STUDY/'shortlist.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')
    print(len(meta), 'pool;', len(rows), 'titles from', len(Counter(r['uploader'] for r in rows)), 'uploaders')
    for r in rows:
        print(r['uploader'][:12], '|', r['title'][5:70], '|', r['seconds'], '|', r['desc'][:45].replace('\n', ' '))


if __name__ == '__main__':
    main()
