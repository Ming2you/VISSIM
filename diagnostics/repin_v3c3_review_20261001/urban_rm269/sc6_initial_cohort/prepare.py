"""Reuse the reviewed SC6 observation projection on the current fixed baseline.

No new travel-time formula, rate fit, native run or optimizer change.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
H = HERE.parent
ROOT = HERE.parents[3]
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write(name, data):
    p = HERE / name
    assert not p.exists(), str(p)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf8')


def main():
    assert read(HERE / 'assessment.json')['status'] == 'closed_initial_cohort_diagnosis_complete'
    config = read(H / 'connector_lane/config.json')
    original_contract = ROOT / config['urban']['arrival']['kinematic_contract']
    contract = read(original_contract)
    old_sources = set(contract['sources'])
    source = 'SC12_to_SC6'
    assert source not in old_sources
    contract['sources'][source] = read(H / 'arrival_head/contract.json')['sources'][source]
    assert set(contract['sources']) == old_sources | {source}
    contract['scope'] = 'Existing66 projection plus already reviewed SC6 terminal road only. Current lane/position/speed; no native future labels, no SC101 projection or new head rates.'
    config['urban']['arrival']['kinematic_contract'] = (HERE / 'contract.json').relative_to(ROOT).as_posix()
    write('contract.json', contract)
    write('config.json', config)

    # Reuse the complete canonical fixed-action harness, retaining the same
    # receiving/service candidates. Only the initialization assertions differ.
    harness = (H / 'sc101_recombined/forecast.py').read_text(encoding='utf8')
    edits = {
        "choices=['sc101_recombined'], default='sc101_recombined'": "choices=['sc6_initial_cohort'], default='sc6_initial_cohort'",
        "tuning = H / 'connector_lane/config.json'": "tuning = HERE / 'config.json'",
        "            fields=('urban_movement_queue','urban_link_storage','ramp_queue','freeway_density','freeway_speed','urban_arrival_buffer','boundary_queue','urban_queue')": "            fields=('urban_link_storage','ramp_queue','freeway_density','freeway_speed','boundary_queue','urban_queue')",
        "            save('initialization_verification.json',dict(status='passed',unchanged_state_fields=fields,candidate='finite_connector_stages',changed_aliases=['urban_storage_release_buffer','known_legsplit_route_state'],new_initial_stock=0))": """            source = 'SC12_to_SC6'
            moves = {m for m, row in cfg.network.urban_movements.items() if row.get('origin') == source}
            for field, allowed in (('urban_movement_queue', moves), ('urban_arrival_buffer', {source})):
                new = json.loads(json.dumps(getattr(state, field)))
                assert {k:v for k,v in new.items() if k not in allowed} == {k:v for k,v in old_state[field].items() if k not in allowed}, field
            qnew = sum(state.urban_movement_queue[m] for m in moves)
            qold = sum(old_state['urban_movement_queue'][m] for m in moves)
            assert abs(qnew-qold) < 1e-7
            assert abs(sum(state.urban_arrival_buffer[source].values())-sum(old_state['urban_arrival_buffer'][source].values())) < 1e-7
            tags = state.gate_initial_route_tags[source]
            assert all(set(row) <= moves for row in tags.values())
            save('initialization_verification.json',dict(status='passed',unchanged_state_fields=fields,candidate='existing_SC6_current_cohort_projection',new_initial_stock=0,queue_total_unchanged=qnew,tagged_residual=sum(sum(row.values()) for row in tags.values()),future_destination_inputs=False))""",
        "scope='Spatial receiving diagnostic plus previously audited SC101 straight service ceiling after SC1 supply repair. Same state, fixed actual commands, receiving constraints,450s horizon. No new fit, native, optimizer, or production change.'": "scope='Existing SC6 terminal-road current-lane/position projection added to fixed sc101_recombined diagnostic baseline. Same total initial stock, head service, spatial receiving, controls, future inputs and450s horizon. No new fit, native or optimizer.'"
    }
    for before, after in edits.items():
        assert harness.count(before) == 1, before
        harness = harness.replace(before, after)
    p = HERE / 'forecast.py'
    assert not p.exists()
    p.write_text(harness, encoding='utf8')
    pins = dict(read(H / 'sc101_recombined/plan_at_execution.json')['source_pins'])
    for p in (Path(__file__), HERE / 'forecast.py', HERE / 'assessment.json',
              HERE / 'config.json', HERE / 'contract.json', original_contract,
              H / 'arrival_head/contract.json', ROOT / 'evaluation/controllers/observation_projection.py'):
        pins[str(p)] = sha(p)
    for p, digest in pins.items():
        assert sha(Path(p)) == digest, p
    plan = dict(status='prepared_not_executed', source_pins=pins,
        hypothesis='Current SC6 residual is reallocated by global beta even though most initial left vehicles are already segregated into lane4 queue. Reuse current-lane projection, retaining uncertainty for upstream vehicles.',
        budget=dict(pair450=2, conditional3300_150=1, new_fits=0, full_ad=0, full_sdmpc=0, native=0),
        baseline='sc101_recombined; exact same physical candidate and commands',
        success='SC6 phase discharge/current stock improves, paired Omega gain error does not worsen, conservation and same caps remain feasible. Joint sign still required for overall control qualification.',
        condition3300='Paired SC6 phase absolute error improves by at least10percent and wholeOmega delta error does not worsen; same observed state only, no new calibration.',
        stop='No new initial-route fractions or rates fitted to observed future crossings; preserve result and reassess if unsupported.',
        priority='Calibration/control response first, full SDMPC wall optimization after.')
    write('plan.json', plan)
    write('plan_at_execution.json', plan)
    write('preflight.json', dict(status='passed', pins_verified=len(pins),
        config_only_changed_key='urban.arrival.kinematic_contract', added_source=source,
        prior_source_set=sorted(old_sources), projection_implementation_unchanged=True))
    print('Prepared two fixed450 forecasts and one conditional150 check; no new fitted parameters.')


if __name__ == '__main__':
    main()
