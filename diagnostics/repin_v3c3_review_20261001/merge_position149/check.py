"""Geometry and six-call speed contract before the bounded autonomous test."""
import ast
import copy
import math
from pathlib import Path
from types import SimpleNamespace
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    from evaluation.controllers import lane_plant_runtime as lpr,physical_lane_groups as lanes,area_freeway_accounting as area
    from evaluation.controllers.freeway_fd import cell_state_response,state_response_coefficients
    from src.models.state import ControlAction
    assert not (HERE/'unit_result.json').exists()
    source=h.read(h.R/'spatial_context148/forecast/executed_function_sources.json')
    new=h.merge_position149_source(source)
    for value in new.values():ast.parse(value)
    def methods(code):return {n.name:ast.dump(n) for n in ast.parse(code).body[0].body if isinstance(n,ast.FunctionDef)}
    oldmethods=methods(source['RouteLaneRegion']);newmethods=methods(new['RouteLaneRegion'])
    same=[k for k in oldmethods if k.startswith('_split19')]
    assert all(oldmethods[k]==newmethods[k] for k in same)
    assert all(new[k]==v for k,v in source.items() if k not in ('RouteLaneRegion','rollout'))
    before={n.name:ast.dump(n) for n in ast.parse((HERE/'helper_before.py.txt').read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef)}
    after={n.name:ast.dump(n) for n in ast.parse(Path(h.__file__).read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef)}
    assert all(before[k]==after[k] for k in before if k!='validate_frozen132')
    assert set(after)-set(before)=={'merge_position149_source'}
    context,_,_=common.setup();manifest=h.R/'lane_state132/eval_01/manifest.json'
    cfg=lpr.load_sources(manifest)['component']._config('FW_E',context['parameters']['by_direction']['FW_E'])
    net=cfg.network;mn=area._mn;p=net.freeway_segment_params['FW_E'][23];response=cell_state_response(net,'FW_E',23)
    geometry=h.read(h.R/'flow_regime147/geometry_verification.json')
    for path,digest in geometry['pins'].items():assert h.sha(path)==digest,path
    lengths=[(geometry['native_chain_position_m']-7498.790500000001)/1000.,(7663.052375-geometry['native_chain_position_m'])/1000.]
    assert abs(sum(lengths)-p['segment_length_km'])<1e-9
    ns={};exec(compile(new['RouteLaneRegion'],'149_unit','exec'),lanes.__dict__,ns)
    obj=ns['RouteLaneRegion'].__new__(ns['RouteLaneRegion']);obj.road='FW_E';obj.groups=3
    obj.lengths=[x['segment_length_km'] for x in net.freeway_segment_params['FW_E']]
    obj.split23_lengths=lengths;obj.split23_n0=[[r*lengths[j] for r in densities] for j,densities in enumerate(((20.,30.,40.),(25.,35.,45.)))]
    obj.split23_oldv=[[20.,40.,60.],[25.,45.,65.]];obj.split23_exchange_v=copy.deepcopy(obj.split23_oldv)
    obj.split23_next=[[{'test':n} for n in row] for row in obj.split23_n0]
    obj.n0={24:[r*obj.lengths[24] for r in (20.,25.,30.)]};obj.oldv={22:[65.]*3};obj.merge={23:[.5,0.,0.]};obj.next_v={}
    command=max(cfg.freeway_follower.vsl_set);control=ControlAction(vsl={'FW_E':command})
    oldupdate=mn.metanet_speed_update_kmh;ctx=oldupdate.__globals__['_FW_SEG_CTX'];saved=copy.deepcopy(ctx);calls=[]
    delta=.4;kappa=10.
    def update(*args,**kwargs):
        snapshot=copy.deepcopy(ctx);value=oldupdate(*args,**kwargs)
        calls.append(dict(context=snapshot,value=value));return value
    try:
        mn.metanet_speed_update_kmh=update
        obj._split23_speed(SimpleNamespace(),cfg,control,mn,None,delta,kappa)
    finally:
        mn.metanet_speed_update_kmh=oldupdate;ctx.clear();ctx.update(saved)
    errors=[]
    for part in (0,1):
        for lane in range(3):
            call=calls[3*part+lane];length=lengths[part];rho=obj.split23_n0[part][lane]/length;v=obj.split23_oldv[part][lane]
            down=obj.split23_n0[1][lane]/lengths[1] if part==0 else obj.n0[24][lane]/obj.lengths[24]
            up=65. if part==0 else obj.split23_oldv[0][lane]
            target=p['v_free']*math.exp(-(rho/p['rho_crit'])**p['metanet_a_m']/p['metanet_a_m'])
            tau,nu=state_response_coefficients(response,v,target,rho,down,p['rho_crit'],p['metanet_tau_h'],p['metanet_nu_km2_h'])
            dt=cfg.simulation.T_f_h
            expected=max(net.v_min,v+dt/tau*(target-v)+dt/length*v*(up-v)-nu*dt/(tau*length)*(down-rho)/(rho+p['metanet_kappa_veh_km_lane']))
            if part==1:expected=max(net.v_min,expected-delta*obj.merge[23][lane]*v/(length*(rho+kappa)))
            errors.append(abs(obj.split23_next_v[part][lane]-expected))
            assert call['context']['armed']
            for key in ('v_free','rho_crit','metanet_a_m','metanet_tau_h','metanet_nu_km2_h'):
                assert call['context']['p'][key]==p[key],key
            assert abs(call['context']['p']['segment_length_km']-length)<1e-12
    assert len(calls)==6 and max(errors)<1e-8
    h.save(HERE/'proposed_sources.json',new)
    (HERE/'executed_helper.py.txt').write_bytes(Path(h.__file__).read_bytes())
    result=dict(lengths_km=lengths,merge_speed_loss_only_back=True,manual_speed_max_error=max(errors),speed_calls=6,
        unchanged_split19_methods=same,unchanged_helper_functions=len(before)-1,other_physical_sources_exact=True,
        helper_sha256=h.sha(h.__file__),geometry=geometry,unit_states='Synthetic below-jam states; interface check only,not a traffic gain claim.',
        source_sha256=h.sha(HERE/'proposed_sources.json'),hooks_restored=True)
    h.save(HERE/'unit_result.json',result)
    print('PASS',lengths,'speed_error',max(errors),'split19 preserved',len(same))


if __name__=='__main__':main()
