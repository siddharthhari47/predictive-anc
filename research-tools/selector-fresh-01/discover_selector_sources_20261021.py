"""Commons metadata only; never downloads or decodes media."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT=Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
DEST=ROOT/'results-selector-fresh-01/metadata'
QUERIES=[
 'intitle:fan filetype:audio', 'intitle:ventilation filetype:audio',
 'intitle:engine filetype:audio', 'intitle:diesel filetype:audio',
 'intitle:train filetype:audio', 'intitle:hum filetype:audio',
 'intitle:tractor filetype:audio', 'intitle:aircraft filetype:audio',
 'intitle:vacuum filetype:audio', 'intitle:compressor filetype:audio',
 'intitle:generator filetype:audio', 'intitle:machine filetype:audio',
 'intitle:fan filetype:video', 'intitle:ventilation filetype:video',
 'intitle:engine filetype:video', 'intitle:diesel filetype:video',
 'intitle:tractor filetype:video', 'intitle:compressor filetype:video',
 'intitle:generator filetype:video', 'intitle:lathe filetype:video',
 'intitle:air_conditioner filetype:video', 'intitle:washing_machine filetype:video',
 'intitle:helicopter filetype:video', 'intitle:locomotive filetype:video',
]

def save(path,x):
 with path.open('x',encoding='utf-8') as f:json.dump(x,f,indent=2,ensure_ascii=False)

def get(params):
 url='https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode(dict(format='json',formatversion=2,maxlag=5,**params))
 for n in range(3):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'PredictiveANCResearch/0.6 (offline research; metadata only)'}),timeout=30) as r:
    result=json.load(r)
   if 'error' in result:raise RuntimeError(result['error'])
   return result
  except (urllib.error.HTTPError,urllib.error.URLError) as exc:
   if n==2:raise
   print('Metadata request retry',str(exc)[:100],flush=True)
   time.sleep(30*(n+1))

def main():
 sys.stdout.reconfigure(encoding='utf-8')
 if not DEST.exists():
  DEST.mkdir(parents=True)
  save(DEST/'discovery_plan.json',{'created_utc':datetime.now(timezone.utc).isoformat(),'queries':QUERIES,'limit_each':50,'media_access':False})
 else:
  assert not (DEST/'all_metadata.json').exists(), 'Completed discovery is immutable'
 found={}
 for i,q in enumerate(QUERIES):
  cached=DEST/f'search-{i:02d}.json'
  if cached.exists():data=json.loads(cached.read_text(encoding='utf-8'))
  else:
   try:data=get({'action':'query','list':'search','srsearch':q,'srnamespace':6,'srlimit':50})
   except urllib.error.HTTPError as exc:
    save(DEST/f'search-{i:02d}-error.json',{'query':q,'error':str(exc)})
    continue
   save(cached,data)
   time.sleep(5)
  for h in data['query']['search']:found.setdefault(h['title'],[]).append(q)
  print('Metadata search',i+1,'/',len(QUERIES),'unique titles',len(found),flush=True)
 titles=sorted(found);meta={}
 for i in range(0,len(titles),35):
  cached=DEST/f'info-{i//35:02d}.json'
  if cached.exists():data=json.loads(cached.read_text(encoding='utf-8'))
  else:
   data=get({'action':'query','titles':'|'.join(titles[i:i+35]),'prop':'imageinfo',
    'iiprop':'url|sha1|size|mime|extmetadata|mediatype|user|timestamp',
    'iiextmetadatafilter':'ImageDescription|Artist|LicenseShortName|LicenseUrl|Credit|ObjectName|Categories'})
   save(cached,data)
   time.sleep(5)
  for page in data['query']['pages']:
   if page.get('imageinfo'):meta[page['title']]={'found_by':found.get(page['title'],[]),'info':page['imageinfo'][0]}
  print('Metadata info',min(i+35,len(titles)),'/',len(titles),flush=True)
 save(DEST/'all_metadata.json',meta)
 print('Metadata discovery complete',len(meta),flush=True)

if __name__=='__main__':main()
