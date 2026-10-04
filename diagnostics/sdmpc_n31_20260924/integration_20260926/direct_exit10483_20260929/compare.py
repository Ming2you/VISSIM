"""Compare completed destination-preservation forecasts against closed native evidence."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
I=HERE.parent
pins={}
def load(path):
    data=path.read_bytes();pins[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(data)

assert not (HERE/'comparison.json').exists()
native=load(I/'seed43_fullplant_20260929/comparison.json')
old=load(I/'closedloop_recorded2250_lever450_gate_full_four_s43_v3/summary.json')['results']
new=load(I/'closedloop_recorded2250_lever450_direct10483_enabled_s43/summary.json')['results']
rows=[]
for arm,key in [('nc','held_actual'),('rm','rm'),('vsl','vsl'),('both','both')]:
    assert old[key]['commands']==new[key]['commands']
    base=native['costs']['nc']['native_omega_veh_h']
    alias=new[key]['direct_exit_final_accounting']
    assert alias['plan'] is None
    assert abs(alias['received']-alias['departed']-sum(alias['cohorts'].values()))<1e-7
    rows.append(dict(arm=arm,native_delta=native['costs'][arm]['native_omega_veh_h']-base,
        before_delta=old[key]['ttt_omega_veh_h']-old['held_actual']['ttt_omega_veh_h'],
        after_delta=new[key]['ttt_omega_veh_h']-new['held_actual']['ttt_omega_veh_h'],
        native_omega=native['costs'][arm]['native_omega_veh_h'],
        before_omega=old[key]['ttt_omega_veh_h'],after_omega=new[key]['ttt_omega_veh_h'],
        direct10483_received=alias['received'],direct10483_free_exit=alias['departed'],
        direct10483_retained=sum(alias['cohorts'].values())))
ramps=[]
for r in native['ramps']:
    key='held_actual' if r['arm']=='nc' else r['arm']
    newer=new[key]['ramps'][r['ramp']]
    assert abs(newer['residual'])<1e-7
    ramps.append(dict(arm=r['arm'],ramp=r['ramp'],actual=r['actual'],before=r['predicted'],after=newer))
metrics=('arrival','merge','final_stock')
mae={version:{k:sum(abs(r[version][k]-r['actual'][k]) for r in ramps)/len(ramps) for k in metrics}
     for version in ('before','after')}
cross=load(I/'gate_entry_geometry_20260929/crossmodel_selected_comparison.json')
old47=load(I/'closedloop_recorded2700_select_check_gate_crossmodel_sc109_native_s47/summary.json')['results']
new47=load(I/'closedloop_recorded2700_select_check_direct10483_enabled_s47_v2/summary.json')['results']
for key in ('held_actual','selected'):
    assert old47[key]['commands']==new47[key]['commands']
rows47=[]
for r in cross['rows']:
    key='held_actual' if r['arm']=='hold' else 'selected'
    newer=new47[key]['ramps'][r['ramp']]
    assert abs(newer['residual'])<1e-7
    rows47.append(dict(arm=r['arm'],ramp=r['ramp'],actual={k:r['actual_'+k] for k in metrics},
        before={k:r['current_'+k] for k in metrics},after=newer))
mae47={version:{k:sum(abs(r[version][k]-r['actual'][k]) for r in rows47)/len(rows47) for k in metrics}
       for version in ('before','after')}
comparison47=dict(native_delta=cross['native_delta_omega_veh_h'],
    before_delta=cross['current_prediction_delta_omega_veh_h'],
    after_delta=new47['selected']['ttt_omega_veh_h']-new47['held_actual']['ttt_omega_veh_h'],
    native_total_with_uninserted_delta=cross['native_delta_total_including_uninserted_veh_h'],
    ramp_mae=mae47,ramps=rows47)
report=dict(seed43=dict(costs=rows,ramp_mae=mae,ramps=ramps),seed47=comparison47,
    new_prediction_count=6,default_parity_forecasts=4,coefficient_fit=False,new_native_runs=0,
    causal_forecasts=True,cohorts_are_existing_stock_labels=True,initial_destination_unknown=True,
    commands_unchanged=True,source_pins=pins,goal_complete=False)
(HERE/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
print(json.dumps(dict(seed43_cost=rows,seed43_mae=mae,seed47={k:v for k,v in comparison47.items() if k!='ramps'})))
