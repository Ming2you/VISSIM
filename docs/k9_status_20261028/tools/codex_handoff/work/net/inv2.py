import xml.etree.ElementTree as ET, json, copy
V='D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx'
C='D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
def norm(e):
    e=copy.deepcopy(e)
    for x in e.iter():
        x.text=(x.text or '').strip() or None; x.tail=None
    return ET.tostring(e,encoding='unicode')
a=ET.parse(V).getroot(); b=ET.parse(C).getroot()
ca={c.tag:c for c in a}; cb={c.tag:c for c in b}
res={}
for tag in sorted(set(ca)|set(cb)):
    A=ca.get(tag); B=cb.get(tag)
    ea=list(A); eb=list(B)
    key=lambda e,i: e.get('no') or str(i)
    da={key(e,i):norm(e) for i,e in enumerate(ea)}; db={key(e,i):norm(e) for i,e in enumerate(eb)}
    oa=set(da)-set(db); ob=set(db)-set(da); diff=[k for k in set(da)&set(db) if da[k]!=db[k]]
    if oa or ob or diff or A.attrib!=B.attrib:
        res[tag]={'n_v3c3':len(ea),'n_64cf':len(eb),'only_v3c3':sorted(oa,key=lambda x:(len(x),x)),'only_64cf':sorted(ob,key=lambda x:(len(x),x)),'differ':sorted(diff,key=lambda x:(len(x),x)),'attr_differ':A.attrib!=B.attrib}
        print(f'{tag:34s} n={len(ea):5d}/{len(eb):5d} onlyV={len(oa):4d} onlyC={len(ob):4d} differ={len(diff):4d} attr={A.attrib!=B.attrib}')
json.dump(res,open('inv2.json','w'),indent=1)
print('rest identical after whitespace normalization:', len(set(ca))-len(res))
