"""Freeze completed evidence; failure of gain qualification is not a tool failure."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from datetime import datetime
import ast
import hashlib

HERE=Path(__file__).resolve().parent;H=HERE.parent


def pin(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(4*1024*1024),b''):digest.update(chunk)
    return {'path':str(path.relative_to(e.ROOT)).replace('\\','/'),
            'sha256':digest.hexdigest(),'bytes':path.stat().st_size}


def main():
    output=HERE/'QUALIFICATION.json'
    if output.exists():raise FileExistsError(output)
    tests=e.load(HERE/'tests.json');model=e.load(HERE/'qualification_v1/verification.json')
    assert tests['passed'] and tests['tests']==81
    assert model['default_predictions_exact']==model['previous_candidate_exact']==12
    assert model['west_unchanged'] and model['future_state_resets']==model['future_exchange_inputs']==0
    assert model['state_guards_passed']==6 and model['state_guards_total']==12
    summary23=e.load(HERE/'dispersion_analysis_v1/summary.json')
    summary33=e.load(HERE/'dispersion_seed33_analysis_v1/summary.json')
    assert summary23['delta_vs_none_veh_h']['spread_only']['total']<0
    assert summary33['delta_vs_none_veh_h']['spread_only']['total']>0
    runs=[];paths=set(HERE.glob('*.py'))|set(HERE.glob('*.md'))
    for p in paths:
        if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
    paths.update([e.ROOT/'evaluation/controllers/physical_lane_groups.py',
        e.ROOT/'evaluation/controllers/desired_speed_transport.py',
        e.ROOT/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py',
        H/'evaluate_response.py',H/'lane_group_response_20260919/qualification_v6/parameters.json',
        H/'merge_drain_response_20260919/decisions_v1/internal_cost/port_profile.json',
        e.ROOT/'diagnostics/fast_nc_run.ps1',e.ROOT/'diagnostics/fast_fixed_profile.py',
        e.ROOT/'docs/HANDOFF_20260919_cost_and_ramp_response.md',
        HERE/'tests.json',HERE/'parameter_check.txt'])
    for folder in ['fit_v1','qualification_v1','observations_v2','dispersion_analysis_v1',
                   'dispersion_seed33_analysis_v1','dispersion_spatial_v2']:
        paths.update((HERE/folder).glob('*.json'))
        if folder=='observations_v2':paths.update((HERE/folder).glob('*.csv'))
    for root,seed,arms,summary in [
        (HERE/'dispersion_native_v1',23,['mean_only','spread_only','affine_both'],summary23),
        (HERE/'dispersion_seed33_v1',33,['spread_only'],summary33)]:
        paths.add(root/'protocol.json')
        for arm in arms:
            folder=root/arm;run=folder/'run';r=e.load(run/'run.json');v=e.load(run/'fixed_validation.json')
            assert r['completed'] and not r['error'] and r['terminal_sec']==3000 and r['exit_code']==0
            assert r['seed']==seed and not r['owned_native_alive']
            assert v['passed'] and v['event_readbacks']==128 and not v['unrecorded_signal_groups']
            assert v['untargeted_snapshot_sha256_before']==v['untargeted_snapshot_sha256_after']
            a=summary['results'][arm]
            assert a['local_balance_residual']==0 and not a['explicit_component_removals']
            assert a['precontrol_exact_rows']>8_000_000 and a['first_dsd_verified_crossings']>500
            assert a['first_dsd_max_error_kmh']<.000811
            runs.append({'seed':seed,'arm':arm,'completed':True,'terminal_s':3000,
                'elapsed_wall_s':(datetime.fromisoformat(r['finished'])-datetime.fromisoformat(r['started'])).total_seconds(),
                'event_readbacks':v['event_readbacks'],'unrecorded_signal_groups':v['unrecorded_signal_groups'],
                'precontrol_exact_rows':a['precontrol_exact_rows'],
                'desired_speed_verified_crossings':a['first_dsd_verified_crossings'],
                'desired_speed_max_error_kmh':a['first_dsd_max_error_kmh'],
                'local_balance_residual':0,'explicit_component_removals':0,
                'source_recording':str((run/'vissim_eval/baseline_001.fzp').relative_to(e.ROOT)).replace('\\','/')})
            paths.update([folder/'profile.json',folder/'prepared/network/baseline.inpx',
                run/'run.json',run/'fixed_validation.json',run/'baseline_001.err',
                run/'vissim_eval/baseline_001.fzp'])
            paths.update((folder/'prepared/network').glob('*.sig'))
            paths.update(run.glob('*.csv'))
            paths.update((run/'vissim_eval').glob('*.ldp'))
    result={'schema':'state-exchange-and-dispersion-qualification/v1',
        'model_status':'NOT_QUALIFIED','promoted_to_default':False,
        'native_diagnostic_status':'COMPLETED_AND_EXECUTION_VERIFIED',
        'dispersion_benefit_status':'NOT_UNIVERSAL_OPPOSITE_SIGN_IN_SEED33',
        'tests':tests,'model_verification':model,'native_runs':runs,
        'delta_ttt_veh_h':{'seed23':summary23['delta_vs_none_veh_h'],
                           'seed33':summary33['delta_vs_none_veh_h']},
        'scope':'450s FW_E mainline + four on-ramp and four off-ramp connectors; NOT Omega or closed-loop controller improvement',
        'remaining':['DSD transport is not connected to the mainline dynamics',
                     'RM mainline recovery magnitude remains underpredicted',
                     'Current-state lane exchange fails gain and state-error qualification',
                     'Multi-bottleneck downstream response; demand realization differences not isolated',
                     'Full GNE / Omega accounting on new geometry not completed'],
        'pins':[pin(p) for p in sorted(paths)]}
    e.save(output,result)
    print({'model_status':result['model_status'],'native_runs':len(runs),
           'pins':len(result['pins']),'elapsed_native_s':[r['elapsed_wall_s'] for r in runs]},flush=True)


if __name__=='__main__':main()
