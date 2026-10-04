"""Review one completed saved-state search ablation; no traffic prediction."""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from evaluation.controllers.sdmpc_sequence import SequenceCoordinates

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'closedloop_recorded3600_select_rm_activation_v2'
NATIVE = Path('E:/VISSIM_runs/20260929_sd31_head10119_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
pins = {}


def read(path):
    raw = path.read_bytes()
    pins[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)


def commands(path):
    return [{k: v for k, v in row.items() if k != 'metadata'}
            for row in csv.DictReader(path.open(encoding='utf-8-sig'))]


old = read(NATIVE / 'action_003600.joint.json')
new = read(OUT / 'unused_action.joint.json')
assert old['completed'] and new['completed']
prior = read(OUT / 'prior_policy_ablation.json')
assert prior['original_receipt']['committed'] and prior['production_price_guard_unchanged']
a, b = old['selection'], new['selection']
assert a['held_objective'] == b['held_objective']
assert a['warm_start_objective'] == b['warm_start_objective']
assert a['final_constraints'] == b['final_constraints']
assert commands(NATIVE / 'action_003600.csv') == commands(OUT / 'unused_action.csv')
rows = [row for row in b['gradient_rows'] if row.get('fallback_reason') == 'open_meter_legal_edge']
assert len(rows) == 44
probes = []
for row in rows:
    # The actual configured FD is2s. The temporary far-edge stencil and the
    # final unchanged canonical FD stencil produce exactly the same endpoints
    # here: all three commands are OPEN, with2s consecutive-block limits.
    assert row['anchor_z'] == 0 and row['fd'] == .2 and row['reference_value'] == 10
    assert set(row['allowed']) <= set(range(2, 11))
    c = SequenceCoordinates.__new__(SequenceCoordinates)
    c.vsl_activation_secant = False
    c.meter_activation_secant = True
    c.axes = [dict(row, block=k) for k in range(3)]
    c.lower = np.array([-.2, -.4, -.6]); c.upper = np.zeros(3)
    c.G = np.array([[-1., 1., 0.], [0., -1., 1.]])
    c.glo = np.array([-.2, -.2]); c.ghi = -c.glo
    actual = c.stencil(np.zeros(3), row['block'])
    assert np.allclose(actual, row['stencil'], rtol=0, atol=1e-12)
    delta = row['stencil'][0] - row['stencil'][1]
    probes.append(dict(ramp=row['key'], block=row['block'], endpoints_green=[8, 10],
        delta_omega_veh_h_lower_minus_current=delta*row['total'],
        delta_np_veh=delta*row['resource_derivatives_scaled'][0]*b['policy']['budget_scale_np_veh'],
        delta_nuf_veh_h=delta*row['resource_derivatives_scaled'][1]*b['policy']['budget_scale_nuf_veh_h']))
result = dict(
    status='PROBING_WORKS_COMMAND_UNCHANGED_NOT_PRODUCTION_ADOPTED',
    initial_state_sec=3600, native_runs=0, future_measurements_used_for_prediction=False,
    held_and_pfo_warm_objectives_exact=True, physical_csv_exact=True,
    final_quantity_constraints_exact=True, original_prices_preserved=prior,
    selected_objective_veh_h=b['selected_objective'],
    rm_secant_rows=len(rows), extra_scalar_rollouts=new['physical_response_cache']['scalar_rollouts']-old['physical_response_cache']['scalar_rollouts'],
    solver_elapsed_sec={'native_recorded': old['elapsed_sec'], 'ablation': new['elapsed_sec']},
    sdmpc_candidates=b['candidates'],
    pfo={key: b['pfo_warm_start'][key] for key in ('max_iterations','executed_iterations','accepted_iterations','converged')},
    probes=probes,
    final_canonical_stencil_reproduces_all44_measured_endpoints=True,
    tests={'rm_vsl_unit_tests_passed': 8, 'sequence_cap_tests_passed': 27,
           'sequence_cap_subtests_passed': 24, 'historical_fixture_setup_errors': 5,
           'fixture_error': 'Old SavedCoordinateTests reference missing TRLAB machine network path; not repaired or counted as passed.'},
    limitations=[
        'Endpoint differences are relative to each PFO/SDMPC iteration anchor, not to the original actual-held command or native NC.',
        'The scalar endpoints supply secant gradients; this is not an exhaustive finite-neighbor optimum or Nash certificate.',
        'Original recorded solve and new solve have different cache/wall conditions; elapsed comparison is descriptive, not a controlled speed benchmark.',
        'First attempt stopped at the unchanged prior-policy hash guard before optimization. Explicit offline ablation verified the original policy/receipt and held its prices.',
        'The earlier synthetic fd1 stencil diagnosis is not the actual runtime setting: its recorded FD is2s, while the AD service-table slope still uses adjacent values.',
        'No service cap, objective, physical model, demand, command limits or horizon was modified. The new option remains opt-in.',
    ], source_sha256=pins)
for file in ('evaluation/controllers/sdmpc.py','evaluation/controllers/sdmpc_sequence.py'):
    pins[file] = hashlib.sha256(Path(file).read_bytes()).hexdigest()
(HERE / 'meter_activation_comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k: v for k, v in result.items() if k not in ('source_sha256','probes','original_prices_preserved')},ensure_ascii=False))
print(json.dumps([row for row in probes if abs(row['delta_omega_veh_h_lower_minus_current']) > 1e-8],ensure_ascii=False))
