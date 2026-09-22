"""Isolate the existing open-terminal option on the matched RM states.

Only the FW_E terminal boundary changes. No fitted capacity, native run,
future observation, actuator change or production adoption.
"""
from pathlib import Path
import hashlib
import json
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import matched_port_timing_response as p
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.ramp_lane_coupling_check import audit

K,e,m=p.K,p.e,p.m
OUT=K/'matched_outlet_response_v1'


def main():
    OUT.mkdir(exist_ok=False)
    sources=[Path(__file__),Path(p.__file__),p.OUT/'partition8_13.json',m.MODEL/'selected_parameters.json',
             e.CAL/'canonical_harness.py',e.ROOT/'evaluation/controllers/physical_lane_groups.py',
             e.ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py']
    params=e.load(m.MODEL/'selected_parameters.json')['parameters']
    results={};checks=0
    for seed in (23,33):
        gp=(m.BANK/'observations/rm8/geometry.json' if seed==23 else K/'matched_meter_midpoint_s33_v2/observations/rm8/geometry.json')
        model=e.load_base_model(e.load(gp),p.OUT/'partition8_13.json')
        original=model._config
        def configured(road,parameters):
            cfg=original(road,parameters)
            if road=='FW_E':cfg.network.terminal_zero_gradient=True
            return cfg
        model._config=configured
        cases={}
        for arm in ('rm8','rm6','rm_ramp'):
            wp=p.OUT/f'window_s{seed}_partition8_13_{arm}.json'
            bp=p.OUT/f'prediction_s{seed}_partition8_13_{arm}.json'
            window=e.load(wp);prediction=e.simulate(model,window,params);baseline=e.load(bp)
            proof=audit(prediction,baseline);checks+=proof['lane_interface_checks']
            assert all(r['continuity_residual_max_veh']<1e-7 and r['negative_density_count']==0
                       for r in prediction['diagnostics']['roads'])
            assert all(abs(r['conservation_residual_veh'])<1e-7 for r in prediction['ports']+prediction['ramps'])
            cases[arm]=dict(component=m.parts(prediction),interface=proof,
                terminal=sum(r['terminal_exits'] for r in prediction['flows'] if r['road']=='FW_E'),
                end_cell20=next(r for r in prediction['cells'] if r['road']=='FW_E' and r['cell']==20 and r['time_s']==3000),
                closed_terminal=sum(r['terminal_exits'] for r in baseline['flows'] if r['road']=='FW_E'))
            e.save(OUT/f'prediction_s{seed}_{arm}.json',prediction)
            sources.extend([wp,bp])
            print(json.dumps(dict(seed=seed,arm=arm,cost=cases[arm]['component'],terminal=cases[arm]['terminal'])),flush=True)
        for arm in ('rm6','rm_ramp'):
            delta={k:cases[arm]['component'][k]-cases['rm8']['component'][k] for k in ('mainline','on','off')}
            cases[arm]['delta_vs_g8']=dict(**delta,total=sum(delta.values()))
        results[str(seed)]=cases
        e.save(OUT/f'result_s{seed}.json',cases)
    e.save(OUT/'result.json',dict(qualified=False,production_adopted=False,future_inputs=False,
        fitted_parameters=0,new_native_runs=0,cases=results,exact_west_cases=6,lane_interface_checks=checks,
        change='Diagnostic instance FW_E network.terminal_zero_gradient=True. Removes fixed terminal flow cap and copies terminal density for the downstream speed boundary; internal/source/actuator laws and all inputs unchanged.',
        source_pins={f.relative_to(e.ROOT).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in sources}))


if __name__=='__main__':main()
