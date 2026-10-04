"""Assess matched interval diagnostics against already completed native evidence."""
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
pins={}
def read(path):
    raw=path.read_bytes();pins[str(path)]=hashlib.sha256(raw).hexdigest();return json.loads(raw)
def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')
assert not (HERE/'assessment.json').exists()
assert read(HERE/'run_status_selected.json')['stage']=='complete'
protocol=read(HERE/'protocol_selected.json')
for name,digest in protocol['source_pins'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
old_release=read(I/'closedloop_recorded2700_lever450_s67_service66_20261003_actuator_equivalent/summary.json')
old_selected=read(I/'closedloop_recorded2700_budget_check_selected_vsl13_s67_service66_selection77_access/summary.json')
paths={j['name']:Path(j['output']) for j in protocol['jobs']}
paths['release']=Path(protocol['completed_release_output'])
new_release=read(paths['release']/'summary.json');new_selected=read(paths['selected']/'summary.json')
assert set(new_release['results'])==set(old_release['results']) and set(new_selected['results'])==set(old_selected['results'])
parity=[]
for name,old in old_release['results'].items():
    new=new_release['results'][name]
    assert {k:v for k,v in old.items() if k!='wall_sec'}=={k:v for k,v in new.items() if k not in ('wall_sec','executed_intervals')},name
    parity.append(name)
for name,old in old_selected['results'].items():
    new=new_selected['results'][name]
    assert old['commands']==new['commands'] and old['surrogate']==new['surrogate'],name
    assert {k:v for k,v in old['execution'].items() if k!='wall_sec'}=={k:v for k,v in new['execution'].items() if k not in ('wall_sec','executed_intervals')},name
    parity.append(name)
native76=read(HERE.parent/'s67_full_observation/response_assessment76.json')
native80=read(HERE.parent/'s67_selected_vsl78/response_assessment80.json')
snap76=read(HERE.parent/'s67_full_observation/snapshot_errors76.json')
snap80=read(HERE.parent/'s67_selected_vsl78/observed_snapshots80.json')
actual={}
for row in snap76:actual[(row['arm'],row['time_sec'],row['cell'])]=(row['actual_stock'],row['actual_speed_kmh'])
for row in snap80:
    for c in row['east_cells']:actual[(row['arm'],row['time_sec'],c['cell'])]=(c['n'],c['speed_kmh'])
cases={name:(paths['release'],name+'_actual',new_release['results'][name+'_actual']) for name in ('release','release_vsl90')}
cases.update({name:(paths['selected'],name,new_selected['results'][name]['execution']) for name in ('selected','vsl90')})
rows=[];terms=[];components={};boundary=[]
for name,(folder,key,result) in cases.items():
    blocks=result['executed_intervals'];assert len(blocks)==3
    assert abs(sum(b['ttt_omega_veh_h'] for b in blocks)-result['ttt_omega_veh_h'])<1e-7
    costs={}
    for b in blocks:
        for stock,cost in b['cost_by_stock'].items():costs[stock]=costs.get(stock,0.)+cost
        end=b['physical_cell_states'][-1];sec=end['time_sec']
        for cell in range(31):
            n,v=actual[(name,sec,cell)]
            rows.append(dict(case=name,time_sec=sec,cell=cell,observed_stock=n,
                predicted_stock=end['vehicle_count']['FW_E'][cell],observed_speed_kmh=v,
                predicted_speed_kmh=end['speed_kmh']['FW_E'][cell]))
        for road in ('FW_E','FW_W'):
            flow=b['transfers']
            boundary.append(dict(case=name,start_sec=b['start_sec'],end_sec=b['end_sec'],road=road,
                source=sum(x['vehicles'] for x in flow if x['source']=='origin:'+road and x['target']=='freeway:'+road),
                off=sum(x['vehicles'] for x in flow if x['source']=='freeway:'+road and x['target'].startswith('storage:')),
                terminal=sum(x['vehicles'] for x in flow if x['source']=='freeway:'+road and x['target']=='external:terminal:'+road),
                predicted_ramps=b['ramps'],predicted_offramps=b['offramps']))
    components[name]={road:costs['freeway:'+road] for road in ('FW_E','FW_W')}
    components[name]['ramps']=sum(v for k,v in costs.items() if k.startswith('ramp:'))
    components[name]['other_omega']=result['ttt_omega_veh_h']-sum(components[name].values())
    trace_path=folder/(key.removesuffix('_actual')+'.terms.gz');pins[str(trace_path)]=hashlib.sha256(trace_path.read_bytes()).hexdigest()
    with gzip.open(trace_path,'rt',encoding='utf-8') as stream:trace=json.load(stream)
    assert len(trace)==4500
    for start in (2700,2850,3000):
        for cell in range(16,26):
            values=[r for r in trace if r['cell']==cell and start<=r['time_sec']<start+150]
            assert len(values)==150 and len({r['time_sec'] for r in values})==150
            terms.append(dict(case=name,start_sec=start,cell=cell,**{k:sum(r[k] for r in values)/150 for k in
                ('speed_before','rho','downstream_rho','desired','relaxation','convection','anticipation','lane_drop_raw','post_equation_change','tau_sec','nu')}))
delta={}
for policy,left,right,native in [('native_city_release','release','release_vsl90',native76['component_delta_veh_h']),
                               ('selected_city_rm','selected','vsl90',native80['actual_component_delta_veh_h'])]:
    delta[policy]={k:dict(actual=native[k]['actual'] if isinstance(native[k],dict) else native[k],
                         predicted=components[right][k]-components[left][k]) for k in components[left]}
report=dict(status='DIAGNOSTIC_REPLAY_EXACT_NOT_NEW_CALIBRATION',physical_result_parity=parity,
    component_delta=delta,predicted_components450=components,
    interpretation='Compare conditional policy effects; do not attribute combined city/RM changes to one lever. Speed-term post-equation change includes merge and any receiving/clipping effects.',
    successful_exact450_forecasts=5,surrogate450_forecasts=3,prior_attempt_exact_forecasts=3,
    exact_compute_sec=sum(r['wall_sec'] for r in new_release['results'].values())+sum(r['execution']['wall_sec'] for r in new_selected['results'].values()),
    new_native_runs=0,new_calibration=0,production_changes=0,blind_holdout=False,input_sha256=pins)
save(HERE/'interval_boundary_predictions.json',boundary);save(HERE/'cell_errors.json',rows)
save(HERE/'speed_terms_by_interval.json',terms);save(HERE/'assessment.json',report)
print(json.dumps({k:v for k,v in report.items() if k!='input_sha256'}))
