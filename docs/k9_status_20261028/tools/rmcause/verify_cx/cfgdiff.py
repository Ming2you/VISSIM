import json,sys
a=json.load(open('w264_cfg_git.json',encoding='utf-8'))['config_overrides']
b=json.load(open('ours_cfg.json',encoding='utf-8'))['config_overrides']
def flat(d,p=''):
    out={}
    if isinstance(d,dict):
        for k,v in d.items():
            out.update(flat(v,p+'/'+k))
    else:
        out[p]=d
    return out
fa=flat(a); fb=flat(b)
keys=sorted(set(fa)|set(fb))
n=0
for k in keys:
    va=fa.get(k,'<absent>'); vb=fb.get(k,'<absent>')
    if va!=vb:
        sa=json.dumps(va,ensure_ascii=False); sb=json.dumps(vb,ensure_ascii=False)
        if len(sa)>160: sa=sa[:160]+'...'
        if len(sb)>160: sb=sb[:160]+'...'
        n+=1
        print(f'{k}\n   W264={sa}\n   OURS={sb}')
print('ndiff',n,'of',len(keys))
