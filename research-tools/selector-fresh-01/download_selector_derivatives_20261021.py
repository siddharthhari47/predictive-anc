"""Conservative acquisition of one official smaller representation per fixed source."""
from datetime import datetime,timezone
import hashlib,json,sys,time,urllib.request
from pathlib import Path
ROOT=Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
sys.path.insert(0,str(ROOT))
from anc_lab import selector_headroom as h
S=ROOT/'results-selector-fresh-01'
DEST=ROOT/'external-audio/wikimedia-commons-selector-fresh-01/small'

def main():
 p=h.read(S/'protocol.json');a=h.read(S/'acquisition-amendment-01.json')
 assert h.sha(S/'protocol.json')==a['original_protocol_sha256']
 assert h.sha(S/'acquisition-amendment-01.json')==h.read(S/'acquisition-amendment-frozen.json')['sha256']
 assert h.sha(Path(__file__))==a['runner_sha256']
 stage=S/'download-small';stage.mkdir(exist_ok=False);DEST.mkdir(exist_ok=False)
 h.write_new(stage/'start.json',{'started_utc':datetime.now(timezone.utc).isoformat(),'amendment_sha256':h.sha(S/'acquisition-amendment-01.json')})
 entries={e['id']:e for e in p['sources']};rows=[]
 for n,rep in enumerate(a['representations'],1):
  e=entries[rep['id']];row={'id':e['id'],'title':e['title'],'status':'missing','representation':rep,'attempts':[]}
  target=DEST/e['file']
  if rep['kind']=='unavailable':row['reason']=rep['reason']
  else:
   for attempt in range(2):
    partial=target.with_suffix(target.suffix+f'.attempt-{attempt+1}.part')
    try:
     req=urllib.request.Request(rep['url'],headers={'User-Agent':'PredictiveANCResearch/0.6 (local offline research; smaller Commons transcodes)'})
     size=0;sha1=hashlib.sha1();sha256=hashlib.sha256()
     with urllib.request.urlopen(req,timeout=90) as response,partial.open('xb') as out:
      assert response.url.startswith('https://upload.wikimedia.org/')
      etag=response.headers.get('ETag')
      expected=int(response.headers['Content-Length']) if response.headers.get('Content-Length') else None
      while data:=response.read(1<<20):
       size+=len(data)
       if size>25000000:raise ValueError('Small representation exceeds 25 MB cap')
       out.write(data);sha1.update(data);sha256.update(data)
     if expected is not None and size!=expected:raise ValueError('Incomplete HTTP body')
     if rep['kind']=='original' and (size!=rep['expected_bytes'] or sha1.hexdigest()!=e['sha1']):raise ValueError('Original identity mismatch')
     partial.rename(target)
     row.update(status='verified',local_path=str(target.relative_to(ROOT)),bytes=size,
         sha1=sha1.hexdigest(),sha256=sha256.hexdigest(),http_etag=etag,
         verification_kind='parent identity/API derivative URL plus local receipt' if rep['kind']=='official_derivative' else 'external size/SHA1 match')
     row['attempts'].append({'attempt':attempt+1,'status':'verified'});break
    except Exception as exc:
     row['reason']=f'{type(exc).__name__}: {exc}'
     row['attempts'].append({'attempt':attempt+1,'error':row['reason']})
     print('Small-media request failed',n,attempt+1,row['reason'][:150],flush=True)
     if isinstance(exc,(ValueError,AssertionError)):break
     if attempt==0:
      print('Backing off for 90 seconds before the one allowed retry.',flush=True)
      time.sleep(90)
  h.write_new(stage/f"{e['id']}.json",row);rows.append(row)
  print(json.dumps({'completed':n,'of':len(entries),'id':e['id'],'status':row['status'],'bytes':row.get('bytes',0)}),flush=True)
  time.sleep(10)
 manifest={'protocol_sha256':h.sha(S/'protocol.json'),'acquisition_amendment_sha256':h.sha(S/'acquisition-amendment-01.json'),
    'files':rows,'verified_count':sum(r['status']=='verified' for r in rows),
    'completed_utc':datetime.now(timezone.utc).isoformat()}
 h.write_new(S/'download/manifest.json',manifest)
 sources=['# Frozen fresh-selector source attribution','','All media stay local. Official smaller copies were selected under acquisition-amendment-01.json before decoding.','']
 for e in p['sources']:sources.append('- '+e['file']+' — '+e['title']+'; '+e['author']+'; '+e['licence']+'; '+e['source_page'])
 (DEST.parent/'SOURCES.md').write_text('\n'.join(sources)+'\n',encoding='utf-8')
 print('Small-media acquisition finished',manifest['verified_count'],'/',len(entries),flush=True)

if __name__=='__main__':main()
