"""Observe two unchanged 450s forecasts; no fitting, future native input or VISSIM."""
import ctypes
import gzip
import hashlib
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
I = HERE.parent
ROOT = I.parents[2]
ROUTED = '--route-inventory' in sys.argv
EARLY_RESET = '--reset-at-cell25' in sys.argv
assert not (ROUTED and EARLY_RESET), 'Test one structural difference at a time'
OUT = HERE/('vsl_reset_location_trace' if EARLY_RESET else 'vsl_route_inventory_trace' if ROUTED else 'vsl_response_trace')
BASE_TUNING = I/'baseline_reproduction_20260929/cellwise_calibration/coupled_expanded_joint/candidate_config.json'
TUNING = I/'route_coupled_20260930/candidate_config.json' if ROUTED else BASE_TUNING
OLD = Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
PRIOR = I/'closedloop_recorded2250_lever450_RM_C10484_trace10484_of2'
ARMS = ('held_actual','vsl_release')


def save(path, value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    OUT.mkdir(exist_ok=False)
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    from evaluation.controllers import obs150_contract as oc
    assert json.loads((HERE/'observer_replay_v3/summary.json').read_bytes())['stage']=='consumed_head_and_vsl_history_exact'
    def readonly(raw,derived):
        obs=raw[oc.RAW_STATE_KEY];path=oc.resolve(obs,oc.derived_path(obs['sim_sec']))
        assert path.read_bytes()==oc.derived_bytes(derived)
        return path
    oc.write_derived=readonly
    source=I/'probe_selected_arrival_path.py'
    spec=importlib.util.spec_from_file_location('vsl_trace_probe',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    original=module.probe_levers
    files=[Path(__file__),source,TUNING,HERE/'observer_replay_v3/summary.json',HERE/'analysis/summary.json',
        OLD/'state_002250.json',OLD/'action_002250.json',
        ROOT/'evaluation/controllers/area_freeway_accounting.py',ROOT/'evaluation/controllers/freeway_fd.py',
        ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',ROOT/'evaluation/controllers/lane_plant_runtime.py',
        Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')]
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    if ROUTED:
        base=json.loads(BASE_TUNING.read_bytes());candidate=json.loads(TUNING.read_bytes())
        contract=candidate['freeway'].pop('offramp_route_inventory')
        assert candidate==base, 'The only permitted change is existing route inventory'
        for p in (BASE_TUNING,ROOT/contract,I/'route_coupled_20260930/comparison.json'):
            pins[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    save(OUT/'protocol.json',dict(max_forecasts=2,arms=ARMS,optimizer_iterations=0,coefficient_fits=0,
        new_native_runs=0,future_observation_inputs=False,source_pins=pins,route_inventory=ROUTED,
        reset_at_cell25=EARLY_RESET,
        purpose=('Reset incoming FW_E vehicles at cell25 upstream boundary instead of26. Native reset is inside25: this is a location sensitivity probe, NOT exact native placement or a proven bound on TTT. Initial cohorts and all physical equations are unchanged.' if EARLY_RESET else
            'Existing route-inventory candidate, same onset2250 held/release commands and physical initial state. No coefficient selection or automatic adoption; prior seed43 wrong-sign result retained.' if ROUTED else
            'Trace desired speed, METANET terms, sending and receiving. Exact parity with previously saved autonomous outputs required. No coefficient selection.')))
    calls=[]
    def audited(captured,reference,output,**kwargs):
        from src.controllers import rollout_endpoint as ep
        from src.models import metanet as mn
        from evaluation.controllers import vissim_stackelberg_adapter as adapter
        from evaluation.controllers.freeway_fd import state_response_coefficients,cell_state_response,VSLExposure
        evaluate=ep.evaluate_price_point;speed_original=mn.metanet_speed_update_kmh
        advance_original=VSLExposure.advance
        reset_visits=[]
        def earlier_reset(exposure,old_n,new_n,internal,total_out,entry,ramps,commands):
            caller=sys._getframe(1).f_locals
            if caller.get('link')=='FW_E':
                assert len(old_n)==31 and 16 in exposure.signs
                assert float(commands[26])==110. and float(ramps[25])==0.
                if 26 in exposure.signs:
                    assert 25 not in exposure.signs
                    exposure.signs=frozenset((set(exposure.signs)-{26})|{25})
                    exposure.spec=dict(exposure.spec,sign_cells=sorted(exposure.signs))
                assert 25 in exposure.signs and 26 not in exposure.signs
                commands=list(commands);commands[25]=commands[26]
                reset_visits.append(dict(time=caller['state'].time_sec,accepted_into25=internal[24]))
            return advance_original(exposure,old_n,new_n,internal,total_out,entry,ramps,commands)
        if ROUTED:
            inv=captured['state'].offramp_route_inventory_state
            assert set(inv['cells'])=={'FW_E','FW_W'} and all(len(v)==31 for v in inv['cells'].values())
            save(OUT/'initial_route_inventory.json',inv)
        rows=[]
        def speed_observer(*args):
            c=sys._getframe(1).f_locals
            selected=c.get('link')=='FW_E' and 'rho_for_flow' in c
            context=dict(adapter._FW_SEG_CTX) if selected else None
            value=speed_original(*args)
            if not selected:return value
            assert context['armed']
            s,up,rho,down,desired,dt,length,tau,nu,kappa,vmin=args
            local=context['p'];cell=c['i'];net=c['net']
            tau=local.get('metanet_tau_h',tau);length=local.get('segment_length_km',length)
            kappa=local.get('metanet_kappa_veh_km_lane',kappa)
            tau,nu=state_response_coefficients(context.get('state_response',{}),s,desired,rho,down,
                context.get('response_rho_crit',context.get('rho_crit_link')),tau,nu)
            relax=dt/max(tau,1e-9)*(desired-s)
            conv=dt/max(length,1e-9)*s*(up-s)
            ant=-nu*dt/(max(tau,1e-9)*max(length,1e-9))*(down-rho)/max(rho+kappa,1e-9)
            raw=s+relax+conv+ant;base=max(vmin,raw)
            phi,dl=context.get('phi',0),context.get('dlam',0)
            rc=local.get('rho_crit',context.get('rho_crit_link'))
            drop=(-phi*dt*dl*max(rho,0)*s*s/(max(length,1e-9)*max(context['lanes'],1e-9)*max(rc,1e-9))
                  if phi and dl and phi>0 and dl>0 else 0.)
            assert abs(max(vmin,base+drop)-value)<1e-9,(cell,value,base,drop)
            ramp=c['ramp_in_by_link']['FW_E'][cell]
            delta=cell_state_response(net,'FW_E',cell).get('delta_merge',c['delta_m'])
            mk=(net.freeway_segment_params['FW_E'][cell]['metanet_kappa_veh_km_lane']
                if c['direction_params'] else net.metanet_kappa_veh_km_lane)
            merge=-delta*dt*ramp*s/(length*max(c['lanes_now'][cell],1e-9)*(rho+mk)) if delta>0 and ramp>0 else 0.
            after=max(vmin,value+merge);cap=c['boundary_speed_cap']
            final=max(vmin,cap) if cap is not None and after>cap else after
            p=net.freeway_segment_params['FW_E'][cell]
            vf=p.get('v_free',net.v_free);critical=p.get('rho_crit',net.rho_crit);shape=p.get('metanet_a_m',net.metanet_a_m)
            nominal=vf*math.exp(-(max(0.,rho)/critical)**shape/shape)
            last=cell==len(c['rhos'])-1
            accepted=c['terminal_out'] if last else c['q_inter'][cell]
            receiving=None if last else c['receiving_for_mainline'][cell+1]
            exposure=c['exposure']
            rows.append(dict(time=c['state'].time_sec,cell=cell,stock=c['vehicles'][cell],rho=rho,speed=s,
                next_stock=c['vehicle_new'],final_speed=final,upstream_speed=up,downstream_rho=down,
                displayed=float(c['vsl_i']),nominal_fd_speed=nominal,desired=desired,critical=critical,
                cohorts=None if exposure is None else dict(exposure.cohorts[cell]),
                tau_sec=tau*3600,nu=nu,relaxation=relax,convection=conv,anticipation=ant,
                lane_drop=value-base,base_clip=base-raw,merge=after-value,boundary_cap=final-after,
                q_raw=rho*s*c['lanes_now'][cell],q_values=c['q_values'][cell],
                mainline_sending=c['mainline_sending'][cell],downstream_receiving=receiving,
                mainline_out=accepted,q_in=c['q_in'],q_out=c['q_out'],ramp=ramp,
                off_out=c['effective_off_total'],entry=c['core_in0'] if cell==0 else 0.,
                rho_max=net.rho_max,lanes=c['lanes_now'][cell],length=length,dt_h=dt))
            return value
        def bounded(*args,**kw):
            assert len(calls)<2,'Finite forecast budget exhausted'
            arm=ARMS[len(calls)];rows.clear()
            point=evaluate(*args,**kw)
            assert len(rows)==450*31,(arm,len(rows))
            if not (ROUTED or EARLY_RESET):
                assert abs(point.ttt-json.loads((PRIOR/(arm+'.json')).read_bytes())['ttt_omega_veh_h'])<1e-9
            with gzip.open(OUT/(arm+'.json.gz'),'wt',encoding='utf-8') as stream:
                json.dump(rows,stream,allow_nan=False)
            calls.append(dict(arm=arm,ttt=point.ttt,rows=len(rows)))
            return point
        ep.evaluate_price_point=bounded;mn.metanet_speed_update_kmh=speed_observer
        if EARLY_RESET:VSLExposure.advance=earlier_reset
        try:
            original(captured,reference,output,**dict(kwargs,onset_factorial=True,
                candidate_names=ARMS,first_interval_audit=True))
        finally:
            ep.evaluate_price_point=evaluate;mn.metanet_speed_update_kmh=speed_original
            VSLExposure.advance=advance_original
        checks=[]
        for arm in ARMS:
            now=json.loads((output/(arm+'.json')).read_bytes());prior=json.loads((PRIOR/(arm+'.json')).read_bytes())
            if EARLY_RESET:
                assert now['commands']==prior['commands']
                assert now['physical_cell_states'][0]==prior['physical_cell_states'][0]
                with gzip.open(HERE/'vsl_response_trace'/(arm+'.json.gz'),'rt',encoding='utf-8') as stream:
                    baseline=json.load(stream)
                with gzip.open(OUT/(arm+'.json.gz'),'rt',encoding='utf-8') as stream:
                    current=json.load(stream)
                assert current[:31]==baseline[:31], 'First update must preserve physical and latent initial states'
                checks.append(dict(arm=arm,commands_and_initial_states_exact=True,first31_rows_exact=True))
            elif ROUTED:
                assert now['commands']==prior['commands']
                assert now['physical_cell_states'][0]==prior['physical_cell_states'][0]
                assert len(now['offramp_route_inventory_checks'])==6
                assert max(r['max_cell_residual'] for r in now['offramp_route_inventory_checks'])<1e-7
                checks.append(dict(arm=arm,commands_and_initial_states_exact=True,
                    maximum_route_partition_residual=max(r['max_cell_residual'] for r in now['offramp_route_inventory_checks'])))
            else:
                for key in prior:
                    if key=='wall_sec':continue
                    assert now[key]==prior[key],(arm,key)
                checks.append(dict(arm=arm,prior_fields_exact_except_wall=True))
        save(OUT/'results_location.json',dict(output=str(output),checks=checks))
        if EARLY_RESET:
            assert len(reset_visits)==900
            save(OUT/'reset_visits.json',reset_visits)
    module.probe_levers=audited
    sys.argv=[str(source),'--closedloop-recorded','--at=2250','--lever-probe450',
        '--meter-ramp=RM_C10484','--trace-ramp=RM_C10484','--warm-head-history','--replay-vsl-history',
        '--recording-dir='+str(OLD),'--tuning-json='+str(TUNING),
        '--probe-label='+('vsl_reset25_20261001' if EARLY_RESET else 'vsl_route2_20261001' if ROUTED else 'vsl_terms2_20261001')]
    start=time.perf_counter();module.main()
    assert len(calls)==2
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in pins.items())
    save(OUT/'completion.json',dict(stage='two_reset_location_forecasts_traced' if EARLY_RESET else 'two_route_inventory_forecasts_traced' if ROUTED else 'two_unchanged_forecasts_traced',calls=calls,wall_sec=time.perf_counter()-start,
        source_pins_unchanged=True,optimizer_iterations=0,coefficient_fits=0,new_native_runs=0))


if __name__=='__main__':main()
