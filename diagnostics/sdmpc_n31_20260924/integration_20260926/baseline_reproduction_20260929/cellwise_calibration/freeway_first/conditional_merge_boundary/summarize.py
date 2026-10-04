import csv,gzip,json,hashlib
from pathlib import Path
OUT=Path(__file__).resolve().parent
CW=OUT.parent.parent
I=CW.parents[1]
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
s=load(OUT/'summary.json')
for p,digest in s['pins'].items():
    assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest,p
records=[r for r in load(CW/'data_catalog.json')['checked_records'] if r['case']=='s29_early']
t0=records[0]['cutoff'];times=[round(t0+30*j,6) for j in range(16)]
data={}
for r in records:
    arm=r['arm'];truth=Path(r['truth'])
    with (truth/'cells_30s.csv').open(encoding='utf-8-sig',newline='') as f:
        cells={(round(float(x['time_s']),6),int(x['cell'])):float(x['n_veh']) for x in csv.DictReader(f)
            if x['road']=='FW_E' and t0<=float(x['time_s'])<=times[-1]}
    with (truth/'flows_30s.csv').open(encoding='utf-8-sig',newline='') as f:
        flows={(round(float(x['window_end_s']),6),int(x['cell'])):
            {k:float(x[k if k!='terminal_exits' else 'terminal_exits_inferred'])
             for k in ('source_admissions','ramp_merges','off_departures','terminal_exits','downstream_crossings')}
            for x in csv.DictReader(f) if x['road']=='FW_E' and t0<float(x['window_end_s'])<=times[-1]}
    data['actual',arm]=cells,flows
    for version,filename in [('autonomous',f'saved_merge_parity_{arm}.json.gz'),('conditional',f'merge_{arm}.json.gz')]:
        with gzip.open(OUT/filename,'rt',encoding='utf-8') as f:p=json.load(f)
        pc={(round(x['time_s'],6),x['cell']):x['n_veh'] for x in p['cells']}
        pc.update({(t0,c):cells[t0,c] for c in range(31)})
        pf={(round(x['window_end_s'],6),x['cell']):x for x in p['flows']}
        data[version,arm]=pc,pf
results=[];max_mass=0
for version in ('actual','autonomous','conditional'):
    n0,f0=data[version,'none']
    for arm in ('vsl','rm','both'):
        n1,f1=data[version,arm];rows=[]
        terms={k:0. for k in ('source_admissions','ramp_merges','off_departures','terminal_exits')}
        for c in range(31):
            series=[];volume=0;ttt=0
            for a,b in zip(times,times[1:]):
                for ns,fs in ((n0,f0),(n1,f1)):
                    f=fs[b,c];incoming=f['source_admissions'] if c==0 else fs[b,c-1]['downstream_crossings']
                    residual=ns[b,c]-ns[a,c]-incoming-f['ramp_merges']+f['off_departures']+f['downstream_crossings']+f['terminal_exits']
                    max_mass=max(max_mass,abs(residual))
                ttt+=((n1[a,c]-n0[a,c])+(n1[b,c]-n0[b,c]))*(b-a)/7200
                delta=f1[b,c]['downstream_crossings']-f0[b,c]['downstream_crossings'];volume+=delta
                series.append(dict(time_s=b,delta_n=n1[b,c]-n0[b,c],cumulative_downstream_delta=volume))
                for k in terms:
                    terms[k]+=(f1[b,c][k]-f0[b,c][k])*(times[-1]-b+15)/3600*(1 if k in ('source_admissions','ramp_merges') else -1)
            rows.append(dict(cell=c,delta_ttt=ttt,delta_downstream_volume=volume,series=series))
        assert abs(sum(x['delta_ttt'] for x in rows)-sum(terms.values()))<1e-8
        results.append(dict(version=version,arm=arm,ttt=sum(x['delta_ttt'] for x in rows),signed_terms=terms,cells=rows))
assert max_mass<1e-8
result=dict(rows=results,max_cell_mass_error=max_mass,future_boundary_diagnostic_only=True,new_rollouts=0,
            artifacts_retained=8,numerical_rollouts_executed=9,
            failed_attempts=['run.log: index lookup failed before native-merge forecast',
                             'resume.log: first native-merge forecast completed but save failed on Windows path length; repeated once in resume2.log'],
            caveat='Accounting terms and conditional response are not independent causal effects. Fluid receiving-envelope excess is not proof of a native physical violation.')
(OUT/'spatial.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
for r in results:print(r['version'],r['arm'],r['ttt'],r['signed_terms'])
for version in ('autonomous','conditional'):
    a=next(r for r in results if r['version']=='actual' and r['arm']=='rm')
    p=next(r for r in results if r['version']==version and r['arm']=='rm')
    ranked=sorted(zip(a['cells'],p['cells']),key=lambda pair:abs(pair[0]['delta_downstream_volume']-pair[1]['delta_downstream_volume']),reverse=True)[:5]
    print('largest RM downstream-delta gaps',version,[(x['cell'],x['delta_downstream_volume'],y['delta_downstream_volume']) for x,y in ranked])
print('checks',max_mass,len(s['pins']))
