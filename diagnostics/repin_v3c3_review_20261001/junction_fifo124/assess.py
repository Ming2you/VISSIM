"""Saved autonomous node experiment: audit conservation and response, no reruns."""
import ast
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace as NS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
D = HERE/'dynamic'


def read(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def save(name, data):
    (HERE/(name+'.json')).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def node_checks():
    """Actual executed class, finite supply: no exit bypass of a full shared lane."""
    from evaluation.controllers import physical_lane_groups as lanes
    namespace = dict(lanes.__dict__)
    exec(compile(read(D/'executed_function_sources.json')['RouteLaneRegion'], 'executed124', 'exec'), namespace)
    cls = namespace['RouteLaneRegion']
    records = []
    for room in (0., .5, 10.):
        for exit_capacity in (0., 3600.):
            outputs = []
            for reciprocal in (None, '10483'):
                obj = cls.__new__(cls)
                obj.road='FW_E'; obj.cells=[20,21]; obj.groups=3
                obj.lengths=[.1]*31; obj.rates=[[0.]*3 for _ in range(3)]
                obj.off_access={'10483':0}; obj.ramp_access={}; obj.receiving_cells=[]
                obj.reciprocal_off=reciprocal; obj.junction_rows=[]
                obj.stocks={20:[{'a|10483':1.,'a|terminal':9.},{'a|terminal':7.},{'a|terminal':5.}],
                            21:[{'a|terminal':18.-room},{},{}]}
                obj.v={20:[36.]*3,21:[36.]*3}; obj.inlet={}
                stock=[{} for _ in range(31)]
                for i,rows in obj.stocks.items():
                    for row in rows:
                        for key,n in row.items():stock[i][key]=stock[i].get(key,0.)+n
                state=NS(time_sec=0.,offramp_route_inventory_state={'cells':{'FW_E':stock}})
                cfg=NS(simulation=NS(T_f_h=1/3600),network=NS(rho_max=180.,offramp_route_inventory={
                    'branches':{'10483':{'source_cell':20}},'merges':{}}))
                mainline=[0.]*31; q=[0.]*30; req={}
                obj.plan(state,cfg,mainline,req,q,[36000.]*31,{}, {'10483':exit_capacity})
                initial=sum(sum(r.values()) for rows in obj.stocks.values() for r in rows)
                final=sum(sum(r.values()) for rows in obj.next.values() for r in rows)
                off=sum(obj.off_sent['10483'])
                assert abs(final-(initial-off-q[21]/3600))<1e-10
                assert all(n>=-1e-12 for rows in obj.next.values() for row in rows for n in row.values())
                assert all(sum(row.values())<=18.+1e-10 for rows in obj.next.values() for row in rows)
                outputs.append(dict(off=off,through=obj.outgoing[20],final=final))
            old,new=outputs
            assert old['through'][1:]==new['through'][1:]
            assert new['off']<=old['off']+1e-12
            if room==0:assert new['off']==0. and new['through'][0]==0.
            if room==10:assert old==new
            if exit_capacity==0:assert new['off']==0. and new['through'][0]==0.
            records.append(dict(room_veh=room,exit_capacity_vph=exit_capacity,old=old,new=new))
    return records


def main():
    protocol=read(HERE/'protocol.json'); summary=read(D/'summary.json')
    assert summary['completed']==8
    rows={r['version']:r for r in summary['rows']}
    assert all(not r['score']['invalid'] for r in rows.values())
    keys=('ttt','mainline_ttt','ramp_ttt','off_ttt','end_n','exits')
    native={k:rows['lanes_release_vsl90']['actual'][k]-rows['lanes_release']['actual'][k] for k in keys}
    responses={version:{k:rows[version+'_release_vsl90']['predicted'][k]-rows[version+'_release']['predicted'][k] for k in keys}
               for version in ('lanes','receiving','shared')}
    details={}
    for version in responses:
        for arm in ('release','release_vsl90'):
            label=version+'_'+arm; pred=read(D/(label+'.json.gz'))
            region=pred['diagnostics']['roads'][0]['joint_lane_region']
            assert region['route_marginal_max_error']<1e-7
            for r in region['junction_rows']:
                assert -1e-10<=r['off_accepted_veh']<=r['off_before_veh']+1e-10
                assert r['through_receiving_veh']>=-1e-10
            limited=[r for r in region['junction_rows'] if r['off_accepted_veh']<r['off_before_veh']-1e-9]
            lane_steps={(round(r['time_s'],4),r['cell'],r['lane']):r for r in region['rows']}
            budget_residuals=[]
            for receiving in region['receiving_rows']:
                step=lane_steps[(round(receiving['time_s']+1.,4),receiving['cell'],receiving['lane'])]
                budget_residuals.append(step['mainline_in_veh']+step['merge_veh']-receiving['accepted_budget_veh'])
            assert max(budget_residuals,default=0.)<1e-7
            flows={cell:[sum(r['downstream_crossings'] for r in pred['flows'] if r['cell']==cell
                and r['window_start_s']>=2670.1+150*j-1e-5 and r['window_end_s']<=2820.1+150*j+1e-5)
                for j in range(3)] for cell in (19,20,21)}
            details[label]=dict(route_partition_error=region['route_marginal_max_error'],
                receiving_overallocation_max_veh=max(0.,max(budget_residuals,default=0.)),
                physical_merges_in_lane_region_veh=sum(r['merge_veh'] for r in region['rows']),
                receiving_records=len(region['receiving_rows']),junction_records=len(region['junction_rows']),
                additional_off_restriction_steps=len(limited),off_demand_withheld=sum(r['off_before_veh']-r['off_accepted_veh'] for r in limited),
                through150_by_cell=flows,
                restriction_steps150=[sum(2670.1+150*j-1e-6<=r['time_s']<2820.1+150*j-1e-6 for r in limited) for j in range(3)],
                max_lane1_n={i:max(r['n_veh'] for r in region['rows'] if r['cell']==i and r['lane']==1) for i in (20,21)})
    node=node_checks()
    for path,h in protocol['protected_sha256'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h
    assert hashlib.sha256(Path(protocol['STOP']['path']).read_bytes()).hexdigest()==protocol['STOP']['sha256']
    functions={n.name:hashlib.sha256(ast.dump(n,include_attributes=False).encode()).hexdigest() for n in ast.parse((HERE.parent/'entry10682/audit.py').read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef)}
    preserved=[n for n in protocol['helper_functions_before'] if n!='run_lane_receiving107']
    assert all(functions[n]==protocol['helper_functions_before'][n] for n in preserved)
    parity=read(D/'disabled_parity.json');assert all(parity.values())
    result=dict(status='complete_fixed_coefficients_not_adopted',native_delta=native,predicted_deltas=responses,
        scope='FW_E31cells+four on/four off connectors; not wholeOmegaTTT orTTD',
        autonomous_no_future_state=True,fixed_coefficients_not_calibration_ceiling=True,
        details=details,node_checks=node,preserved_helpers=preserved,default_off_parity=parity,core_files_preserved=9,
        full_goal_complete=False,production_adopted=False,forecasts=8,new_native=0,new_fits=0,new_FZP=0,
        failure='First attempt stopped after3valid forecasts at tuple-vs-JSON-list comparison. Saved physicalfields exactlymatch107; fixed comparison, reused3results, computedremaining5 once. Failure/log preserved.',
        remaining='Lane states/recovery and reciprocalFIFO strength need dynamics-consistent limited calibration/validation; no conclusion about calibrated ceiling. Do not adopt a new restriction only because it has a plausible location.')
    save('assessment',result)
    save('completion',dict(status=result['status'],goal='ACTIVE_NOT_QUALIFIED',previous_goal_turn='NO_PROGRESS_user_clarification_only',current_goal_turn='PROGRESS_eight_valid_autonomous_forecasts_and_node_invariants',owned_session_exit_code=0))
    save('dynamic_status',dict(status=result['status'],completed=8,assessment='assessment.json'))
    print(json.dumps({k:result[k] for k in ('status','native_delta','predicted_deltas')},ensure_ascii=False,indent=2))
    print(json.dumps({k:{n:v[n] for n in ('additional_off_restriction_steps','off_demand_withheld','restriction_steps150')} for k,v in details.items() if k.startswith('shared')},indent=2))


if __name__=='__main__':main()
