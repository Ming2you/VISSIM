import json, hashlib, os, sys
O='D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/scenario/'
C='D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/diagnostics/sdmpc_n31_20260924/integration_20260926/selected/scenario/'
def flat(x,p=''):
    out={}
    if isinstance(x,dict):
        for k,v in x.items(): out.update(flat(v,p+'/'+str(k)))
    elif isinstance(x,list):
        for i,v in enumerate(x): out.update(flat(v,p+'/'+str(i)))
    else: out[p]=x
    return out
res={}
for f in sorted(set(os.listdir(O))|set(os.listdir(C))):
    po,pc=O+f,C+f
    if not(os.path.exists(po) and os.path.exists(pc)): print('ONLY',f, os.path.exists(po), os.path.exists(pc)); continue
    bo,bc=open(po,'rb').read(),open(pc,'rb').read()
    if bo==bc: print(f'{f:60s} BYTE-EQUAL'); res[f]='equal'; continue
    if f.endswith('.json'):
        fo,fc=flat(json.loads(bo)),flat(json.loads(bc))
        keys=sorted(set(fo)|set(fc)); d=[k for k in keys if fo.get(k)!=fc.get(k)]
        print(f'{f:60s} DIFF {len(d)} leaves')
        for k in d[:8]: print('     ',k,'| ours=',str(fo.get(k))[:90],'| codex=',str(fc.get(k))[:90])
        res[f]=d
    else:
        print(f'{f:60s} DIFF (non-json) sizes {len(bo)} {len(bc)}')
        import difflib
        for l in list(difflib.unified_diff(bo.decode('utf-8','replace').splitlines(),bc.decode('utf-8','replace').splitlines(),lineterm='',n=0))[:30]: print('     ',l[:200])
json.dump(res,open('pack_diff.json','w'),indent=1)
