import json,sys
a=json.load(open('results-tuning-fresh-01/rooms-attempt-1.json',encoding='utf-8'));b=json.load(open('results-tuning-fresh-01/rooms.json',encoding='utf-8'))
B={s['source_id']:s for s in b['sources']}
same=[s['source_id'] for s in a['sources'] if s['status']=='built' and s['cases']==B[s['source_id']]['cases']]
print('rebuilt identical',len(same),'of',sum(s['status']=='built' for s in a['sources']))
for s in b['sources']:
    if s['status']!='built': print(s['source_id'],s['title'].encode('ascii','replace').decode()[:60],s.get('reason'))
