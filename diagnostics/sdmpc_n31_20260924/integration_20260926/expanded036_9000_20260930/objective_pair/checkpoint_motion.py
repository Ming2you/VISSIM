"""Summarize verified route additions; no simulation or external data scan."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'vendor/NumSim-mine').is_dir())
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

archives={sha(p):str(p) for p in (HERE/'before').glob('*.txt')}
results={}
for stage in ('route_choice','owned','direct'):
    path=HERE/('distance_'+stage+'_result.json'); r=load(path)
    assert r['scalar_response_and_trajectory_exact'] and r['max_state_error']==r['initial_state_error']==0.
    assert r['ttt_omega_veh_h']==517.5983935981086 and r['full_omega_scoring_rejected']
    resolved={}
    for name,h in r['pins'].items():
        p=Path(name)
        if p.exists() and sha(p)==h:
            continue
        if h not in archives:
            raise ValueError('Historical execution pin has no retained source: '+name)
        resolved[name]=archives[h]
    results[stage]=dict(result=str(path),sha256=sha(path),historical_sources=resolved,
        exact=True,covered_subtotal_veh_km=r['receipt']['covered_subtotal_veh_km'],
        unclassified_positive_stock_count=len(r['receipt']['unresolved_positive_stocks']),
        initial_reservation_counts=r['native_motion'].get('initial_reservations',
            r['native_motion'].get('initial_seeded_vehicles')),
        elapsed_seconds=[r['baseline_seconds'],r['observed_seconds']])

# Original controller/terminal/endpoint/owner code remains unchanged this turn.
plan=load(HERE/'plan.json')
for relative,h in plan['source_before'].items():
    assert sha(ROOT/relative)==h,relative
changed={}
for name in ('native_input_routes','native_input_prehead','sdmpc_aggregate',
             'route_choice_corridor','shared_approach','sc2001_corridor','physical_ramp_branches'):
    p=ROOT/'evaluation/controllers'/(name+'.py')
    old=HERE/'before'/(name+'.py.before_distance.txt')
    def functions(path):
        return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text(encoding='utf-8')).body
                if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
    a,b=functions(old),functions(p)
    assert set(a)==set(b),name
    changed[name]=dict(sha256=sha(p),changed_functions=[k for k in a if a[k]!=b[k]],
                      unchanged_functions=sum(a[k]==b[k] for k in a))

report=dict(stage='urban_motion_extensions_verified_full_omega_pending',results=results,
    tests_passed=47,tests_log='tests_direct_distance.log',source_changes=changed,
    five_objective_core_sources_unchanged=True,full_omega_objective_enabled=False,
    new_native_runs=0,fzp_scans=0,pushes=0,
    note='Reservation counts are path allocations, not unique vehicles. Positive-stock coverage diagnostic includes stationary movement queues and tiny instantaneous merge_pending mirrors; do not call them all unmodeled roads or missing vehicles.',
    remaining=['Ordinary urban receiving/storage travel and current initial positions',
               'Initial physical gate city-lock cohorts (future admissions are connected)',
               '10643/10700 cumulative-link interior motion',
               'Explicit full stock coverage, endpoint/owners/AD/final gate wiring',
               'Bounded strong-RM/recovery CTG check, closed9000 analysis, two finite objective runs'])
(HERE/'motion_implementation_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
plan['current_native_actual_sec_at_least']=8400
plan['distance_options']['status']='urban_route_shared_sc2001_legsplit_direct_gate_future_motion_verified_full_scope_pending'
plan['implementation_status']='47 tests PASS; route-choice/shared/SC2001/known-legsplit/direct-exit/future-gate distance connected. Three successive fixed450 ON/OFF comparisons exact (six total forecasts, including previous route-choice launch). Ordinary urban and initial gate/cumulative transport, full coverage and objective/AD remain. No fullOmega reward enabled; current native at least8400; weight pending.'
(HERE/'plan.json').write_text(json.dumps(plan,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(dict(stage=report['stage'],results=results,source_changes=changed),indent=2))
