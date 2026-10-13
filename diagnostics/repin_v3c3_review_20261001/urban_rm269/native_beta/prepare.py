"""Repair two complete native destination priors; no parameter fitting."""
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
H = HERE.parent
ROOT = HERE.parents[3]
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    evidence = H.parent / 'sc105_supply/physical_routes.json'
    base = H / 'sc6_queue/service_config.json'
    state_network = H / 'selection2400/network.json'
    document, config, net = read(evidence), read(base), read(state_network)
    groups = {
        'SC12_S_SC16': dict(decision='34', origin='SC16_to_SC12', signal='SC12',
            stopline='1210012700', route_to_movement={
                '34:1': 'SC12_S_SC16_to_W_SC11', '34:2': 'SC12_S_SC16_to_N_SC6',
                '34:3': 'SC12_S_SC16_to_E_SC106'}),
        'SC16_S_SC109': dict(decision='284', origin='SC109_to_SC16', signal='SC16',
            stopline='1210009503', route_to_movement={
                '284:1': 'SC16_S_SC109_to_W_SC7', '284:2': 'SC16_S_SC109_to_N_SC12',
                '284:3': 'SC16_S_SC109_to_E'}),
    }
    for name, row in groups.items():
        assert name not in document['native_choice_groups']
        row['expected_specs'] = {m: {k: net['urban_movements'][m][k] for k in
            ('kind', 'origin', 'signal', 'destination', 'receiving_link')}
            for m in row['route_to_movement'].values()}
        row['rationale'] = ('Use the complete pinned native decision before service estimation and state projection. '
            'The old routing table reserved mass for phantom aliases and then merged them into physical turns. '
            'No fitted rate, total demand change, future observation or synthetic inventory.')
    document['native_choice_groups'].update(groups)
    config['urban']['movements']['physical_route_topology'] = (HERE/'physical_routes.json').relative_to(ROOT).as_posix()
    for name, data in [('physical_routes.json', document), ('config.json', config)]:
        dest = HERE/name
        assert not dest.exists(), dest
        dest.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    pins = {str(p): sha(p) for p in (Path(__file__), evidence, base, state_network,
        ROOT/document['network']['path'], ROOT/'evaluation/controllers/physical_movement_routes.py',
        HERE/'physical_routes.json', HERE/'config.json')}
    plan = dict(status='prepared_not_validated', groups=list(groups), source_pins=pins,
        base_config=str(base), config=str(HERE/'config.json'), fit_coefficients=0,
        max_forecasts=3, forecasts_completed=0, full_selections=0, native_runs=0,
        scope=['Canonical initialization2400 and unused3300, exact physical stock preservation',
            'Two fixed450 hold/selected forecasts at2400 and one fixed150 applied forecast at3300',
            'Reuse prior queue-service forecasts; no optimizer, future state input or FZP rescan'],
        success='Native routing agreement and improved observed response, without declaring control benefit from routing alone.',
        runtime_gate='Complete bounded calibration/control qualification before full SDMPC wall-time comparison.')
    (HERE/'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(status='prepared', groups=list(groups), forecasts=0)))


if __name__ == '__main__':
    main()
