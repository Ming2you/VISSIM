"""Attribute an audited endpoint's Omega exit score to accepted model routes.

One held-action endpoint, with a read-only ledger observer. Physical measurements
come from the completed interval audit; no new FZP scan or future model input.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import pickle
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
from diagnostics.probe_model_area_integration import build_projected
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers.control_area_objective import ModelAreaLedger
from src.controllers import rollout_endpoint
from src.models.demand import DemandStep
from src.models.state import ControlAction


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('audit', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix('.md').exists():
        raise FileExistsError('Refusing to replace an earlier attribution')
    started = time.monotonic()
    audit_hash, producer_hash = sha(args.audit), sha(__file__)
    audit = json.loads(args.audit.read_text(encoding='utf-8'))
    if not (audit['replay_matches_executed_model'] and audit['executed_command_audit_valid']):
        raise ValueError('Executed-model and actual-command audit required')
    expected = audit['source_sha256_start']
    differences = [path for path, value in expected.items() if sha(ROOT/path) != value]
    if differences:
        raise ValueError('Audited sources or inputs changed: '+str(differences))
    inputs = audit['inputs']
    cfg, state, detectors, tuning, raw, mapping, metadata = build_projected(
        ROOT/inputs['config'], ROOT/inputs['state'], ROOT/inputs['previous'], fixture_inputs=False)
    action = adapter.control_from_json(ROOT/inputs['action'], cfg, ControlAction)
    calibration = adapter.deep_update(dict(adapter.load_optional_json(str(
        ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))),
        tuning.get('calibration_override', {}))
    forecast = adapter.demand_from_state(raw, cfg, DemandStep, 1, calibration, detectors)
    original_bytes = pickle.dumps((state, action, forecast), protocol=5)
    attributed = defaultdict(Counter)
    observed_ledgers = {}
    original = ModelAreaLedger.transfer

    def observe(ledger, source, target, vehicles, **kwargs):
        observed_ledgers[id(ledger)] = ledger
        before = (ledger.ttd_veh, ledger.entered_veh, ledger.event_count,
                  ledger.flow_counts['spatial_remap_exit_veh'])
        result = original(ledger, source, target, vehicles, **kwargs)
        if ledger.event_count != before[2]:
            key = str(kwargs.get('route_key') or f'{source}->{target}')
            row = attributed[key]
            row['accepted_veh'] += vehicles
            row['ttd_veh'] += ledger.ttd_veh-before[0]
            row['entered_veh'] += ledger.entered_veh-before[1]
            row['remap_exit_veh'] += ledger.flow_counts['spatial_remap_exit_veh']-before[3]
            row['events'] += 1
        return result

    with patch.object(ModelAreaLedger, 'transfer', observe):
        point = rollout_endpoint.evaluate_price_point(state, action, forecast, [],
            rollout_endpoint.ObjectiveSpec(cfg, depth_override=1, box_walk=False, score_mode='raw'))
    if point.aborted or len(point.states) != 1:
        raise AssertionError('Held-action endpoint is incomplete')
    if pickle.dumps((state, action, forecast), protocol=5) != original_bytes:
        raise AssertionError('Observer or endpoint mutated its input')
    if len(observed_ledgers) != 1 or sum(row['events'] for row in attributed.values()) != point.control_area['event_count']:
        raise AssertionError('Expected one closing ledger and exact accepted-event coverage')
    for key in ('ttt_veh_h', 'ttd_veh', 'entered_veh', 'event_count', 'flow_counts'):
        if point.control_area[key] != audit['model']['metrics'][key]:
            raise AssertionError('Observed endpoint differs from the audited result: '+key)
    for key in ('ttd_veh', 'entered_veh'):
        if abs(sum(row[key] for row in attributed.values())-point.control_area[key]) > 1e-8:
            raise AssertionError('Attribution does not close '+key)
    if [path for path, value in expected.items() if sha(ROOT/path) != value]:
        raise AssertionError('Sources or inputs changed during attribution')
    if sha(args.audit) != audit_hash or sha(__file__) != producer_hash:
        raise AssertionError('Audit or observer source changed during attribution')
    rows = [{'route': key, **dict(values), 'route_contract': cfg.network.control_area_routes.get(key)}
            for key, values in sorted(attributed.items(), key=lambda item: -item[1]['ttd_veh'])
            if values['ttd_veh'] > 1e-10]
    categories = Counter()
    for row in rows:
        categories[row['route'].split(':')[0]] += row['ttd_veh']
    physical = audit['physical']
    mapped = Counter()
    for row in rows:
        turns = (row['route_contract'] or {}).get('physical_turns', [])
        if len(turns) != 1 or row['remap_exit_veh'] != 0:
            continue
        edges = [edge for edge in turns[0].get('crossing_edges', []) if edge['from_inside'] and not edge['to_inside']]
        if not edges or abs(len(edges)*row['accepted_veh']-row['ttd_veh']) > 1e-8:
            continue
        for edge in edges:
            mapped[f"{edge['source']}->{edge['target']}"] += row['accepted_veh']
    boundary_rows = [{'pair': key, 'model_unique_path_veh': value,
                      'physical_exact_sampled_pair_veh': physical['exit_pairs'].get(key, 0)}
                     for key, value in sorted(mapped.items(), key=lambda item: -physical['exit_pairs'].get(item[0], 0))]
    result = {'schema': 'area-exit-attribution/v1', 'run': audit['run'], 'interval_sec': audit['interval_sec'],
        'audit': {'path': str(args.audit), 'sha256': audit_hash},
        'producer_sha256': producer_hash, 'source_inputs_unchanged': True,
        'endpoint_exact_audited_result': True, 'input_state_action_forecast_unchanged': True,
        'observed_ledger_count': len(observed_ledgers), 'accepted_event_count': sum(row['events'] for row in attributed.values()),
        'model_ttd_veh': point.control_area['ttd_veh'], 'by_route_category_veh': dict(categories),
        'model_spatial_remap_exit_veh': point.control_area['flow_counts']['spatial_remap_exit_veh'],
        'uniquely_mapped_boundary_pairs': boundary_rows,
        'model_ttd_without_unique_boundary_pair_veh': point.control_area['ttd_veh']-sum(mapped.values()),
        'routes': rows, 'physical_totals': physical['totals'], 'physical_exit_pairs': physical['exit_pairs'],
        'physical_unresolved_disappearance_links': physical['unresolved_disappearance_links'],
        'limitation': 'Exact replay comparison covers accounting metrics and all accepted-flow counts, not full state identity. Only a unique physical path whose crossings close its route TD is mapped to a boundary pair. Other model exit categories are left unmapped. A skipped connector in 1s recording can change the sampled pair; exact-pair counts are not a complete movement-flow measurement. Proportional grouped-stock remapping, terminal inference and interior disappearance retain the original audit definitions.',
        'wall_sec': round(time.monotonic()-started, 3)}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    text = [f"{audit['run']}: {audit['interval_sec'][0]}–{audit['interval_sec'][1]} s", '',
            'One held-action endpoint. TTT, TD, entries, event count and every accepted-flow count match the previous audited result exactly.', '',
            '| Model exit category | TD vehicles |', '|---|---:|']
    text += [f'| {key} | {value:.6f} |' for key, value in categories.items()]
    text += ['', f"Total model TD {result['model_ttd_veh']:.6f}; spatial-remap component {result['model_spatial_remap_exit_veh']:.6f} (included in the categories above).", '',
             '| Largest model exit route | Accepted vehicles | TD vehicles | Remap TD |', '|---|---:|---:|---:|']
    text += [f"| {row['route']} | {row['accepted_veh']:.6f} | {row['ttd_veh']:.6f} | {row['remap_exit_veh']:.6f} |" for row in rows[:20]]
    text += ['', '| Unique predicted boundary | Model vehicles | Physical exact sampled pair |', '|---|---:|---:|']
    text += [f"| {row['pair']} | {row['model_unique_path_veh']:.6f} | {row['physical_exact_sampled_pair_veh']} |" for row in boundary_rows[:20]]
    text += ['', result['limitation'], '']
    args.output.with_suffix('.md').write_text('\n'.join(text), encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('interval_sec', 'model_ttd_veh', 'by_route_category_veh', 'model_spatial_remap_exit_veh', 'wall_sec')}))


if __name__ == '__main__':
    main()
