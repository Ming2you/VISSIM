import json, os, re, hashlib, subprocess
R='D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/'
CF='diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config.json'
def strings(x,p=''):
    if isinstance(x,dict):
        for k,v in x.items(): yield from strings(v,p+'/'+str(k))
    elif isinstance(x,list):
        for i,v in enumerate(x): yield from strings(v,p+'/'+str(i))
    elif isinstance(x,str): yield p,x
pat=re.compile(r'\.(json|csv|vbs|inpx|py|sig|txt|md)$',re.I)
seen={}; queue=[(CF,'ROOT')]
while queue:
    f,by=queue.pop(0)
    if f in seen: continue
    fp=R+f
    if not os.path.exists(fp): seen[f]={'exists':False,'by':by}; continue
    b=open(fp,'rb').read()
    info={'exists':True,'by':by,'sha8':hashlib.sha256(b).hexdigest()[:8],'pins64cf':b.count(b'64cf5f55'),'pins3de8':b.count(b'3de889f0'),'mentions_seed29':len(re.findall(rb'seed ?29|_s29|seed29',b))}
    seen[f]=info
    if f.endswith('.json'):
        try: d=json.loads(b)
        except Exception: continue
        for p,s in strings(d):
            s2=s.replace(chr(92),'/')
            if pat.search(s2) and not s2.startswith(('C:/','D:/','E:/')) and '/' in s2 and len(s2)<300:
                if os.path.exists(R+s2) and s2 not in seen: queue.append((s2,f+':'+p))
json.dump(seen,open('config_refs.json','w'),indent=1)
n=len(seen); pin=[k for k,v in seen.items() if v.get('pins64cf')]
print('files reached',n,'missing',sum(1 for v in seen.values() if not v['exists']),'pinning 64cf',len(pin),'pin 3de8',sum(1 for v in seen.values() if v.get('pins3de8')),'mention seed29',sum(1 for v in seen.values() if v.get('mentions_seed29')))
for k,v in seen.items(): print(v.get('pins64cf',0), v.get('mentions_seed29',0), k)
