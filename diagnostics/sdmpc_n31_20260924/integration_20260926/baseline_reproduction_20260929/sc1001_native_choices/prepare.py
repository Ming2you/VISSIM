"""Bind three selected native decisions through the existing choice contract."""
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
I = HERE.parents[1]
ROOT = I.parents[2]


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    base_path = I/'baseline_reproduction_20260929/ramp_entry_space/peeloff10121/candidate_config.json'
    cfg = read(base_path)
    evidence_path = ROOT/cfg['urban']['movements']['physical_route_topology']
    doc = read(evidence_path)
    network_path = ROOT/doc['network']['path']
    assert sha(network_path) == doc['network']['sha256']
    tree = ET.parse(network_path).getroot()
    decisions = {d.get('no'): d for d in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')}
    specs = cfg['config_overrides']['network']['urban_movements']
    plans = [
        ('N_SC2002', '1116', '37', ['E_SC1002', 'S_SC1003', 'W_RAMP']),
        ('E_SC1002', '1118', '29', ['S_SC1003', 'W_RAMP', 'N_SC2002']),
        ('S_SC1003', '1119', '40', ['W_RAMP', 'N_SC2002', 'E_SC1002']),
    ]
    audit = {}
    for approach, decision_id, link, exits in plans:
        d = decisions[decision_id]
        assert d.get('link') == link and d.get('combineStaRoutDec') == 'true'
        members = {}; expected = {}
        for rid, exit_name in enumerate(exits, 1):
            name = f'SC1001_{approach}_to_{exit_name}'
            original = name.replace('_to_W_RAMP', '_to_W')
            source = specs[original]
            members[f'{decision_id}:{rid}'] = name
            expected[name] = {k:source[k] for k in ('kind', 'origin', 'signal', 'phase', 'destination', 'receiving_link')}
        row = dict(decision=decision_id, origin=source['origin'], signal='SC1001', stopline=link,
                   route_to_movement=members, expected_specs=expected,
                   rationale='Selected native choice replaces legacy measured beta; preserves total approach demand. Downstream1137 remains separately modeled.')
        doc['native_choice_groups'][f'SC1001_{approach}'] = row
        entry = []
        for connector in tree.findall('./links/link'):
            end = connector.find('toLinkEndPt')
            if end is not None and end.get('lane').split()[0] == link:
                assert float(end.get('pos')) < float(d.get('pos'))
                entry.append(dict(connector=connector.get('no'), **end.attrib))
        inputs = [x.attrib for x in tree.findall('./vehicleInputs/vehicleInput') if x.get('link') == link]
        assert not inputs
        other_decisions = [x for x in decisions.values() if x.get('link') == link and x is not d]
        assert all(not x.findall('./vehRoutSta/vehicleRouteStatic') for x in other_decisions)
        audit[approach] = dict(native_decision=dict(d.attrib), entries=entry, inputs=inputs,
                               empty_other_decisions=[x.get('no') for x in other_decisions],
                               route_rows=[dict(x.attrib) for x in d.findall('./vehRoutSta/vehicleRouteStatic')])
    candidate = copy.deepcopy(cfg)
    candidate['urban']['movements']['physical_route_topology'] = str((HERE/'physical_routes.json').relative_to(ROOT)).replace('\\','/')
    protocol = dict(previous_goal_turn='no_progress: existing-result explanation only; no new evidence or state change',
                    base_config=str(base_path), base_config_sha256=sha(base_path),
                    previous_evidence=str(evidence_path), previous_evidence_sha256=sha(evidence_path),
                    network=doc['network'], source_audit=audit,
                    core_sha256={name:sha(ROOT/name) for name in [
                        'evaluation/controllers/physical_movement_routes.py', 'evaluation/controllers/runtime_setup.py',
                        'evaluation/controllers/lane_plant_runtime.py','evaluation/controllers/area_freeway_accounting.py',
                        'evaluation/controllers/freeway_fd.py','evaluation/controllers/vissim_stackelberg_adapter.py']},
                    planned_forecasts=6, new_native=0, coefficient_fit=False, production_adopted=False,
                    future_observation_input=False,
                    comparison='same seed47@2700 hold/release and seed43@2250 NC/RM/VSL/both commands, 450s; full Omega plus tracked outside diagnostic')
    for name, value in [('physical_routes.json',doc),('candidate_config.json',candidate),('protocol.json',protocol)]:
        path=HERE/name
        assert not path.exists(), path
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(groups=list(doc['native_choice_groups']),audit=audit),ensure_ascii=False,indent=2))


if __name__ == '__main__':
    prepare()
