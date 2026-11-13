"""Acquire only the complete pre-frozen list; never decode, listen or score."""
from datetime import datetime,timezone
import hashlib,json,sys,time,urllib.error,urllib.request
from pathlib import Path
ROOT=Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
sys.path.insert(0,str(ROOT))
from anc_lab import selector_headroom as h
STUDY=ROOT/'results-selector-fresh-01'
DEST=ROOT/'external-audio/wikimedia-commons-selector-fresh-01'

def main():
 p=h.read(STUDY/'protocol.json');frozen=h.read(STUDY/'frozen.json')
 assert h.sha(STUDY/'protocol.json')==frozen['protocol_sha256']
 assert h.sha(Path(__file__))==p['runner_sha256'][Path(__file__).name]
 for name,digest in p['code_sha256'].items():assert h.sha(ROOT/name)==digest
 stage=STUDY/'download';stage.mkdir(exist_ok=False);DEST.mkdir(exist_ok=False)
 h.write_new(stage/'start.json',{'started_utc':datetime.now(timezone.utc).isoformat(),
    'protocol_sha256':frozen['protocol_sha256'],'direct_user_authorization':p['authorization']})
 rows=[]
 for index,entry in enumerate(p['sources'],1):
  row={'id':entry['id'],'title':entry['title'],'status':'missing','attempts':[]}
  target=DEST/entry['file']
  for attempt in range(3):
   partial=target.with_suffix(target.suffix+f'.attempt-{attempt+1}.part')
   try:
    req=urllib.request.Request(entry['url'],headers={'User-Agent':'PredictiveANCResearch/0.6 (local offline experiment; frozen Commons inputs)'})
    one=hashlib.sha1();two=hashlib.sha256();size=0
    with urllib.request.urlopen(req,timeout=90) as resp, partial.open('xb') as out:
     if not resp.url.startswith('https://upload.wikimedia.org/'):raise ValueError('Unexpected download redirect')
     while data:=resp.read(1<<20):
      size+=len(data)
      if size>entry['bytes'] or size>125000000:raise ValueError('Exceeded frozen byte size')
      out.write(data);one.update(data);two.update(data)
    if size!=entry['bytes'] or one.hexdigest()!=entry['sha1']:raise ValueError('Frozen file identity mismatch')
    partial.rename(target)
    row.update(status='verified',local_path=str(target.relative_to(ROOT)),sha1=one.hexdigest(),sha256=two.hexdigest(),bytes=size)
    row['attempts'].append({'attempt':attempt+1,'status':'verified'});break
   except Exception as exc:
    row['reason']=f'{type(exc).__name__}: {exc}'
    row['attempts'].append({'attempt':attempt+1,'error':row['reason']})
    print('Acquisition issue',index,attempt+1,row['reason'][:140],flush=True)
    # Identity mismatches do not warrant fetching a changed version repeatedly.
    if isinstance(exc,ValueError):break
    if attempt<2:time.sleep((15,30)[attempt])
  h.write_new(stage/f"{entry['id']}.json",row);rows.append(row)
  print(json.dumps({'file':index,'total':len(p['sources']),'id':entry['id'],'status':row['status']}),flush=True)
  time.sleep(2)
 result={'protocol_sha256':frozen['protocol_sha256'],'files':rows,
   'verified_count':sum(r['status']=='verified' for r in rows),'completed_utc':datetime.now(timezone.utc).isoformat()}
 h.write_new(stage/'manifest.json',result)
 sources=['# Fresh selector-test sources','','Original media stay local. Every identity and licence was frozen before access.','']
 for e in p['sources']:
  sources+=['- '+e['file']+' — '+e['title']+'; '+e['author']+'; '+e['licence']+'; '+e['source_page']]
 (DEST/'SOURCES.md').write_text('\n'.join(sources)+'\n',encoding='utf-8')
 print('Acquisition complete',result['verified_count'],'/',len(rows),flush=True)

if __name__=='__main__':main()
