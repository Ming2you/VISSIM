import json
a=json.load(open('w264_cfg_git.json',encoding='utf-8'))
b=json.load(open('ours_cfg.json',encoding='utf-8'))
def flat(d,p=''):
    out={}
    if isinstance(d,dict):
        if not d: out[p]={}
        for k,v in d.items(): out.update(flat(v,p+'/'+k))
    else: out[p]=d
    return out
fa=flat(a); fb=flat(b)
keys=sorted(set(fa)|set(fb))
n=0
for k in keys:
    if k.startswith('/notes') or k.startswith('/description') or '_note' in k: continue
    va=fa.get(k,'<absent>'); vb=fb.get(k,'<absent>')
    if va!=vb:
        sa=json.dumps(va,ensure_ascii=False); sb=json.dumps(vb,ensure_ascii=False)
        n+=1
        print(f'{k}\n   W264={sa[:220]}\n   OURS={sb[:220]}')
print('ndiff',n,'of',len(keys))
