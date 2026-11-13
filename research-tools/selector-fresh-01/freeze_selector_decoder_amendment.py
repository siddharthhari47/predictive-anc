"""Record a metadata-dispatch correction before any fresh decoding or scoring."""
from datetime import datetime, timezone
from pathlib import Path
import sys
ROOT=Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
sys.path.insert(0,str(ROOT))
from anc_lab import selector_headroom as h
S=ROOT/'results-selector-fresh-01'
assert not (S/'test').exists()
p=h.read(S/'protocol.json')
name='anc_lab/selector_fresh_study.py'
original='results-selector-fresh-01/runner-before-decoder-fix.py'
assert h.sha(ROOT/original)==p['code_sha256'][name]
for path,digest in p['code_sha256'].items():
    if path!=name:assert h.sha(ROOT/path)==digest,path
a={'created_utc':datetime.now(timezone.utc).isoformat(),
   'original_protocol_sha256':h.sha(S/'protocol.json'),
   'acquisition_amendment_sha256':h.sha(S/'acquisition-amendment-01.json'),
   'before_fresh_decoding_and_scoring':True,
   'reason':'Code inspection found six frozen .ogv sources labelled application/ogg. The runner only recognized video/* MIME and would wrongly send video containers to the audio-only loader.',
   'change':'Route video MIME, .ogv/.webm/.mp4/.mkv containers or official video derivatives through the already frozen first-audio-track ffmpeg decoder. Ordinary audio keeps the original loader. Add explicit immutable amendment verification to the runner.',
   'scientific_invariants':'No source-list, candidate, comparator, normalization, resampling, crop, score, eligibility or decision-rule change. No fresh audio decoded, listened to or scored before this amendment.',
   'code_changes':{name:{'before_sha256':p['code_sha256'][name],'after_sha256':h.sha(ROOT/name),'preserved_original':original}},
   'added_tests_sha256':{'tests/test_selector_media_dispatch.py':h.sha(ROOT/'tests/test_selector_media_dispatch.py')},
   'validation':{'targeted_checks_passed':18,'elapsed_seconds':.510,'includes':'Existing causal selector invariants, seen-data score parity, study aggregation and two metadata-only dispatch cases'},
   'preparer_sha256':h.sha(Path(__file__))}
h.write_new(S/'decoder-amendment-02.json',a)
h.write_new(S/'decoder-amendment-frozen.json',{'sha256':h.sha(S/'decoder-amendment-02.json'),'before_fresh_decoding_and_scoring':True})
print(h.sha(S/'decoder-amendment-02.json'))
