"""Compare raw Omega stock with modeled physical assignments and FW continuity."""
from pathlib import Path
import sys
import json
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'diagnostics'), str(ROOT / 'vendor/NumSim-mine')]
from probe_area_endpoint import fixture
from evaluation.controllers.control_area_objective import physical_membership_from_ledger
from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts


def audit(path=None):
    cfg, state, _, raw = fixture(path)
    physical = physical_membership_from_ledger(json.loads((ROOT / 'diagnostics/control_area_membership.json').read_text(encoding='utf-8')))
    tuning = json.loads((ROOT / 'evaluation/configs/n21_n7_20260908.json').read_text(encoding='utf-8'))
    mapping = json.loads((ROOT / tuning['mapping_json']).read_text(encoding='utf-8'))
    fw_links = {str(link) for spec in mapping['freeway_model_links'].values() for link in spec['chain_links']}
    counts = raw['vehicle_records']['full_network_link_counts']
    assignments = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    raw_inside = sum(v for k, v in counts.items() if physical[k])
    modeled_inside = sum(row['inside'] for row in state._control_area_ledger.stocks.values())
    differences = []
    for link, count in counts.items():
        if not physical[link] or link in fw_links:
            continue
        assigned = sum(assignments.get(link, {}).values())
        if abs(count - assigned) > 1e-8:
            differences.append({'physical_link': link, 'raw_veh': count, 'model_assigned_veh': assigned,
                                'residual_veh': count - assigned})
    output = {'state_sec': state.time_sec, 'raw_omega_veh': raw_inside, 'model_omega_veh': modeled_inside,
              'residual_veh': raw_inside - modeled_inside,
              'raw_fw_veh': sum(counts.get(k, 0) for k in fw_links),
              'model_fw_veh': sum(sum(v) for v in continuity_vehicle_counts(state, cfg).values()),
              'urban_assignment_differences': differences}
    return output


if __name__ == '__main__':
    result = audit(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
    (ROOT / 'diagnostics/area_initial_projection_audit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
