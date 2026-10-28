import json
A=json.load(open('D:/VISSIM-merge/sim3-n31-k8/diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/v3c3_nc_20261001/observations/s31_v3c3nc_observations/geometry.json',encoding='utf-8'))
B=json.load(open('D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json',encoding='utf-8'))
def flat(x,p=''):
    out={}
    if isinstance(x,dict):
        for k,v in x.items(): out.update(flat(v,p+'/'+str(k)))
    elif isinstance(x,list):
        for i,v in enumerate(x): out.update(flat(v,p+'/'+str(i)))
    else: out[p]=x
    return out
print('keys A',list(A.keys())); print('keys B',list(B.keys()))
fa,fb=flat(A),flat(B)
d=[k for k in sorted(set(fa)|set(fb)) if fa.get(k)!=fb.get(k)]
print('leaves',len(fa),len(fb),'diff',len(d))
import collections
c=collections.Counter('/'.join(k.split('/')[:3]) for k in d)
for k,v in c.most_common(40): print('  ',v,k)
for k in d[:60]: print(k,'| v3c3=',str(fa.get(k))[:80],'| 64cf=',str(fb.get(k))[:80])
