import xml.etree.ElementTree as ET, copy, json, hashlib
C='D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
cands={
 'userfixVer2(085a10c7)':'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx',
 'rampdsd_src(fcb349d3)':'rampdsd_src.inpx',
 'v2nc':'v2nc.inpx','v3bnc':'v3bnc.inpx',
 'v3cnc_s31':'D:/VISSIM_runs/20260927_v3c/s31_v3cnc/prepared/network/baseline_s31_v3cnc.inpx',
 'v3c1nc':'v3c1nc.inpx',
 'v3c2nc_s31':'D:/VISSIM_runs/20260930_v3c2/s31_v3c2nc/prepared/network/baseline_s31_v3c2nc.inpx',
 'v3c3nc':'D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx'}
def norm(e):
    e=copy.deepcopy(e)
    for x in e.iter():
        x.text=(x.text or '').strip() or None; x.tail=None
    return ET.tostring(e,encoding='unicode')
def load(p):
    r=ET.parse(p).getroot(); out={}
    for c in r:
        if c.tag in ('simulation','evaluation'): continue
        out[c.tag]={(e.get('no') or str(i)):norm(e) for i,e in enumerate(c)}
    return out
B=load(C)
summary={}
for name,p in cands.items():
    A=load(p); tot=0; parts={}
    for tag in sorted(set(A)|set(B)):
        da=A.get(tag,{}); db=B.get(tag,{})
        oa=set(da)-set(db); ob=set(db)-set(da); d=[k for k in set(da)&set(db) if da[k]!=db[k]]
        if oa or ob or d: parts[tag]=(len(oa),len(ob),len(d)); tot+=len(oa)+len(ob)+len(d)
    sha=hashlib.sha256(open(p,'rb').read()).hexdigest()[:8]
    summary[name]={'sha8':sha,'total_elem_diffs':tot,'parts':parts}
    print(f'{name:24s} sha={sha} total={tot:4d}', {k:v for k,v in parts.items()})
json.dump(summary,open('ancestry_distance.json','w'),indent=1)
