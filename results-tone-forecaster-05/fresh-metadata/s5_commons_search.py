"""Study 05: search Wikimedia Commons metadata (titles, descriptions, sizes, SHA-1, licences) for fresh test candidates.

Metadata only: no audio is downloaded. Args: output json, then search phrases."""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = 'https://commons.wikimedia.org/w/api.php'
UA = 'predictive-anc-offline-study/0.6 (local research; metadata only)'


def get(params, tries=5):
    url = API+'?'+urllib.parse.urlencode({**params, 'format':'json', 'formatversion':2, 'maxlag':5})
    req = urllib.request.Request(url, headers={'User-Agent':UA})
    for n in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code != 429 or n == tries-1:
                raise
            wait = float(e.headers.get('Retry-After') or 10*(n+1))
            print('429, waiting', wait, flush=True)
            time.sleep(wait)


def search(phrase, limit=50):
    out = get({'action':'query', 'list':'search', 'srsearch':f'{phrase} filetype:audio', 'srnamespace':6,
               'srlimit':limit})
    return [h['title'] for h in out['query']['search']]


def info(titles):
    res = {}
    for i in range(0, len(titles), 40):
        out = get({'action':'query', 'titles':'|'.join(titles[i:i+40]), 'prop':'imageinfo',
                   'iiprop':'sha1|size|mime|extmetadata|mediatype|user|timestamp', 'iiextmetadatafilter':
                   'ImageDescription|Artist|LicenseShortName|Credit|ObjectName|Categories'})
        for p in out['query']['pages']:
            ii = (p.get('imageinfo') or [{}])[0]
            em = ii.get('extmetadata', {})
            res[p['title']] = {'sha1':ii.get('sha1'), 'bytes':ii.get('size'), 'seconds':ii.get('duration'),
                               'mime':ii.get('mime'), 'uploader':ii.get('user'),
                               'author':em.get('Artist', {}).get('value'), 'licence':em.get('LicenseShortName', {}).get('value'),
                               'description':em.get('ImageDescription', {}).get('value'),
                               'categories':em.get('Categories', {}).get('value')}
        time.sleep(3)
    return res


def main():
    dest = sys.argv[1]
    titles = {}
    for phrase in sys.argv[2:]:
        for t in search(phrase):
            titles.setdefault(t, []).append(phrase)
        time.sleep(3)
    meta = info(sorted(titles))
    for t, m in meta.items():
        m['found_by'] = titles[t]
    json.dump(meta, open(dest, 'w', encoding='utf-8'), indent=1)
    print(len(meta), 'files')


if __name__ == '__main__':
    main()
