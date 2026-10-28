import xml.etree.ElementTree as ET, hashlib, json, sys
V='D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx'
C='D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
def canon(e):
    return ET.tostring(e, encoding='unicode')
a=ET.parse(V).getroot(); b=ET.parse(C).getroot()
print('root', a.tag, a.attrib.get('version'), b.attrib.get('version'))
ca={c.tag:c for c in a}; cb={c.tag:c for c in b}
res={}
for tag in sorted(set(ca)|set(cb)):
    A=ca.get(tag); B=cb.get(tag)
    if A is None or B is None:
        print(f'{tag:40s} onlyV3c3={A is not None} only64cf={B is not None}'); continue
    ea=list(A); eb=list(B)
    def key(e,i):
        return e.get('no') or e.get('id') or e.get('key') or str(i)
    da={key(e,i):canon(e) for i,e in enumerate(ea)}; db={key(e,i):canon(e) for i,e in enumerate(eb)}
    same_all = canon(A)==canon(B)
    oa=set(da)-set(db); ob=set(db)-set(da)
    diff=[k for k in set(da)&set(db) if da[k]!=db[k]]
    res[tag]={'n_v3c3':len(ea),'n_64cf':len(eb),'only_v3c3':sorted(oa,key=lambda x:(len(x),x)),'only_64cf':sorted(ob,key=lambda x:(len(x),x)),'differ':sorted(diff,key=lambda x:(len(x),x)),'identical_bytes':same_all}
    print(f'{tag:40s} n={len(ea):5d}/{len(eb):5d} onlyV={len(oa):4d} onlyC={len(ob):4d} differ={len(diff):4d} identical={same_all}')
json.dump(res,open('inv.json','w'),indent=1)
