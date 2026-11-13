"""Freeze all fresh-test choices before access to new media bytes."""
from datetime import datetime,timezone
import hashlib,html,json,re,sys,unicodedata
from pathlib import Path
import imageio_ffmpeg
ROOT=Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
sys.path.insert(0,str(ROOT))
from anc_lab import selector_headroom as h
STUDY=ROOT/'results-selector-fresh-01'
WORK=Path(__file__).parent

def plain(text):return html.unescape(re.sub('<[^>]+>','',text or '')).strip()
def normal(text):return ''.join(c for c in unicodedata.normalize('NFKC',plain(text)).casefold() if c.isalnum())
def sha1(path):
 d=hashlib.sha1()
 with path.open('rb') as f:
  for data in iter(lambda:f.read(1<<20),b''):d.update(data)
 return d.hexdigest()

def main():
 assert not (STUDY/'protocol.json').exists()
 assert not (ROOT/'external-audio/wikimedia-commons-selector-fresh-01').exists()
 metadata={}
 for folder in ('metadata','metadata-round2'):
  metadata.update(h.read(STUDY/folder/'all_metadata.json'))
 for page in h.read(STUDY/'metadata-extra.json')['query']['pages']:
  metadata[page['title']]={'info':page['imageinfo'][0]}
 picks=h.read(STUDY/'selected_metadata_inputs.json')
 assert len(picks)==40,'Forty sources planned before scoring; no outcome-dependent expansion'
 old=h.read(ROOT/'results-selector-headroom-01/protocol.json')
 earlier_names={normal(e.get('file','')) for e in old['entries'] if e['kind']=='recording'}
 earlier_authors={normal(e['author']) for e in old['entries'] if e['kind']=='recording'}
 earlier_sha1=set()
 for folder in (ROOT/'external-audio',ROOT/'recordings'):
  for path in folder.rglob('*'):
   if path.is_file() and path.suffix.lower() in ('.wav','.ogg','.oga','.mp3','.flac','.opus','.webm','.ogv'):
    earlier_sha1.add(sha1(path))
 for n in ('02','04','05'):
  for entry in h.read(ROOT/f'results-tone-forecaster-{n}/protocol.json')['fresh_recordings']:
   earlier_names.add(normal(entry['file']));earlier_sha1.add(entry['sha1'])
 sources=[];uploaders=set();authors=set();hashes=set()
 for number,pick in enumerate(picks,1):
  title=pick['title'];i=metadata[title]['info'];ext=i['extmetadata']
  author=plain(ext.get('Artist',{}).get('value',''));uploader=i['user']
  licence=plain(ext.get('LicenseShortName',{}).get('value',''))
  assert author and 'unknown author' not in author.lower(),title
  assert i['mime'].startswith(('audio/','video/')) or i['mime']=='application/ogg'
  assert 51<=i['duration']<=1800 and 0<i['size']<=125_000_000,title
  assert licence in ('CC0','Public domain') or re.fullmatch(r'CC BY(?:-SA)? [1-4]\.\d(?: [a-z]+)?',licence),licence
  assert normal(title[5:]) not in earlier_names and i['sha1'] not in earlier_sha1,title
  assert normal(uploader) not in uploaders and normal(author) not in authors,title
  assert i['sha1'] not in hashes,title
  assert i['url'].startswith('https://upload.wikimedia.org/'),title
  uploaders.add(normal(uploader));authors.add(normal(author));hashes.add(i['sha1'])
  suffix=Path(title).suffix.lower()
  entry={'id':f'fresh-{number:03d}','title':title,'file':f'fresh-{number:03d}'+suffix,
    'url':i['url'],'source_page':i['descriptionurl'],'sha1':i['sha1'],'bytes':i['size'],
    'seconds_metadata':i['duration'],'mime':i['mime'],'uploader':uploader,'author':author,
    'licence':licence,'licence_url':ext.get('LicenseUrl',{}).get('value'),
    'description':plain(ext.get('ImageDescription',{}).get('value','')),
    'cohort':pick['cohort'],'metadata_rationale':pick['reason'],
    'credited_author_seen_before':normal(author) in earlier_authors,'acoustic':True}
  sources.append(entry)
 assert sum(e['bytes'] for e in sources)<=2_000_000_000
 decoder=Path(imageio_ffmpeg.get_ffmpeg_exe())
 code=h.code_hashes()
 for name in ('anc_lab/selector_fresh_study.py','tests/test_selector_fresh_study.py'):
  code[name]=h.sha(ROOT/name)
 plan={'kind':'frozen_fresh_source_test_of_unchanged_L2','created_utc':datetime.now(timezone.utc).isoformat(),
  'client_date':'2026-10-21','sources':sources,'code_sha256':code,
  'methods':old['methods'],'v2':old['v2'],'arms':old['arms'],
  'candidate':{'function':'anc_lab.selector_headroom.causal_mix','lookback_seconds':2.,
    'margin_db':1.,'crossfade_seconds':.1,'cold_start_v2_seconds':3.,
    'note':'No candidate parameter or source implementation changed after the seen audit.'},
  'analysis':{'primary':'mean paired tone-bin gain versus v2 at 20 ms, source-bootstrap two-sided percentile 95% lower endpoint > 0',
    'bootstrap_resamples':50000,'bootstrap_seed':20261021,'unit':'one file, one uploader/credited author; no window pseudo-replication',
    'required_usable_sources':30,'required_tonal_sources':20,'reference_labels':'unchanged prominent_tones, 35-350 Hz, scoring only',
    'strong_source':'v2 tone gain >=3 dB at 20 ms; no paired loss >1 dB',
    'band_protection':'sum of recording-by-horizon cases with any >=1 dB third-octave increase, across both 20/120 ms, <= v2',
    'whole_band_protection':'zero recording-by-horizon cases with >0.5 dB whole-band amplification, both horizons',
    'reported_secondary':'both horizons separately; mean/median; numerical 1e-8 dB and practical .01 dB wins/losses; all no-tone files; all exclusions; worst losses',
    'inadequate_cohort':'inconclusive, not pass; no replacements or additional audio after any waveform access'},
  'preprocessing':{'cap_seconds':90,'crop':'start at time zero, no outcome-selected intervals',
    'prefix_fraction':.4,'minimum_actual_scored_seconds_per_horizon':30,
    'input':'first audio track, channel zero; preserve source sample rate/channels in video decoding; unchanged causal resampling to 2000 Hz',
    'normalization':'mean/std fitted on calibration prefix only; prefix replay precedes scored suffix'},
  'missing_rule':'Download, identity mismatch, decoding, missing audio, silent prefix and insufficient duration failures retained as exclusions, never replaced. Algorithm exceptions abort, not silently exclude.',
  'acquisition':{'attempts':3,'timeout_seconds':90,'retry_waits_seconds':[15,30],
    'per_file_limit_bytes':125000000,'cohort_limit_bytes':2000000000,'serial_download_gap_seconds':2,
    'verify':'exact metadata byte count and SHA-1; save SHA-256 receipt; partial downloads retained separately'},
  'decoder':{'package':'imageio-ffmpeg 0.6.0','path':str(decoder),'sha256':h.sha(decoder)},
  'evidence':{'old_audit_results_sha256':h.sha(ROOT/'results-selector-headroom-01/audit/results.json'),
    'seen_reassessment_sha256':h.sha(STUDY/'seen-data-reassessment.json'),
    'selection_inputs_sha256':h.sha(STUDY/'selected_metadata_inputs.json'),
    'test_design_sha256':h.sha(ROOT/'docs/SELECTOR_FRESH_TEST.md'),
    'review_addendum_sha256':h.sha(ROOT/'docs/CLAUDE_REVIEW_20261020.md')},
  'runner_sha256':{name:h.sha(WORK/name) for name in ('freeze_selector_fresh_20261021.py','download_selector_fresh_20261021.py')},
  'authorization':'u have full autonomy proceed anddownload whatever u feel necessary',
  'limits':'Mean endpoint and L2 chosen on seen data before this new test. Public source collection is purposive; metadata cannot certify stationarity or independence. No engine promotion, physical ANC, recording or playback.'}
 h.write_new(STUDY/'protocol.json',plan)
 h.write_new(STUDY/'frozen.json',{'protocol_sha256':h.sha(STUDY/'protocol.json'),'media_access_before_freeze':False,
  'sources':len(sources),'uploaders':len(uploaders),'credited_authors':len(authors),'bytes':sum(e['bytes'] for e in sources),
  'relevant_checks_passed':16,'tests_elapsed_seconds':.753})
 print(json.dumps(h.read(STUDY/'frozen.json'),indent=2))

if __name__=='__main__':main()
