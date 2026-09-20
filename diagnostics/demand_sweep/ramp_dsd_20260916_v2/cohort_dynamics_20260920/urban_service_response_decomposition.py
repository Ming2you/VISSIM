"""Identify which missing future states change the existing drainage predictor.

Future native features below are explicitly diagnostic oracles, not an online
forecast. No coefficient fit, vehicle flow override, or new simulation occurs.
"""
from pathlib import Path
import sys,hashlib
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.urban_receiving_probe import dataset,features,NAMES

HERE=Path(__file__).resolve().parent


def main():
    out=HERE/'urban_service_response_decomposition_v1.json'
    if out.exists():raise FileExistsError(out)
    calibration=HERE/'urban_receiving_lag_probe_v1/result.json'
    spec=next(r for r in e.load(calibration)['models'] if r['name']=='history_signal_state')
    coef=np.asarray(spec['coefficients_by_lane']);lag=spec['signal_lag_s']
    masks={'frozen':[],'off_state':[5,6,7,8],'urban_state':[9,10,11,12],
           'past_discharge':[1,2],'all_state':[1,2,5,6,7,8,9,10,11,12]}
    files=[Path(__file__),calibration,HERE/'urban_receiving_probe.py'];cases={};xs={};truth={};clean={}
    for case in ('s23_none','s23_vsl','s33_none','s33_spread'):
        paths=[HERE/'urban_drain_observations_v5'/f'{case}{suffix}' for suffix in ('.csv','_evidence.json')]
        files+=paths;rows,program,offset=dataset(*paths)
        times=list(range(2400,2850,10));x=np.asarray([features(rows,program,offset,t,lag) for t in times])
        anchor=features({t:r for t,r in rows.items() if t<=2400},program,offset,2400,lag)
        assert np.array_equal(anchor,x[0])
        y=np.asarray([[sum(rows[t][f'off_lane{l}_departures'] for t in range(s,s+10)) for l in (1,2)] for s in times])
        clean[case]=np.asarray([not any(rows[t][f'urban_sg{g}_removals'] for t in range(s,s+10) for g in (2,5)) for s in times])
        predictions={}
        for mode,indices in masks.items():
            z=np.tile(anchor,(len(times),1));z[:,3:5]=x[:,3:5]
            z[:,indices]=x[:,indices]
            prediction=np.maximum(0.,z@coef)*10
            predictions[mode]=dict(count_by_lane=prediction.sum(axis=0).tolist(),
                count_rmse_by_lane=np.sqrt(np.mean((prediction-y)**2,axis=0)).tolist(),
                predictions=prediction.tolist())
        xs[case]=x;truth[case]=y
        cases[case]=dict(actual_by_lane=y.sum(axis=0).tolist(),predictions=predictions,
            clean_intervals=int(clean[case].sum()),intervals=len(times),
            urban_abnormal_removals=sum(rows[t][f'urban_sg{g}_removals'] for t in range(2400,2850) for g in (2,5)),
            current_features=dict(zip(NAMES,anchor.tolist())),
            mean_future_features=dict(zip(NAMES,np.mean(x,axis=0).tolist())))
    pairs={}
    for base,controlled in [('s23_none','s23_vsl'),('s33_none','s33_spread')]:
        assert np.array_equal(xs[base][0],xs[controlled][0]),'Paired current states differ'
        assert np.array_equal(xs[base][:,3:5],xs[controlled][:,3:5]),'Paired signals differ'
        delta_x=xs[controlled]-xs[base]
        raw={name:(delta_x[:,indices]@coef[indices]*10).sum(axis=0).tolist() for name,indices in masks.items() if name not in ('frozen','all_state')}
        assert np.allclose(np.sum(list(raw.values()),axis=0),(delta_x@coef*10).sum(axis=0))
        both_clean=clean[base]&clean[controlled]
        pairs[controlled]=dict(actual_delta_by_lane=(truth[controlled]-truth[base]).sum(axis=0).tolist(),
            predicted_delta_by_mode={m:(np.asarray(cases[controlled]['predictions'][m]['count_by_lane'])-
                cases[base]['predictions'][m]['count_by_lane']).tolist() for m in masks},
            raw_linear_feature_group_contributions=raw,
            paired_clean_intervals=int(both_clean.sum()),
            paired_clean_actual_delta=(truth[controlled]-truth[base])[both_clean].sum(axis=0).tolist())
        print(controlled,pairs[controlled],flush=True)
    e.save(out,dict(status='FUTURE_STATE_DIAGNOSTIC_ONLY',cases=cases,pairs=pairs,
        calibration='Existing NC13 coefficients and lag, unchanged; no treatment gain fit',
        scope='2400-2850s; s23 original VSL distribution and s33 spread-only counterexample; not RM/full-GNE/whole-Omega',
        caveats=['Frozen mode advances known signals only. All other modes selectively use future measured features.',
            'Past-discharge features at later horizon times contain future outcomes relative to cutoff; not a causal450s input.',
            'Feature coefficients are predictive associations, not identified causal lane mechanisms.',
            'Native abnormal urban removals are counted explicitly; clean-window restriction does not erase earlier loss effects.'],
        qualified=False,new_native_runs=0,source_pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}))


if __name__=='__main__':main()
