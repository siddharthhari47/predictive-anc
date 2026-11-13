"""Commons metadata only; never downloads or decodes media."""
import json, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
DEST = ROOT/'results-tuning-fresh-01/metadata'
TERMS = ['fan', 'ventilation', 'ventilator', 'air_conditioning', 'air_conditioner', 'HVAC', 'blower', 'extractor', 'dehumidifier',
         'refrigerator', 'fridge', 'freezer', 'hum', 'mains_hum', 'transformer', 'substation', 'generator', 'compressor', 'pump',
         'motor', 'engine', 'diesel', 'idling', 'idle', 'turbine', 'propeller', 'cabin', 'interior', 'tractor', 'bus', 'tram',
         'subway', 'metro', 'train', 'ferry', 'ship', 'boat', 'helicopter', 'aircraft', 'airplane', 'vacuum_cleaner', 'hair_dryer',
         'hand_dryer', 'dishwasher', 'washing_machine', 'dryer', 'lathe', 'mill', 'factory', 'machine', 'workshop', 'lawn_mower',
         'chainsaw', 'drone', 'printer', 'loom', 'sawmill', 'windmill']
QUERIES = [f'intitle:{t} filetype:{k}' for t in TERMS for k in ('audio', 'video')]


def get(params):
    url = 'https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode(dict(format='json', formatversion=2, maxlag=5, **params))
    for n in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'PredictiveANCResearch/0.7 (offline research; metadata only)'}), timeout=30) as r:
                result = json.load(r)
            if 'error' in result:
                raise RuntimeError(result['error'])
            return result
        except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError) as exc:
            if n == 3:
                raise
            print('retry', str(exc)[:100], flush=True)
            time.sleep(20*(n+1))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    found, meta = {}, {}
    for i, q in enumerate(QUERIES):
        data = get({'action': 'query', 'list': 'search', 'srsearch': q, 'srnamespace': 6, 'srlimit': 50})
        (DEST/f'search-{i:03d}.json').write_text(json.dumps(data), encoding='utf-8')
        for hit in data['query']['search']:
            found.setdefault(hit['title'], []).append(q)
        time.sleep(1.5)
        if i % 20 == 19:
            print('searched', i+1, 'of', len(QUERIES), 'titles', len(found), flush=True)
    titles = sorted(found)
    for i in range(0, len(titles), 40):
        data = get({'action': 'query', 'titles': '|'.join(titles[i:i+40]), 'prop': 'imageinfo',
                    'iiprop': 'url|sha1|size|mime|extmetadata|mediatype|user|timestamp',
                    'iiextmetadatafilter': 'ImageDescription|Artist|LicenseShortName|LicenseUrl|Credit|ObjectName|Categories'})
        for page in data['query']['pages']:
            if page.get('imageinfo'):
                meta[page['title']] = {'found_by': found.get(page['title'], []), 'info': page['imageinfo'][0]}
        time.sleep(1.5)
        print('info', min(i+40, len(titles)), 'of', len(titles), flush=True)
    (DEST/'all_metadata.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
    print('complete', len(meta), flush=True)


if __name__ == '__main__':
    main()
