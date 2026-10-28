# my own recount of A0 replay outputs vs record (no re-run): rows differing by kind, max |green|/|offset| diffs, meter diffs
import csv, io, json
REC='D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29'
A0='D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/out'
def rows(p): return list(csv.DictReader(io.StringIO(open(p,encoding='utf-8').read())))
out={}
for lab in ['base','env_hsw','spd_hsw','py31214_base','py31214_hsw']:
    for T in (900,2700,4950):
        t6=f'{T:06d}'; p=f'{A0}/{lab}/T{t6}/files/sdmpc/decisions_sdmpc31_sdmpc8100_s29/action_{t6}.csv'
        try: a=rows(p)
        except FileNotFoundError: continue
        b=rows(f'{REC}/action_{t6}.csv')
        if len(a)!=len(b): out[f'{lab}|{T}']='row count differs'; continue
        kinds={}; mg=0; mo=0; meters=[]; vsl=0; sc=set()
        for x,y in zip(a,b):
            if x==y: continue
            kinds[x['kind']]=kinds.get(x['kind'],0)+1
            for c in ('p1_green','p2_green','p3_green','p4_green'):
                if x[c] and y[c]: mg=max(mg,abs(float(x[c])-float(y[c])))
            if x['offset'] and y['offset']:
                d=abs(float(x['offset'])-float(y['offset'])); mo=max(mo,min(d,abs(d-0)))
            if x['kind']=='ramp_meter': meters.append((x['id'],x['green_sec'],y['green_sec'],x['rate_vph'],y['rate_vph']))
            if x['kind']=='vsl': vsl+=1
            if x['sc_no']: sc.add(x['sc_no'])
        out[f'{lab}|{T}']=dict(differing=sum(kinds.values()),kinds=kinds,max_green=round(mg,4),max_offset=round(mo,4),meters=meters,vsl_rows=vsl,scs=sorted(sc,key=int))
for k,v in out.items(): print(k,v)
json.dump(out,open('cmp_a0_outputs.json','w'),indent=1)
