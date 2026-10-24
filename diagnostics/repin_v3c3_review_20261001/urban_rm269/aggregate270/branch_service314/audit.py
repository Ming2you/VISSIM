"""Bounded read-only diagnosis from retained past tracks and two saved forecasts.

No FZP scan, parameter fit, prediction, optimizer, or native execution.
"""
from collections import defaultdict
from pathlib import Path
import gzip
import hashlib
import json
import pickle
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
A = HERE.parent
ROOT = HERE.parents[4]
PAST = Path('E:/VISSIM_analysis/20261010_sc107_composition312')
FORECAST = Path('E:/VISSIM_analysis/20261010_sc108_geometry311/forecast2400')
PINS = {}


def read(path):
    path = Path(path)
    data = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(data).hexdigest()
    return data


def main():
    assert not (HERE / 'assessment.json').exists(), 'Reuse completed diagnosis'
    cfg, state, _ = pickle.loads(read(A / 'citysplit287/forecast2400/initial.pickle'))
    spec = next(x for x in cfg.network.route_choice_corridor['corridors'] if x['decision'] == '1129')
    branch = spec['branches']['1']
    assert cfg.simulation.T_f_sec == 5 and cfg.simulation.T_u_sec == 10
    assert branch['mode'] == 'free_storage' and branch['connector'] == '10621'
    assert branch['lanes'] == 2 and not spec.get('native_fixed_service')
    rate = spec['per_lane_capacity_veh_h'] * branch['lanes']

    completion = json.loads(read(PAST / 'retained_completion.json'))
    data = read(completion['cache'])
    assert hashlib.sha256(data).hexdigest() == completion['cache_sha256']
    past = json.loads(gzip.decompress(data))
    network_path = next(p for p in past['source_pins'] if p.endswith('.inpx'))
    network = read(network_path)
    assert hashlib.sha256(network).hexdigest() == past['source_pins'][network_path]
    conn = ET.fromstring(network).find("./links/link[@no='10621']")
    assert conn.find('fromLinkEndPt').get('lane').split()[0] == '56'
    assert len(conn.findall('./lanes/lane')) == branch['lanes']

    crossings = []
    for vehicle, rows in past['tracks'].items():
        for before, after in zip(rows, rows[1:]):
            if (before['link'] == '56' and after['link'] == '10621'
                    and 1800 <= before['sec'] < after['sec'] < 2250):
                assert 0 < after['sec'] - before['sec'] <= 5.00001
                crossings.append(dict(vehicle=vehicle, low_sec=before['sec'], high_sec=after['sec']))
    assert len({x['vehicle'] for x in crossings}) == len(crossings)
    floor = len(crossings) * 3600 / 450
    assert floor > rate

    results = {}
    for arm in ('hold', 'city'):
        response = json.loads(gzip.decompress(read(FORECAST / (arm + '.response.json.gz'))))
        service = [x for x in response['resource_allocations']
                   if x['kind'] == 'route_choice_branch_service'
                   and x['resource'] == '1129:branch:bypass']
        receiving = [x for x in response['resource_allocations']
                     if x['kind'] == 'route_choice_receiving'
                     and x['resource'] == 'storage:SC1004_to_SC107']
        assert len(service) == len(receiving) == 44
        assert all(abs(x['available_veh'] - rate * 10 / 3600) < 1e-10 for x in service)
        assert all(abs(x['available_veh'] - x['accepted_total_veh']) < 1e-10 for x in service)
        assert all(x['available_veh'] > x['accepted_total_veh'] + 1 for x in receiving)
        incoming = defaultdict(float)
        for row in response['transfers']:
            if row['target'] == 'storage:SC1004_E_choice' and row['source'] != row['target']:
                incoming[row['route_key']] += row['vehicles']
        results[arm] = dict(
            incoming_by_route=dict(incoming), incoming_total=sum(incoming.values()),
            bypass_accepted=sum(x['accepted_total_veh'] for x in service),
            active_intervals=len(service), binding_intervals=len(service), receiving_binding_intervals=0)
    assert abs(results['hold']['bypass_accepted'] - results['city']['bypass_accepted']) < 1e-10
    assert results['hold']['incoming_total'] - results['city']['incoming_total'] > 20
    for rel in ('evaluation/controllers/runtime_setup.py',
                'evaluation/controllers/vissim_stackelberg_adapter.py',
                'evaluation/controllers/route_choice_corridor.py',
                'evaluation/controllers/aggregate_route_corridors.py',
                'diagnostics/repin_v3c3_review_20261001/upstream_worklog/02_urban_b2/diag_c3_r2/U7.md'):
        read(ROOT / rel)
    read(__file__)
    report = dict(
        status='complete_confirmed_bypass_service_bound_masks_upstream_response',
        goal_complete=False, production_adopted=False,
        clock=dict(freeway_sec=5, urban_sec=10),
        per_lane_model_rate_veh_h=spec['per_lane_capacity_veh_h'],
        bypass_model_rate_veh_h=rate,
        past_window_sec=[1800, 2250], certain_observed_crossings=crossings,
        past_sample_achieved_rate_lower_bound_veh_h=floor,
        model_full450_max_departures=rate * 450 / 3600,
        results=results, source_pins=PINS,
        budget=dict(new_predictions=0, fits=0, native_runs=0, fzp_passes=0, optimizers=0),
        limits=[
            'Past tracks select vehicles that later crossed SC107 heads;113 is a witnessed lower bound, not all bypass traffic or a saturation estimate.',
            'Past1800..2250 disproves the413veh/h physical maximum. It is not measured2400..2850 inflow or a future boundary input.',
            'An artificial active cap masks model upstream-response differences; removing it does not by itself prove whole-Omega gain accuracy.',
            'SC107 future route/head access mismatch and SC1005 supply need separate qualification.',
            'Immutable native queue unchanged; no fresh runtime-status claim.'])
    (HERE / 'assessment.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: report[k] for k in ('status', 'bypass_model_rate_veh_h',
          'past_sample_achieved_rate_lower_bound_veh_h', 'model_full450_max_departures', 'results', 'budget')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
