"""Recheck completed cohort pairing and outlet experiment; no model execution."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import matched_cohort_response as c

K,e=c.K,c.e


def main():
    cohorts=e.load(c.OUT/'result.json')
    out=K/'matched_outlet_response_v1'
    results=e.load(out/'result.json')
    pins=pairs=forecasts=west=0
    for result in (cohorts,results):
        assert result['qualified'] is False and result['future_inputs'] is False
        for name,digest in result['source_pins'].items():
            assert hashlib.sha256((e.ROOT/name).read_bytes()).hexdigest()==digest,name
            pins+=1
    for seed in (23,33):
        saved={}
        reference=e.load(K/('matched_meter_midpoint_v1/result_v2.json' if seed==23 else 'matched_meter_midpoint_s33_v2/result.json'))
        for arm in ('rm8','rm6','rm_ramp'):
            row=e.load(c.OUT/f's{seed}_{arm}.json')
            for key in ('initial_frame','cars'):row[key]={int(k):v for k,v in row[key].items()}
            saved[arm]=row
            assert abs(sum(v['n'] for v in row['trace'][1:])/3600-reference['actual'][arm]['component']['mainline'])<1e-8
            pred=e.load(out/f'prediction_s{seed}_{arm}.json')
            old=e.load(K/f'matched_port_timing_response_v2/prediction_s{seed}_partition8_13_{arm}.json')
            for field in ('cells','flows','ports','ramps'):
                assert [v for v in pred[field] if v['road']=='FW_W']==[v for v in old[field] if v['road']=='FW_W']
            assert all(r['continuity_residual_max_veh']<1e-7 and r['negative_density_count']==0 for r in pred['diagnostics']['roads'])
            assert all(abs(r['conservation_residual_veh'])<1e-7 for r in pred['ports']+pred['ramps'])
            west+=1;forecasts+=1
        for arm in ('rm6','rm_ramp'):
            fresh=c.compare(saved['rm8'],saved[arm])
            assert fresh==cohorts['cases'][str(seed)][arm]
            pairs+=len(fresh['pairs'])
        assert all(row['trajectory'][:151]==saved['rm_ramp']['cars'][vid]['trajectory'][:151] for vid,row in saved['rm6']['cars'].items())
    names=['evaluation/controllers/physical_lane_groups.py','evaluation/controllers/physical_ramp_boundary.py',
           'evaluation/controllers/vissim_stackelberg_adapter.py',
           'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py']
    for name in names:
        assert subprocess.check_output(['git','show','1fcca58:'+name],cwd=e.ROOT)==(e.ROOT/name).read_bytes(),name
    result=dict(passed=True,qualified=False,source_pins=pins,paired_initial_vehicles=pairs,
        saved_forecasts_checked=forecasts,west_exact=west,mainline_costs_reconciled=6,
        core_unchanged_from='1fcca58',new_native_runs=0,forecasts_recomputed=False,
        previous_goal_turn='progress: committed and remotely verified the delivery',
        current_goal_turn='progress: paired-cohort propagation and terminal-boundary counterexample',
        goal_status='active; NOT_QUALIFIED',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    e.save(out/'verification_v2.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
