"""Completed offline responses and matching first150 native projection only."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'goal8_265/spillback2000/coupling268'
F=Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
read=lambda p:json.loads(p.read_bytes())
pins={}
scope_audit=read(HERE/'urban66_scope_audit.json')
scope_rows={r['start_sec']:r for r in scope_audit['rows']}

def stocks(response,end):
    out={};c=response['central_physical'];prefix=f'physical/{end}/'
    for name,value in zip(c['names'],c['values']):
        if not name.startswith(prefix):continue
        parts=name[len(prefix):].split('/')
        if parts[0]=='storage' and parts[-1]=='upper':out['storage:'+parts[1]]=-value
        elif parts[0] in ('ramp_queue','urban_movement_queue') and parts[-1]=='lower':
            out[('ramp:' if parts[0]=='ramp_queue' else 'movement:')+parts[1]]=-value
    return out

def one(folder,at):
    f=folder/'continuous450.json';raw=f.read_bytes();pins[str(f)]=hashlib.sha256(raw).hexdigest()
    rows=json.loads(raw);assert len(rows)==2
    s,r=[row['response'] for row in rows];p=read(folder/'audit_protocol.json')
    target_path=F/f'action_{at+150:06}.json'
    target=read(target_path)['projection_diagnostics']['physical_stock_assignment_by_link']
    initial=read(F/f'action_{at:06}.json')['projection_diagnostics']['physical_stock_assignment_by_link']
    keys_by_link=dict(p['local_stock_keys'])
    keys_by_link['66']=list(initial['66'])
    first_s,first_r=stocks(s,at+150),stocks(r,at+150)
    match={link:dict(predicted=sum(first_s[k] for k in keys),
                    release=sum(first_r[k] for k in keys),
                    observed=sum(parts.get(k,0.) for parts in target.values() for k in keys))
           for link,keys in keys_by_link.items()}
    # An initial assignment is not an exhaustive evolving physical footprint.
    # New gate transit appears on66 after initialization and is counted in TTT.
    old66=match['66']
    scope=scope_rows[at]
    if scope['status']=='complete_first150_footprint':
        transit=scope['omitted_gate_transit150']
        match['66']=dict(predicted=old66['predicted']+transit,
                        release=old66['release']+transit,observed=old66['observed'],
                        gate_transit_included=transit,footprint_complete=True,
                        superseded_partial_values=old66)
    else:
        match['66']=dict(predicted=None,release=None,observed=old66['observed'],
                        footprint_complete=False,superseded_partial_values=old66,
                        limitation='Gate transit missing: do not infer a model underprediction from these partial values.')
    delta={key:r['diagnostic_stock_costs_veh_h'].get(key,0.)-s['diagnostic_stock_costs_veh_h'].get(key,0.)
           for key in set(s['diagnostic_stock_costs_veh_h'])|set(r['diagnostic_stock_costs_veh_h'])}
    by_type={kind:sum(v for k,v in delta.items() if k.split(':')[0]==kind)
             for kind in sorted({k.split(':')[0] for k in delta})}
    assert abs(sum(by_type.values())-(r['objective_veh_h']-s['objective_veh_h']))<1e-7
    return dict(folder=str(folder),start_sec=at,seconds=[x['seconds'] for x in rows],
        omega_hold=s['objective_veh_h'],omega_release=r['objective_veh_h'],
        release_minus_hold=r['objective_veh_h']-s['objective_veh_h'],
        release_cost_delta_by_stock_kind=by_type,
        release_cost_delta_by_owner={k:r['sdmpc_omega_partition']['costs'][k]-v
                                    for k,v in s['sdmpc_omega_partition']['costs'].items()},
        predicted_merge=[x['control_area']['predicted_ramp_merge'] for x in (s,r)],
        model_valid=[x['model_feasible'] for x in rows],cap_feasible=[x['shared_constraints']['feasible'] for x in rows],
        cap_residuals=[{q:x['shared_constraints'][q]['residual'] for q in ('np','nuf')} for x in rows],
        same_stock_first150=match)

result=dict(scope='Matching first150 native stock projection only. Future frames are targets, not inputs. RM release is an offline counterfactual; no native gain claim.',comparisons=[])
for at,leaf in ((1800,'local1800'),(2400,'local2400_v2'),(3300,'local3300'),(4500,'local4500')):
    folder=HERE/leaf
    if not (folder/'audit_done.json').is_file():continue
    item={'candidate':one(folder,at)}
    old=OLD/f'lane{at}'
    if not (old/'continuous450.json').is_file():old=HERE/f'baseline{at}'
    if (old/'continuous450.json').is_file():item['baseline']=one(old,at)
    result['comparisons'].append(item)
result['source_pins']=pins
result['urban66_scope_audit_sha256']=hashlib.sha256((HERE/'urban66_scope_audit.json').read_bytes()).hexdigest()
(HERE/'response_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(result['comparisons'],ensure_ascii=False,indent=2))
