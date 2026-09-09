"""Read-only provenance/arithmetic audit; no simulation, fit, or runtime edits."""
from pathlib import Path
import csv
import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
from evaluation.controllers import vissim_stackelberg_adapter as adapter

NETWORK = 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
CONFIG = 'diagnostics/area_candidate_configs/n7_area_beta0.json'
CALIBRATION = 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'
ATTRIBUTE = Path(r'C:\Program Files\PTV Vision\PTV Vissim 2020\Doc\Eng\attribute.xlsx')
GROUPS = {'OR_F_E': ('1130', '10682', '10643'), 'OR_D_E': ('1131', '10483', '10481'),
          'OR_D_W': ('1132', '10479', '10491'), 'OR_F_W': ('1133', '10645', '10638')}


def load(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8-sig'))


def fingerprint(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    return {'path': str(path), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    sources = [NETWORK, CONFIG, CALIBRATION, 'evaluation/parameters.json',
               'vendor/NumSim-mine/src/config/default.yaml', 'vendor/NumSim-mine/src/models/state.py',
               'evaluation/controllers/vissim_stackelberg_adapter.py',
               'evaluation/controllers/area_freeway_accounting.py',
               'vendor/NumSim-mine/src/controllers/local_freeway_plant.py',
               'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json',
               'outputs/freeway_ramp_split_v2_20260907.json',
               'diagnostics/live_beta0_interval_prediction.json',
               'diagnostics/live_beta0_interval_prediction_trace.json', ATTRIBUTE]
    before = [fingerprint(p) for p in sources]
    workbook = openpyxl.load_workbook(ATTRIBUTE, read_only=True, data_only=True)
    official = []
    for index, row in enumerate(workbook['Attributes'].values, 1):
        if row[0:2] == ('VehicleRouteStatic', 'RelFlow'):
            official.append({'sheet': 'Attributes', 'row': index, 'object': row[0],
                             'attribute': row[1], 'subattribute': row[6], 'default': float(row[14]),
                             'description': row[23]})
    workbook.close()
    assert len(official) == 1 and official[0]['default'] == 1.0
    tree = ET.parse(ROOT / NETWORK).getroot()
    tuning = adapter.load_optional_json(str(ROOT / CONFIG))
    adapter.install_config_switches(tuning)
    calibration = adapter.deep_update(load(CALIBRATION), tuning.get('calibration_override', {}))
    adapter.repo_imports(ROOT / 'vendor/NumSim-mine')
    cfg = adapter.build_config(ROOT / 'vendor/NumSim-mine', 150, 5400, 'fast-smoke',
                               calibration, tuning, local_observation=True, flagship=True)
    assert cfg.network.off_ramp_split_ratio == dict.fromkeys(GROUPS, 0.2)
    mapping = load(tuning['mapping_json'])
    split = load('outputs/freeway_ramp_split_v2_20260907.json')
    physical = load('diagnostics/live_beta0_interval_prediction.json')
    trace = load('diagnostics/live_beta0_interval_prediction_trace.json')['accepted_flow_trace']
    model = {row['group']: row for row in physical['offramps']}
    rows, details = [], {}
    for group, (decision_id, direct, signal) in GROUPS.items():
        decision = tree.find(f".//vehicleRoutingDecisionStatic[@no='{decision_id}']")
        chain = mapping['freeway_model_links']['FW_' + group[-1]]
        offsets = dict(zip(map(str, chain['chain_links']), chain['chain_offsets_m']))
        decision_pos = offsets[decision.get('link')] + float(decision.get('pos'))
        routes = []
        for route in decision.findall('./vehRoutSta/vehicleRouteStatic'):
            path = [decision.get('link')]
            path += [x.get('key') for x in route.findall('./linkSeq/intObjectRef')]
            if path[-1] != route.get('destLink'):
                path.append(route.get('destLink'))
            raw = route.get('relFlow')
            if raw == '':
                weight = official[0]['default']
            else:
                match = re.fullmatch(r'2 0:([0-9.]+)', raw)
                assert match, (decision_id, raw)
                weight = float(match[1])
            kind = 'direct' if direct in path else 'signal' if signal in path else 'through'
            routes.append({'route': route.get('no'), 'kind': kind, 'raw_relFlow': raw,
                           'default_used': raw == '', 'weight': weight, 'full_path': path,
                           'destination_link': route.get('destLink'), 'destination_pos_m': float(route.get('destPos'))})
        assert len(routes) == 3 and {r['kind'] for r in routes} == {'direct', 'signal', 'through'}
        weights = {r['kind']: r['weight'] for r in routes}
        total_ratio = (weights['direct'] + weights['signal']) / sum(weights.values())
        predicted = model[group]['predicted_fw_to_off_group_veh']
        accepted = sum(t['diagnostics']['offramp_flow_' + group] * 10 / 3600 for t in trace)
        blocked = sum(t['diagnostics']['offramp_blocked_flow_' + group] * 10 / 3600 for t in trace)
        assert math.isclose(predicted, accepted, abs_tol=1e-9) and blocked == 0
        assert model[group]['scheduled_rejected_veh'] == 0
        branches = [r for r in split['off_ramps'] if r['legacy_group'] == group]
        merges = [r for r in split['on_ramps'] if r['direction'] == 'FW_' + group[-1]
                  and decision_pos < r['chain_pos_m'] < max(z['chain_pos_m'] for z in branches)]
        observed = sum(b['measured_connector']['observed_entries_veh'] for b in model[group]['physical_branches'])
        row = {'group': group, 'decision': decision_id, 'signal_weight': weights['signal'],
               'direct_weight': weights['direct'], 'through_weight': weights['through'],
               'total_off_prior': total_ratio, 'current_total_ratio': 0.2,
               'model_cell': model[group]['group_assigned_model_cell'],
               'model_accepted_veh': predicted, 'model_gross_sending_integral_veh': accepted / .2,
               'observed_branch_entries_veh': observed, 'blocked_veh': blocked,
               'fixed_q_algebra_native_weights_veh': total_ratio * accepted / .2}
        rows.append(row)
        details[group] = {'decision_attributes': decision.attrib, 'decision_chain_pos_m': decision_pos,
                          'routes': routes, 'physical_branches': branches,
                          'merges_after_decision_before_last_branch': merges,
                          'observed_branch_rows': model[group]['physical_branches']}
    assert sum(r['observed_branch_entries_veh'] for r in rows) == 295
    assert [fingerprint(p) for p in sources] == before
    output = {'schema': 'total-offramp-ratio-audit/v1', 'sources': before,
              'official_default': official[0], 'effective_cfg_total_ratios': cfg.network.off_ramp_split_ratio,
              'table': rows, 'native_routes_and_order': details,
              'source_link_observations': {k: physical['physical_link_measurement'][k] for k in ['2', '26', '119', '120']},
              'arithmetic_only_warning': 'Fixed-q multiplication is not a rollout, calibration, or causal decomposition: changing split changes downstream states. Native weights condition on decision cohort.',
              'checks': {'sources_unchanged': True, 'all_15_steps_integrated': len(trace) == 15,
                         'flow_trace_matches_schedule': True, 'no_receiving_rejection': True,
                         'full_paths_include_destination': True}}
    assert output['checks']['all_15_steps_integrated']
    target = ROOT / 'diagnostics/total_offramp_ratio_audit.json'
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with target.with_suffix('.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({'rows': rows, 'checks': output['checks']}, indent=2))


if __name__ == '__main__':
    main()
