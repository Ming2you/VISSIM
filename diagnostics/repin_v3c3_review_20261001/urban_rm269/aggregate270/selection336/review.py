"""Review the saved full choice and per-cap finite RM evidence, no rollout."""
from pathlib import Path
import hashlib,importlib.util,json,math

HERE=Path(__file__).resolve().parent;A=HERE.parent
read=lambda p:json.loads(p.read_bytes())


def main():
    execution=read(HERE/'execution.json')
    assert execution['status']=='complete_pending_review'
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in execution['source_pins'].items())
    spec=importlib.util.spec_from_file_location('retained_inspector',A.parent/'runtime_pair2400_numericfix/compare.py')
    inspector=importlib.util.module_from_spec(spec);spec.loader.exec_module(inspector)
    run=inspector.inspect(HERE/'full3300',dict(status='complete_uncompared',exit_code=0,
        external_process_wall_sec=execution['wall_sec']))
    assert run['policy']['max_iterations']==run['policy']['pfo_cap_options']['max_iterations']==2
    joint=read(HERE/'full3300/unused.joint.json');selection=joint['selection']
    assert run['policy']['derivative_workers']==8
    assert read(HERE/'bootstrap_parity.json')==dict(cfg=True,state=True,forecast=True)
    binding=read(HERE/'query_binding.json')
    assert binding['latest_state'] and binding['latest_cfg'] and binding['latest_static_specs']
    audit_rows=[]
    for audit in read(HERE/'finite_rm_audits.json'):
        rows=audit['receipt']['candidates'];evaluations=audit['evaluations']
        assert len(rows)==len(evaluations)
        for row,e in zip(rows,evaluations):
            assert abs(row['objective']-e['objective'])<1e-9 and row['feasible']==e['feasible']
            quantities=e['quantities']
            np_actual=math.fsum(v['net_inflow_veh'] for v in quantities['owners'].values())
            nuf_actual=math.fsum(quantities['predicted_ramp_merge']['rate_veh_h_by_ramp'].values())
            audit_rows.append(dict(row,np_actual=np_actual,np_cap=e['np_cap'],
                nuf_actual=nuf_actual,nuf_cap=e['nuf_cap'],rm10681=e['rm10681'],
                owner_costs=e['owner_costs'],predicted_merge=quantities['predicted_ramp_merge']))
    assert any(r['candidate']=='RM_C10681:release' for r in audit_rows)
    workers=[]
    for directory in sorted((HERE/'workers').glob('[0-9]*')):
        if directory.name=='0000':continue # independent cache witness, not optimization
        receipt=read(directory/'receipt.json');done=read(directory/'completion.json')
        assert receipt['exit_code']==0 and done['status']=='complete'
        assert done['branch315_dynamic_ast_instrumented']
        assert receipt['hooks'][0]['conservation_states']==4
        workers.append(dict(worker=directory.name,mode=receipt['mode'],seconds=receipt['wall_sec']))
    assert len(workers)==run['query_stats']['total_rollouts']
    old=read(A/'decision285/full_decision_execution.json')
    report=dict(status='full_choice_and_finite_rm_reviewed',source_pins=execution['source_pins'],
        whole_wall_sec=execution['wall_sec'],decision_wall_sec=run['decision_wall_sec'],
        pfo_sec=run['pfo_seconds'],after_pfo_sec=run['sdmpc_after_pfo_seconds'],
        target600_met=execution['wall_sec']<=600,old285_whole_sec=old['wall_sec'],
        timing_comparison_scope='Different plant, candidate workload and machine load; not a controlled speedup test.',
        converged=run['converged'],selection_status=run['selection_status'],
        held_ttt=selection['held_objective'],selected_ttt=selection['selected_objective'],
        delta_model_ttt=selection['selected_objective']-selection['held_objective'],
        selected_rm_by_block=run['selected_rm_by_block'],query_stats=run['query_stats'],
        final_constraints=selection['final_constraints'],owner_costs=selection['omega_partition']['costs'],
        meter_audit=run['meter_audit'],finite_rm_rows=audit_rows,workers=workers,
        three_block_actuator_constraints_checked=True,latest_model_all_layers=True,
        physical_model_checks_passed=True,continuous_prediction=True,execution_model_evaluated=False,
        native_run=False,production_adopted=False,goal_complete=False,
        remaining=['Selected joint command physical-clock and native response are not verified.',
            'Unused state/seed and city/joint major gain ranking still unqualified.',
            'SC105 arrival/ready-stock mismatch remains; do not tune tiny net signs.'])
    path=HERE/'review.json';assert not path.exists();path.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf8')
    print(json.dumps({k:report[k] for k in ('status','whole_wall_sec','decision_wall_sec','pfo_sec','after_pfo_sec',
        'target600_met','converged','selection_status','held_ttt','selected_ttt','delta_model_ttt','query_stats')},ensure_ascii=False))
    print(json.dumps(dict(rm10681=[r for r in audit_rows if r['candidate']=='RM_C10681:release'],
        selected=[b.get('rw_meter_green_RM_C10681') for b in run['selected_rm_by_block']]),ensure_ascii=False))


if __name__=='__main__':main()
