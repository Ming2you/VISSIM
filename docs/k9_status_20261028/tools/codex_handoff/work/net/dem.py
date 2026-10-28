import xml.etree.ElementTree as ET, csv, json
V='D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx'
C='D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
EV='D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/handoff/evidence/'
def vin(p):
    r=ET.parse(p).getroot(); out={}
    for vi in r.find('vehicleInputs'):
        rows=[]
        for t in vi.iter('timeIntervalVehVolume'):
            rows.append((int(t.get('timeInt').split()[1])/1000.0,float(t.get('volume')),t.get('vehComp'),t.get('volType'),t.get('cont')))
        out[vi.get('no')]=(vi.get('link'),rows)
    return out
A=vin(V);B=vin(C)
# check csv vs 64cf
rows=list(csv.DictReader(open(EV+'demand_34_inputs.csv',encoding='utf-8-sig')))
bad=0;n=0
for r in rows:
    n+=1
    link,ints=B[r['input']]
    m=[x for x in ints if abs(x[0]-float(r['start_s']))<1e-6]
    if r['link']!=link or not m or abs(m[0][1]-float(r['volume_veh_h']))>1e-6 or m[0][2]!=r['vehicle_composition']: bad+=1; print('MISMATCH',r)
print('csv rows',n,'mismatch vs 64cf',bad,'inputs in csv',len({r['input'] for r in rows}))
# totals per interval
starts=[0,900,1800,2700,3600,4500]
def tot(D,excl=()):
    t=[]
    for s in starts:
        t.append(sum([x[1] for k,(l,ints) in D.items() if k not in excl for x in ints if x[0]==s]))
    return t
tv=tot(A); tc=tot(B)
print('total v3c3',[round(x,1) for x in tv]); print('total 64cf',[round(x,1) for x in tc]); print('ratio',[round(c/v,3) for c,v in zip(tc,tv)])
print('1098 v3c3',[x[1] for x in A['1098'][1]],A['1098'][0]); print('1098 64cf',[x[1] for x in B['1098'][1]])
print('1099 v3c3',[x[1] for x in A['1099'][1]]); print('1099 64cf',[x[1] for x in B['1099'][1]])
print('1099/1098 64cf',[round(b[1]/a[1],6) for a,b in zip(B['1098'][1],B['1099'][1])])
print('1099 64cf/v3c3',[round(b[1]/a[1],3) for a,b in zip(A['1099'][1],B['1099'][1])])
# veh-h input total over 0-8100 (last interval extends) 
def cum(ints,T):
    s=0
    for i,(st,v,*_) in enumerate(ints):
        en=ints[i+1][0] if i+1<len(ints) else T
        s+=v*max(0,min(en,T)-st)/3600
    return s
for T in (8100,9000):
    print(T,'1099 veh v3c3',round(cum(A['1099'][1],T)),'64cf',round(cum(B['1099'][1],T)),'1098 64cf',round(cum(B['1098'][1],T)),'all v3c3',round(sum(cum(x[1],T) for x in A.values())),'all 64cf',round(sum(cum(x[1],T) for x in B.values())))
same=[k for k in A if A[k]==B[k]]
print('identical inputs',len(same),'differ',[k for k in A if A[k]!=B[k]])
print('links of inputs:',sorted((k,A[k][0]) for k in A)[:40])
