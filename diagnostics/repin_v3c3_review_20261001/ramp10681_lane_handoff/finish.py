"""Preserve the bounded handoff candidate and restore the previous production bytes."""
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output=HERE/'completion.json';assert not output.exists()
    a=json.loads((HERE/'assessment.json').read_bytes());tests=json.loads((HERE/'tests.json').read_bytes())
    assert a['forecasts']==6 and tests['passed'] and tests['tests']==30
    previous=json.loads((HERE.parent/'lane10682_inlet_flux/completion.json').read_bytes())
    executed=json.loads((HERE/'executed_sources.json').read_bytes());before=json.loads((HERE/'before.json').read_bytes())
    stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP');assert sha(stop)==previous['stop_sha256']
    for relative,digest in executed.items():
        assert sha(ROOT/relative)==digest,relative
        assert sha(HERE/'executed_sources'/Path(relative).name)==digest,relative
        assert sha(HERE/(Path(relative).name+'.before'))==before[relative],relative
    receipts={}
    for seed,prefix in [('43','closedloop_recorded2250_lever450_trace10681_'),('47','closedloop_recorded2700_select_check_trace10681_')]:
        folder=I/(prefix+'ramp10681_lane_handoff'+seed)
        trace=json.loads(gzip.decompress((folder/'held_actual_RM_C10681_trace.json.gz').read_bytes()))
        steps=[x['receipt'] for x in trace['lane_interval_receipts']]
        values=[sum(x['lane_receipts'][g]['accepted_merge_veh'] for x in steps) for g in (0,1)]
        assert abs(sum(values)-sum(x['accepted_merge_veh'] for x in steps))<1e-8
        receipts[seed]=values
    for relative in before:(ROOT/relative).write_bytes((HERE/(Path(relative).name+'.before')).read_bytes())
    for relative,digest in before.items():assert sha(ROOT/relative)==digest,relative
    for path,digest in previous['previous_production_exact'].items():assert sha(Path(path))==digest,path
    assert sha(stop)==previous['stop_sha256']
    result=dict(status='interface_corrected_in_candidate_not_gain_qualified_sources_restored',goal_status='ACTIVE/NOT_QUALIFIED',
        tests=30,forecasts=6,forecast_compute_sec=a['wall_sec'],fit_calls=0,
        owned_sessions={'83301':'EXIT0','13497':'EXIT0'},restored_exact=before,
        previous_production_exact=previous['previous_production_exact'],stop_sha256=sha(stop),
        new_native=0,new_fzp=0,push=0,mass_residual=a['mass_residual'],route_residual=a['route_residual'],resource_exceedance=a['resource_exceedance'],
        predicted_ramp_receipts_by_lane=receipts,
        native_observation_scope='Reused seed29/43 none2250.1-2700.1 departure CSV plus5s mainline cache. No exact47 lane crossing observation claimed.',
        failures_preserved=['audit.log: incorrect Windows handle declaration before data scan','audit_v2.log: nonexistent1s snapshot; actual saved frames150s'],
        conclusion='Lane receipt loss was real, but preserving receipts does not by itself fix congestion or RM response.43merge107.37 versus134native worsens from121.42;47merge121.38 versus150native also short.',
        next='Use saved native per-lane through counts and current predicted conflict inputs to separate gap receiving from local speed response. Existing gap uses all-lane average uniformly, despite receiving lanes1/2 differing from3/4. No capacity bonus or new coefficient grid; verify causal lane conflict before calibration.')
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('status','tests','forecasts','forecast_compute_sec','new_native')},ensure_ascii=False))


if __name__=='__main__':main()
