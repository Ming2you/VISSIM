import xml.etree.ElementTree as ET, json
V='D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx'
C='D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
a=ET.parse(V).getroot(); b=ET.parse(C).getroot()
inv=json.load(open('inv2.json'))['vehicleRoutingDecisionsStatic']
def dec(r):
    out={}
    for d in r.find('vehicleRoutingDecisionsStatic'):
        rs=[]
        for v in d.iter('vehicleRouteStatic'):
            rs.append((v.get('no'),v.get('destLink'),round(float(v.get('destPos')),2),v.get('relFlow')))
        out[d.get('no')]=dict(name=d.get('name'),link=d.get('link'),pos=round(float(d.get('pos')),2),cls=d.get('vehClasses'),tf=d.get('allVehTypes'),routes=rs,attrs={k:v for k,v in d.attrib.items() if k not in('no','name','link','pos')})
    return out
A=dec(a);B=dec(b)
out={'only_v3c3':{},'differ':{}}
for k in inv['only_v3c3']:
    print('ONLY v3c3',k,A[k]['name'],'link',A[k]['link'],'pos',A[k]['pos'],'routes',A[k]['routes']); out['only_v3c3'][k]=A[k]
for k in inv['differ']:
    x,y=A[k],B[k]
    ch=[]
    for f in ('name','link','pos','attrs'):
        if x[f]!=y[f]: ch.append(f)
    ra={r[0]:r[1:] for r in x['routes']}; rb={r[0]:r[1:] for r in y['routes']}
    rd=[]
    for no in sorted(set(ra)|set(rb),key=int):
        if ra.get(no)!=rb.get(no): rd.append((no,ra.get(no),rb.get(no)))
    print(f'DIFF {k} link {x["link"]}@{x["pos"]} name={x["name"]!r} fields={ch}')
    for r in rd: print('     route',r[0],'v3c3',r[1],'| 64cf',r[2])
    out['differ'][k]={'v3c3':x,'64cf':y,'fields':ch,'route_diffs':rd}
json.dump(out,open('routes_diff.json','w'),indent=1,ensure_ascii=False)
