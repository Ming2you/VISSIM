"""Bounded post-run component and removal audit; no model evaluation or FZP scan."""
import csv
import hashlib
import json
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT))
from diagnostics.capture_native_runtime_errors import parse_bytes
OLD=ROOT.parent/'control-full-review/diagnostics'
pins={}
def read(path):
    data=path.read_bytes();pins[str(path)]=hashlib.sha256(data).hexdigest();return data
def load(path):return json.loads(read(path))
def rows(path):return list(csv.DictReader(read(path).decode('utf-8-sig').splitlines()))

target=HERE/'decomposition.json';assert not target.exists()
comparison=load(HERE/'comparison.json')
prediction=load(HERE.parent/'closedloop_recorded2250_lever450_gate_full_four_s43_v3/summary.json')
native_proof=load(OLD/'metanet_net_gain_goal_20260924/heldout43/native_summary.json')
result={}
for arm,key in [('nc','held_actual'),('rm','rm'),('vsl','vsl'),('both','both')]:
    folder=OLD/('dsd110_20260923/response_recalibration_20260924/gain_response/seed43/none' if arm=='nc'
        else f'metanet_net_gain_goal_20260924/heldout43/observations/{arm}')
    native={};data=rows(folder/'cells_30s.csv')
    for road in ('FW_E','FW_W'):
        snapshot={}
        for row in data:
            t=float(row['time_s'])
            if row['road']==road and 2250.1<=t<=2700.1:snapshot[t]=snapshot.get(t,0)+float(row['n_veh'])
        pairs=sorted(snapshot.items());assert len(pairs)==16
        native[road]=sum((a[1]+b[1])*(b[0]-a[0])*.5/3600 for a,b in zip(pairs,pairs[1:]))
    ports=[r for r in rows(folder/'ports_30s.csv') if r['kind']=='ramp'
           and float(r['window_start_s'])>=2250.1-1e-7 and float(r['window_end_s'])<=2700.1+1e-7]
    assert len(ports)==120
    native['eight_on_ramps']=sum((float(r['start_n_veh'])+float(r['end_n_veh']))*15/3600 for r in ports)
    costs=prediction['results'][key]['cost_by_stock']
    model={road:costs['freeway:'+road] for road in ('FW_E','FW_W')}
    model['eight_on_ramps']=sum(v for k,v in costs.items() if k.startswith('ramp:'))
    if arm=='nc':
        err_files=list(Path('D:/VISSIM_runs/20260924_bottleneck90_full_s43/none/run').glob('*.err'))
        assert err_files
        removals=[e for f in err_files for e in parse_bytes(read(f))['events'] if e['kind']=='lane_change_removal']
    else:removals=native_proof['arms'][arm]['removals']
    selected=[{k:r[k] for k in ('time_sec','vehicle_id','link')} for r in removals if 2250<=r['time_sec']<=2700.1]
    assert len({(r['vehicle_id'],r['time_sec']) for r in selected})==len(selected)
    result[arm]=dict(native_30s_veh_h=native,predicted_veh_h=model,removal_count=len(selected),removals=selected)
for arm,row in result.items():
    for kind in ('native_30s_veh_h','predicted_veh_h'):
        row['delta_'+kind]={k:v-result['nc'][kind][k] for k,v in row[kind].items()}
    row['removed_ids_differ_from_nc']=sorted({r['vehicle_id'] for r in row['removals']}^
                                           {r['vehicle_id'] for r in result['nc']['removals']})
read(Path(__file__))
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in pins.items())
target.write_text(json.dumps(dict(arms=result,source_pins=pins,phase_aware=True,
    limitations=['Native component TTT uses30s snapshots, unlike5s fullOmega; do not treat the residual as exact urban TTT.',
      'Removed vehicle counts differ, so identical network demand is not identical future microscopic traffic.',
      'RM/both have fewer deletions here; their lower TTT is not accompanied by a higher deletion count.',
      'No equivalent-window uninserted delay record; native full waiting-cost qualification remains incomplete.',
      'This decomposition localizes discrepancies and does not prove which dynamic term caused them.']),
    ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
print(json.dumps({a:{k:v for k,v in r.items() if k not in ('removals','removed_ids_differ_from_nc')} for a,r in result.items()}))
