"""Check saved offline SDMPC selection; no rollout, COM or native dispatch."""
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'selection5100'
PREVIOUS = Path('D:/VISSIM_runs/20261006_urban_storage40_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29/action_004950.json')


def main():
    pins = {}

    def read(path):
        raw = path.read_bytes()
        pins[str(path)] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    completion = read(OUT / 'completion.json')
    assert completion['status'] == 'complete' and completion['full_selection']
    joint = read(OUT / 'unused.joint.json')
    selection = joint['selection']
    assert joint['completed'] and joint['sim_sec'] == 5100 and selection['feasible']
    written = read(OUT / 'unused.joint_written.json')
    assert written['prewrite_binding_passed'] and written['written_command_binding_passed']
    assert not written.get('native_execution_passed')
    assert not (OUT / 'unused.json.applied').exists()
    csv_path = OUT / 'unused.csv'
    assert hashlib.sha256(csv_path.read_bytes()).hexdigest() == written['expected_csv_sha256']
    with csv_path.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == written['ordered_row_count']
    for key in ('np', 'nuf'):
        constraint = selection['final_constraints'][key]
        assert constraint['mode'] == 'cap' and constraint['constraint_checked']
        assert constraint['satisfied'] and constraint['actual'] <= constraint['target'] + constraint['tolerance']
    previous = read(PREVIOUS)
    price = selection['price_state']['previous_application']
    ack = Path(str(PREVIOUS) + '.applied')
    assert price['committed'] and Path(price['source']).resolve() == ack.resolve()
    assert hashlib.sha256(ack.read_bytes()).hexdigest() == price['receipt_sha256']
    action = read(OUT / 'unused.json')
    sequence = action['diagnostics']['sdmpc_prediction_sequence']
    blocks = [action, *sequence['future']]
    assert len(blocks) == 3 and selection['control_sequence']['all_actuator_and_step_constraints_checked']
    ramps = selection['meter_operating_bounds']['ramps']
    meter_rows = []
    prior = previous
    for index, block in enumerate(blocks):
        greens = {}
        for ramp, bound in ramps.items():
            key = 'rw_meter_green_' + ramp
            green = block['diagnostics'][key]
            assert green >= bound['minimum_green_sec'] - 1e-9
            assert abs(green - prior['diagnostics'][key]) <= 2 + 1e-9
            greens[ramp] = green
        assert block['vsl'] == read(OUT / 'scheduled_vsl.json')[index]['vsl']
        meter_rows.append(greens)
        prior = block
    rm = [r for r in rows if r['id'] == 'RM_C10681']
    assert rm and all(float(r['green_sec']) == meter_rows[0]['RM_C10681'] for r in rm)
    mass = read(OUT / 'expanded_area_check.json')
    assert abs(mass['observed_inside_veh'] - mass['seeded_inside_veh']) < 1e-6
    partition = selection['omega_partition']
    assert abs(sum(partition['costs'].values()) - selection['selected_objective']) < 1e-6
    budget = read(OUT / 'unused.decision_budget.json')
    assert budget['output_completed'] and not budget['output_error']
    result = dict(status='passed_offline_selection_and_written_binding', sim_sec=5100,
                  seconds=completion['seconds'], native_gain_verified=False, source_pins=pins,
                  initial_inside_veh=mass['observed_inside_veh'], price_history=price,
                  rm_greens_by_block=meter_rows, shared_constraints={k:selection['final_constraints'][k] for k in ('np','nuf')},
                  selected_objective_veh_h=selection['selected_objective'],
                  protected_initial_objective_veh_h=selection['held_objective'],
                  selected_vs_protected_initial_veh_h=selection['selected_objective']-selection['held_objective'],
                  pfo={k:selection['pfo_warm_start'][k] for k in ('max_iterations','executed_iterations','accepted_iterations','converged','status','seconds')},
                  leader_candidates=selection['candidates'], converged=selection['converged'],
                  finite_meter_audit=selection['meter_neighbor_audit'],
                  rollout_work=selection['surrogate_query'], written_rows=len(rows),
                  budget={k:budget[k] for k in ('unlimited_time','configured_inactive_budget_sec','wall_sec','cpu_sec')},
                  limitations=['Native VISSIM application and traffic benefit not tested; STOP retained.',
                               'Initial objective uses the projected storage-protecting seed, not an independently evaluated native hold.',
                               'Finite SDMPC search is not a Nash or optimality certificate.',
                               'Model predictions are not actual TTT or counterfactual deletion estimates.'])
    (HERE / 'selection5100_assessment.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','seconds','rm_greens_by_block','shared_constraints','selected_vs_protected_initial_veh_h','converged')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
