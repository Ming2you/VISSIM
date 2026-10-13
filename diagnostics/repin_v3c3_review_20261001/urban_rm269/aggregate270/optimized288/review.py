"""Review one completed VSL-enabled choice and its ordinary response checks."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    receipt = read(HERE/'full_decision_execution_r3.json')
    assert receipt['status'] == 'complete_pending_review'
    assert all(sha(p)==h for p,h in receipt['source_pins'].items())
    full = Path(receipt['output'])
    spec = importlib.util.spec_from_file_location('retained_inspector288',HERE.parent.parent/'runtime_pair2400_numericfix/compare.py')
    inspector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inspector)
    run = inspector.inspect(full,dict(status='complete_uncompared',exit_code=0,external_process_wall_sec=receipt['wall_sec']))
    assert run['policy']['max_iterations'] == run['policy']['pfo_cap_options']['max_iterations'] == 2
    assert not run['policy'].get('fixed_vsl')
    coords = read(full/'coordinates.json')['axes']
    assert len(coords)==237 and sum(a['kind']=='vsl' for a in coords)==24
    physical = [row for row in run['first_physical_csv'] if row['kind']=='vsl']
    assert physical and all(float(row['speed_kph']) in range(50,111,10) for row in physical)
    ordinary = read(full.parent/'execution3300/summary.json')
    assert ordinary['status']=='complete' and ordinary['forecasts']==2
    for p,h in ordinary['source_pins'].items():
        assert sha(p)==h,p
    rows = ordinary['results']
    assert all(r['writer_three_blocks'] and r['conservation_states']==4 and r['resource_max_exceedance']<1e-7 for r in rows.values())
    selection = read(full/'unused.joint.json')['selection']
    # Preserve the entire validated report on E; only small decisive fields on C.
    (full.parent/'full_review.json').write_text(json.dumps(run,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    summary = dict(status='complete_optimized_vsl_choice_and_ordinary_checks',
        whole_wall_sec=receipt['wall_sec'],target600_met=receipt['wall_sec']<=600,
        axes=237,vsl_axes=24,query_stats=run['query_stats'],converged=run['converged'],
        selection_status=run['selection_status'],policy=run['policy'],
        pfo={k:selection['pfo_warm_start'][k] for k in ('max_iterations','executed_iterations','accepted_iterations','converged','seconds')},
        cap_runs=selection['candidates'],
        continuous_held=run['costs_and_constraints']['held_objective'],
        continuous_selected=run['costs_and_constraints']['selected_objective'],
        ordinary_held=rows['hold']['omega_ttt_veh_h'],ordinary_selected=rows['selected']['omega_ttt_veh_h'],
        ordinary_delta=rows['selected']['omega_ttt_veh_h']-rows['hold']['omega_ttt_veh_h'],
        ordinary_shared_feasible={name:r['shared_constraints']['feasible'] for name,r in rows.items()},
        physical_and_writer_passed=True,same_initial_state_and_reference=True,
        selected_vsl_by_block=rows['selected']['vsl_by_block'],
        selected_rm_by_block=run['selected_rm_by_block'],native_runs=0,coefficient_fits=0,
        goal_complete=False,initialization_failures_preserved=2,
        limits=['One different-history optimized3300 state; not a timing-only comparison to fixedVSL.',
                'Model command choice does not prove actual VSL or whole-network gain.',
                'Existing finite native queue and city-only prepared experiment unchanged.'])
    assert not (HERE/'completion.json').exists()
    (HERE/'completion.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:summary[k] for k in ('status','whole_wall_sec','target600_met','ordinary_delta','ordinary_shared_feasible','converged')}),flush=True)


if __name__ == '__main__':
    main()
