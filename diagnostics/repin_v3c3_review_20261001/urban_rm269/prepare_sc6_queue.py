"""Prepare one geometry-only queue-attribution diagnostic; no fitted rates."""
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / 'sc6_queue'
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def save(name, value):
    path = OUT / name
    assert not path.exists(), path
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')


def main():
    assert not OUT.exists(), 'Preserve existing diagnostic preparation'
    base_path = HERE / 'config_candidate.json'
    cfg = read(base_path)
    contract_path = ROOT / cfg['urban']['queue']['head_lane_contract']
    contract = read(contract_path)
    authority_path = HERE / 'selection2400/network.json'
    authority = read(authority_path)
    old_authority_path = ROOT / contract['authority']['path']
    assert sha(old_authority_path) == contract['authority']['sha256']
    old = read(old_authority_path)['network']
    geometry_path = ROOT / contract['network']['path']
    assert sha(geometry_path) == contract['network']['sha256']
    tree = ET.parse(geometry_path)
    links = {x.get('no'): x for x in tree.findall('./links/link')}
    # Preserve every previous movement and its physical evidence, including
    # earlier SC101/40 and upstream-stopline repairs.
    for name, row in contract['movements'].items():
        assert all(authority['urban_movements'][name][k] == v for k, v in row['expected_spec'].items()), name
        for net in (old, authority):
            turns = [t for t in net['control_area_routes']['movement:' + name]['physical_turns']
                     if t.get('source_evidence', {}).get('canonical_approach_leg')
                     and t['from_link'] == row['from_link']]
            assert len(turns) == 1, name
            assert all(turns[0][k] == row[k] for k in ('from_link', 'connector', 'to_link')), name
    original_rows = copy.deepcopy(contract['movements'])
    added = {}
    for name, spec in authority['urban_movements'].items():
        if not name.startswith(('SC6_S_SC12_', 'SC6_E_SC104_')):
            continue
        turns = [t for t in authority['control_area_routes']['movement:' + name]['physical_turns']
                 if t.get('source_evidence', {}).get('canonical_approach_leg')]
        assert len(turns) == 1, name
        turn = turns[0]
        assert turn['from_link'] in ('1210018302', '1220021201')
        connector = links[turn['connector']]
        start, end = connector.find('fromLinkEndPt'), connector.find('toLinkEndPt')
        assert start.get('lane').split()[0] == turn['from_link']
        assert end.get('lane').split()[0] == turn['to_link']
        first = int(start.get('lane').split()[1])
        added[name] = dict(expected_spec={k: spec[k] for k in ('signal', 'phase', 'origin', 'receiving_link', 'kind')},
                           **{k: turn[k] for k in ('from_link', 'connector', 'to_link')},
                           lanes=list(range(first, first + len(connector.findall('./lanes/lane')))))
    assert len(added) == 6 and not (set(added) & set(original_rows))
    OUT.mkdir()
    save('authority.json', dict(network=authority, source=str(authority_path.relative_to(ROOT)), source_sha256=sha(authority_path)))
    contract['authority'] = dict(path=str((OUT / 'authority.json').relative_to(ROOT)), sha256=sha(OUT / 'authority.json'))
    contract['movements'].update(added)
    contract['scope'] += ' Add only SC6 south/east head connector-lane queue support; preserve shared-lane uncertainty, no service or arrival fit.'
    save('head_lane_support.json', contract)
    cfg['urban']['queue']['head_lane_contract'] = str((OUT / 'head_lane_support.json').relative_to(ROOT))
    save('config.json', cfg)
    pins = [base_path, contract_path, authority_path, old_authority_path, geometry_path,
            Path(__file__), ROOT / 'evaluation/controllers/observation_projection.py',
            ROOT / 'evaluation/controllers/vissim_stackelberg_adapter.py',
            HERE.parent / 'urban260/verify.py', OUT / 'config.json', OUT / 'head_lane_support.json', OUT / 'authority.json']
    save('plan.json', dict(status='prepared_initialization_only', candidate_count=1, coefficient_fits=0,
        states=[2400, 3300], initializations_max=2, forecasts_consumed=0,
        possible_followup='Only if initialization proves a physical allocation error: fixed-command forecasts, no parameter grid.',
        native_runs=0, full_optimizations=0, adopted=False,
        change='Existing head-phase queue attribution extended to two observed approaches, with existing coefficients/arrivals/services/commands unchanged.',
        original_contract_rows_preserved=len(original_rows), added=added,
        source_pins={str(p): sha(p) for p in pins},
        claude_review='upstream_worklog/02_urban_b2/diag_c3/C3_DIAGNOSIS.md: arrival/discharge error cancellation at SC6_S; reuse prior SC101 queue support method.',
        success='Initial physical stock conserved per link and whole Omega; only observed lane-supported queues change. This is not a native/control-gain qualification.'))
    print(json.dumps(dict(output=str(OUT), added=added), ensure_ascii=False))


if __name__ == '__main__':
    main()
