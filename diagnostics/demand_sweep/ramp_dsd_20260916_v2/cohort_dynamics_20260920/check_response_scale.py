"""Separate transport resolution from the calibrated physical response scale."""
from pathlib import Path
import hashlib
import json
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import target_acceleration_coupling as c

K,e,s=c.K,c.e,c.s
OUT=K/'physical_response_scale_v1'


def main():
    OUT.mkdir(exist_ok=False)
    gp=s.d.H/'controller_response_s23_v1/none/geometry.json'
    cp=K/'transport_step1_exchange_off_v2/config.json';pp=K/'port_travel_fit_v1/selected_parameters.json'
    ip=c.OUT/'initials.json';op=K/'compact_lane_state_v1/states.json'
    model=e.load_base_model(e.load(gp),cp);cfg=model._config('FW_E',e.load(pp)['parameters']['by_direction']['FW_E'])
    initials=e.load(ip);observed=e.load(op);exact=0;runs=[]
    for arm,starts in initials.items():
        for start,value in starts.items():
            start=int(start);inputs=value['inputs'];inputs['rates']={int(k):r for k,r in inputs['rates'].items()}
            baseline,_=s.rollout(inputs,cfg,30,momentum_advection=True)
            assert json.loads(json.dumps(baseline))==e.load(c.OUT/f'{arm}_{start}_base.json');exact+=1
            for response in ('transport','physical_cell'):
                # Preserve both full150s traces;30s is their exact prefix.
                trace,checks=s.rollout(inputs,cfg,150,momentum_advection=True,response_resolution=response)
                if response=='transport':assert trace[:30]==baseline
                record=dict(arm=arm,start_s=start,response=response,checks=checks,
                    prefix30=c.score(trace[:30],observed,arm,start),full150=c.score(trace,observed,arm,start))
                runs.append(record)
                e.save(OUT/f'{arm}_{start}_{response}.json',trace)
            print('CASE',arm,start,[(r['response'],r['prefix30']['speed_rmse'],r['full150']['speed_rmse']) for r in runs[-2:]],flush=True)
    source=[Path(__file__),Path(s.__file__),Path(c.__file__),gp,cp,pp,ip,op]
    e.save(OUT/'result.json',dict(qualified=False,production_adopted=False,new_native_runs=0,future_inputs=False,
        fitted_parameters=0,default30s_traces_exact=exact,runs=runs,
        source_pins={p.relative_to(s.d.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source},
        limitations=['Local downstream15-20cells only; all ports/source forecasts are outside this gate.',
            'Same100m transport and parameters; only equilibrium/anticipation density and their physical length use original cell-lane scale.',
            'Acceleration memory and reconstructed flux remain disabled in both variants.',
            'Post-treatment2550/2700 states differ; this is propagation validation, not matched-state lever/cost selection.',
            'Known past/current boundaries only; no future observed speed or flow resets.']))


if __name__=='__main__':main()
