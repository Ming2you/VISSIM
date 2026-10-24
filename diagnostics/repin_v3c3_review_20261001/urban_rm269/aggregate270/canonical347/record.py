from pathlib import Path
import hashlib,json
A=Path(r"C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.worktrees/sd31-upstream-20260926/diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270")
evidence=Path('E:/VISSIM_analysis/20261010_canonical347/matched_v2/assessment.json')
result=json.loads(evidence.read_bytes())
assert result['status']=='explicit_branch_service_matches_legacy_primal_and_full_gradient'
item=dict(status='static_branch_service_worker_equivalence_passed',evidence=str(evidence),
    sha256=hashlib.sha256(evidence.read_bytes()).hexdigest(),tests_passed=6,predictions=4,
    dynamic_vs_static_max_error=0,scalar_ad_max_error=max(result['errors']['static_scalar__static_ad'].values()),
    axes=213,central_constraints=5112,goal_complete=False,new_native=0,full_selection=0,
    report=str(A/'canonical347/README.md'))
for p in (A/'plan.json',A.parent/'plan.json'):
    data=json.loads(p.read_bytes())
    data['canonical347']=item
    data['current_stage']='static_branch_service_canonical_equivalence_passed_remaining_hooks_pending'
    data['current_workers']=[]
    data['latest_evidence']=str(evidence)
    data['next_step']='Continue canonical aggregate integration of remaining331/current339 initialization and rollout hooks, retaining physical provenance and fixed calibration/current-state separation.347 branch service static option matches scalar/AD all213 axes exactly; do not repeat its4 forecasts.10681 discharge magnitude and2400 city-control gain error remain open. Preserve5sFW/10surban,450s horizon/terminalOFF/Omega701. Validate material feasible control ranking and matched-budget wall after integration; no automatic full optimizer/native repetition, grids or push.'
    data['goal_complete']=False
    temp=p.with_suffix('.347.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8');temp.replace(p)
print('Recorded347 in two authoritative plans; goal remains incomplete.')

