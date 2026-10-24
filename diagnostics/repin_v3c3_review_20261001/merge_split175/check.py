"""Bounded interface and conservation checks; no traffic forecasts or fit."""
import ast
import copy
import math
from pathlib import Path
from types import SimpleNamespace
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent


def main():
    assert not (HERE/'unit_result.json').exists(), 'Preserve completed checks'
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    from evaluation.controllers import lane_plant_runtime as lpr, physical_lane_groups as lanes, area_freeway_accounting as area
    from evaluation.controllers.freeway_fd import cell_state_response, state_response_coefficients
    from src.models.state import ControlAction

    source = h.read(HERE/'executed_function_sources.json')
    prior = h.read(h.R/'merge_target173/executed_function_sources.json')
    protocol = h.read(HERE/'protocol.json')
    pins = {str(Path(__file__)):h.sha(__file__), str(HERE/'executed_function_sources.json'):h.sha(HERE/'executed_function_sources.json')}
    for p,d in {**protocol['pins'], **protocol['protected_sha256'], protocol['STOP']['path']:protocol['STOP']['sha256']}.items():
        assert h.sha(p)==d,p
    for value in source.values():ast.parse(value)
    assert all(source[k]==v for k,v in prior.items() if k not in ('RouteLaneRegion','rollout'))
    context,_,_ = common.setup()
    manifest = h.R/'coupled_recovery153/candidate/manifest.json'
    pins[str(manifest)] = h.sha(manifest)
    cfg = lpr.load_sources(manifest)['component']._config('FW_E',context['parameters']['by_direction']['FW_E'])
    assert cfg.simulation.T_f_sec == 1, 'Preserve the existing one-second integrator'
    net = cfg.network
    mn = area._mn
    p = net.freeway_segment_params['FW_E'][10]
    response = cell_state_response(net,'FW_E',10)
    lengths = [0.1562058217847052,0.037846623687150895]
    assert abs(sum(lengths)-p['segment_length_km'])<1e-9
    namespace = {}
    exec(compile(source['RouteLaneRegion'],'175_unit','exec'),lanes.__dict__,namespace)
    cls = namespace['RouteLaneRegion']
    obj = cls.__new__(cls)
    obj.road='FW_E';obj.groups=4
    obj.lengths=[v['segment_length_km'] for v in net.freeway_segment_params['FW_E']]
    obj.split10_lengths=lengths
    obj.split10_n0=[[rho*lengths[j] for rho in densities] for j,densities in enumerate(((20,30,40,50),(25,35,45,55))) ]
    obj.split10_oldv=[[20.,30.,40.,50.],[25.,35.,45.,55.]]
    obj.split10_exchange_v=copy.deepcopy(obj.split10_oldv)
    obj.split10_next=[[{'test|through':n} for n in row] for row in obj.split10_n0]
    obj.n0={11:[rho*obj.lengths[11] for rho in (20.,25.,30.,35.)]}
    obj.merge={10:[.25,0.,0.,0.]};obj.next_v={}
    state=SimpleNamespace(freeway_speed={'FW_E':[65.]*31})
    control=ControlAction(vsl={'FW_E':max(cfg.freeway_follower.vsl_set)})
    original=mn.metanet_speed_update_kmh
    ctx=original.__globals__['_FW_SEG_CTX'];saved=copy.deepcopy(ctx);calls=[]
    def audit(*args,**kw):
        snapshot=copy.deepcopy(ctx);value=original(*args,**kw)
        calls.append(dict(context=snapshot,value=value));return value
    delta=.4;kappa=10.
    try:
        mn.metanet_speed_update_kmh=audit
        obj._split10_speed(state,cfg,control,mn,None,delta,kappa)
    finally:
        mn.metanet_speed_update_kmh=original;ctx.clear();ctx.update(saved)
    errors=[]
    for part in (0,1):
        for lane in range(4):
            call=calls[4*part+lane];length=lengths[part]
            rho=obj.split10_n0[part][lane]/length;v=obj.split10_oldv[part][lane]
            down=obj.split10_n0[1][lane]/lengths[1] if part==0 else obj.n0[11][lane]/obj.lengths[11]
            up=65. if part==0 else obj.split10_oldv[0][lane]
            target=p['v_free']*math.exp(-(rho/p['rho_crit'])**p['metanet_a_m']/p['metanet_a_m'])
            tau,nu=state_response_coefficients(response,v,target,rho,down,p['rho_crit'],p['metanet_tau_h'],p['metanet_nu_km2_h'])
            dt=cfg.simulation.T_f_h
            expected=max(net.v_min,v+dt/tau*(target-v)+dt/length*v*(up-v)-nu*dt/(tau*length)*(down-rho)/(rho+p['metanet_kappa_veh_km_lane']))
            if part:expected=max(net.v_min,expected-delta*obj.merge[10][lane]*v/(length*(rho+kappa)))
            errors.append(abs(obj.split10_next_v[part][lane]-expected))
            assert call['context']['armed']
            assert call['context']['state_response']==response
            for key in ('v_free','rho_crit','metanet_a_m','metanet_tau_h','metanet_nu_km2_h'):
                assert call['context']['p'][key]==p[key],key
            assert abs(call['context']['p']['segment_length_km']-length)<1e-12
    assert len(calls)==8 and max(errors)<1e-8
    # Check actual plan allocation with the rear full, and with room shared
    # between the accepted merge and conservative internal through movement.
    allocation=[]
    for full in (True,False):
        test=cls.__new__(cls)
        test.road='FW_E';test.groups=4;test.cells=[10,11];test.lengths=obj.lengths
        test.split10_lengths=lengths;test.rates=h.read(HERE/'spec.json')['exchange_rates_per_sec']
        test.receiving_cells=[10,11];test.receiving_rows=[];test.reciprocal_off=None
        test.off_access={'10682':0};test.ramp_access={'RM_C10639':0}
        test.inlet={'through':[.25]*4};test.junction_rows=[]
        key='unit|through'
        rear=[net.rho_max*lengths[1] if full else 1.]*4
        test.split10=[[{key:3.} for _ in range(4)],[{key:n} for n in rear]]
        test.split10_v=[[40.]*4,[20.]*4]
        test.stocks={10:[{key:3.+n} for n in rear],11:[{key:2.} for _ in range(4)]}
        test.v={10:[30.]*4,11:[30.]*4}
        local=copy.deepcopy(cfg)
        local.network.offramp_route_inventory={'merges':{'RM_C10639':{'cell':10,'route_weights':{'through':1.}}},
             'branches':{'10682':{'source_cell':11}}}
        state=SimpleNamespace(time_sec=0.,offramp_route_inventory_state={'cells':{'FW_E':{9:{key:20.}}}})
        mainline=[360.]*31;flows=[0.]*31;receiving=[7200.]*31
        budget=test._split10_budget(local,rear[0],lengths[1])
        merge=0. if full else min(.2,budget)
        old_total=sum(sum(r.values()) for rows in test.stocks.values() for r in rows)
        test.plan(state,local,mainline,{},flows,receiving,{'RM_C10639':merge/local.simulation.T_f_h},{'10682':1800.})
        new_total=sum(sum(r.values()) for rows in test.next.values() for r in rows)
        incoming=sum(test.incoming[10]);outgoing=sum(test.outgoing[11])
        assert abs(new_total-old_total-incoming-merge+outgoing)<1e-9
        for g in range(4):
            combined={}
            for part in test.split10_next:
                for k,n in part[g].items():combined[k]=combined.get(k,0.)+n
            assert all(abs(n-test.next[10][g].get(k,0.))<1e-9 for k,n in combined.items())
            assert sum(test.split10_inner[g].values())+test.merge[10][g]<=test.split10_backbudget[g]+1e-9
            assert all(n>=-1e-9 for part in test.split10_next for n in part[g].values())
        if full:
            assert budget==0 and all(not any(r.values()) for r in test.split10_inner)
        allocation.append(dict(full_rear=full,rear_budget=budget,accepted_merge=merge,
            internal_lane1=sum(test.split10_inner[0].values()),mass_error=new_total-old_total-incoming-merge+outgoing))
    for path,digest in {**pins,**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items():assert h.sha(path)==digest,path
    result=dict(status='pass',speed_calls=8,manual_speed_max_error=max(errors),lengths_km=lengths,
        allocation=allocation,source_sha256=h.sha(HERE/'executed_function_sources.json'),input_sha256=pins,
        protected_and_STOP_preserved=True,forecasts=0,fit=0,new_native=0,
        limits='Synthetic interfaces and plan balance only. Actual initial states, stability, autonomous gain are pending.')
    h.save(HERE/'unit_result.json',result)
    print('PASS',result,flush=True)


if __name__=='__main__':main()
