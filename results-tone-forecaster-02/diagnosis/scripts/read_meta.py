"""Summarize Commons imageinfo JSON (untrusted data). Args: path to meta.json."""
import json
import re
import sys

d = json.load(open(sys.argv[1], encoding='utf-8'))
for page in d['query']['pages'].values():
    if 'imageinfo' not in page:
        print('MISSING', page.get('title'))
        continue
    ii = page['imageinfo'][0]
    em = ii.get('extmetadata', {})
    strip = lambda s: re.sub(r'<[^>]+>', '', s or '').strip()[:80]
    print(json.dumps({'title':page['title'], 'url':ii['url'], 'bytes':ii['size'], 'sha1':ii['sha1'], 'mime':ii['mime'],
                      'duration':ii.get('duration'), 'uploader':ii.get('user'), 'uploaded':ii.get('timestamp'),
                      'artist':strip(em.get('Artist', {}).get('value')), 'licence':strip(em.get('LicenseShortName', {}).get('value')),
                      'page':ii.get('descriptionurl')}, ensure_ascii=True))
