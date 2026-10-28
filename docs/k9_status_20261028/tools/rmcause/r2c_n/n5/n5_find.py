import json,sys,os
D=r'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/decisions_sdmpc31_sdmpc9000_s29'
f=os.path.join(D,sys.argv[1])
o=json.load(open(f,encoding='utf-8'))
pats=sys.argv[2].split(',')
hits=[]
def walk(x,path,depth):
    if depth>12: return
    if isinstance(x,dict):
        for k,v in x.items():
            p=path+'/'+str(k)
            if any(s.lower() in str(k).lower() for s in pats):
                hits.append((p,type(v).__name__,len(json.dumps(v))))
            walk(v,p,depth+1)
    elif isinstance(x,list):
        for i,v in enumerate(x[:3]):
            walk(v,path+f'[{i}]',depth+1)
walk(o,'',0)
for h in hits[:200]: print(h)
md=o['metadata']
print('--- metadata keys by size')
for k,v in sorted(md.items(), key=lambda kv:-len(json.dumps(kv[1])))[:40]:
    print(k, type(v).__name__, len(json.dumps(v)))
