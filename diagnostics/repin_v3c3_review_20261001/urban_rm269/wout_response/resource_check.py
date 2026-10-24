"""Saved-response attribution only; no new prediction or controller change."""
import ctypes
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'sc1_supply/forecast2400'
PINS = {}


def read(path, compressed=False):
    raw = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if compressed else raw)


def main():
    out = HERE / 'resource_check.json'
    assert not out.exists()
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    net = read(BASE / 'network.json')
    state = read(BASE / 'state.json')
    assessment = read(HERE / 'assessment_integer_ids.json')
    local = net['known_legsplit_routes']['entry_lane_receiving']
    occupied = Counter()
    for c in state['known_legsplit_route_state']['cohorts']:
        tag = c.get('lane68')
        if tag and (c['target'] in (local['ramp'], 'unknown') or c.get('local68_queue') or 2400 < tag['exit_step']):
            for lane, share in tag['shares'].items():
                occupied[lane] += c['vehicles'] * share
    native_initial = assessment['arms']['hold'][0]['native']['initial']
    initial = []
    for lane, cap in local['road_capacity_veh'].items():
        n = native_initial['lanes'].get('68:' + lane, 0)
        initial.append(dict(lane=lane, physical_68_stock=n,
            model_68_reserved_stock=occupied[lane], other_location_reservation=occupied[lane]-n,
            road_capacity=cap, physical_unused_room=max(0, cap-n),
            model_unused_room=max(0, cap-occupied[lane])))
    arms = {}
    movements = local['incoming']
    for arm in ('hold', 'selected'):
        response = read(BASE / (arm + '.response.json.gz'), True)
        rows = {}
        for r in response['resource_allocations']:
            if r['resource'] in movements and r['kind'] in ('urban_movement_stock', 'urban_movement_intended_limit'):
                rows.setdefault((r['resource'], r['start_sec']), {})[r['kind']] = r
        blocks = []
        for start in (2400, 2550, 2700):
            values = {}
            for m in movements:
                totals = Counter()
                for t in range(start, start+150):
                    rr = rows[m, t]
                    q = rr['urban_movement_stock']['available_veh']
                    offered = rr['urban_movement_intended_limit']['available_veh']
                    accepted = rr['urban_movement_intended_limit']['accepted_total_veh']
                    assert -1e-8 <= accepted <= offered+1e-8 <= q+2e-8
                    totals['offered'] += offered
                    totals['accepted'] += accepted
                    totals['rejected_after_initial_request'] += offered-accepted
                    if offered > 1e-8:
                        totals['positive_request_steps'] += 1
                        if offered-accepted > 1e-8:
                            totals['limited_request_steps'] += 1
                values[m] = dict(totals)
            blocks.append(dict(start_sec=start, movements=values))
        arms[arm] = blocks
        del response
    PINS[str(Path(__file__))] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result = dict(status='complete', initial_lane_reservation=initial, arms=arms,
        new_predictions=0, production_edits=0, source_pins=PINS,
        limits=['Offered-minus-accepted also includes intervening shared-head and aggregate receiving limits; not all rejection is uniquely caused by the68 gate.',
                'Connector vehicles reserve future road space intentionally; this proves spatial compression, not that all extra native service is usable without finite connector and road staging.',
                'Physical unused room is geometric stock capacity, not a lateral gap or guaranteed receiving flow.'])
    out.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='source_pins'}, indent=2))


if __name__ == '__main__':
    main()
