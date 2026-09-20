"""Verify new response identification and strict cutoff-safe marginal replay."""
from pathlib import Path
import copy
import hashlib
import json
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import paired_response_identification as r
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import matched_meter_increment as m


def main():
    out = r.HERE / 'response_identification_validation_v1'; out.mkdir(exist_ok=False)
    observed = r.load(r.HERE / 'paired_response_identification_v1/result.json')
    pair = []
    for seed in r.SEEDS:
        _, paths = r.folders(seed)
        records = {arm:r.read_case(path) for arm,path in paths.items()}
        base = records['none']
        for arm in r.ARMS:
            actual = records[arm]
            pair.append(dict(seed=seed,arm=arm,base=base,actual=actual,
                delta_incoming=actual['incoming']-base['incoming'],
                delta_outgoing=actual['outgoing']-base['outgoing'],
                delta_speed=actual['v14']-base['v14'],delta_merge=actual['merge']-base['merge']))
    metrics = {}
    forecasts = 0
    for mode, folds in observed['results'].items():
        actual_cost=[]; predicted_cost=[]; zero_cost=[]; q=[]; q0=[]
        for held in r.SEEDS:
            train=[p for p in pair if p['seed']!=held]
            assert {p['seed'] for p in train} == set(r.SEEDS)-{held}
            beta, training = r.fit(train,mode)
            assert training == folds[str(held)]['training']
            for p in [p for p in pair if p['seed']==held]:
                expected=folds[str(held)]['tests'][p['arm']]
                got=r.integrate(p,r.features(p,mode)@beta)
                zero=r.integrate(p,np.zeros(15))
                assert got==expected['fitted'] and zero==expected['zero_response']
                assert not got['projections']
                forecasts+=1
                actual_cost.append(got['actual_delta_ttt30']);predicted_cost.append(got['predicted_delta_ttt30'])
                zero_cost.append(zero['predicted_delta_ttt30']);q.append(got['delta_outflow_rmse']**2);q0.append(zero['delta_outflow_rmse']**2)
        rmse=lambda ys:float(np.sqrt(np.mean((np.array(ys)-actual_cost)**2)))
        metrics[mode]=dict(region_ttt_rmse=rmse(predicted_cost),zero_response_ttt_rmse=rmse(zero_cost),
            outflow_rmse=float(np.sqrt(np.mean(q))),zero_response_outflow_rmse=float(np.sqrt(np.mean(q0))),
            sign_correct=sum(a*b>0 for a,b in zip(actual_cost,predicted_cost)),
            zero_response_sign_correct=sum(a*b>0 for a,b in zip(actual_cost,zero_cost)), cases=len(actual_cost))
    native=m.prepare_data(m.BANK/'observations/rm8')
    model=m.e.load_base_model(native.geometry,m.MODEL/'config.json')
    profile=m.e.load(m.MODEL/'port_profile.json')
    parameters=m.e.load(m.MODEL/'selected_parameters.json')['parameters']
    protocol=r.load(r.HERE/'matched_meter2550_v1/protocol.json')
    exact=0; truncated_counts={}
    for arm in m.ARMS:
        def command(t):
            return {'RM_C10490':protocol['commands'][arm][int((t-m.START)//150)]},{}
        window=m.e.window(native,model,m.START,'history_forecast',profile,command)
        cut=copy.deepcopy(native)
        # Include the cached port_events installed by window(), not only the
        # events attribute populated by prepare_data(). All future counts go.
        for field in ('events','heads','port_events'):
            if hasattr(cut,field):
                old=getattr(cut,field)
                kept=[row for row in old if float(row['time_s'])<=m.START]
                setattr(cut,field,kept);truncated_counts[field]=len(old)-len(kept)
        cut.cells={t:rows for t,rows in cut.cells.items() if t<=m.START}
        for field in ('flows','boundaries','ports','headstocks','arrivals','departures','head_counts'):
            old=getattr(cut,field)
            setattr(cut,field,type(old)({key:value for key,value in old.items() if key[0]<=m.START}))
        cut.port_cohorts={t:rows for t,rows in cut.port_cohorts.items() if float(t)<=m.START}
        assert truncated_counts['port_events']>0
        truncated_window=m.e.window(cut,model,m.START,'history_forecast',profile,command)
        assert truncated_window==window
        prediction=m.e.simulate(model,truncated_window,parameters)
        saved=r.load(r.HERE/'matched_meter2550_v1'/f'prediction_{arm}.json')
        assert json.loads(json.dumps(prediction))==saved
        exact+=1
    pins={**observed['source_pins'],**protocol['source_pins']}
    for name,digest in pins.items():
        assert hashlib.sha256((r.ROOT/name).read_bytes()).hexdigest()==digest,name
    report=dict(passed=True,source_pins_verified=len(pins),identification_forecasts_exact=forecasts,
        oracle_flow_mass_steps=forecasts*15,cutoff2550_full_forecasts_exact=exact,
        future_rows_removed=truncated_counts,metrics=metrics,new_native_runs=0,production_changes=0,
        qualified=False,meaning='Verification of diagnostic method and records,not successful prediction qualification.')
    (out/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':
    main()
