"""Check saved results and source versions; never execute the plant or VISSIM."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
R=HERE.parent
C=R/'sc1001_connection'
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'


def read(path):return json.loads(path.read_text(encoding='utf8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target=HERE/'verification.json';assert not target.exists()
    protocol=read(HERE/'protocol.json');pins={}
    wrapper=C/'check_connection.py'
    for name,expected in protocol['source_pins'].items():
        path=Path(name) if Path(name).is_absolute() else ROOT/name
        if path.resolve()==wrapper.resolve():path=HERE/'check_connection.before.py.txt'
        assert sha(path)==expected,name
        pins[str(path)]=expected
    before=(HERE/'check_connection.before.py.txt').read_text(encoding='utf8')
    after=wrapper.read_text(encoding='utf8')
    assert after==before.replace(
        "if routed and not four_arm:raise ValueError('Route combination check is bounded to four existing seed43 responses')",
        "if routed and not forecast:raise ValueError('Route combination check requires bounded saved-state forecasts')")
    for p in (wrapper,HERE/'assess.py',HERE/'verify.py'):ast.parse(p.read_text(encoding='utf8'))
    (HERE/'check_connection.executed.py.txt').write_bytes(wrapper.read_bytes())
    a=read(HERE/'assessment.json')
    assert a['forecasts']==2 and a['max_route_residual']<1e-7 and a['max_resource_exceedance']<1e-7
    assert a['release_minus_hold']['native']['omega']>a['release_minus_hold']['before']['omega']>a['release_minus_hold']['after']['omega']>0
    d=I/'closedloop_recorded2700_budget_check_derivatives_sc1001_s47'
    s=read(d/'summary.json');ad=read(d/'ad_columns.json')
    assert s['status']=='complete' and s['primal_outputs_match'] and s['files_unchanged']
    assert s['ad_query']['total_rollouts']==1 and s['independent_scalar_query']['scalar_rollouts']==13
    rows=[]
    for row in s['rows']:
        axis=row['axis'];scale=axis['scale']
        rows.append(dict(key=axis['key'],reference=axis['reference_value'],scale=scale,
            comparisons=[dict(step=c['step_physical'],ad_per_unit=c['omega_ad_per_z']/scale,
                central_per_unit=c['omega_fd_per_z']/scale,left_per_unit=sum(c['left_costs'])/scale,
                right_per_unit=sum(c['right_costs'])/scale,all_cost_resource_match=c['all_match'],
                normalized_cost_max_error=c['max_cost_error'],normalized_resource_max_error=c['max_resource_error'])
                for c in row['comparisons']]))
    assert [all(c['all_cost_resource_match'] for c in row['comparisons']) for row in rows]==[True,False,True]
    shared={k:v for k,v in ad['transformed_source_sha256'].items() if k.endswith('lane_offramp_runtime.py')}
    assert len(shared)==1 and all(sha(Path(k))==v for k,v in shared.items())
    derivative=dict(status='PARTIAL_CHECK_PASSED_EXISTING_RM10490_ANCHOR_MISMATCH',rows=rows,
        primal_cost_max_error=s['primal_cost_max_error'],primal_resource_max_error=s['primal_resource_max_error'],
        cost_partition_count=len(ad['costs']),resources=ad['resources'],wall_sec=s['wall_sec'],
        ad_rollouts=1,independent_scalar_rollouts=13,full_trajectory_jacobian_verified=False,
        all_axes_verified=False,green_offset_fd_verified=False,optimizer=0,new_native=0,
        source_pins={str(d/name):sha(d/name) for name in ('summary.json','protocol.json','ad_columns.json','scalar_responses.json')},
        current_shared_approach_transformed_source=shared,
        vsl_activation_secant_configured=read(C/'candidate_config.json')['adapter']['sdmpc_vsl_activation_secant'],
        interpretation='VSL infinitesimal flatness is not absence of finite-step benefit. RM10490 exact-anchor mismatch remains; do not certify every derivative.')
    (HERE/'derivative_assessment.json').write_text(json.dumps(derivative,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    pins[str(wrapper)]=sha(wrapper)
    report=dict(status='VERIFIED_PROGRESS_NOT_GAIN_QUALIFIED',previous_goal_turn='PROGRESS',current_goal_turn='PROGRESS',
        source_pins=pins,artifacts={p.name:sha(p) for p in HERE.iterdir() if p.is_file()},
        completed_canonical_forecasts=2,canonical_compute_sec=a['forecast_compute_sec'],
        ad_rollouts=1,independent_scalar_rollouts=13,derivative_compute_sec=s['wall_sec'],
        changed_production_functions=[],changed_diagnostic_wrapper_lines=1,
        previous_tests_reused=23,previous_tests_rerun=0,fit=0,optimizer=0,new_native=0,fzp_reads=0,push=0,
        failed_preflight_calls=1,all_owned_sessions_terminal=[11467,38086],remaining_owned_processes=0,
        default_route_inventory_enabled=False,goal='ACTIVE / NOT_QUALIFIED',
        limitation='No blanket AD pass, model gain qualification or new native performance claim.')
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_pins','artifacts')},ensure_ascii=False))


if __name__=='__main__':main()
