import json,gzip,csv,math
from pathlib import Path
root=Path.cwd();cw=root/'diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/cellwise_calibration'
records=json.loads((cw/'additional_admission_s53.json').read_text(encoding='utf-8-sig'))['records']
data={}
for rec in records:
    truth=Path(rec['truth']);arm=rec['arm']
    def rows(name):
        with (truth/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
    cells={(round(float(x['time_s']),6),int(x['cell'])):x for x in rows('cells_30s.csv') if x['road']=='FW_E'}
    flows={(round(float(x['window_end_s']),6),int(x['cell'])):x for x in rows('flows_30s.csv') if x['road']=='FW_E'}
    data['actual',arm]=(cells,flows)
    for v,folder in [('prior',cw/'check53/prior'),('joint',cw/'check53/joint'),('expanded',cw/'freeway_first/expanded_seed53/expanded')]:
        with gzip.open(folder/(arm+'_prediction.json.gz'),'rt',encoding='utf8') as f:p=json.load(f)
        pc={(round(x['time_s'],6),x['cell']):x for x in p['cells']}
        pc.update({(2670.1,c):cells[2670.1,c] for c in range(31)})
        pf={(round(x['window_end_s'],6),x['cell']):x for x in p['flows']}
        data[v,arm]=(pc,pf)
times=[round(2670.1+30*j,6) for j in range(16)]
details=[]
for c in range(31):
    for v in ['actual','prior','joint','expanded']:
        row=dict(cell=c,version=v,arms={})
        for arm in ['hold','release','hold_vsl90','release_vsl90']:
            cells,flows=data[v,arm];vs=[float(cells[t,c]['v_kmh']) for t in times[1:]]
            row['arms'][arm]=dict(mean_speed=sum(vs)/15,low60_samples=sum(x<60 for x in vs),final_speed=vs[-1],
                speed=vs,stock=[float(cells[t,c]['n_veh']) for t in times],
                downstream=sum(float(flows[t,c]['downstream_crossings']) for t in times[1:]),
                off=sum(float(flows[t,c]['off_departures']) for t in times[1:]),
                merge=sum(float(flows[t,c]['ramp_merges']) for t in times[1:]))
        row['release_delta']={key:row['arms']['release'][key]-row['arms']['hold'][key] for key in ['mean_speed','low60_samples','downstream','off','merge']}
        details.append(row)
out=cw/'freeway_first/expanded_seed53/spatial.json'
out.write_text(json.dumps(dict(definition='30s snapshot speed; low60 is snapshot count, not exact congestion duration.',times=times,cells=details,new_rollouts=0),indent=2)+'\n',encoding='utf8')
print(json.dumps([{'cell':x['cell'],'version':x['version'],'hold_mean':x['arms']['hold']['mean_speed'],'release_mean':x['arms']['release']['mean_speed'],'delta':x['release_delta']} for x in details if x['cell'] in [9,10,11,12,18,19,20,21,22,23,24,25,30] and x['version'] in ['actual','expanded']],ensure_ascii=False))
