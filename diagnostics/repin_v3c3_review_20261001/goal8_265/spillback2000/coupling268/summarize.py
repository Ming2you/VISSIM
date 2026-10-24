"""Reuse completed scalar/AD summaries; no forecasts, FZP reads, or COM."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
F=Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
read=lambda p:json.loads(p.read_bytes())

def stocks(response,end):
    central=response['central_physical']
    vals=dict(zip(central['names'],central['values']))
    out={}
    prefix=f'physical/{end}/'
    for name,value in vals.items():
        if not name.startswith(prefix):continue
        parts=name[len(prefix):].split('/')
        if parts[0]=='storage' and parts[-1]=='upper':out['storage:'+parts[1]]=-value
        elif parts[0] in ('ramp_queue','urban_movement_queue') and parts[-1]=='lower':
            out[('ramp:' if parts[0]=='ramp_queue' else 'movement:')+parts[1]]=-value
    return out

def comparison(folder,at):
    rows=read(folder/'continuous450.json')
    selected,released=[r['response'] for r in rows]
    protocol=read(folder/'audit_protocol.json')
    if 'stock_support' not in protocol:
        current=read(HERE/f'response{at}'/'audit_protocol.json')
        assert protocol['at']==current['at'] and protocol['local_stock_keys']==current['local_stock_keys']
        protocol['stock_support']=current['stock_support']
    observed=read(F/f'state_{at+150:06}.json')['vehicle_records']['full_network_link_counts']
    future_assignment=read(F/f'action_{at+150:06}.json')['projection_diagnostics']['physical_stock_assignment_by_link']
    predicted=stocks(selected,at+150)
    alternate=stocks(released,at+150)
    local={}
    for link,keys in protocol['local_stock_keys'].items():
        support=sorted(set(p for key in keys for p in protocol['stock_support'][key]))
        local[link]=dict(model_stocks=keys,physical_support=support,
            native_same_stock_projection_veh=sum(parts.get(k,0.) for parts in future_assignment.values() for k in keys),
            native_initial_support_full_link_veh=sum(observed.get(p,0) for p in support),
            selected_veh=sum(predicted[k] for k in keys),
            release_veh=sum(alternate[k] for k in keys),
            delta_cost_veh_h=sum(released['diagnostic_stock_costs_veh_h'][k]-selected['diagnostic_stock_costs_veh_h'][k] for k in keys))
    return dict(start_sec=at,end_sec=at+450,
        selected_cost=selected['objective_veh_h'],release_cost=released['objective_veh_h'],
        delta_veh_h=released['objective_veh_h']-selected['objective_veh_h'],
        model_valid=[r['model_feasible'] for r in rows],caps=[r['shared_constraints'] for r in rows],
        costs_partition_residual=[r['response']['sdmpc_omega_partition']['residual_veh_h'] for r in rows],
        initial_native_applied_first150_only=local,
        scope='Observed next150 and its recorded stock assignment are validation-only, never forecast inputs. A model storage may span parts of multiple links; full-link counts on its initial support are context only, not the matching stock target. Later native commands differ; release is a model counterfactual, not a VISSIM result.')

result={'comparisons':[],'native_runs':0,'horizon_sec':450,'terminal_cost':'unchanged OFF'}
for at in (2400,3300):
    result['comparisons'].append(comparison(HERE/f'response{at}',at))
    local=HERE/f'lane{at}'/'completion.json'
    if local.exists() and read(local).get('status')=='complete':
        result.setdefault('local_lane_comparisons',[]).append(comparison(local.parent,at))
    ad=HERE/f'ad{at}'/'meter_derivative.json'
    if at==2400:ad=HERE/'ad2400_v2/meter_derivative.json'
    if ad.exists():result.setdefault('derivative',{})[str(at)]=read(ad)
result['baseline3300']=comparison(HERE.parent/'four_causes3300',3300)
(HERE/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
for row in result['comparisons']:
    print(row['start_sec'],row['delta_veh_h'],row['initial_native_applied_first150_only'])
