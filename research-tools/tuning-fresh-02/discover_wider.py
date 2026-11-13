"""Wider Commons metadata search for the second fresh test; never downloads or decodes media."""
import json, sys, time
from pathlib import Path

ROOT = Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
sys.path.insert(0, str(ROOT/'research-tools/tuning-fresh-01'))
from discover_tuning_sources import get

DEST = ROOT/'results-tuning-fresh-02/metadata'
TITLE = ['truck', 'lorry', 'car', 'van', 'taxi', 'motorcycle', 'motorbike', 'moped', 'scooter', 'locomotive', 'railcar', 'railway', 'rail',
         'hovercraft', 'tugboat', 'cruise', 'ship_engine', 'engine_room', 'excavator', 'bulldozer', 'crane', 'forklift', 'escalator',
         'elevator', 'lift', 'treadmill', 'drill', 'grinder', 'sander', 'jackhammer', 'concrete_mixer', 'hydroelectric', 'power_plant',
         'power_station', 'boiler', 'sewing_machine', 'mixer', 'blender', 'microwave', 'shaver', 'toothbrush', 'kettle', 'hard_drive',
         'server_room', 'data_center', 'projector', 'photocopier', 'pylon', 'power_line', 'electric', 'cab_ride', 'onboard', 'on_board',
         'riding', 'inside', 'aboard', 'cockpit', 'jet', 'airliner', 'plane', 'sailing', 'waterjet', 'water_pump', 'windshield',
         'farm_machine', 'combine_harvester', 'thresher', 'weaving', 'press', 'conveyor', 'cement', 'quarry', 'noise', 'sound', 'ambience',
         'ambient', 'recording', 'buzz', 'whir', 'rumble', 'drone_sound']
PHRASES = ['engine noise', 'engine sound', 'motor noise', 'motor sound', 'machine noise', 'machine sound', 'machinery noise', 'fan noise',
           'cabin noise', 'interior noise', 'cab ride', 'train ride', 'bus ride', 'field recording', 'room tone', 'background noise',
           'ambient sound', 'ambient noise', 'industrial noise', 'factory noise', 'traffic noise', 'noise of', 'sound of a', 'electrical hum',
           'hum of', 'no narration', 'no commentary', 'natural sound']
QUERIES = [f'intitle:{t} filetype:{k}' for t in TITLE for k in ('audio', 'video')]
QUERIES += [f'"{t}" filetype:{k}' for t in PHRASES for k in ('audio', 'video')]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    found, meta = {}, {}
    for i, q in enumerate(QUERIES):
        data = get({'action': 'query', 'list': 'search', 'srsearch': q, 'srnamespace': 6, 'srlimit': 50})
        for hit in data['query']['search']:
            found.setdefault(hit['title'], []).append(q)
        time.sleep(1.5)
        if i % 40 == 39:
            print('searched', i+1, 'of', len(QUERIES), 'titles', len(found), flush=True)
    done = json.loads((ROOT/'results-tuning-fresh-01/metadata/all_metadata.json').read_text(encoding='utf-8'))
    titles = sorted(set(found)-set(done))
    print('new titles', len(titles), flush=True)
    for i in range(0, len(titles), 40):
        data = get({'action': 'query', 'titles': '|'.join(titles[i:i+40]), 'prop': 'imageinfo',
                    'iiprop': 'url|sha1|size|mime|extmetadata|mediatype|user|timestamp',
                    'iiextmetadatafilter': 'ImageDescription|Artist|LicenseShortName|LicenseUrl|Credit|ObjectName|Categories'})
        for page in data['query']['pages']:
            if page.get('imageinfo'):
                meta[page['title']] = {'found_by': found.get(page['title'], []), 'info': page['imageinfo'][0]}
        time.sleep(1.5)
    (DEST/'all_metadata.json').write_text(json.dumps({**done, **meta}, ensure_ascii=False, indent=1), encoding='utf-8')
    print('complete', len(meta), 'new; pool', len(done)+len(meta), flush=True)


if __name__ == '__main__':
    main()
