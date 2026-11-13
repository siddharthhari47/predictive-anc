"""Study 05: filter the Commons metadata (commons02.json) to plausible fresh test candidates. Metadata only.
Args: project path, metadata json."""
import json, re, sys, html
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
root = Path(sys.argv[1]); meta = json.load(open(sys.argv[2], encoding='utf-8'))
audio = root/'external-audio'
local = {p.name for p in audio.rglob('*') if p.is_file()}
credits = ' '.join(p.read_text(encoding='utf-8') for p in audio.rglob('SOURCES.md')).lower()
def plain(s): return html.unescape(re.sub('<[^>]+>', '', s or '')).strip()
FREE = ('cc0', 'public domain', 'cc by 4.0', 'cc by-sa 4.0', 'cc by 3.0', 'cc by-sa 3.0', 'cc by 2.0', 'cc by-sa 2.0', 'cc by 2.5', 'cc by-sa 2.5', 'pd')
rows = []
for t, m in meta.items():
    s, b = m.get('seconds') or 0, m.get('bytes') or 0
    lic = (m.get('licence') or '').lower()
    a = plain(m.get('author')); fname = t[5:].replace(' ', '_')
    if not (10 <= s <= 150) or b > 25e6 or not any(lic.startswith(f) for f in FREE): continue
    if fname in local: continue
    flag = 'AUTHOR-SEEN' if a and a.lower() in credits else ''
    rows.append((t, s, b, m.get('licence'), a, m.get('uploader'), flag, plain(m.get('description'))[:220], ','.join(m['found_by'])))
print(len(rows), 'pass length/licence/size/not-local')
for r in sorted(rows, key=lambda r: r[8]):
    print(f"{r[0]} | {r[1]:.1f}s | {r[2]/1e6:.2f}MB | {r[3]} | {r[4]} ({r[5]}) {r[6]}\n    {r[7]}\n    [{r[8]}]")
