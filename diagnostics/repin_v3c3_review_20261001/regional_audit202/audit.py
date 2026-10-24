"""Two150s read-only witnesses using the existing complete plant and actions."""
import copy
import gzip
import hashlib
import json
import math
import time
from pathlib import Path

HERE=Path(__file__).resolve().parent
R=HERE.parent
ROOT=HERE.parents[2]
def save(name,value):
    raw=json.dumps(value,indent=None if name.endswith('.gz') else 2,allow_nan=False).encode()
    (HERE/name).write_bytes(gzip.compress(raw) if name.endswith('.gz') else raw)

def run(captured,candidates,coord,output):
    from evaluation.controllers import physical_lane_groups as lanes,area_freeway_accounting as area
    from evaluation.controllers import sdmpc_sequence as sequence,vissim_stackelberg_adapter as adapter
    from evaluation.controllers.freeway_fd import state_response_coefficients
    from evaluation.controllers.area_meter_finalization import for_endpoint
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    from src.controllers import rollout_endpoint as endpoint
    assert list(candidates)==['release_actual','release_vsl90_actual']
    assert not (HERE/'summary.json').exists()
    state,cfg=captured['state'],captured['cfg']
    assert state.time_sec==2700
    previous=json.loads((R/'coupled_lane200/enabled_protocol.json').read_bytes())
    full=json.loads((Path(previous['output'])/'summary.json').read_bytes())
    source_pins={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in (ROOT/'evaluation/controllers').glob('*.py')}
    save('protocol.json',dict(previous_goal_turn='PROGRESS201 response localization',
        purpose='Distinguish regional speed equation and shared-lane flux clamp at first150; no changed physical law or calibration.',
        budget=dict(predictions150=2,fits=0,native=0,FZP=0),seed=73,start_sec=2700,
        native_observations_are_labels_only=True,source_sha256=source_pins,
        frozen_structure='148 regional19..25, deployedU7/service66 FD as200',
        previous_output=previous['output'],output=str(output),production_adopted=False))
    cls=lanes.RouteLaneRegion;speed=cls.speed;update=area._mn.metanet_speed_update_kmh
    active={};rows=[];formula_error=0.;speed_error=0.
    def observe_update(v,up,rho,down,target,dt,length,tau,nu,kappa,minimum):
        nonlocal formula_error
        ctx=copy.deepcopy(adapter._FW_SEG_CTX)
        result=update(v,up,rho,down,target,dt,length,tau,nu,kappa,minimum)
        if not active:return result
        assert ctx['armed']
        p=ctx['p'];length=p.get('segment_length_km',length);tau=p.get('metanet_tau_h',tau);kappa=p.get('metanet_kappa_veh_km_lane',kappa)
        tau,nu=state_response_coefficients(ctx.get('state_response',{}),v,target,rho,down,ctx['response_rho_crit'],tau,nu)
        relaxation=dt/max(tau,1e-9)*(target-v)
        convection=dt/max(length,1e-9)*v*(up-v)
        anticipation=-nu*dt/(max(tau,1e-9)*max(length,1e-9))*(down-rho)/max(rho+kappa,1e-9)
        drop=ctx['phi']*dt*ctx['dlam']*max(rho,0.)*v*v/(max(length,1e-9)*max(ctx['lanes'],1e-9)*max(p.get('rho_crit',ctx['rho_crit_link']),1e-9))
        expected=max(minimum,max(minimum,v+relaxation+convection+anticipation)-drop)
        formula_error=max(formula_error,abs(expected-result));assert abs(expected-result)<1e-8
        active['calls'].append(dict(speed_before=v,upstream_speed=up,rho=rho,downstream_rho=down,target=target,
            relaxation=relaxation,convection=convection,anticipation=anticipation,lane_drop=drop,
            speed_after_equation=result,length_km=length,tau_sec=tau*3600,nu=nu))
        return result
    def observe_speed(obj,i,s,kernel,control,mn,exposure,delta,kappa):
        nonlocal speed_error
        assert not active
        active.update(calls=[])
        try:
            result=speed(obj,i,s,kernel,control,mn,exposure,delta,kappa)
            calls=active['calls'];assert len(calls)==(6 if i==19 else 3)
            for j,row in enumerate(calls):
                row.update(time_sec=s.time_sec,cell=i,lane=j%3+1,part=j//3 if i==19 else None)
                if i!=19:
                    n=obj.n0[i][j];rho=n/obj.lengths[i]
                    merged=obj.merge[i][j]
                    merge_loss=delta*merged*obj.oldv[i][j]/(obj.lengths[i]*(rho+kappa)) if delta>0 and merged else 0.
                    offnames=[off for off in obj.off_requests if obj.off_access[off]==j and kernel.network.offramp_route_inventory['branches'][off]['source_cell']==i]
                    request=sum(obj.off_requests[o][j] for o in offnames);sent=sum(obj.off_sent[o][j] for o in offnames)
                    cap=(obj.outgoing[i][j]+sent)*obj.lengths[i]/(kernel.simulation.T_f_h*n) if request>sent+1e-9 and n else None
                    uncapped=row['speed_after_equation']-merge_loss
                    expected=max(kernel.network.v_min,min(uncapped,cap) if cap is not None else uncapped)
                    actual=obj.next_v[i][j];speed_error=max(speed_error,abs(expected-actual));assert abs(expected-actual)<1e-8
                    row.update(initial_n=n,merge_veh=merged,merge_speed_loss=merge_loss,
                        mainline_in_veh=obj.incoming[i][j],mainline_out_veh=obj.outgoing[i][j],
                        off_request_veh=request,off_accepted_veh=sent,shared_flux_speed_cap=cap,
                        speed_without_flux_cap=max(kernel.network.v_min,uncapped),speed_final=actual,
                        extra_speed_loss_by_flux_cap=max(kernel.network.v_min,uncapped)-actual)
                else:
                    row.update(initial_n=obj.split19_n0[j//3][j%3],speed_final=obj.split19_next_v[j//3][j%3])
                rows.append(row)
            return result
        finally:active.clear()
    area._mn.metanet_speed_update_kmh=observe_update;cls.speed=observe_speed
    results={}
    try:
        for name,action in candidates.items():
            rows.clear();coord.validate(action);started=time.perf_counter()
            # This diagnostic intentionally evaluates only block zero. Extract
            # it explicitly; do not silently truncate the three-block contract.
            first=for_endpoint(sequence.first_action(action),(),
                endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'))
            point=endpoint.evaluate_price_point(state,first,captured['forecast'][:1],(),
                endpoint.ObjectiveSpec(cfg,depth_override=1,box_walk=False,score_mode='raw'),capture_response=True)
            elapsed=time.perf_counter()-started
            assert not point.aborted and len(point.states)==1 and point.states[0].time_sec==2850
            interval=probe.first_interval_response(state,point,cfg)
            expected=full['results'][name]['executed_intervals'][0]
            checks={key:interval[key]==expected[key] for key in expected}
            assert all(checks.values()),checks
            region=point.states[-1]._route_lane_regions['FW_E'];region.assert_partition(point.states[-1])
            assert len(rows)==150*24
            save(name+'.json.gz',dict(terms=rows,lanes=region.rows,split19=region.split19_rows,
                receiving=region.receiving_rows,junction=region.junction_rows,interval=interval))
            results[name]=dict(wall_sec=elapsed,parity=checks,ttt_omega=point.ttt,
                scalar_calls=len(rows),lane_rows=len(region.rows),max_route_residual=region.max_residual)
            print(json.dumps(dict(arm=name,elapsed=elapsed,parity=True)),flush=True)
    finally:area._mn.metanet_speed_update_kmh=update;cls.speed=speed
    assert source_pins=={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'evaluation/controllers').glob('*.py')}
    save('summary.json',dict(status='TWO_PREFIX_AUDITS_COMPLETE',results=results,
        formula_error=formula_error,speed_error=speed_error,predictions150=2,optimizer_iterations=0,
        fits=0,new_native=0,FZP_reads=0,production_adopted=False,goal='ACTIVE_NOT_QUALIFIED'))
