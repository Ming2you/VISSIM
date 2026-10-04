"""Reproduce and repair split19's consumed cell-parameter context."""
import ast
import copy
import math
from pathlib import Path
from types import SimpleNamespace
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'unit_result.json').exists()
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    from evaluation.controllers import lane_plant_runtime as lpr,physical_lane_groups as lanes,area_freeway_accounting as area
    from evaluation.controllers.freeway_fd import cell_state_response,state_response_coefficients
    from src.models.state import ControlAction
    context,_,_=common.setup();manifest=h.R/'lane_state132/eval_01/manifest.json'
    cfg=lpr.load_sources(manifest)['component']._config('FW_E',context['parameters']['by_direction']['FW_E'])
    mn=area._mn;net=cfg.network;p=net.freeway_segment_params['FW_E'][19];spec=cell_state_response(net,'FW_E',19)
    sourcepath=h.R/'spatial_speed144/audit_repair/executed_function_sources.json';source=h.read(sourcepath);fixed=h.spatial_context148_source(source)
    protected=h.read(h.R/'flow_regime147/protocol.json')
    paths=[Path(__file__),HERE/'helper_before.py.txt',sourcepath,manifest,manifest.parent/'reference_config.json',
        h.ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',h.ROOT/'evaluation/controllers/freeway_fd.py',
        h.R/'upstream_worklog/07_fww_sc1001eb/fww-struct/P_PLANT.md',
        h.F/'joint_lane_region/executed_sources/physical_lane_groups.py']
    pins={str(x):h.sha(x) for x in paths}
    h.save(HERE/'protocol.json',dict(previous_goal_turn='PROGRESS:147 completed flow ledgers and23 interior source accounting.',
        change_of_plan='Before extending spatial transport to23, inspect existing144 subcell19 parameter binding. A consumed scalar context is armed only once for sixupdates, and physical_length is not passed.',
        budget=dict(unit_speed_calls=12,baseline450=1,candidate450=8,new_fits=0,new_native=0,new_FZP=0),
        expected='Each of6part/lane speed calls uses physical19 FD/response and half-cell length. Canonical wrapper resets armed context after each update.',
        exclusions='Synthetic valid states below jam used only for interface contract; no traffic performance claims from unit results. No changes to selected network,model coefficients,costs or commands.',
        prior_checked='Claude P_PLANT distinguishes armed cell context; earlier joint_lane_region implementation already uses physical_length_km per update.144 diagnostic implementation omitted those calls.',
        protected_sha256=protected['protected_sha256'],STOP=protected['STOP'],pins=pins))
    oldtarget=mn.effective_desired_speed_kmh;oldupdate=mn.metanet_speed_update_kmh
    ctx=oldupdate.__globals__['_FW_SEG_CTX'];saved_ctx=copy.deepcopy(ctx)
    half=p['segment_length_km']/2;control=ControlAction(vsl={'FW_E':max(cfg.freeway_follower.vsl_set)})
    state=SimpleNamespace(freeway_speed={'FW_E':[65.]*31})
    results={}
    try:
        for name,version in [('executed144',source),('corrected148',fixed)]:
            ns={};exec(compile(version['RouteLaneRegion'],name,'exec'),lanes.__dict__,ns)
            obj=ns['RouteLaneRegion'].__new__(ns['RouteLaneRegion'])
            obj.road='FW_E';obj.groups=3;obj.lengths=[x['segment_length_km'] for x in net.freeway_segment_params['FW_E']]
            obj.split19_n0=[[rho*half for rho in (20.,30.,40.)],[rho*half for rho in (25.,35.,45.)]]
            obj.split19_oldv=[[20.,40.,60.],[25.,45.,65.]];obj.split19_exchange_v=copy.deepcopy(obj.split19_oldv)
            obj.split19_next=[[{'test':n} for n in row] for row in obj.split19_n0]
            obj.n0={20:[rho*obj.lengths[20] for rho in (20.,25.,30.)]};obj.next_v={}
            target_rows=[];speed_rows=[]
            def target(*a,**kw):
                snapshot=copy.deepcopy(ctx);value=oldtarget(*a,**kw)
                target_rows.append(dict(context=snapshot,args=list(a),value=value));return value
            def update(*a,**kw):
                snapshot=copy.deepcopy(ctx);value=oldupdate(*a,**kw)
                speed_rows.append(dict(context=snapshot,args=list(a),value=value));return value
            mn.effective_desired_speed_kmh=target;mn.metanet_speed_update_kmh=update
            obj._split19_speed(state,cfg,control,mn,None)
            assert len(target_rows)==len(speed_rows)==6
            manual=[]
            for part in (0,1):
                for lane in range(3):
                    rho=obj.split19_n0[part][lane]/half;speed=obj.split19_oldv[part][lane]
                    down=obj.split19_n0[1][lane]/half if part==0 else obj.n0[20][lane]/obj.lengths[20]
                    up=65. if part==0 else obj.split19_oldv[0][lane]
                    desired=p['v_free']*math.exp(-(rho/p['rho_crit'])**p['metanet_a_m']/p['metanet_a_m'])
                    tau,nu=state_response_coefficients(spec,speed,desired,rho,down,p['rho_crit'],p['metanet_tau_h'],p['metanet_nu_km2_h'])
                    dt=cfg.simulation.T_f_h
                    velocity=max(net.v_min,speed+dt/tau*(desired-speed)+dt/half*speed*(up-speed)
                        -nu*dt/(tau*half)*(down-rho)/(rho+p['metanet_kappa_veh_km_lane']))
                    manual.append(dict(part=part,lane=lane+1,rho=rho,desired=desired,speed=velocity,tau_h=tau,nu=nu,length_km=half))
            results[name]=dict(targets=target_rows,updates=speed_rows,manual=manual,
                armed=[x['context']['armed'] for x in speed_rows],
                target_max_error=max(abs(a['value']-b['desired']) for a,b in zip(target_rows,manual)),
                speed_max_error=max(abs(a['value']-b['speed']) for a,b in zip(speed_rows,manual)))
        assert results['executed144']['armed']==[True,False,False,False,False,False]
        assert results['executed144']['updates'][0]['context']['p']['segment_length_km']==p['segment_length_km']
        assert results['executed144']['target_max_error']>1. and results['executed144']['speed_max_error']>1.
        assert all(results['corrected148']['armed'])
        assert all(x['context']['p']['segment_length_km']==half for x in results['corrected148']['updates'])
        assert results['corrected148']['target_max_error']<1e-8 and results['corrected148']['speed_max_error']<1e-8
    finally:
        mn.effective_desired_speed_kmh=oldtarget;mn.metanet_speed_update_kmh=oldupdate
        ctx.clear();ctx.update(saved_ctx)
    # Only one physical method changes; no flow or stock update can be altered here.
    before=ast.parse(source['RouteLaneRegion']).body[0];after=ast.parse(fixed['RouteLaneRegion']).body[0]
    aa={x.name:ast.dump(x,include_attributes=False) for x in before.body if isinstance(x,ast.FunctionDef)}
    bb={x.name:ast.dump(x,include_attributes=False) for x in after.body if isinstance(x,ast.FunctionDef)}
    assert aa.keys()==bb.keys() and all(aa[k]==bb[k] for k in aa if k!='_split19_speed')
    assert all(source[k]==fixed[k] for k in source if k!='RouteLaneRegion')
    for path,digest in {**pins,**protected['protected_sha256']}.items():assert h.sha(path)==digest,path
    assert h.sha(protected['STOP']['path'])==protected['STOP']['sha256']
    h.save(HERE/'unit_traces.json',results)
    h.save(HERE/'unit_result.json',dict(old_armed=results['executed144']['armed'],old_target_max_error=results['executed144']['target_max_error'],
        old_speed_max_error=results['executed144']['speed_max_error'],fixed_all_contexts_armed=all(results['corrected148']['armed']),
        fixed_manual_max_error=max(results['corrected148']['target_max_error'],results['corrected148']['speed_max_error']),
        fixed_physical_length=half,other_physical_methods_exact=len(aa)-1,other_physical_sources_exact=True,hooks_restored=True,
        input_sha256=pins,core=True,STOP=True))
    print({k:v for k,v in h.read(HERE/'unit_result.json').items() if k!='input_sha256'})


if __name__=='__main__':main()
