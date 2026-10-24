"""Actual speed-method consistency fixtures and unchanged finite rollout gates."""
from pathlib import Path
from types import SimpleNamespace as NS
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def unit():
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    common.setup()
    from evaluation.controllers import physical_lane_groups as lanes
    from src.models import metanet as mn
    classes={}
    for name,path in [('before',h.R/'transport_once179'),('after',HERE)]:
        source=h.read(path/'executed_function_sources.json')['RouteLaneRegion']
        ns={};exec(compile(source,'181_'+name,'exec'),lanes.__dict__,ns)
        classes[name]=ns['RouteLaneRegion']
    rows=[]
    for name,s,slow_moment,moment,target,command in [('equilibrium',2.,0.,400.,40.,110.),
            ('relax',2.,0.,400.,60.,110.),('vsl_cap',2.,0.,400.,90.,90.),
            ('all_moving',0.,0.,400.,60.,110.),('all_stopped',10.,0.,0.,40.,110.),
            ('lower_moment_bound',2.,4.,400.,.1,110.)]:
        values={};details={}
        for mode,cls in classes.items():
            obj=cls.__new__(cls);obj.road='FW_E';obj.lengths=[.2]*31
            obj.n0={20:[10.],21:[10.]};obj.oldv={20:[moment/10],19:[40.]}
            obj.split19_oldv=[[40.],[40.]];obj.phase0={};obj.phase_events=[{}]
            obj.next={20:[{'test':10.}]};obj.next_v={};obj.merge={20:[0.]}
            obj.off_requests={};obj.off_sent={};obj.off_access={}
            p=[s,slow_moment,moment];obj._phase_change=lambda *args:(p,10.)
            net=NS(v_free=110.,v_min=5.,rho_crit=40.,rho_max=140.,alpha_vsl=0.,
                   metanet_a_m=1.6,metanet_tau_h=12/3600,
                   metanet_kappa_veh_km_lane=5.,offramp_route_inventory={'branches':{}})
            cfg=NS(network=net,simulation=NS(T_f_h=1/3600),freeway_follower=NS(vsl_set=[50,60,70,80,90,100,110]))
            operator=NS(segment_vsl=lambda *a:command,effective_desired_speed_kmh=lambda *a:target,
                        select_anticipation_nu=lambda *a:0.,metanet_speed_update_kmh=mn.metanet_speed_update_kmh)
            values[mode]=obj.speed(20,NS(),cfg,None,operator,None,0.,5.)
            details[mode]=obj.phase_events[-1]
        initial=(slow_moment+moment)/10
        attainable=max(slow_moment/10,min(target,(slow_moment+(10-s)*(90. if command==90 else 110.))/10))
        expected=slow_moment/10 if s==10 else initial+(attainable-initial)/12
        assert abs(values['after']-expected)<1e-12,(name,values,expected)
        if name=='equilibrium':assert values['before']<40. and values['after']==40.
        if name=='all_moving':assert values['before']==values['after']
        if name=='vsl_cap':assert details['after']['moving_target']==90.
        rows.append(dict(case=name,observed=values,expected=expected,details=details))
    h.save(HERE/'unit.json',dict(status='pass',actual_speed_methods=True,canonical_speed_operator=True,
        isolated_fixed_phase_no_transport=True,rows=rows))
    return rows


def main():
    unit()
    assert h.read(HERE/'coefficients.json')==h.read(h.R/'queue_dynamics178/coefficients.json')
    assert all(h.read(HERE/'forecast/old179_parity.json').values())
    from diagnostics.repin_v3c3_review_20261001.queue_dynamics178 import verify,context
    verify.HERE=HERE;verify.main()
    context.HERE=HERE;context.main()
    checks=0;cap_count=0;maxerr=0.
    for p in (HERE/'forecast/queue').glob('*_phase.json.gz'):
        for e in h.read(p)['events']:
            m=e['moving_n'];n=e['n_next'];s=e['slow_moment'];cap=e['moving_cap']
            if not n or m<=1e-10:continue
            predicted=(s+m*e['moving_target'])/n
            desired=max(s/n,min(e['macro_target'],(s+m*cap)/n))
            err=abs(predicted-desired);maxerr=max(maxerr,err);assert err<1e-8
            cap_count+=int(e['moving_target']>=cap-1e-9);checks+=1
    h.save(HERE/'equilibrium_verification.json',dict(checked=checks,cap_bound=cap_count,max_error=maxerr))


if __name__=='__main__':
    import sys
    if '--unit' in sys.argv:print(unit())
    else:main()
