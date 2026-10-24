"""Verify completed236 files against235; no optimization or simulation."""
import hashlib
import json
from pathlib import Path

D=Path(__file__).resolve().parent
ROOT=D.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())


def main():
    completion=read(D/'completion.json')
    protocol=read(D/'protocol.json')
    out=Path(protocol['output'])
    joint=read(out/'unused_action.joint.json')
    action=read(out/'unused_action.json')
    writer=read(out/'unused_action.joint_written.json')
    summary=read(out/'summary.json')
    expected=read(D.parent/'budget235/postsearch/selected_action.json')
    sel=joint['selection']
    cache=joint['physical_response_cache']
    assert joint['completed'] and sel['feasible']
    assert all(sha(ROOT/p)==h for p,h in protocol['source_sha256'].items())
    assert all(sha(Path(p))==h for p,h in summary['files'].items())
    assert not summary['native_started']
    assert len(sel['candidates'])==3
    assert sel['meter_neighbor_audit']['distinct_budget_incumbents']==2
    assert sel['meter_neighbor_audit']['selected']=='RM_C10480:release'
    assert abs(completion['difference_from_saved_stage'])<1e-9
    fields=('N_P_star','N_UF_star','ramp_metering','vsl','green_times','offsets','inflow_outflow_allocation')
    field_checks={k:action[k]==expected[k] for k in fields}
    assert all(field_checks.values()), field_checks
    assert sel['final_constraints']['feasible']
    assert sel['control_sequence']['all_actuator_and_step_constraints_checked']
    assert cache['failed_batches']==0 and cache['closed'] and cache['owned_workers_alive']==[]
    assert writer['prewrite_binding_passed'] and writer['written_command_binding_passed']
    for key in ('action_json','action_csv'):
        assert sha(Path(writer[key]['path']))==writer[key]['sha256']
    meters={k.removeprefix('rw_meter_green_'):v for k,v in action['diagnostics'].items()
            if k.startswith('rw_meter_green_')}
    assert meters['RM_C10480']==2. and meters['RM_C10681']==0.
    result=dict(status='full_selection_and_writer_verified_not_native_qualified',
        completed=True,feasible=True,converged=sel['converged'],
        wall_sec=completion['wall_sec'],objective=sel['selected_objective'],
        held_objective=sel['held_objective'],
        difference_from_saved_stage=completion['difference_from_saved_stage'],
        seven_command_fields_exact=field_checks,meters=meters,candidates=sel['candidates'],
        constraints={k:sel['final_constraints'][k] for k in ('np','nuf','feasible')},
        control_sequence=sel['control_sequence'],derivative_axes=len(sel['coordinates']),
        model_calls={k:cache[k] for k in ('scalar_rollouts','tangent_rollouts','total_rollouts',
                                         'failed_batches','owned_workers_alive','closed')},
        writer=writer,sources_unchanged=True,
        model_execution_check='Reuses235 discrete actuator model forecast: identical seven command fields',
        native_runs=0,fit=0,new_fzp_reads=0,gain_qualified=False)
    (D/'assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','wall_sec','objective','meters','model_calls')},ensure_ascii=False))


if __name__=='__main__':main()
