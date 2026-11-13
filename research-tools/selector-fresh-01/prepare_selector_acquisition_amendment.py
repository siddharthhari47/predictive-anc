"""Record a smaller-media acquisition amendment before any fresh decoding/scoring."""
from datetime import datetime,timezone
import importlib.util,json,sys,time
from pathlib import Path
ROOT=Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
sys.path.insert(0,str(ROOT))
from anc_lab import selector_headroom as h
S=ROOT/'results-selector-fresh-01'
work=Path(__file__).parent
spec=importlib.util.spec_from_file_location('discovery',work/'discover_selector_sources_20261021.py')
discovery=importlib.util.module_from_spec(spec);spec.loader.exec_module(discovery)
policy={
 'created_utc':datetime.now(timezone.utc).isoformat(),
 'reason':'Commons rejects larger originals with HTTP 429 and asks clients to use smaller copies. Original batch stopped after ten completed file receipts. No fresh media decoded or scored.',
 'source_list_and_model_unchanged':True,
 'rule':'For every frozen source, prefer the lowest-bandwidth official audio/Opus derivative. For video with no audio-only derivative, use the lowest-bandwidth official VP9/Opus video derivative. If neither exists, retain the original only when <=25 MB. Otherwise exclude. Apply uniformly to all 40 files, not only failed originals.',
 'provenance':'Original source title, size and SHA-1 must still match the original freeze. Derivative URLs and codec metadata are frozen before downloading derivatives. Commons exposes no derivative reference checksum here: save actual byte count/SHA-256 and HTTP ETag as local receipts, not a claim of verification against an external checksum.',
 'rate':'One request at a time; >=10 seconds between files. At most two attempts for each nominated derivative, 90 seconds after failure. Do not try other variants on failure.',
 'limits':'No changed endpoint, source substitution, extra source, tuning, crop selection or waveform-based eligibility. Original protocol and all original download receipts preserved. This is a documented acquisition deviation before any waveform inspection.'}

def main():
 assert not (S/'test').exists()
 assert not (S/'acquisition-amendment-01.json').exists()
 h.write_new(S/'acquisition-amendment-intent.json',policy)
 p=h.read(S/'protocol.json');metadata={}
 for start in range(0,len(p['sources']),10):
  data=discovery.get({'action':'query','titles':'|'.join(e['title'] for e in p['sources'][start:start+10]),
    'prop':'videoinfo','viprop':'url|derivatives|size|sha1'})
  h.write_new(S/f'derivatives-{start//10:02d}.json',data)
  for page in data['query']['pages']:
   if page.get('videoinfo'):metadata[page['title']]=page['videoinfo'][0]
  print('Derivative metadata',start+10,'/',len(p['sources']),flush=True)
  time.sleep(5)
 chosen=[]
 for e in p['sources']:
  i=metadata[e['title']]
  assert i['sha1']==e['sha1'] and i['size']==e['bytes'],e['title']
  derivatives=i.get('derivatives',[])
  audio=[d for d in derivatives if d.get('transcodekey') and d['type'].startswith('audio/') and 'opus' in d['type']]
  video=[d for d in derivatives if d.get('transcodekey') and 'vp9' in d['type'] and 'opus' in d['type']]
  options=audio or video
  if options:
   selected=min(options,key=lambda d:(d.get('bandwidth',float('inf')),d.get('height',0),d['src']))
   assert selected['src'].startswith('https://upload.wikimedia.org/wikipedia/commons/transcoded/')
   chosen.append({'id':e['id'],'kind':'official_derivative','url':selected['src'],'metadata':selected,
      'parent_title':e['title'],'parent_sha1':e['sha1'],'estimated_bytes':round(selected['bandwidth']*e['seconds_metadata']/8)})
  elif e['bytes']<=25000000:
   chosen.append({'id':e['id'],'kind':'original','url':e['url'],'parent_title':e['title'],
     'parent_sha1':e['sha1'],'expected_bytes':e['bytes'],'estimated_bytes':e['bytes']})
  else:
   chosen.append({'id':e['id'],'kind':'unavailable','reason':'No nominated small representation within the amended limit','estimated_bytes':0})
 amendment={**policy,'original_protocol_sha256':h.sha(S/'protocol.json'),'representations':chosen,
  'runner_sha256':h.sha(work/'download_selector_derivatives_20261021.py'),
  'estimated_total_bytes':sum(e['estimated_bytes'] for e in chosen),
  'original_batch_receipts':{f.name:h.sha(f) for f in sorted((S/'download').glob('fresh-*.json'))}}
 h.write_new(S/'acquisition-amendment-01.json',amendment)
 h.write_new(S/'acquisition-amendment-frozen.json',{'sha256':h.sha(S/'acquisition-amendment-01.json'),'before_fresh_decoding_and_scoring':True})
 print(json.dumps({'estimated_bytes':amendment['estimated_total_bytes'],
  'representations':{k:sum(e['kind']==k for e in chosen) for k in ('original','official_derivative','unavailable')}},indent=2))

if __name__=='__main__':main()
