"""Read the completed450s caches once; no forecasts or native data scanning."""
import csv
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent
assert h.read(HERE/'status.json')['status']=='complete_macro_gate_failed'
arms=('release','release_vsl90')
rows=h.read(HERE/'training/rows.json')
base_rows=h.read(h.R/'lane_state132/autonomous_diagnostic/training/rows.json')
versions={}
times=[round(2670.1+30*j,6) for j in range(16)]
pins={}
for arm in arms:
    path=h.I/'heldout67_freeway_20260930/observations'/arm/'cells_30s.csv'
    pins[str(path)]=h.sha(path)
    with path.open(encoding='utf-8-sig',newline='') as f:
        native=[dict(time_s=float(x['time_s']),cell=int(x['cell']),n_veh=float(x['n_veh']))
                for x in csv.DictReader(f) if x['road']=='FW_E']
    path=path.parent/'flows_30s.csv';pins[str(path)]=h.sha(path)
    with path.open(encoding='utf-8-sig',newline='') as f:
        flows=[{k:(float(v) if k in ('cell','window_end_s','downstream_crossings','off_departures','ramp_merges') else v)
                for k,v in x.items()} for x in csv.DictReader(f) if x['road']=='FW_E']
    versions.setdefault('actual',{})[arm]=dict(cells=native,flows=flows)
    for label,folder in [('frozen132',h.R/'lane_state132/autonomous_diagnostic/training'),('accepted133',HERE/'training')]:
        path=folder/('s67_late_'+arm+'.json.gz');pins[str(path)]=h.sha(path)
        pred=h.read(path)
        pred['cells'] += [x for x in native if abs(x['time_s']-times[0])<1e-7]
        versions.setdefault(label,{})[arm]=pred

integrals={};discharge={}
for label,by_arm in versions.items():
    integrals[label]={};discharge[label]={}
    for arm,pred in by_arm.items():
        stocks={(round(x['time_s'],6),x['cell']):x['n_veh'] for x in pred['cells']}
        values=[];blocks=[]
        for j in range(3):
            window=times[j*5:(j+1)*5+1]
            values.append([sum((stocks[a,i]+stocks[b,i])*(b-a)/7200 for a,b in zip(window,window[1:])) for i in range(31)])
            flows=[x for x in pred['flows'] if window[0]+1e-7<x['window_end_s']<=window[-1]+1e-7]
            blocks.append({str(i):{k:sum(x[k] for x in flows if x['cell']==i)
                            for k in ('downstream_crossings','off_departures','ramp_merges')} for i in (19,20,21,22,23,24,25)})
        integrals[label][arm]=values;discharge[label][arm]=blocks
        source=base_rows if label=='frozen132' else rows
        record=next(x for x in source if x['case']=='s67_late' and x['arm']==arm)
        expected=record['actual' if label=='actual' else 'predicted']['mainline_ttt']
        assert abs(sum(sum(v) for v in values)-expected)<1e-8

delta={label:[[by_arm[arms[1]][j][i]-by_arm[arms[0]][j][i] for i in range(31)] for j in range(3)] for label,by_arm in integrals.items()}
totals={k:[sum(row[i] for row in vals) for i in range(31)] for k,vals in delta.items()}
ranking=sorted(range(31),key=lambda i:abs(totals['accepted133'][i]-totals['actual'][i]),reverse=True)
output=dict(scope='450s FW_E31 cell TTT; same30s trapezoid, original2670.1 stock. Not wholeOmega. 90 minus110 with RM release fixed.',
    cells=[dict(cell=i,actual=totals['actual'][i],frozen132=totals['frozen132'][i],accepted133=totals['accepted133'][i]) for i in ranking],
    delta150=delta,totals=totals,discharge150=discharge,source_sha256=pins,
    invariant='Every31cell integral equals the corresponding completed component mainlineTTT to1e-8.',new_forecasts=0,new_native=0,new_FZP=0)
h.save(HERE/'spatial_response.json',output)
print('Largest signed VSL cost-error contributions:',output['cells'][:8])
for label,both in discharge.items():
    print(label,'middle150 cell20 through/off',[(both[a][1]['20']['downstream_crossings'],both[a][1]['20']['off_departures']) for a in arms])
