"""Pin the completed fixed forecasts and one-arm preflight before freezing."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
H=HERE.parent
U=H.parents[2]
I=U/'diagnostics/sdmpc_n31_20260924/integration_20260926'
P=I/'native_urbanrm269_10681only_2400'


def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def main():
    assert not (HERE/'launch_plan.json').exists()
    now=datetime.now(timezone.utc).isoformat()
    assert read(P/'status.json')['stage']=='preflight_complete'
    protocol=read(P/'protocol.json')
    for p,h in protocol['command_pins'].items():assert sha(Path(p))==h,p
    summary=read(HERE/'forecast2400/summary.json')
    assert summary['native_preparation_allowed']
    pins={}
    for p in (P/'protocol.json',P/'launch_inputs.json',HERE/'finish_freeze.ps1',
              HERE/'prepare_native.py',HERE/'test_analysis_scope.py',Path(__file__),
              HERE/'baseline_reuse_qualification.json',HERE/'forecast2400/summary.json',
              I/'native_pair1200/run_pair.ps1',I/'native_pair1200/analyze_pair.py',
              U/'tools/sdmpc31/freeze_worktree.ps1',U/'diagnostics/sdmpc_n31_20260924/tools/freeze_manifest.py'):
        pins[str(p)]=sha(p)
    for p in (P/'selected').glob('*'):
        if p.is_file():pins[str(p)]=sha(p)
    membership=H.parent/'urban_area263/approaches_only/membership.json'
    analyzer=I/'native_pair1200/analyze_pair.py'
    post=dict(status='waiting_for_closed_native',analysis_attempts=0,
        python='C:/Users/alsrj/anaconda3/python.exe',
        argv=[str(analyzer),'--replay-protocol',str(P/'protocol.json'),
              '--runs-root','E:/VISSIM_runs/20261009_urbanrm269_10681only_s29',
              '--output-dir',str(HERE/'native_analysis'),'--membership-json',str(membership)],
        source_pins={str(p):sha(p) for p in (analyzer,membership,U/'scripts/measure_control_area.py',U/'diagnostics/com_execution_equivalence/verify_pair.py')},
        guard='Require normalSIM_DONE2850, canonical runner success, exact owner PID/birth closure; write native_analysis/runtime_closure.json first. No activeFZP scans or duplicate analysis.',
        baseline=str(Path(protocol['reuse_native_baseline']['run'])),
        window=[2400,2850],area='Omega701',
        followup='Compare actual10681 head/merge,68lane and52/66stocks,mainline/ramp/outsidecosts. The historical cached-ramp helper has a different prediction artifact schema; do not invoke it on this new output without an explicit reviewed adapter.',
        no_tiny_gain_sign_fitting=True,complete_sdmpc_wall_benchmark_pending=True)
    save(HERE/'postprocess_plan.json',post)
    pins[str(HERE/'postprocess_plan.json')]=sha(HERE/'postprocess_plan.json')
    save(HERE/'launch_plan.json',dict(status='preflight_complete_freeze_then_single_native',prepared_utc=now,
        protocol=str(P/'protocol.json'),source_pins=pins,
        results_root='E:/VISSIM_runs/20261009_urbanrm269_10681only_s29',
        runtime='E:/VISSIM_runtime/20261009_urbanrm269_10681only',
        maximum_new_native_arms=1,automatic_retries=0,preflight_passed=True,
        analysis_regression_tests_passed=4,only_modified_actuator='RM_C10681',
        baseline_reused=True,production_plant_adopted=False,
        gain_calibration_complete=False,full_sdmpc_runtime_benchmark_started=False))
    stage=read(HERE/'plan.json')
    stage.update(status='two_fixed_predictions_and_native_preflight_complete',
        model_summary=str(HERE/'forecast2400/summary.json'),native_launch_plan=str(HERE/'launch_plan.json'),
        forecast_process=dict(pid=21884,created_utc='2026-10-09T00:53:33.330491Z',exit_code=0,session_id=35569),
        completed_fixed_predictions=2,new_native_runs=0,calibration_complete=False)
    save(HERE/'plan.json',stage)
    root=read(H/'plan.json')
    root['previous_goal_turn']=dict(time_utc=now,classification='progress',completed=[
        'Actual closed hold2400 state: two10681-only fixed450s predictions complete; samecaps/conservation/physicalrows passed.',
        'Predicted extra10681merge84.533vehicles; mainline+5.522/Wout-3.877/ramp-2.074/Omega-0.727vehh. Native isolated gain still unknown.',
        'One-arm canonical preflight passes; closedhold reused with scoped new-pair qualification, old microscopic replay failure preserved.',
        'Postprocess same-endpoint/unknown-outside reporting repaired,4tests pass; no production plant adoption or fullSDMPC runtime comparison.'],
        next='Canonical freeze and one10681-only native replay; validate actual isolated response, then finalize meaningful calibration scope before full SDMPC wall-equivalence benchmark.')
    root['isolated10681']=dict(plan=str(HERE/'plan.json'),launch_plan=str(HERE/'launch_plan.json'),
        priority='calibration_and_control_response_then_complete_sdmpc_wall',status='prepared_one_native')
    save(H/'plan.json',root)
    print('FINALIZED_PREPARATION',len(pins),'pins',flush=True)


if __name__=='__main__':main()
