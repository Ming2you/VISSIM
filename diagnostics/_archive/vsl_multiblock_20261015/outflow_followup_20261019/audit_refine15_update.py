"""Reconstruct three saved middle-compartment updates; no rollout or fitting."""
import os
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import copy, hashlib, json, math, sys
from pathlib import Path

OUT=Path(__file__).resolve().parent
HERE=OUT.parent
ROOT=Path('D:/VISSIM_packages/vsl_multizone355_20261015')
PINS={}
def read(p):
    p=Path(p); b=p.read_bytes(); PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(b)

def main():
    dest=OUT/'refine15_update_audit.json'
    assert not dest.exists(), 'Reuse completed audit'
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    from evaluation.controllers import lane_plant_runtime as lpr, freeway_fd as fd
    from evaluation.controllers import area_freeway_accounting as area, vissim_stackelberg_adapter as adapter
    from src.models.state import ControlAction
    tuning=read(ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/vsl_schedules_20261015/config.json')
    ctx=lpr.load_sources(tuning['freeway']['lane_plant'])
    cfg=ctx['component']._config('FW_E',ctx['parameters']['by_direction']['FW_E'])
    net,mn=cfg.network,area._mn
    active=read(HERE/'cached_vsl_exposure_audit_v2/active_component_config.json')
    parent=read(HERE/'matched_off2250_v3/network.json')
    assert net.freeway_segment_params['FW_E']==active['parameters']
    heads=parent['freeway_vsl_zone_heads']['FW_E']
    net.freeway_vsl_zone_heads['FW_E']=heads
    net.freeway_vsl_zone_head_of_cell['FW_E']=active['head_of_physical_cell']
    net.freeway_vsl_zone_of_cell['FW_E']=[heads.index(h) for h in active['head_of_physical_cell']]
    net.freeway_vsl_zone_free=tuning['freeway']['vsl_zone_free']
    params=active['parameters'][15]; length=params['segment_length_km']/3
    adapter._FW_SEG_CTX_STATE['profile']={'FW_E':[4.]*len(active['parameters'])}
    action=ControlAction(vsl={'FW_E':110,**{f'FW_E__seg{h}':110 for h in heads}})
    initial=read(OUT/'refine15_candidate/initial_refinement.json')
    trace=read(OUT/'refine15_candidate/hold_subcells.json')
    previous=dict(time=2250,n=[sum(r.values()) for r in initial['routes']],speed=initial['speed'])
    rows=[]
    for following in trace[:3]:
        assert following['fraction90'][1]==0
        dt=following['time']-previous['time']
        v,up=previous['speed'][1],previous['speed'][0]
        rho,down=previous['n'][1]/(4*length),previous['n'][2]/(4*length)
        vsl=mn.segment_vsl(action,'FW_E',15,cfg,physical_length_km=length,segment_end=False)
        assert float(vsl)==110
        desired=mn.effective_desired_speed_kmh(rho,net.v_free,net.rho_crit,vsl,net.alpha_vsl,False,net.metanet_a_m,getattr(net,'vsl_fd_two_branch',False),net.rho_max,float(getattr(net,'rho_crit_two_branch',0.) or 0.))
        desired=fd.literature_desired_speed((getattr(net,'freeway_vsl_fd_response',{}) or {}).get('FW_E'),cfg,'FW_E',15,rho,desired,vsl,False)
        # Uniform110 exposure returns the same target (no tangent or mixing).
        nu0=mn.select_anticipation_nu(rho,net,vsl)
        armed=copy.deepcopy(adapter._FW_SEG_CTX)
        assert armed['armed'] and armed['dlam']==0
        tau,nu=fd.state_response_coefficients(fd.cell_state_response(net,'FW_E',15),v,desired,rho,down,armed['response_rho_crit'],params['metanet_tau_h'],nu0)
        relax=dt/3600/tau*(desired-v)
        conv=dt/3600/length*v*(up-v)
        anti=-nu*dt/3600/(tau*length)*(down-rho)/(rho+params['metanet_kappa_veh_km_lane'])
        unclipped=v+relax+conv+anti
        actual=mn.metanet_speed_update_kmh(v,up,rho,down,desired,dt/3600,length,net.metanet_tau_h,nu0,net.metanet_kappa_veh_km_lane,net.v_min)
        assert abs(actual-max(net.v_min,unclipped))<1e-7
        assert abs(actual-following['speed'][1])<1e-7, (actual,following['speed'][1])
        rows.append(dict(start_sec=previous['time'],end_sec=following['time'],dt_sec=dt,
            speed_kmh=v,upstream_speed_kmh=up,rho=rho,downstream_rho=down,desired_kmh=desired,
            tau_sec=tau*3600,nu_km2_h=nu,relaxation_delta_kmh=relax,convection_delta_kmh=conv,
            anticipation_delta_kmh=anti,unclipped_speed_kmh=unclipped,recorded_speed_kmh=actual,
            lower_bound_active=unclipped<net.v_min,advection_cfl=v*dt/3600/length,
            fixed_state_operator_sensitivity=dict(parent_length_unclipped_speed_kmh=v+relax+(conv+anti)/3,
                half_dt_unclipped_speed_kmh=v+(relax+conv+anti)/2)))
        previous=following
    for p in [Path(__file__),Path(fd.__file__),Path(area.__file__),Path(adapter.__file__),*map(Path,ctx['paths'].values())]:
        PINS[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    for p,h in PINS.items(): assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
    result=dict(status='three_saved_middle_subcell_updates_reproduced',parent_length_m=length*3000,subcell_length_m=length*1000,
        parent_parameters=params,state_response=fd.cell_state_response(net,'FW_E',15),rows=rows,
        new_forecasts=0,new_native=0,new_fits=0,production_edits=0,source_pins=PINS,
        interpretation='Uncalibrated spatial refinement failed; its model class was not falsified. The saved baseline transient activates the speed floor despite advection CFL below1. This does not by itself prove instability or identify parameter error as the sole cause.',
        limitations=['Frozen-state operator sensitivity is neither a consistent coarse-grid trajectory nor a recalibrated forecast.',
            'Smaller time steps and altered coefficients have not been integrated or independently validated.',
            'Conservation and advection CFL do not establish second-order speed stability or behavioral calibration.'])
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('status','parent_length_m','subcell_length_m','state_response','rows')},indent=2))

if __name__=='__main__': main()
