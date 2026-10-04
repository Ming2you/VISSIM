"""Saved short-probe assessment, not autonomous gain qualification."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
R=HERE.parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'


def read(p):return json.loads(p.read_text(encoding='utf-8'))


def main():
    assert not (HERE/'assessment.json').exists()
    assert read(HERE/'shared_probe_status.json')['phase']=='complete_pending_assessment'
    assert read(HERE/'shared_restoration.json')['core_inputs_STOP_unchanged']
    names={'baseline':'baseline2_junction121','branch_only':'conditional2_junction121','shared':'conditional_shared123'}
    arms=('release_actual','release_vsl90_actual')
    results={}
    for key,label in names.items():
        out=I/('closedloop_recorded2700_lever450_'+label)
        results[key]={arm:read(out/(arm+'.json')) for arm in arms}
    native=read(R/'s67_full_observation/analysis/summary.json')['arms']
    actual=native['release_vsl90']['TTT_2700p1_3150_veh_h']-native['release']['TTT_2700p1_3150_veh_h']
    gains={key:rows[arms[1]]['ttt_omega_veh_h']-rows[arms[0]]['ttt_omega_veh_h'] for key,rows in results.items()}
    checks=[]
    for arm in arms:
        a=results['baseline'][arm];b=results['shared'][arm]
        assert a['commands']==b['commands']
        assert a['executed_intervals'][0]['physical_cell_states'][0]==b['executed_intervals'][0]['physical_cell_states'][0]
        assert b['future_observation_inputs'] and not b['conditional_diagnostic']['autonomous']
        assert all(x['future_observation_inputs'] for x in b['executed_intervals'])
        residual=max(abs(x['max_cell_residual']) for x in b['offramp_route_inventory_checks'])
        assert residual<1e-7
        assert max(abs(x['residual']) for x in b['ramps'].values())<1e-7
        assert abs(sum(b['cost_by_stock'].values())-b['ttt_omega_veh_h'])<1e-7
        checks.append(dict(arm=arm,initial_and_commands_identical=True,max_class_stock_residual=residual))
    geo=read(I/'selected/port_gain/geometry.json')
    boundaries=[x for x in geo['boundaries'] if x['road']=='FW_E']
    ramps=[x for x in boundaries if x['kind']=='ramp'];off=[x for x in boundaries if x['kind']=='offramp']
    actual_flux=read(R/'s67_policy_response81/cell_flux82.json')
    rows=[];max_balance=0.
    for label,pair in results.items():
        for arm,pred in pair.items():
            for b in pred['executed_intervals']:
                flow=lambda source,target:sum(x['vehicles'] for x in b['transfers'] if x['source']==source and x['target']==target)
                merges={x['to_cell']:flow('merge_pending:'+x['id'],'freeway:FW_E') for x in ramps}
                stores={v['connector']:v['storage'] for v in b['offramps'].values()}
                exits={x['from_cell']:flow('freeway:FW_E','storage:'+stores[x['connector']]) for x in off}
                n0,n1=[x['vehicle_count']['FW_E'] for x in b['physical_cell_states']]
                q={30:flow('freeway:FW_E','external:terminal:FW_E')}
                for c in reversed(range(31)):q[c-1]=q[c]+n1[c]-n0[c]-merges.get(c,0.)+exits.get(c,0.)
                balance=abs(q[-1]-flow('origin:FW_E','freeway:FW_E'));max_balance=max(max_balance,balance)
                assert balance<1e-7 and min(q.values())>-1e-7
                native_case=arm.removesuffix('_actual')
                truth=next(x for x in actual_flux if x['case']==native_case and x['cell']==20 and x['start_sec']==b['start_sec'])
                rows.append(dict(version=label,arm=native_case,start_sec=b['start_sec'],end_sec=b['end_sec'],
                    through20=q[20],native_through20=truth['native_through'],exit10483=exits[20],
                    omega_ttt=b['ttt_omega_veh_h'],cell20_final_stock=n1[20]))
    sending=read(HERE/'shared_sending_witness.json')
    assert len(sending)==1800
    assert all(0<=x['after_through_vph']<=x['before_through_vph'] for x in sending)
    for arm in ('release','release_vsl90'):
        for caller in ('evaluation.controllers.lane_ramp_runtime','evaluation.controllers.area_freeway_accounting'):
            selected=[x for x in sending if x['arm']==arm and x['caller']==caller]
            assert [x['time_sec'] for x in selected]==list(range(2700,3150))
    costs={k:{v:pair[arms[1]]['cost_by_stock'][k]-pair[arms[0]]['cost_by_stock'][k] for v,pair in results.items()}
        for k in results['baseline'][arms[0]]['cost_by_stock']}
    protocol=read(HERE/'shared_probe_protocol.json')
    for p,sha in protocol['core_and_input_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha
    output=dict(status='COMPLETE_FIXED_PARAMETER_CONDITIONAL_SHARED_LANE_TEST',
        actual_omega_delta_ttt_veh_h=actual,model_delta_ttt_veh_h=gains,
        incremental_gain_vs_branch_only_veh_h=gains['shared']-gains['branch_only'],
        fixed_parameter_response_error_reduction_percent=100*(abs(gains['baseline']-actual)-abs(gains['shared']-actual))/abs(gains['baseline']-actual),
        blocks=rows,cost_response=costs,verification=checks,whole_road_conservation_max= max_balance,
        physical_and_ramp_query_count=len(sending),new_forecasts=2,new_fits=0,new_native=0,
        autonomous=False,adopted=False,calibrated_performance_ceiling_claimed=False,
        next='Use the demonstrated shared discharge path when defining a current-state blockage model and a bounded joint calibration comparison; do not claim fixed-parameter residual rules out that combination.')
    (HERE/'assessment.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in output.items() if k not in ('cost_response','blocks')},ensure_ascii=False,indent=2))
    for start in (2700,2850,3000):
        delta={}
        for label in results:
            a,b=[next(x for x in rows if x['version']==label and x['arm']==arm and x['start_sec']==start) for arm in ('release','release_vsl90')]
            delta[label]={k:b[k]-a[k] for k in ('through20','native_through20','exit10483','omega_ttt')}
        print(start,json.dumps(delta))


if __name__=='__main__':main()
